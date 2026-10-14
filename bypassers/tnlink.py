"""Bypasser plugin for tnlink.in and tnshort.net."""

import asyncio
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class TnLinkBypasser(BaseBypasser):
    name = "TNLink"
    domains = ["tnlink.in", "tnshort.net", "tnvalue.in"]

    async def bypass(self, url: str) -> str:
        clean_url = url.rstrip("/")
        code = clean_url.split("/")[-1]
        domain = "https://news.sagenews.in"
        referer = "https://knowstuff.in/"

        resp = await safe_fetch_url(
            f"{domain}/{code}",
            method="GET",
            referer=referer,
            follow_redirects=True,
        )
        if resp.status_code == 404:
            raise LinkDeadError("TNLink link not found.")

        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find(id="go-link") or soup.find("form")
        if not form:
            # Check if original url directly responds
            resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
            soup = BeautifulSoup(resp.text, "html.parser")
            form = soup.find(id="go-link") or soup.find("form")

        if not form:
            raise BypassError("Could not parse TNLink form.")

        inputs = form.find_all("input")
        data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name") and inp.get("value")}

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

        raise BypassError("TNLink bypass did not return target URL.")
