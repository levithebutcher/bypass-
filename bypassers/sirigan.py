"""Bypasser plugin for safeurl.sirigan.my.id multi-layer base64 redirects."""

import base64
from urllib.parse import unquote
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class SiriganBypasser(BaseBypasser):
    name = "Sirigan"
    domains = ["sirigan.my.id"]

    async def bypass(self, url: str) -> str:
        resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
        if resp.status_code == 404:
            raise LinkDeadError("Sirigan link not found (404).")

        curr_url = str(resp.url)
        if "asu=" in curr_url:
            encoded_part = curr_url.split("asu=", 1)[-1]
        elif "=" in curr_url:
            encoded_part = curr_url.split("=", 1)[-1]
        else:
            raise BypassError("No encoded payload found in Sirigan URL.")

        decoded = encoded_part
        # Iteratively decode base64
        for _ in range(5):
            try:
                temp = base64.b64decode(decoded).decode("utf-8")
                decoded = temp
            except Exception:
                break

        if "url=" in decoded:
            return decoded.split("url=", 1)[-1]
        elif decoded.startswith("http"):
            return decoded

        raise BypassError("Failed to decode Sirigan payload to a valid URL.")
