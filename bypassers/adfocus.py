"""Bypasser plugin for adfoc.us shortlinks."""

import re
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class AdFocusBypasser(BaseBypasser):
    name = "AdFocus"
    domains = ["adfoc.us"]

    async def bypass(self, url: str) -> str:
        resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
        if resp.status_code == 404:
            raise LinkDeadError("AdFocus link does not exist (404 Not Found).")

        html = resp.text

        # 1. Look for click_url javascript variable
        match = re.search(r'var\s+click_url\s*=\s*["\'](https?://[^"\']+)["\']', html)
        if match:
            return match.group(1)

        # 2. Look for skip button or link in HTML
        soup = BeautifulSoup(html, "html.parser")
        skip_btn = soup.find("a", {"class": re.compile(r"skip", re.I)}) or soup.find(id="show_skip")
        if skip_btn and skip_btn.get("href"):
            href = skip_btn["href"]
            if href.startswith("http"):
                return href

        # 3. Check for any destination parameter in URL/scripts
        param_match = re.search(r'click_url\s*:\s*["\'](https?://[^"\']+)["\']', html)
        if param_match:
            return param_match.group(1)

        raise BypassError("Could not extract destination URL from AdFocus page.")
