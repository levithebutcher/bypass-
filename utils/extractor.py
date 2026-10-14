"""URL extraction and normalization helpers."""

import re
from typing import List
from urllib.parse import urlparse

# Regular expression matching http and https URLs
URL_PATTERN = re.compile(
    r'(https?://[^\s<>"\')]+)',
    re.IGNORECASE
)


def extract_urls(text: str) -> List[str]:
    """
    Finds and extracts all valid URLs from the given text.
    Strips trailing punctuation and deduplicates while preserving order.
    """
    if not text:
        return []

    raw_urls = URL_PATTERN.findall(text)
    cleaned_urls: List[str] = []
    seen = set()

    for url in raw_urls:
        # Strip common trailing punctuation
        cleaned = url.rstrip('.,);!?"\'>')
        
        # Verify valid scheme and domain
        try:
            parsed = urlparse(cleaned)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                if cleaned not in seen:
                    seen.add(cleaned)
                    cleaned_urls.append(cleaned)
        except Exception:
            continue

    return cleaned_urls
