"""Bypasser plugin for Loot-Link, LootLinks, LootDest and related mirror domains."""

import re
import json
import base64
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url, get_default_headers


class LootLinkBypasser(BaseBypasser):
    name = "LootLink"
    priority = 9
    domains = [
        "loot-link.com", "loot-link.co", "loot-link.org", "loot-link.net", "loot-link.info",
        "loot-links.com", "loot-links.co", "loot-links.org", "loot-links.net", "loot-links.info",
        "lootlinks.com", "lootlinks.co", "lootlinks.org", "lootlinks.net", "lootlinks.info",
        "lootdest.com", "lootdest.co", "lootdest.org", "lootdest.net", "lootdest.info",
        "links-loot.com", "links-loot.co", "links-loot.org", "links-loot.net", "links-loot.info",
        "linksloot.com", "linksloot.co", "linksloot.org", "linksloot.net", "linksloot.info",
        "lootlink.com", "lootlink.co", "lootlink.org", "lootlink.net", "lootlink.info",
    ]

    async def bypass(self, url: str) -> str:
        resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
        if resp.status_code == 404:
            raise LinkDeadError("LootLink page returned 404 Not Found.")

        html = resp.text

        # 1. Search for embedded target in script variables or JSON configs
        match = re.search(r'["\']?(?:target_url|unlocked_url|target|destination)["\']?\s*[:=]\s*["\'](https?://[^"\']+)["\']', html)
        if match:
            candidate = match.group(1)
            if not any(d in candidate for d in self.domains):
                return candidate

        # 2. Check for base64 encoded targets in HTML or data attributes
        atob_matches = re.findall(r'atob\s*\(\s*["\']([a-zA-Z0-9+/=]+)["\']\s*\)', html)
        for b64 in atob_matches:
            try:
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                if decoded.startswith("http://") or decoded.startswith("https://"):
                    if not any(d in decoded for d in self.domains):
                        return decoded
            except Exception:
                continue

        # 3. Check public bypasser endpoint fallback
        for api_url in [
            f"https://bypass.pm/bypass2?url={url}",
            f"https://api.bypass.vip/",
        ]:
            try:
                if "bypass2" in api_url:
                    r = await safe_fetch_url(api_url, method="GET")
                else:
                    r = await safe_fetch_url(api_url, method="POST", data={"url": url})
                
                data = r.json()
                dest = data.get("destination") or data.get("url")
                if dest and dest.startswith("http"):
                    return dest
            except Exception:
                pass

        raise BypassError("LootLink requires interactive task completion or solver is unavailable.")
