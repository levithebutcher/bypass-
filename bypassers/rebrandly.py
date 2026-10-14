"""Bypasser plugin for rebrand.ly shortlinks."""

import httpx
from bypassers.base import BaseBypasser
from bypassers.exceptions import LinkDeadError, BypassError
from utils.http import safe_fetch_url


class RebrandlyBypasser(BaseBypasser):
    name = "Rebrandly"
    domains = ["rebrand.ly", "rebrandly.com"]

    async def bypass(self, url: str) -> str:
        try:
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            if resp.status_code == 404:
                raise LinkDeadError("Rebrandly link does not exist or expired.")
            final_url = str(resp.url)
            if "rebrand.ly" in final_url and final_url == url:
                raise BypassError("Rebrandly redirect could not be resolved.")
            return final_url
        except httpx.HTTPError as e:
            raise BypassError(f"Network error resolving Rebrandly: {e}")
