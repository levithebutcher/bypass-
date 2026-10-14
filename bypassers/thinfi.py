"""Bypasser plugin for thinfi.com passwordless/passworded shortlinks."""

from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class ThinfiBypasser(BaseBypasser):
    name = "Thinfi"
    domains = ["thinfi.com"]

    async def bypass(self, url: str) -> str:
        resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
        if resp.status_code == 404:
            raise LinkDeadError("Thinfi link does not exist (404).")

        soup = BeautifulSoup(resp.text, "html.parser")
        p_tag = soup.find("p")
        if p_tag and p_tag.find("a"):
            dest = p_tag.find("a").get("href")
            if dest and dest.startswith("http"):
                return dest

        # Fallback to any valid external link on page
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("http") and "thinfi.com" not in href:
                return href

        raise BypassError("Could not extract destination URL from Thinfi.")
