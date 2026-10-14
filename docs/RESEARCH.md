# Link Bypasser Research & Analysis

## 1. Cloned & Analyzed Repositories

| Repository | Author | License | Primary Purpose | Key Methods Identified |
| :--- | :--- | :--- | :--- | :--- |
| **Link-Bypasser-Bot** | TheCaduceus | MIT | Multi-shortener Telegram Bot | Cloudscraper sessions, external bypass APIs, adfly decryption, base64 unravelling |
| **PyBypass** | sanjit-sinha | MIT | Standalone Python bypass library | Form token parsing, timed POST requests, AdLinkFly standard flows, AdFly XOR cipher |
| **FZBypassBot** | RJRiajul / MysterySD | MIT | Async Telegram Bypass Bot | aiohttp client session, reCAPTCHA v3 simulation, AdLinkFly `transcript` pattern |
| **ouo-bypass** | xcscxr | Public Domain / MIT | Dedicated ouo.io/ouo.press solver | Google reCAPTCHA v3 anchor/reload token emulation using curl-cffi and requests |

---

## 2. Summary Comparison Table

| Repository | Supported Sites | Method | Status / Reliability |
| :--- | :--- | :--- | :--- |
| **TheCaduceus/Link-Bypasser-Bot** | ouo, gplinks, droplink, linkvertise, shareus, gyanilinks, adfly, shortlingly, sirigan, mdisk | Third-party APIs (bypass.vip, emilyx), cloudscraper form POST, adfly ysmm decrypt | **Mixed**: Third-party APIs frequently go down or require paid keys; native form POSTs and adfly decrypt logic remain functional. |
| **sanjit-sinha/PyBypass** | bitly, tinyurl, adfly, gplinks, shortest, linkvertise, sirigan, thinfi, 20+ AdLinkFly clones | Pure HTTP requests, XOR cipher, timing delays, form extraction via BeautifulSoup | **High for standard shorteners**: AdFly, bitly, tinyurl, thinfi work cleanly. AdLinkFly clones work when referrer requirements are kept up to date. |
| **RJRiajul/FZBypassBot** | 50+ AdLinkFly shorteners, ouo.io, gdtot, filepress, appdrive, mediafire | Async aiohttp, curl_cffi for Cloudflare TLS impersonation, headless reCAPTCHA v3 token generation | **High**: The `transcript` reusable pattern generalizes AdLinkFly bypasses across dozens of domains cleanly. |
| **xcscxr/ouo-bypass** | ouo.io, ouo.press | Simulates reCAPTCHA v3 invisible token exchange, extracts CSRF token, sends POST to `/go/{id}` | **Working**: Avoids heavy browser automation for ouo shorteners by querying Google's reCAPTCHA anchor/reload endpoints directly. |

---

## 3. Deep Dive into Bypass Mechanics

### A. Plain HTTP & Redirection Tracking
* **Targets**: `bit.ly`, `tinyurl.com`, `t.co`, `cutt.ly`, `is.gd`, `rebrand.ly`, `shorturl.at`, `v.gd`.
* **Mechanism**:
  1. Perform an async `HEAD` or `GET` request with custom desktop headers (`User-Agent`, `Accept`).
  2. Follow 301, 302, 303, 307, 308 redirects.
  3. Validate final target URL.
* **Fallback**: When redirects are done via HTML `<meta http-equiv="refresh" content="...">` or inline JS (`window.location.href = ...`), parse the HTML payload using regex or BeautifulSoup.

### B. Mathematical / Algorithmic Decryption
* **Targets**: `adf.ly` and its 60+ domain aliases (`j.gs`, `q.gs`, `ay.gy`, etc.), `sirigan.my.id`.
* **Mechanism**:
  - `adf.ly`: Extracts the JavaScript variable `ysmm = "..."` from the landing page. It splits the string into even and odd indices, recombines them, applies an XOR bitwise operation (`int(key[i]) ^ int(key[j])`), and base64 decodes the result. The destination URL is extracted cleanly without visiting ads or waiting.
  - `sirigan`: Repeated base64 decoding until reaching the final URL query parameter.

### C. AdLinkFly / MightyScripts Form Flow (The "Transcript" Pattern)
* **Targets**: `gplinks.co`, `shrinkme.io`, `droplink.co`, `tnlink.in`, `earnlink.io`, `shortner.in`, `urlshortx.com`, etc.
* **Mechanism**:
  1. Retrieve landing page with specific required `Referer` (e.g. intermediate blog or news domain).
  2. Parse the HTML form (commonly `<form id="go-link">` or hidden inputs) to capture `_csrfToken`, `ad_form_data`, and session cookies.
  3. Wait for the required server countdown timer (e.g. 3 to 10 seconds).
  4. Submit an AJAX `POST` request to `{domain}/links/go` with `X-Requested-With: XMLHttpRequest`.
  5. The server returns JSON: `{"status": "success", "url": "https://final-destination.com"}`.

### D. Google reCAPTCHA v3 Headless Emulation
* **Targets**: `ouo.io`, `ouo.press`.
* **Mechanism**:
  - Rather than launching a heavy browser or paying for captcha-solving APIs, `ouo` validates against Google's invisible reCAPTCHA v3 score.
  - The script makes a GET request to Google's reCAPTCHA anchor API (`https://www.google.com/recaptcha/api2/anchor?k=...&co=...`) to acquire an internal token.
  - It then executes a POST to `https://www.google.com/recaptcha/api2/reload` with client challenge parameters.
  - The returned token is submitted as `x-token` alongside the form token to `ouo.io/go/{id}` and `ouo.io/xreallcygo/{id}`.

### E. Multi-Layer Generic Fallback Chain
For any unknown or unhandled shortened URL, our engine executes a 5-step fallback pipeline:
1. **HTTP Redirect Follower**: Async HTTP client (`httpx` / `aiohttp`) following redirects.
2. **HTML Meta-Refresh / JavaScript Redirect Parser**: Extracts `meta refresh`, `location.href`, `location.replace`, and window redirect patterns.
3. **Cloudflare Evasion (`cloudscraper` / `curl_cffi`)**: Handles TLS fingerprinting and Cloudflare interstitial pages.
4. **Automated Form & Countdown Inspector**: Detects AdLinkFly-like forms, countdown scripts, and attempts automated AJAX resolution.
5. **Headless Browser (Playwright)**: Last-resort headless browser with network redirection interceptor and strict timeout.

---

## 4. Sanitation and Safety Rules Applied

1. **Stripped Malicious / Suspicious Logic**: Removed third-party tracking, arbitrary code execution, telemetry, and unverified sketchy API calls.
2. **Removed Hardcoded Credentials**: Cloned repos had hardcoded cookie hashes, tokens, and personal keys; all removed in favor of clean `.env` configuration.
3. **File Safety / Download Protection**: The bypasser is strictly a URL expander. If a resolved URL headers indicate a direct executable download (`.exe`, `.scr`, `.bat`, `.apk`, `.vbs`, `.cmd`, `.msi`, `.ps1`), or `Content-Disposition: attachment; filename="*.exe"`, the bot refuses to trigger download execution and returns the resolved link with a safety advisory.
