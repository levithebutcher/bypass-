"""Bypasser plugin for shrinkme.io and shrinke.me shortlinks."""

import asyncio
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class ShrinkMeBypasser(BaseBypasser):
    name = "ShrinkMe"
    domains = ["shrinkme.io", "shrinkme.net", "shrinke.me"]

    async def bypass(self, url: str) -> str:
        clean_url = url.rstrip("/")
        code = clean_url.split("/")[-1]
        domain = "https://shrinkme.io"
        referer = "https://themezon.net/"

        resp = await safe_fetch_url(
            f"{domain}/{code}",
            method="GET",
            referer=referer,
            follow_redirects=True,
        )
        if resp.status_code == 404:
            raise LinkDeadError("ShrinkMe URL does not exist (404).")

        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find(id="go-link") or soup.find("form")
        if not form:
            raise BypassError("Could not find ShrinkMe form.")

        inputs = form.find_all("input")
        data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name") and inp.get("value")}

        # Countdown wait
        await asyncio.sleep(5)

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{domain}/{code}",
        }
        api_resp = await safe_fetch_url(
            f"{domain}/links/go",
            method="POST",
            data=data,
            headers=headers,
        )

        try:
            res_json = api_resp.json()
            if "url" in res_json:
                return res_json["url"]
        except Exception:
            pass

        raise BypassError("ShrinkMe failed to yield destination link.")
