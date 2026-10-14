"""HTTP helper module with rotating User-Agents, retries, and proxy support."""

import asyncio
import random
import logging
from typing import Optional, Dict, Any
import httpx
from config import (
    USER_AGENTS,
    PROXY_URL,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    MAX_REDIRECTS,
)
from utils.safety import is_dangerous_url, is_dangerous_response_headers

logger = logging.getLogger(__name__)


def get_random_user_agent() -> str:
    """Returns a random modern User-Agent."""
    return random.choice(USER_AGENTS)


def get_default_headers(custom_referer: Optional[str] = None) -> Dict[str, str]:
    """Generates standard browser headers."""
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if custom_referer:
        headers["Referer"] = custom_referer
    return headers


def get_httpx_client(
    follow_redirects: bool = True,
    timeout: Optional[int] = None,
    verify: bool = True,
) -> httpx.AsyncClient:
    """Creates an httpx.AsyncClient with proxy and timeout configuration."""
    req_timeout = httpx.Timeout(timeout or REQUEST_TIMEOUT, connect=10.0)
    client_kwargs: Dict[str, Any] = {
        "follow_redirects": follow_redirects,
        "timeout": req_timeout,
        "max_redirects": MAX_REDIRECTS,
        "verify": verify,
    }
    if PROXY_URL:
        client_kwargs["proxy"] = PROXY_URL
    return httpx.AsyncClient(**client_kwargs)


async def safe_fetch_url(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Any] = None,
    json: Optional[Any] = None,
    follow_redirects: bool = True,
    referer: Optional[str] = None,
    timeout: Optional[int] = None,
) -> httpx.Response:
    """
    Executes an HTTP request with exponential backoff retry.
    Checks safety before and after request.
    """
    is_dangerous, reason = is_dangerous_url(url)
    if is_dangerous:
        raise ValueError(reason)

    req_headers = get_default_headers(referer)
    if headers:
        req_headers.update(headers)

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with get_httpx_client(follow_redirects=follow_redirects, timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    data=data,
                    json=json,
                )
                
                # Check headers for binary executable downloads
                is_danger_hdr, hdr_reason = is_dangerous_response_headers(dict(response.headers))
                if is_danger_hdr:
                    raise ValueError(hdr_reason)
                
                return response
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                sleep_time = 1.0 * (2 ** attempt)
                logger.warning("Request failed (%s). Retrying in %.1fs (attempt %d/%d)...", e, sleep_time, attempt + 1, MAX_RETRIES)
                await asyncio.sleep(sleep_time)
            else:
                break

    raise last_error or RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts.")
