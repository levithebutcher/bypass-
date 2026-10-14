"""Bypasser plugin for shorte.st and its network (festyy, gestyy, corneey, etc.)."""

import re
import asyncio
from urllib.parse import urlparse
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


class ShortestBypasser(BaseBypasser):
    name = "Shorte.st"
    domains = [
        "shorte.st", "festyy.com", "gestyy.com", "corneey.com",
        "destyy.com", "ceesty.com", "cllkme.com"
    ]

    async def bypass(self, url: str) -> str:
        parsed = urlparse(url)
        resp = await safe_fetch_url(url, method="GET", referer=url)
        if resp.status_code == 404:
            raise LinkDeadError("shorte.st link does not exist (404).")

        session_matches = re.findall(r"sessionId(?:\s*)?[:=](?:\s*)?['\"](.*?)['\"]", resp.text)
        if not session_matches:
            # Check if direct redirect took place
            if not any(d in str(resp.url) for d in self.domains):
                return str(resp.url)
            raise BypassError("Failed to extract shorte.st session token.")

        session_id = session_matches[0]
        final_api = f"{parsed.scheme}://{parsed.netloc}/shortest-url/end-adsession"
        params = {"adSessionId": session_id, "callback": "_"}

        # Wait small countdown delay to allow session activation
        await asyncio.sleep(3)

        api_resp = await safe_fetch_url(
            final_api,
            method="GET",
            headers={"Referer": url, "X-Requested-With": "XMLHttpRequest"},
        )
        dest_match = re.search(r'"destinationUrl"\s*:\s*"([^"]+)"', api_resp.text)
        if dest_match:
            return dest_match.group(1).replace(r"\/", "/")

        quoted_match = re.findall(r'"(https?://.*?)"', api_resp.text)
        if quoted_match:
            return quoted_match[0].replace(r"\/", "/")

        raise BypassError("shorte.st returned no valid destination URL.")
