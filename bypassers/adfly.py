"""Bypasser plugin for adf.ly and its network of mirror domains using XOR decryption."""

import re
import base64
from urllib.parse import unquote
from bypassers.base import BaseBypasser
from bypassers.exceptions import BypassError, LinkDeadError
from utils.http import safe_fetch_url


def _decrypt_adfly_ysmm(code: str) -> str:
    """Decrypts adfly ysmm JavaScript code via XOR cipher."""
    a, b = "", ""
    for i in range(len(code)):
        if i % 2 == 0:
            a += code[i]
        else:
            b = code[i] + b

    key = list(a + b)
    i = 0
    while i < len(key):
        if key[i].isdigit():
            for j in range(i + 1, len(key)):
                if key[j].isdigit():
                    u = int(key[i]) ^ int(key[j])
                    if u < 10:
                        key[i] = str(u)
                    i = j
                    break
        i += 1

    decrypted = base64.b64decode("".join(key))[16:-16].decode("utf-8")
    return decrypted


class AdFlyBypasser(BaseBypasser):
    name = "Adf.ly"
    domains = [
        "adf.ly", "j.gs", "q.gs", "ay.gy", "zo.ee", "microify.com",
        "tinyium.com", "pintient.com", "kudoflow.com", "infopade.com",
        "linkjaunt.com", "atominik.com", "bluenik.com", "atomcurve.com",
        "picocurl.com", "casualient.com", "battleate.com", "simizer.com",
        "viahold.com", "yoalizer.com", "kibuilder.com", "kimechanic.com",
        "yobuilder.com", "skamason.com", "twineer.com", "vializer.com",
        "viwright.com", "yamechanic.com", "kializer.com", "yoineer.com",
        "skamaker.com", "activeation.com", "brisktopia.com", "rapidtory.com",
        "swiftation.com", "zipteria.com", "agileurbia.com", "threadsphere.bid",
        "fasttory.com", "sprysphere.com", "bullads.net", "clearload.bid",
    ]

    async def bypass(self, url: str) -> str:
        resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
        if resp.status_code == 404:
            raise LinkDeadError("Adf.ly link not found or deleted (404).")

        html = resp.text
        # Search for ysmm parameter in script tags
        ysmm_match = re.search(r"ysmm\s*=\s*['\"]([^'\"]+)['\"]", html)
        if not ysmm_match:
            # Check if page already redirected directly
            if not any(d in str(resp.url) for d in self.domains):
                return str(resp.url)
            raise BypassError("Could not locate ysmm security variable in Adf.ly page.")

        try:
            decrypted = _decrypt_adfly_ysmm(ysmm_match.group(1))
            
            # Check for redirect query parameters
            if "go.php?u=" in decrypted:
                u_param = re.sub(r"(.*?)u=", "", decrypted)
                return base64.b64decode(u_param).decode("utf-8")
            elif "&dest=" in decrypted:
                return unquote(re.sub(r"(.*?)dest=", "", decrypted))
            
            return decrypted
        except Exception as e:
            raise BypassError(f"Failed to decrypt Adf.ly destination: {e}")
