"""Telegram Link Bypasser Bot

Built with python-telegram-bot (v20+, async), supporting concurrent processing,
dynamic plugin loading, result caching, rate limiting, and safety checks.
"""

import sys
import time
import asyncio
import logging
from typing import List, Tuple, Dict, Any
from urllib.parse import urlparse

from telegram import Update, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import (
    BOT_TOKEN,
    ADMIN_IDS,
    ALLOWED_USERS,
    MAX_CONCURRENT_LINKS,
    LOG_LEVEL,
    LOG_FILE,
)
from db.database import db
from utils.extractor import extract_urls
from utils.rate_limiter import rate_limiter
from bypassers.manager import bypasser_manager
from bypassers.exceptions import (
    BypassError,
    LinkDeadError,
    CaptchaRequiredError,
    SafetyBlockedError,
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("BypasserBot")


def check_authorization(user_id: int) -> bool:
    """Verifies whether the user is authorized to use the bot."""
    if not ALLOWED_USERS:
        return True
    return user_id in ALLOWED_USERS or user_id in ADMIN_IDS


async def process_single_link(url: str, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    """Bypasses a single link checking cache and measuring elapsed time."""
    async with semaphore:
        start_time = time.monotonic()
        
        # 1. Check SQLite cache
        cached = await db.get_cached(url)
        if cached:
            bypassed_url, bypasser_name = cached
            elapsed = time.monotonic() - start_time
            return {
                "url": url,
                "success": True,
                "destination": bypassed_url,
                "service": bypasser_name,
                "time": elapsed,
                "cached": True,
            }

        # 2. Perform live bypass
        try:
            destination, service_name = await bypasser_manager.bypass(url)
            elapsed = time.monotonic() - start_time
            
            # Save to cache
            await db.set_cached(url, destination, service_name)
            
            return {
                "url": url,
                "success": True,
                "destination": destination,
                "service": service_name,
                "time": elapsed,
                "cached": False,
            }
        except LinkDeadError as e:
            return {"url": url, "success": False, "error": f"Link is dead or expired: {e}"}
        except CaptchaRequiredError as e:
            return {"url": url, "success": False, "error": f"Interactive Captcha required: {e}"}
        except SafetyBlockedError as e:
            return {"url": url, "success": False, "error": f"Security Alert: {e}"}
        except BypassError as e:
            return {"url": url, "success": False, "error": f"{e}"}
        except Exception as e:
            logger.error("Unexpected error bypassing %s: %s", url, e, exc_info=True)
            return {"url": url, "success": False, "error": "Internal bypass engine error."}


async def handle_bypass_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, urls: List[str]) -> None:
    """Core logic to process, throttle, and reply to link bypass requests."""
    user = update.effective_user
    if not user:
        return

    # 1. Authorization check
    if not check_authorization(user.id):
        await update.effective_message.reply_text("⛔ You are not authorized to use this bot.")
        return

    # 2. Rate limiting check
    is_limited, wait_sec = rate_limiter.is_rate_limited(user.id)
    if is_limited:
        await update.effective_message.reply_text(
            f"⏳ Cooldown active. Please wait <b>{wait_sec:.1f}s</b> before sending another request.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Track user activity in DB
    await db.record_user(user.id)

    if not urls:
        await update.effective_message.reply_text(
            "ℹ️ No valid URLs found in your message.\nSend a link like <code>/bypass https://bit.ly/...</code> or simply send the link directly.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Cap URLs to prevent flood
    if len(urls) > MAX_CONCURRENT_LINKS:
        urls = urls[:MAX_CONCURRENT_LINKS]
        warning_suffix = f"\n<i>(Note: Only the first {MAX_CONCURRENT_LINKS} links are processed per request)</i>"
    else:
        warning_suffix = ""

    # Send progress message
    status_msg = await update.effective_message.reply_text(
        f"⚡ <b>Bypassing {len(urls)} link{'s' if len(urls) > 1 else ''}...</b> Please wait.",
        parse_mode=ParseMode.HTML,
    )

    # Concurrently process links
    semaphore = asyncio.Semaphore(3)
    tasks = [process_single_link(u, semaphore) for u in urls]
    results = await asyncio.gather(*tasks)

    # Format result message
    output_lines = []
    for res in results:
        orig = res["url"]
        if res["success"]:
            dest = res["destination"]
            service = res["service"]
            elapsed = res["time"]
            cached_badge = " ⚡<i>[Cached]</i>" if res.get("cached") else ""
            output_lines.append(
                f"🔗 <b>Original:</b> <code>{orig}</code>\n"
                f"🎯 <b>Destination:</b> <a href=\"{dest}\">{dest}</a>\n"
                f"🛠 <b>Service:</b> <code>{service}</code>{cached_badge}\n"
                f"⏱ <b>Time Taken:</b> {elapsed:.2f}s\n"
            )
        else:
            err = res["error"]
            output_lines.append(
                f"🔗 <b>Original:</b> <code>{orig}</code>\n"
                f"❌ <b>Error:</b> <i>{err}</i>\n"
            )

    final_text = "\n".join(output_lines) + warning_suffix

    # Disable link preview on telegram so it doesn't clutter
    no_preview = LinkPreviewOptions(is_disabled=True)
    try:
        await status_msg.edit_text(final_text, parse_mode=ParseMode.HTML, link_preview_options=no_preview)
    except Exception as e:
        logger.warning("Failed to edit status message (%s), sending as new message.", e)
        await update.effective_message.reply_text(final_text, parse_mode=ParseMode.HTML, link_preview_options=no_preview)


# -------------------------------------------------------------
# COMMAND HANDLERS
# -------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    welcome_text = (
        "👋 <b>Welcome to the Fast Link Bypasser Bot!</b>\n\n"
        "Send me any shortened or gated link, and I will instantly extract and return the direct destination URL.\n\n"
        "<b>📌 How to use:</b>\n"
        "• Send a link directly in chat (e.g. <code>https://bit.ly/xxxx</code>)\n"
        "• Send multiple links in one message\n"
        "• Or use <code>/bypass &lt;link&gt;</code>\n\n"
        "<b>⚙️ Commands:</b>\n"
        "/bypass &lt;link&gt; - Bypass link\n"
        "/sites - List supported shortener platforms\n"
        "/help - Help & troubleshooting\n"
        "/stats - View bot usage statistics (Admins only)"
    )
    await update.effective_message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command."""
    help_text = (
        "📖 <b>Link Bypasser Help Guide</b>\n\n"
        "<b>1. Supported Links:</b>\n"
        "Works with standard shorteners (Bit.ly, TinyURL, Cutt.ly, Is.gd, t.co), AdFly network, "
        "Ouo.io/press, GPLinks, DropLink, ShrinkMe, TNLink, Linkvertise, and 50+ AdLinkFly networks.\n\n"
        "<b>2. Automatic Fallback:</b>\n"
        "Unknown links run through our 5-stage solver (HTTP redirects, Meta-Refresh, Cloudflare solver, "
        "Form/countdown handler, and Headless Browser).\n\n"
        "<b>3. Security Protection:</b>\n"
        "Links leading directly to executable binaries (.exe, .bat, .apk, etc.) are safely halted to prevent harm."
    )
    await update.effective_message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def cmd_bypass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /bypass <url> command."""
    message_text = update.effective_message.text or ""
    # Strip command prefix
    args_text = message_text.partition(" ")[2]
    urls = extract_urls(args_text)
    if not urls:
        # Check if user replied to another message containing a link
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.text:
            urls = extract_urls(update.effective_message.reply_to_message.text)

    await handle_bypass_flow(update, context, urls)


async def cmd_sites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /sites command, listing all automatically loaded shortener plugins."""
    sites = bypasser_manager.get_supported_sites()
    
    site_names = [f"• <b>{s['name']}</b> ({', '.join(s['domains'][:3])}{'...' if len(s['domains']) > 3 else ''})" for s in sites]
    
    response = (
        f"🌐 <b>Supported Shortener Engines ({len(sites)} Plugins Loaded):</b>\n\n"
        + "\n".join(site_names)
        + "\n\n<i>+ Generic 5-Stage Fallback Chain for any other shortened link!</i>"
    )
    await update.effective_message.reply_text(response, parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin-only command to view usage statistics."""
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.effective_message.reply_text("⛔ This command is restricted to bot administrators.")
        return

    stats = await db.get_stats()
    top_services = "\n".join([f"  • {row[0]}: {row[1]} links" for row in stats["top_bypassers"]]) or "  None yet"

    stats_text = (
        "📊 <b>Bot Administration Statistics:</b>\n\n"
        f"👥 <b>Total Unique Users:</b> {stats['total_users']}\n"
        f"📨 <b>Total Requests:</b> {stats['total_requests']}\n"
        f"💾 <b>Cached Unique Links:</b> {stats['unique_links_cached']}\n"
        f"⚡ <b>Total Cache Hits:</b> {stats['total_cache_hits']}\n\n"
        f"🏆 <b>Top Solved Services:</b>\n{top_services}"
    )
    await update.effective_message.reply_text(stats_text, parse_mode=ParseMode.HTML)


async def handle_message_with_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles normal messages, auto-detecting any links sent without a command."""
    text = update.effective_message.text or update.effective_message.caption or ""
    urls = extract_urls(text)
    if urls:
        await handle_bypass_flow(update, context, urls)


async def post_init(application: Application) -> None:
    """Lifecycle hook called after application starts."""
    await db.init_db()
    logger.info("Bot application post_init completed successfully.")


def main() -> None:
    """Entry point for the Telegram Bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing! Please configure it in your .env file.")
        print("ERROR: BOT_TOKEN is missing in .env! Exiting.")
        sys.exit(1)

    print("🚀 Initializing Link Bypasser Telegram Bot...")
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register Command Handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("bypass", cmd_bypass))
    application.add_handler(CommandHandler("sites", cmd_sites))
    application.add_handler(CommandHandler("stats", cmd_stats))

    # Register Text Message Handler for auto-link detection
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_with_links)
    )

    print("✅ Bot is polling for updates. Press Ctrl+C to stop.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
