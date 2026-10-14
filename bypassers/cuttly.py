"""Bypasser plugin for cutt.ly shortlinks."""

import httpx
from bypassers.base import BaseBypasser
from bypassers.exceptions import LinkDeadError, BypassError
from utils.http import safe_fetch_url


class CuttlyBypasser(BaseBypasser):
    name = "Cutt.ly"
    domains = ["cutt.ly"]

    async def bypass(self, url: str) -> str:
        try:
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            if resp.status_code == 404:
                raise LinkDeadError("Cutt.ly link not found or expired.")
            final_url = str(resp.url)
            if "cutt.ly" in final_url and final_url == url:
                raise BypassError("Cutt.ly link could not be bypassed.")
            return final_url
        except httpx.HTTPError as e:
            raise BypassError(f"Network error while resolving Cutt.ly: {e}")
