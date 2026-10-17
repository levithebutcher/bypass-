"""Bypasser plugin for Rekonise and rkns.link social unlock links."""

import re
from urllib.parse import urlparse
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class RekoniseBypasser(BaseBypasser):
    name = "Rekonise"
    domains = ["rekonise.com", "rkns.link"]

    async def bypass(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        # Path format: /<slug>
        slug = path.split("/")[0] if path else ""
        if not slug:
            raise BypassError("Invalid Rekonise URL: slug not found.")

        # Rekonise provides a direct public REST API endpoint
        api_url = f"https://api.rekonise.com/social-unlocks/{slug}"
        try:
            resp = await safe_fetch_url(api_url, method="GET")
            if resp.status_code == 404:
                raise LinkDeadError("Rekonise link does not exist or was deleted (404 Not Found).")

            data = resp.json()
            target_url = data.get("url")
            if target_url and (target_url.startswith("http://") or target_url.startswith("https://")):
                return target_url
        except LinkDeadError:
            raise
        except Exception as e:
            raise BypassError(f"Failed to fetch Rekonise destination from API: {e}")

        raise BypassError("Rekonise API did not return a valid destination URL.")
