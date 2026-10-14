"""Bypasser plugin for the Linkvertise network."""

import re
import json
import time
import base64
import logging
from urllib.parse import urlparse, parse_qs, unquote
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url, get_default_headers

logger = logging.getLogger(__name__)


def _decode_dynamic_r_param(url: str) -> str:
    """
    Decodes the ?r= base64 destination parameter found in Linkvertise dynamic links.
    e.g. https://link-to.net/123/456/dynamic?r=aHR0cHM6Ly9leGFtcGxlLmNvbQ==
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Check query param 'r'
    r_val = query_params.get("r", [None])[0]
    if not r_val:
        # Regex search in case of malformed query string
        m = re.search(r'[?&]r=([a-zA-Z0-9_\-+/=]+)', url)
        if m:
            r_val = m.group(1)

    if r_val:
        # Pad base64 if needed
        padding = len(r_val) % 4
        if padding:
            r_val += "=" * (4 - padding)
        try:
            decoded = base64.b64decode(r_val).decode("utf-8", errors="ignore")
            if decoded.startswith("http://") or decoded.startswith("https://"):
                return decoded
        except Exception:
            pass

    return ""


class LinkvertiseBypasser(BaseBypasser):
    name = "Linkvertise"
    domains = [
        "linkvertise.com", "linkvertise.net", "link-to.net",
        "up-to-down.net", "direct-link.net", "file-link.net",
        "link-center.net", "link-target.net", "link-hub.net",
    ]

    async def bypass(self, url: str) -> str:
        # 1. Fast Path: Check if this is a dynamic link with ?r= (Base64 target)
        dynamic_dest = _decode_dynamic_r_param(url)
        if dynamic_dest:
            logger.info("Decoded dynamic Linkvertise destination directly: %s", dynamic_dest)
            return dynamic_dest

        # 2. Extract Linkvertise link path: /<user_id>/<link_slug>
        clean_url = (
            url.replace("%3D", " ")
            .replace("&o=sharing", "")
            .replace("?o=sharing", "")
            .replace("dynamic?r=", "dynamic/?r=")
        )
        id_match = re.search(r"/\d+/[^/?#]+", clean_url)
        if not id_match:
            raise BypassError("Invalid Linkvertise URL format (could not identify link ID/path).")

        link_path = id_match.group(0)

        # 3. Native Linkvertise API
        headers = {
            "User-Agent": "AppleTV6,2/11.1",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        static_api = f"https://publisher.linkvertise.com/api/v1/redirect/link/static{link_path}"
        try:
            resp = await safe_fetch_url(static_api, method="GET", headers=headers)
            data = resp.json()

            # Check if link was deleted or not found
            if isinstance(data, dict):
                if data.get("error") is True or "Not Found!" in data.get("messages", []):
                    raise LinkDeadError("This Linkvertise link does not exist or has been deleted (404 Not Found).")

                link_info = data.get("data")
                if isinstance(link_info, dict):
                    # Check if destination url is already provided in static response
                    link_obj = link_info.get("link", {})
                    if link_obj.get("target_type") == "paste" and link_obj.get("raw"):
                        return link_obj["raw"]
                    if link_obj.get("url"):
                        return link_obj["url"]

                    link_id = link_obj.get("id")
                    if link_id:
                        # Attempt payload submission
                        out = {
                            "timestamp": int(str(time.time_ns())[:13]),
                            "random": "6548307",
                            "link_id": link_id,
                        }
                        options = {"serial": base64.b64encode(json.dumps(out).encode()).decode()}

                        account_resp = await safe_fetch_url("https://publisher.linkvertise.com/api/v1/account", method="GET", headers=headers)
                        user_token = account_resp.json().get("user_token")

                        submit_url = f"https://publisher.linkvertise.com/api/v1/redirect/link{link_path}/target?X-Linkvertise-UT={user_token}"
                        target_resp = await safe_fetch_url(submit_url, method="POST", json=options, headers=headers)
                        target_data = target_resp.json()
                        target_url = target_data.get("data", {}).get("target")
                        if target_url:
                            return target_url
        except LinkDeadError:
            raise
        except Exception as e:
            logger.debug("Native Linkvertise API failed: %s", e)

        # 4. Third-party resolver fallback (e.g. bypass.pm or bypass.vip)
        for api_url in [f"https://bypass.pm/bypass2?url={url}"]:
            try:
                api_resp = await safe_fetch_url(api_url, method="GET")
                res = api_resp.json()
                if res.get("destination"):
                    return res["destination"]
                if res.get("url"):
                    return res["url"]
            except Exception:
                pass

        raise BypassError("Linkvertise link requires interactive captcha completion or has expired.")
