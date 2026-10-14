"""Bypasser plugin for gplinks.co and gplinks mirrors."""

import re
import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url, get_default_headers


class GpLinksBypasser(BaseBypasser):
    name = "GPLinks"
    domains = ["gplinks.co", "gplinks.in", "gplinks.com"]

    async def bypass(self, url: str) -> str:
        clean_url = url.rstrip("/")
        link_token = clean_url.split("/")[-1]
        domain = "https://gplinks.co/"
        referer = "https://mynewsmedia.co/"

        # Try curl_cffi / cloudscraper to get past initial Cloudflare check
        try:
            from curl_cffi.requests import AsyncSession
            async with AsyncSession(impersonate="chrome120") as session:
                # Initial GET with referer
                init_resp = await session.get(url, headers={"Referer": referer}, allow_redirects=False)
                if init_resp.status_code == 404:
                    raise LinkDeadError("GPLinks URL not found (404).")

                loc = init_resp.headers.get("Location")
                if loc:
                    if "=" in loc:
                        param = loc.split("=")[-1]
                        step_url = f"{clean_url}/?{param}"
                    else:
                        step_url = loc
                else:
                    step_url = url

                # Second step GET
                page_resp = await session.get(step_url, headers={"Referer": domain}, allow_redirects=False)
                soup = BeautifulSoup(page_resp.content, "html.parser")
                form = soup.find(id="go-link") or soup.find("form")
                if not form:
                    # Check if already redirected
                    if loc and not any(d in loc for d in self.domains):
                        return loc
                    raise BypassError("GPLinks form inputs not found.")

                inputs = form.find_all("input")
                data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name") and inp.get("value")}

                # Countdown wait
                await asyncio.sleep(5)

                post_headers = {
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": step_url,
                }
                api_resp = await session.post(f"{domain}links/go", data=data, headers=post_headers)
                try:
                    res_json = api_resp.json()
                    if "url" in res_json:
                        return res_json["url"]
                except Exception:
                    pass
        except LinkDeadError:
            raise
        except Exception:
            pass

        # Fallback using standard safe_fetch_url
        try:
            resp = await safe_fetch_url(url, method="GET", referer=referer, follow_redirects=True)
            if resp.status_code == 404:
                raise LinkDeadError("GPLinks URL not found.")

            soup = BeautifulSoup(resp.text, "html.parser")
            form = soup.find(id="go-link") or soup.find("form")
            if not form:
                raise BypassError("Could not extract GPLinks form tokens.")

            inputs = form.find_all("input")
            data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name") and inp.get("value")}

            await asyncio.sleep(5)
            api_resp = await safe_fetch_url(
                f"{domain}links/go",
                method="POST",
                data=data,
                headers={"X-Requested-With": "XMLHttpRequest", "Referer": str(resp.url)},
            )
            data_json = api_resp.json()
            if "url" in data_json:
                return data_json["url"]
        except Exception as e:
            raise BypassError(f"Failed to bypass GPLinks: {e}")

        raise BypassError("GPLinks bypass failed to resolve final URL.")
