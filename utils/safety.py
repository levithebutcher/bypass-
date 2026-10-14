"""Safety utilities to prevent downloading or executing dangerous files."""

import os
import re
from urllib.parse import urlparse
from typing import Tuple

# Disallowed dangerous executable extensions
DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".msi", ".scr", ".pif", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".ps1", ".ps1xml", ".ps2", ".psc1",
    ".com", ".dll", ".hta", ".cpl", ".msc", ".jar", ".gadget", ".apk"
}

# Dangerous MIME types
DANGEROUS_MIME_TYPES = {
    "application/x-msdownload",
    "application/x-msdos-program",
    "application/x-executable",
    "application/x-bat",
    "application/vnd.android.package-archive",
}


def is_dangerous_url(url: str) -> Tuple[bool, str]:
    """
    Checks if a URL path clearly points to a dangerous executable file.
    Returns (is_dangerous, reason).
    """
    parsed = urlparse(url)
    clean_path = parsed.path.lower().strip()
    
    # Check file extension in the URL path
    _, ext = os.path.splitext(clean_path)
    if ext in DANGEROUS_EXTENSIONS:
        return True, f"Target URL points directly to an executable file ({ext}). For security, direct file execution is blocked."
        
    return False, ""


def is_dangerous_response_headers(headers: dict) -> Tuple[bool, str]:
    """
    Checks HTTP response headers for executable content-disposition or mime-types.
    """
    content_type = headers.get("content-type", "").lower().split(";")[0].strip()
    if content_type in DANGEROUS_MIME_TYPES:
        return True, f"Response MIME-type ({content_type}) indicates an executable binary."

    content_disposition = headers.get("content-disposition", "").lower()
    if "filename=" in content_disposition:
        filename_match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', content_disposition)
        if filename_match:
            filename = filename_match.group(1).lower().strip()
            _, ext = os.path.splitext(filename)
            if ext in DANGEROUS_EXTENSIONS:
                return True, f"Content-Disposition specifies an executable file ({filename})."

    return False, ""
