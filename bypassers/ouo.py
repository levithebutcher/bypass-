"""Bypasser plugin for ouo.io and ouo.press shortlinks with reCAPTCHA v3 emulation."""

import re
import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import get_default_headers, safe_fetch_url


async def _solve_recaptcha_v3() -> str:
    """
    Simulates Google reCAPTCHA v3 invisible token exchange without browser.
    """
    anchor_url = (
        "https://www.google.com/recaptcha/api2/anchor?"
        "ar=1&k=6Lcr1ncUAAAAAH3cghg6cOTPGARa8adOf-y9zv2x&"
        "co=aHR0cHM6Ly9vdW8ucHJlc3M6NDQz&hl=en&v=pCoGBhjs9s8EhFOHJFe8cqis&size=invisible&cb=12345"
    )
    matches = re.findall(r"([api2|enterprise]+)/anchor\?(.*)", anchor_url)[0]
    base_url = f"https://www.google.com/recaptcha/{matches[0]}/"
    params = matches[1]

    # Get anchor page
    resp = await safe_fetch_url(f"{base_url}anchor?{params}", method="GET")
    token_match = re.search(r'"recaptcha-token"\s+value="(.*?)"', resp.text)
    if not token_match:
        raise BypassError("Failed to acquire reCAPTCHA v3 challenge token.")
    token = token_match.group(1)

    # Parse query params for reload payload
    param_dict = dict(pair.split("=") for pair in params.split("&"))
    post_data = {
        "v": param_dict.get("v", ""),
        "reason": "q",
        "c": token,
        "k": param_dict.get("k", ""),
        "co": param_dict.get("co", ""),
    }

    reload_resp = await safe_fetch_url(
        f"{base_url}reload?k={param_dict.get('k', '')}",
        method="POST",
        data=post_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    rresp_match = re.search(r'"rresp","(.*?)"', reload_resp.text)
    if not rresp_match:
        raise BypassError("Failed to extract reCAPTCHA v3 reload response.")
    return rresp_match.group(1)


class OuoBypasser(BaseBypasser):
    name = "Ouo"
    domains = ["ouo.io", "ouo.press"]

    async def bypass(self, url: str) -> str:
        # Standardize domain to ouo.press or ouo.io
        target_url = url.replace("ouo.press", "ouo.io")
        parsed = urlparse(target_url)
        link_id = parsed.path.rstrip("/").split("/")[-1]

        if not link_id:
            raise BypassError("Invalid ouo link structure.")

        # Try curl_cffi if available to bypass Cloudflare TLS fingerprints
        try:
            from curl_cffi.requests import AsyncSession
            use_curl_cffi = True
        except ImportError:
            use_curl_cffi = False

        if use_curl_cffi:
            return await self._bypass_curl_cffi(target_url, link_id)
        else:
            return await self._bypass_standard(target_url, link_id)

    async def _bypass_curl_cffi(self, url: str, link_id: str) -> str:
        from curl_cffi.requests import AsyncSession
        headers = {
            "authority": "ouo.io",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://www.google.com/",
            "upgrade-insecure-requests": "1",
        }

        async with AsyncSession(impersonate="chrome120") as session:
            resp = await session.get(url, headers=headers)
            if resp.status_code == 404:
                raise LinkDeadError("ouo link does not exist (404).")

            parsed = urlparse(url)
            next_url = f"{parsed.scheme}://{parsed.hostname}/go/{link_id}"

            for step in range(2):
                if resp.headers.get("Location"):
                    return resp.headers["Location"]

                soup = BeautifulSoup(resp.content, "html.parser")
                form = soup.find("form")
                if not form:
                    # Check for direct redirect header
                    if "Location" in resp.headers:
                        return resp.headers["Location"]
                    raise BypassError("Unable to locate ouo form on landing page.")

                inputs = form.find_all("input", {"name": re.compile(r"token$", re.I)})
                data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}
                
                # Solve reCAPTCHA v3
                try:
                    data["x-token"] = await _solve_recaptcha_v3()
                except Exception as e:
                    raise BypassError(f"Ouo captcha token acquisition failed: {e}")

                resp = await session.post(
                    next_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    allow_redirects=False,
                )

                if resp.headers.get("Location"):
                    return resp.headers["Location"]

                next_url = f"{parsed.scheme}://{parsed.hostname}/xreallcygo/{link_id}"

            if resp.headers.get("Location"):
                return resp.headers["Location"]

            raise BypassError("Could not extract destination from ouo response.")

    async def _bypass_standard(self, url: str, link_id: str) -> str:
        # Fallback using httpx
        resp = await safe_fetch_url(url, method="GET", follow_redirects=False)
        if resp.status_code == 404:
            raise LinkDeadError("ouo link does not exist (404).")

        parsed = urlparse(url)
        next_url = f"{parsed.scheme}://{parsed.hostname}/go/{link_id}"

        for step in range(2):
            if "location" in resp.headers:
                return resp.headers["location"]

            soup = BeautifulSoup(resp.text, "html.parser")
            form = soup.find("form")
            if not form:
                raise BypassError("Unable to locate ouo form on landing page.")

            inputs = form.find_all("input", {"name": re.compile(r"token$", re.I)})
            data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}
            data["x-token"] = await _solve_recaptcha_v3()

            resp = await safe_fetch_url(
                next_url,
                method="POST",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                follow_redirects=False,
            )

            if "location" in resp.headers:
                return resp.headers["location"]

            next_url = f"{parsed.scheme}://{parsed.hostname}/xreallcygo/{link_id}"

        if "location" in resp.headers:
            return resp.headers["location"]

        raise BypassError("Could not extract destination from ouo response.")
