"""Bypasser plugin for Twitter / X t.co shortlinks."""

import re
import httpx
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import LinkDeadError, BypassError
from utils.http import safe_fetch_url


class TcoBypasser(BaseBypasser):
    name = "T.co"
    domains = ["t.co"]

    async def bypass(self, url: str) -> str:
        try:
            # t.co often responds with an HTML page containing meta-refresh or JS redirect
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            if resp.status_code == 404:
                raise LinkDeadError("t.co link not found.")

            final_url = str(resp.url)
            if "t.co" not in final_url:
                return final_url

            # Inspect HTML body for meta refresh or title/a tag redirect
            soup = BeautifulSoup(resp.text, "html.parser")
            meta_refresh = soup.find("meta", attrs={"http-equiv": re.compile(r"^refresh$", re.I)})
            if meta_refresh and meta_refresh.get("content"):
                match = re.search(r'url=([^;]+)', meta_refresh["content"], re.I)
                if match:
                    return match.group(1).strip("'\"")

            # Check for script location redirect
            js_match = re.search(r'(?:location\.href|location\.replace)\s*=\s*["\']([^"\']+)["\']', resp.text)
            if js_match:
                return js_match.group(1)

            return final_url
        except httpx.HTTPError as e:
            raise BypassError(f"Network error while resolving t.co: {e}")
