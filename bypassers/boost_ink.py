"""Bypasser plugin for Boost.ink and related shorteners (bst.gg, bst.wtf, booo.st)."""

import re
import json
import base64
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class BoostInkBypasser(BaseBypasser):
    name = "Boost.ink"
    domains = [
        "boost.ink", "bst.gg", "bst.wtf", "booo.st", "boost.fusedgt.com"
    ]

    async def bypass(self, url: str) -> str:
        resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
        if resp.status_code == 404:
            raise LinkDeadError("Boost.ink link does not exist (404 Not Found).")

        html = resp.text

        # 1. Search for atob or base64 decoded target variables
        atob_matches = re.findall(r'atob\s*\(\s*["\']([a-zA-Z0-9+/=]+)["\']\s*\)', html)
        for b64 in atob_matches:
            try:
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                if decoded.startswith("http://") or decoded.startswith("https://"):
                    return decoded
            except Exception:
                continue

        # 2. Check for target or destination in window/script tags
        script_targets = re.findall(r'["\']?(?:target|destination_url|targeturl|unlocked_url)["\']?\s*[:=]\s*["\'](https?://[^"\']+)["\']', html, re.I)
        if script_targets:
            return script_targets[0]

        # 3. Check for data-target or data-url attributes in HTML elements
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(attrs={"data-target": True}):
            val = tag["data-target"]
            if val.startswith("http"):
                return val
            try:
                dec = base64.b64decode(val).decode("utf-8")
                if dec.startswith("http"):
                    return dec
            except Exception:
                pass

        for tag in soup.find_all(attrs={"data-url": True}):
            val = tag["data-url"]
            if val.startswith("http"):
                return val

        raise BypassError("Could not extract destination URL from Boost.ink.")
