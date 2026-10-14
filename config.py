"""Configuration management for the Telegram Link Bypasser Bot."""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

# Bot Configuration
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

# Admin IDs (comma-separated list of Telegram user IDs)
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS: List[int] = [
    int(x.strip()) for x in raw_admins.split(",") if x.strip().isdigit()
]

# Allowed Users (if set, only these user IDs can use the bot; empty means public access)
raw_allowed = os.getenv("ALLOWED_USERS", "").strip()
ALLOWED_USERS: List[int] = [
    int(x.strip()) for x in raw_allowed.split(",") if x.strip().isdigit()
]

# Optional HTTP/SOCKS5 Proxy (e.g. "http://127.0.0.1:8080" or "socks5://127.0.0.1:9050")
PROXY_URL: Optional[str] = os.getenv("PROXY_URL", "").strip() or None

# Rate Limiting
RATE_LIMIT_SECONDS: float = float(os.getenv("RATE_LIMIT_SECONDS", "3.0"))

# Concurrency
MAX_CONCURRENT_LINKS: int = int(os.getenv("MAX_CONCURRENT_LINKS", "5"))

# Request settings
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "20"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))
MAX_REDIRECTS: int = int(os.getenv("MAX_REDIRECTS", "15"))

# Database & Cache settings
DATABASE_PATH: Path = BASE_DIR / "db" / os.getenv("DATABASE_FILE", "bypasser.db")
CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
CACHE_TTL_DAYS: int = int(os.getenv("CACHE_TTL_DAYS", "14"))

# Headless Browser (Playwright) Fallback
ENABLE_PLAYWRIGHT: bool = os.getenv("ENABLE_PLAYWRIGHT", "true").lower() in ("true", "1", "yes")
PLAYWRIGHT_TIMEOUT_MS: int = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "15000"))

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: Path = BASE_DIR / "bot.log"

# Rotating User Agents (Modern Desktop & Mobile Chrome/Edge/Firefox)
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]
