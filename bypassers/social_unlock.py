"""Bypasser plugin for Social Unlock & Sub2Unlock networks."""

import re
import json
import base64
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class SocialUnlockBypasser(BaseBypasser):
    name = "Social Unlock"
    priority = 9
    domains = [
        "sub2unlock.com", "sub2unlock.net", "sub2unlock.io",
        "sub1s.com", "sub2get.com", "subtolink.com", "subfinal.com",
        "unlocknow.net", "social-unlock.com", "socialwolvez.com",
        "mboost.me", "leasurepartment.xyz", "empebau.eu",
    ]

    async def bypass(self, url: str) -> str:
        resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
        if resp.status_code == 404:
            raise LinkDeadError(f"{self.name} link not found (404).")

        html = resp.text

        # 1. Search for Base64 atob calls often used by Sub2Unlock & MBoost
        atob_matches = re.findall(r'atob\s*\(\s*["\']([a-zA-Z0-9+/=]+)["\']\s*\)', html)
        for b64 in atob_matches:
            try:
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                if decoded.startswith("http://") or decoded.startswith("https://"):
                    return decoded
            except Exception:
                continue

        # 2. Search for explicit script variables (link, target, dest, redirect)
        patterns = [
            r'["\']?(?:target_url|unlocked_url|targetUrl|destination|targetLink|final_url)["\']?\s*[:=]\s*["\'](https?://[^"\']+)["\']',
            r'var\s+(?:link|url|target|destination)\s*=\s*["\'](https?://[^"\']+)["\']',
            r'window\.(?:location|destination)\s*=\s*["\'](https?://[^"\']+)["\']',
        ]
        for pat in patterns:
            match = re.search(pat, html, re.I)
            if match:
                candidate = match.group(1)
                # Verify candidate is not the locker site itself
                if not any(d in candidate for d in self.domains):
                    return candidate

        # 3. Inspect HTML elements for data attributes or download/unlock links
        soup = BeautifulSoup(html, "html.parser")
        for attr in ["data-target", "data-url", "data-link", "data-href"]:
            for tag in soup.find_all(attrs={attr: True}):
                val = tag[attr]
                if val.startswith("http") and not any(d in val for d in self.domains):
                    return val
                try:
                    dec = base64.b64decode(val).decode("utf-8")
                    if dec.startswith("http"):
                        return dec
                except Exception:
                    pass

        # 4. Check for anchor tag with id="link" or class="btn-unlock"
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("http") and not any(d in href for d in self.domains):
                classes = " ".join(a_tag.get("class", []))
                tag_id = a_tag.get("id", "")
                if any(k in (classes + tag_id).lower() for k in ["unlock", "target", "link", "destination"]):
                    return href

        raise BypassError(f"Could not extract unlocked destination from {self.name} page.")
