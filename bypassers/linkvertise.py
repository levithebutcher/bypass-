"""Bypasser plugin for the Linkvertise network."""

import re
import json
import time
import base64
import logging
from urllib.parse import urlparse, parse_qs, unquote
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url, get_default_headers

logger = logging.getLogger(__name__)


def _decode_dynamic_r_param(url: str) -> str:
    """
    Decodes the ?r= base64 destination parameter found in Linkvertise dynamic links.
    e.g. https://link-to.net/123/456/dynamic?r=aHR0cHM6Ly9leGFtcGxlLmNvbQ==
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Check query param 'r'
    r_val = query_params.get("r", [None])[0]
    if not r_val:
        # Regex search in case of malformed query string
        m = re.search(r'[?&]r=([a-zA-Z0-9_\-+/=]+)', url)
        if m:
            r_val = m.group(1)

    if r_val:
        # Pad base64 if needed
        padding = len(r_val) % 4
        if padding:
            r_val += "=" * (4 - padding)
        try:
            decoded = base64.b64decode(r_val).decode("utf-8", errors="ignore")
            if decoded.startswith("http://") or decoded.startswith("https://"):
                return decoded
        except Exception:
            pass

    return ""


class LinkvertiseBypasser(BaseBypasser):
    name = "Linkvertise"
    domains = [
        "linkvertise.com", "linkvertise.net", "link-to.net",
        "up-to-down.net", "direct-link.net", "file-link.net",
        "link-center.net", "link-target.net", "link-hub.net",
    ]

    async def bypass(self, url: str) -> str:
        # 1. Fast Path: Check if this is a dynamic link with ?r= (Base64 target)
        dynamic_dest = _decode_dynamic_r_param(url)
        if dynamic_dest:
            logger.info("Decoded dynamic Linkvertise destination directly: %s", dynamic_dest)
            return dynamic_dest

        # 2. Extract Linkvertise link path: /<user_id>/<link_slug>
        clean_url = (
            url.replace("%3D", " ")
            .replace("&o=sharing", "")
            .replace("?o=sharing", "")
            .replace("dynamic?r=", "dynamic/?r=")
        )
        id_match = re.search(r"/\d+/[^/?#]+", clean_url)
        if not id_match:
            raise BypassError("Invalid Linkvertise URL format (could not identify link ID/path).")

        link_path = id_match.group(0)

        # 3. Native Linkvertise API via curl_cffi (AppleTV User-Agent impersonation)
        try:
            from curl_cffi.requests import AsyncSession
            headers = {
                "User-Agent": "AppleTV6,2/11.1",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            static_api = f"https://publisher.linkvertise.com/api/v1/redirect/link/static{link_path}"
            async with AsyncSession(impersonate="chrome120") as session:
                resp = await session.get(static_api, headers=headers, timeout=12)
                data = resp.json()

                if isinstance(data, dict):
                    if data.get("error") is True and "Not Found!" in data.get("messages", []):
                        raise LinkDeadError("This Linkvertise link does not exist or has been deleted (404 Not Found).")

                    link_info = data.get("data")
                    if isinstance(link_info, dict):
                        link_obj = link_info.get("link", {})
                        if link_obj.get("target_type") == "paste" and link_obj.get("raw"):
                            return link_obj["raw"]
                        if link_obj.get("url"):
                            return link_obj["url"]
        except LinkDeadError:
            raise
        except Exception as e:
            logger.debug("curl_cffi static Linkvertise check failed: %s", e)

        # 4. Automated Playwright Browser Solver (100% Free, Network-Intercepting)
        from config import ENABLE_PLAYWRIGHT, PLAYWRIGHT_HEADLESS, PLAYWRIGHT_TIMEOUT_MS
        if ENABLE_PLAYWRIGHT:
            logger.info("Engaging Playwright automated solver for Linkvertise: %s", url)
            try:
                playwright_dest = await self._solve_with_playwright(
                    url,
                    headless=PLAYWRIGHT_HEADLESS,
                    timeout_ms=PLAYWRIGHT_TIMEOUT_MS
                )
                if playwright_dest:
                    return playwright_dest
            except Exception as e:
                logger.warning("Playwright Linkvertise solver encountered an issue: %s", e)

        raise BypassError("Linkvertise link could not be bypassed automatically. Check if link is still valid.")

    async def _solve_with_playwright(self, url: str, headless: bool = True, timeout_ms: int = 25000) -> Optional[str]:
        """Automates Linkvertise navigation, ad modal dismissal, and network target interception."""
        import asyncio
        from playwright.async_api import async_playwright

        target_destination: Optional[str] = None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            # Prevent intrusive ad popups
            await page.add_init_script("""
                window.open = function() { return null; };
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            # Network response listener to catch Linkvertise's API target payload
            async def on_response(response):
                nonlocal target_destination
                try:
                    if "publisher.linkvertise.com/api/v1/redirect/link" in response.url:
                        res_data = await response.json()
                        if isinstance(res_data, dict):
                            target = res_data.get("data", {}).get("target")
                            if target and target.startswith("http"):
                                target_destination = target
                                return
                            link_url = res_data.get("data", {}).get("link", {}).get("url")
                            if link_url and link_url.startswith("http"):
                                target_destination = link_url
                                return
                except Exception:
                    pass

            page.on("response", on_response)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception as nav_err:
                logger.debug("Initial page navigation notice: %s", nav_err)

            # Polling loop: look for intercepted target, page redirects, and click through flow
            deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000)
            while asyncio.get_event_loop().time() < deadline:
                if target_destination:
                    break

                curr_url = page.url
                if curr_url and not any(d in curr_url for d in self.domains + ["about:blank"]):
                    if curr_url.startswith("http"):
                        target_destination = curr_url
                        break

                # 1. Click "Free Access" buttons if present
                try:
                    btn = page.locator("button:has-text('Free Access'), div:has-text('Free Access with Ads'), button:has-text('Direct Access'), a:has-text('Free Access')").first
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(1.0)
                except Exception:
                    pass

                # 2. Click Close / Dismiss on article discovery modal
                try:
                    close_btn = page.locator("[class*='close'], button:has-text('I have read'), svg[data-icon='xmark'], button:has-text('Dismiss')").first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await asyncio.sleep(1.0)
                except Exception:
                    pass

                # 3. Click Continue / Get Link
                try:
                    cont_btn = page.locator("button:has-text('Continue'), button:has-text('Get Link'), a:has-text('Continue')").first
                    if await cont_btn.is_visible():
                        await cont_btn.click()
                        await asyncio.sleep(1.0)
                except Exception:
                    pass

                await asyncio.sleep(1.5)

            await browser.close()
            return target_destination
