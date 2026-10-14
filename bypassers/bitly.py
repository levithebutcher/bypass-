"""Bypasser plugin for bit.ly shortlinks."""

import httpx
from bypassers.base import BaseBypasser
from bypassers.exceptions import LinkDeadError, BypassError
from utils.http import safe_fetch_url


class BitlyBypasser(BaseBypasser):
    name = "Bit.ly"
    domains = ["bit.ly", "bitly.com", "bitly.is"]

    async def bypass(self, url: str) -> str:
        try:
            # Bit.ly returns 301 Redirect to destination
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            if resp.status_code == 404:
                raise LinkDeadError("Bit.ly link does not exist or was deleted.")
            final_url = str(resp.url)
            if final_url == url or "bitly.com" in final_url or "bit.ly" in final_url:
                # Sometimes bitly adds a warning page or preview
                raise BypassError("Bit.ly destination could not be resolved.")
            return final_url
        except httpx.HTTPError as e:
            raise BypassError(f"Network error while resolving Bit.ly: {e}")
