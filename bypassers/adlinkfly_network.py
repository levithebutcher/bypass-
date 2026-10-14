"""Generalized bypasser plugin for AdLinkFly & MightyScripts shortlink networks."""

import re
import asyncio
from typing import Dict, Tuple, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url, get_default_headers

# Mapping of known domains to (intermediate_domain, referer_domain, countdown_seconds)
KNOWN_ADLINKFLY_CONFIGS: Dict[str, Tuple[Optional[str], Optional[str], float]] = {
    "shortner.in": (None, "https://shortner.in/", 5.0),
    "urlshortx.com": (None, "https://urlshortx.com/", 5.0),
    "earnlink.io": (None, "https://earnlink.io/", 4.0),
    "try2link.com": ("https://try2link.com", "https://hightrip.net/", 5.0),
    "gyanilinks.com": ("https://go.bloggingaro.com", "https://hipsonyc.com/", 5.0),
    "adrinolinks.in": ("https://adrinolinks.in", "https://wikitraveltips.com/", 5.0),
    "ronylink.com": ("https://go.ronylink.com/", "https://livejankari.com/", 3.5),
    "xpshort.com": ("https://xpshort.com/", "https://www.comptegratuite.com/", 4.5),
    "onepagelink.in": ("https://go.onepagelink.in/", "https://gorating.in/", 3.5),
    "moneykamalo.com": ("https://go.moneykamalo.com/", "https://bloging.techkeshri.com/", 4.0),
    "tinyfy.in": ("https://tinyfy.in", "https://www.yotrickslog.tech/", 2.0),
    "krownlinks.net": ("https://go.hostadviser.net/", "https://blog.hostadviser.net/", 5.0),
    "du-link.in": ("https://du-link.in", "https://profitshort.com/", 2.0),
    "indianshortner.com": ("https://indianshortner.com/", "https://moddingzone.in/", 5.0),
    "short2url.in": ("https://techyuth.xyz/blog", "https://blog.coin2pay.xyz/", 5.0),
    "urlsopen.com": ("https://s.humanssurvival.com/", "https://1topjob.xyz/", 5.0),
    "linkpays.in": ("https://tech.smallinfo.in/Gadget/", "https://finance.filmypoints.in/", 5.0),
    "sklinks.in": ("https://sklinks.in", "https://dailynew.online/", 5.0),
    "link1s.com": ("https://link1s.com", "https://anhdep24.com/", 6.0),
    "viplinks.net": ("https://m.vip-link.net/", "https://m.leadcricket.com/", 5.0),
    "rocklinks.net": ("https://land.povathemes.com/", "https://blog.disheye.com/", 5.0),
    "v2links.com": ("https://vzu.us/", "https://newsbawa.com/", 5.0),
    "tamizhmasters.com": ("https://tamizhmasters.com/", "https://pokgames.com/", 5.0),
    "ez4short.com": ("https://ez4short.com/", "https://ez4mods.com/", 5.0),
    "dalink.in": ("https://get.tamilhit.tech/MR-X/tamil/", "https://www.tamilhit.tech/", 5.0),
    "bindaaslinks.com": ("https://appsinsta.com/blog", "https://pracagov.com/", 4.0),
    "publicearn.com": ("https://publicearn.com/", "https://careersides.com/", 4.5),
    "linkshortx.in": ("https://linkshortx.in/", "https://nanotech.org.in/", 4.5),
}


class AdLinkFlyNetworkBypasser(BaseBypasser):
    name = "AdLinkFly Network"
    priority = 8
    domains = list(KNOWN_ADLINKFLY_CONFIGS.keys())

    def match(self, url: str) -> bool:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        return any(d in hostname for d in self.domains)

    async def bypass(self, url: str) -> str:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        matched_domain = next((d for d in self.domains if d in hostname), None)

        if matched_domain:
            cfg_domain, referer, wait_time = KNOWN_ADLINKFLY_CONFIGS[matched_domain]
        else:
            cfg_domain, referer, wait_time = None, None, 4.0

        clean_url = url.rstrip("/")
        code = clean_url.split("/")[-1]
        
        target_base = cfg_domain or f"{parsed.scheme}://{parsed.netloc}"
        fetch_url = f"{target_base.rstrip('/')}/{code}"
        
        # Step 1: Fetch form page
        resp = await safe_fetch_url(fetch_url, method="GET", referer=referer, follow_redirects=True)
        if resp.status_code == 404:
            raise LinkDeadError(f"{self.name} link returned 404 Not Found.")

        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find(id="go-link") or soup.find("form")
        
        if not form:
            # Fallback to direct URL fetch without intermediate host
            if fetch_url != url:
                resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
                soup = BeautifulSoup(resp.text, "html.parser")
                form = soup.find(id="go-link") or soup.find("form")

        if not form:
            raise BypassError(f"Could not locate AdLinkFly token form for {hostname}.")

        inputs = form.find_all("input")
        data = {
            inp.get("name"): inp.get("value")
            for inp in inputs
            if inp.get("name") and inp.get("value") is not None
        }

        # Step 2: Countdown wait
        await asyncio.sleep(min(wait_time, 8.0))

        # Step 3: POST to links/go
        post_target = f"{target_base.rstrip('/')}/links/go"
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": str(resp.url),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        api_resp = await safe_fetch_url(post_target, method="POST", data=data, headers=headers)
        try:
            res_json = api_resp.json()
            if "url" in res_json and res_json["url"]:
                return res_json["url"]
            if res_json.get("status") == "error":
                raise BypassError(f"Site returned error: {res_json.get('message', 'Validation failed')}")
        except BypassError:
            raise
        except Exception:
            pass

        raise BypassError(f"AdLinkFly solver failed to resolve target URL from {hostname}.")
