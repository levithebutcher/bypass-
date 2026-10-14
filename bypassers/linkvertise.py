"""Bypasser plugin for Linkvertise network."""

import re
import httpx
from urllib.parse import urlparse
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url, get_default_headers


class LinkvertiseBypasser(BaseBypasser):
    name = "Linkvertise"
    domains = [
        "linkvertise.com", "linkvertise.net", "link-to.net",
        "up-to-down.net", "direct-link.net", "file-link.net",
        "link-center.net", "link-target.net", "link-hub.net",
    ]

    async def bypass(self, url: str) -> str:
        # Check standard public resolver API first
        apis = [
            f"https://bypass.pm/bypass2?url={url}",
            f"https://api.bypass.vip/",
        ]

        # 1. Try bypass.pm API
        try:
            resp = await safe_fetch_url(apis[0], method="GET")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("destination"):
                    return data["destination"]
                if data.get("url"):
                    return data["url"]
        except Exception:
            pass

        # 2. Try bypass.vip API
        try:
            resp = await safe_fetch_url(apis[1], method="POST", data={"url": url})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("destination"):
                    return data["destination"]
        except Exception:
            pass

        # 3. Native Linkvertise JSON API attempt
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(path_parts) >= 2:
                user_id, link_slug = path_parts[0], path_parts[1]
                api_url = f"https://publisher.linkvertise.com/api/v1/redirect/link/static/{user_id}/{link_slug}"
                headers = get_default_headers()
                headers.update({
                    "Origin": "https://linkvertise.com",
                    "Referer": url,
                    "Accept": "application/json",
                })
                api_resp = await safe_fetch_url(api_url, method="GET", headers=headers)
                if api_resp.status_code == 200:
                    json_data = api_resp.json()
                    link_data = json_data.get("data", {}).get("link", {})
                    target = link_data.get("url") or link_data.get("target_url")
                    if target:
                        return target
        except Exception:
            pass

        raise BypassError("Linkvertise link requires interactive access or bypass API is unreachable.")
