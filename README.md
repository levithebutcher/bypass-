# 🚀 Telegram Link Bypasser Bot

A production-ready, asynchronous Telegram bot built with `python-telegram-bot` (v20+) that automatically extracts and returns the direct destination URLs from shortened, gated, and monetized links.

Designed with an extensible plugin architecture, robust 5-stage generic fallback solver, automatic link extraction, SQLite result caching, per-user rate limiting, and executable safety guards.

---

## 🌟 Key Features

* **⚡ Auto Link Detection**: Simply send a message containing any link (or multiple links), and the bot automatically extracts, unshortens, and returns the final URLs.
* **🔌 Dynamic Plugin Architecture**: Every supported shortener is an independent module in [`bypassers/`](file:///c:/Users/Lenovo/Desktop/bypasser/bypassers/). Adding a new site requires only dropping a new `.py` file into the folder—no core modifications required.
* **🌐 17+ Supported Shortener Engines & Networks**:
  * **Standard Redirection**: Bit.ly, TinyURL, T.co, Cutt.ly, Is.gd, V.gd, Rebrand.ly.
  * **Cryptographic / Math Solvers**: AdF.ly network (XOR decryption of `ysmm`), Sirigan (multi-round Base64 unraveller).
  * **AdLinkFly / MightyScripts Network**: GPLinks, DropLink, ShrinkMe, TNLink, EarnLink, Shortner.in, Urlshortx, Try2Link, GyaniLinks, AdrinoLinks, RonyLink, XPShort, OnePageLink, MoneyKamalo, TinyFy, KrownLinks, and 30+ clones.
  * **Interactive / Captcha Solvers**: Ouo.io & Ouo.press (headless Google reCAPTCHA v3 invisible token emulation), Linkvertise network.
  * **File & Paste Unshorteners**: Thinfi, Shorte.st / Festyy network.
* **🛡 5-Stage Generic Fallback Chain**: Unknown or uncatalogued links pass through:
  1. *HTTP Redirect Follower* (with custom headers and cookie persistence).
  2. *HTML Meta-Refresh & Inline JavaScript Parser* (`location.href`, `location.replace`).
  3. *Cloudflare TLS Interstitial Evasion* (`curl_cffi` / `cloudscraper` with Chrome 120+ impersonation).
  4. *Automated Form & Countdown Inspector* (detects CSRF tokens and AJAX `/links/go` triggers).
  5. *Headless Browser (Playwright)* (runs headless Chromium with navigation interceptor).
* **🔒 Enterprise Safety & Security**:
  * **Executable Download Guard**: Blocks direct execution or downloading of `.exe`, `.bat`, `.cmd`, `.msi`, `.apk`, `.scr`, `.vbs`, `.ps1` files.
  * **Per-User Rate Limiting**: Enforces cooldowns to prevent spam and server flooding (with admin exemption).
  * **SQLite Cache**: Successfully bypassed links are stored in SQLite; identical links return instantly.
  * **Environment Isolation**: All credentials, tokens, and proxies reside strictly in `.env`.

---

## 📋 Project Structure

```
bypasser/
├── bot.py                  # Main Telegram bot application & command handlers
├── config.py               # Centralized configuration & environment loader
├── .env                    # Environment secrets (BOT_TOKEN, ADMIN_IDS, PROXY)
├── .env.example            # Template for environment configuration
├── requirements.txt        # Pinned Python package dependencies
├── CREDITS.md              # Open-source attributions & licenses
├── README.md               # Complete setup, deployment & usage guide
│
├── bypassers/              # Plugin directory (auto-discovered on startup)
│   ├── base.py             # Abstract Base Class (BaseBypasser)
│   ├── exceptions.py       # Custom exception hierarchy
│   ├── manager.py          # Dynamic plugin loader & dispatcher
│   ├── bitly.py            # Bit.ly bypasser
│   ├── tinyurl.py          # TinyURL bypasser
│   ├── tco.py              # X / Twitter t.co bypasser
│   ├── cuttly.py           # Cutt.ly bypasser
│   ├── isgd.py             # Is.gd & V.gd bypasser
│   ├── rebrandly.py        # Rebrandly bypasser
│   ├── ouo.py              # Ouo.io & Ouo.press (reCAPTCHA v3 solver)
│   ├── adfly.py            # Adf.ly network (XOR decryptor)
│   ├── shortest.py         # Shorte.st / Festyy network
│   ├── gplinks.py          # GPLinks network
│   ├── droplink.py         # DropLink network
│   ├── shrinkme.py         # ShrinkMe & Shrinke.me
│   ├── tnlink.py           # TNLink & TNShort
│   ├── thinfi.py           # Thinfi unshortener
│   ├── sirigan.py          # Sirigan base64 unraveller
│   ├── linkvertise.py      # Linkvertise network
│   ├── adlinkfly_network.py# Generalized AdLinkFly solver (30+ sites)
│   └── generic.py          # 5-stage generic fallback engine
│
├── utils/
│   ├── http.py             # Async HTTP client with backoff & rotating User-Agents
│   ├── safety.py           # Executable file & malicious download detection
│   ├── extractor.py        # URL regex extraction & cleanup
│   └── rate_limiter.py     # Per-user cooldown and rate limiter
│
├── db/
│   └── database.py         # Async SQLite link cache & stats tracker
│
├── docs/
│   └── RESEARCH.md         # Detailed repository research & method breakdown
│
└── tests/
    └── test_bypasser.py    # Unit tests covering all plugins & utilities
```

---

## 💻 Installation & Setup (Windows)

### 1. Prerequisites
Ensure you have **Python 3.10+** and **Git** installed on your Windows machine:
```powershell
python --version
git --version
```

### 2. Clone / Open Directory
```powershell
cd C:\Users\Lenovo\Desktop\bypasser
```

### 3. Create and Activate Virtual Environment
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once).*

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
playwright install chromium
```

### 5. Configure `.env`
Ensure your `.env` file exists and contains your Bot token:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789
RATE_LIMIT_SECONDS=3.0
MAX_CONCURRENT_LINKS=5
CACHE_ENABLED=true
ENABLE_PLAYWRIGHT=true
```

