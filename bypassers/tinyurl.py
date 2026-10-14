"""Bypasser plugin for tinyurl.com shortlinks."""

import httpx
from bypassers.base import BaseBypasser
from bypassers.exceptions import LinkDeadError, BypassError
from utils.http import safe_fetch_url


class TinyUrlBypasser(BaseBypasser):
    name = "TinyURL"
    domains = ["tinyurl.com", "tiny.cc"]

    async def bypass(self, url: str) -> str:
        try:
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            if resp.status_code == 404:
                raise LinkDeadError("TinyURL link does not exist or has expired.")
            final_url = str(resp.url)
            if "tinyurl.com" in final_url and final_url == url:
                raise BypassError("TinyURL redirect could not be resolved.")
            return final_url
        except httpx.HTTPError as e:
            raise BypassError(f"Network error while resolving TinyURL: {e}")
