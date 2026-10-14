"""Generic 5-stage fallback bypasser chain for uncatalogued or unknown shorteners."""

import re
import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import httpx

from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url, get_default_headers
from utils.safety import is_dangerous_url
from config import ENABLE_PLAYWRIGHT, PLAYWRIGHT_TIMEOUT_MS

logger = logging.getLogger(__name__)


class GenericBypasser(BaseBypasser):
    name = "Generic Fallback"
    priority = 0  # Evaluated last
    domains = ["*"]

    def match(self, url: str) -> bool:
        # Matches any valid HTTP/HTTPS URL
        try:
            p = urlparse(url)
            return p.scheme in ("http", "https") and bool(p.netloc)
        except Exception:
            return False

    async def bypass(self, url: str) -> str:
        """Executes the 5-stage fallback chain sequentially."""
        logger.info("Starting generic fallback chain for %s", url)

        # -------------------------------------------------------------
        # STAGE 1: Standard HTTP Redirect Tracking
        # -------------------------------------------------------------
        stage1_result = await self._stage1_http_redirect(url)
        if stage1_result and stage1_result != url:
            logger.info("Generic Stage 1 succeeded: %s -> %s", url, stage1_result)
            return stage1_result

        # -------------------------------------------------------------
        # STAGE 2: HTML Meta-Refresh and Inline JavaScript Redirects
        # -------------------------------------------------------------
        stage2_result = await self._stage2_meta_and_js_redirect(url)
        if stage2_result and stage2_result != url:
            logger.info("Generic Stage 2 succeeded: %s -> %s", url, stage2_result)
            return stage2_result

        # -------------------------------------------------------------
        # STAGE 3: Cloudflare / Anti-Bot Bypass via curl_cffi / cloudscraper
        # -------------------------------------------------------------
        stage3_result = await self._stage3_anti_bot_evasion(url)
        if stage3_result and stage3_result != url:
            logger.info("Generic Stage 3 succeeded: %s -> %s", url, stage3_result)
            return stage3_result

        # -------------------------------------------------------------
        # STAGE 4: Automated Form-Based Token and Countdown Handler
        # -------------------------------------------------------------
        stage4_result = await self._stage4_form_countdown_flow(url)
        if stage4_result and stage4_result != url:
            logger.info("Generic Stage 4 succeeded: %s -> %s", url, stage4_result)
            return stage4_result

        # -------------------------------------------------------------
        # STAGE 5: Headless Browser (Playwright) Fallback
        # -------------------------------------------------------------
        if ENABLE_PLAYWRIGHT:
            stage5_result = await self._stage5_playwright_headless(url)
            if stage5_result and stage5_result != url:
                logger.info("Generic Stage 5 (Playwright) succeeded: %s -> %s", url, stage5_result)
                return stage5_result

        raise BypassError("All generic fallback mechanisms exhausted; link could not be unshortened.")

    # -------------------------------------------------------------
    # STAGE 1 Implementation
    # -------------------------------------------------------------
    async def _stage1_http_redirect(self, url: str) -> Optional[str]:
        try:
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            if resp.status_code == 404:
                raise LinkDeadError("Target URL returned 404 Not Found.")

            final_url = str(resp.url)
            # If final URL changed to a different domain or path
            if final_url != url and urlparse(final_url).netloc != urlparse(url).netloc:
                return final_url
        except LinkDeadError:
            raise
        except Exception as e:
            logger.debug("Stage 1 failed: %s", e)
        return None

    # -------------------------------------------------------------
    # STAGE 2 Implementation
    # -------------------------------------------------------------
    async def _stage2_meta_and_js_redirect(self, url: str) -> Optional[str]:
        try:
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # 1. Meta refresh
            meta_tag = soup.find("meta", attrs={"http-equiv": re.compile(r"^refresh$", re.I)})
            if meta_tag and meta_tag.get("content"):
                match = re.search(r'url\s*=\s*([^;]+)', meta_tag["content"], re.I)
                if match:
                    dest = match.group(1).strip("'\"")
                    resolved = urljoin(str(resp.url), dest)
                    if resolved != url:
                        return resolved

            # 2. JavaScript location redirects
            js_patterns = [
                r'(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
                r'(?:window\.)?location\.replace\s*\(\s*["\']([^"\']+)["\']\s*\)',
                r'var\s+(?:dest|target|redirect_url|link)\s*=\s*["\'](https?://[^"\']+)["\']',
            ]
            for pat in js_patterns:
                m = re.search(pat, html, re.I)
                if m:
                    candidate = m.group(1)
                    resolved = urljoin(str(resp.url), candidate)
                    if resolved != url:
                        return resolved
        except Exception as e:
            logger.debug("Stage 2 failed: %s", e)
        return None

    # -------------------------------------------------------------
    # STAGE 3 Implementation
    # -------------------------------------------------------------
    async def _stage3_anti_bot_evasion(self, url: str) -> Optional[str]:
        try:
            from curl_cffi.requests import AsyncSession
            async with AsyncSession(impersonate="chrome120") as s:
                resp = await s.get(url, allow_redirects=True)
                final_url = str(resp.url)
                if final_url != url and urlparse(final_url).netloc != urlparse(url).netloc:
                    return final_url
        except Exception:
            pass

        try:
            import cloudscraper
            loop = asyncio.get_running_loop()
            scraper = cloudscraper.create_scraper()
            resp = await loop.run_in_executor(None, lambda: scraper.get(url, allow_redirects=True))
            if str(resp.url) != url and urlparse(str(resp.url)).netloc != urlparse(url).netloc:
                return str(resp.url)
        except Exception as e:
            logger.debug("Stage 3 failed: %s", e)
        return None

    # -------------------------------------------------------------
    # STAGE 4 Implementation
    # -------------------------------------------------------------
    async def _stage4_form_countdown_flow(self, url: str) -> Optional[str]:
        try:
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            soup = BeautifulSoup(resp.text, "html.parser")
            form = soup.find(id="go-link") or soup.find("form")
            if not form:
                return None

            action = form.get("action") or ""
            target_post = urljoin(str(resp.url), action) if action else urljoin(str(resp.url), "/links/go")

            inputs = form.find_all("input")
            data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name") and inp.get("value")}

            # Wait short timer in case server enforces countdown
            await asyncio.sleep(3.0)

            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": str(resp.url),
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
            api_resp = await safe_fetch_url(target_post, method="POST", data=data, headers=headers)
            try:
                res_json = api_resp.json()
                if "url" in res_json and res_json["url"]:
                    return res_json["url"]
            except Exception:
                pass
        except Exception as e:
            logger.debug("Stage 4 failed: %s", e)
        return None

    # -------------------------------------------------------------
    # STAGE 5 Implementation
    # -------------------------------------------------------------
    async def _stage5_playwright_headless(self, url: str) -> Optional[str]:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=get_default_headers()["User-Agent"]
                )
                page = await context.new_page()

                # Navigate and wait for potential redirect or network idle
                try:
                    await page.goto(url, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT_MS)
                except Exception:
                    # Timeout or load error, check current page URL anyway
                    pass

                # Allow JS redirect timers up to 3 seconds
                await asyncio.sleep(3.0)

                final_url = page.url
                await browser.close()

                if final_url and final_url != url and not any(p in final_url for p in ["about:blank", "chrome-error:"]):
                    return final_url
        except Exception as e:
            logger.warning("Stage 5 (Playwright) failed: %s", e)
        return None