### 6. Run the Bot
```powershell
.\.venv\Scripts\python.exe bot.py
```

---

## 🐧 Linux / VPS Deployment

To run continuously on a Linux server:

1. Clone and install:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install --with-deps chromium
   ```
2. Create a systemd service (`/etc/systemd/system/bypasserbot.service`):
   ```ini
   [Unit]
   Description=Telegram Link Bypasser Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/bypasser
   ExecStart=/home/ubuntu/bypasser/.venv/bin/python bot.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
3. Start and enable service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now bypasserbot
   ```

---

## 🤖 Bot Commands & Usage

| Command | Description |
| :--- | :--- |
| `/start` | Welcome greeting and quick-start guide. |
| `/help` | Detailed assistance and troubleshooting. |
| `/bypass <link>` | Explicitly bypass one or more URLs. |
| `/sites` | Dynamically lists all supported shorteners from loaded plugins. |
| `/stats` | *(Admin only)* Displays user count, request count, cache hit rate, and top shorteners. |

### Sending Links Directly
Users do **not** need to type `/bypass`. You can simply send any raw text or forwarded message:
> *Check this link: https://bit.ly/3xyz and https://tinyurl.com/app*

The bot will automatically detect both links, show a `⏳ Bypassing...` progress banner, and update with the destinations and response times.

---

## 🧪 Running Unit Tests

Execute the comprehensive test suite (covers plugins, regex extractors, security guards, and database caching):
```powershell
.\.venv\Scripts\python.exe -m unittest tests/test_bypasser.py -v
```

---

## 🧩 Adding a New Shortener Plugin

To add support for a new shortener:
1. Create a new file in `bypassers/` (e.g. `bypassers/mysite.py`).
2. Subclass `BaseBypasser` and implement `domains`, `match()`, and `async bypass()`:

```python
from bypassers.base import BaseBypasser
from utils.http import safe_fetch_url

class MySiteBypasser(BaseBypasser):
    name = "MySite"
    domains = ["mysite.com", "mysite.net"]

    async def bypass(self, url: str) -> str:
        resp = await safe_fetch_url(url, method="GET", follow_redirects=True)
        return str(resp.url)
```
3. Restart the bot. The plugin manager will automatically detect, register, and display it in `/sites`!
