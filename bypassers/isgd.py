"""Bypasser plugin for is.gd and v.gd shortlinks."""

import httpx
from bypassers.base import BaseBypasser
from bypassers.exceptions import LinkDeadError, BypassError
from utils.http import safe_fetch_url


class IsGdBypasser(BaseBypasser):
    name = "Is.gd"
    domains = ["is.gd", "v.gd"]

    async def bypass(self, url: str) -> str:
        # Try official unshorten API first
        api_endpoint = f"https://is.gd/forward.php?format=json&shorturl={url}"
        try:
            resp = await safe_fetch_url(api_endpoint, method="GET")
            if resp.status_code == 200:
                data = resp.json()
                if "url" in data:
                    return data["url"]
                if "errormessage" in data:
                    if "not found" in data["errormessage"].lower():
                        raise LinkDeadError(data["errormessage"])
        except (httpx.HTTPError, ValueError):
            pass

        # Fallback to direct redirect resolution
        try:
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            if resp.status_code == 404:
                raise LinkDeadError("is.gd link not found.")
            final_url = str(resp.url)
            if "is.gd" in final_url and final_url == url:
                raise BypassError("is.gd redirection could not be resolved.")
            return final_url
        except httpx.HTTPError as e:
            raise BypassError(f"Network error resolving is.gd: {e}")
