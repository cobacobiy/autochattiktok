import asyncio
import datetime
import logging
import os
import time

from playwright.async_api import async_playwright

from bot.config import (
    BROWSER_LIFETIME_SECONDS,
    CACHE_EXPIRY_SECONDS,
    HEADLESS,
    HEARTBEAT_CYCLES,
    KNOWLEDGE_RELOAD_CYCLES,
    LOG_DIR,
    POLL_INTERVAL_SECONDS,
    PROFILE_DIR,
)
from bot.ginee_browser import process_unreplied_chats
from bot.ginee_navigation import check_login_status, navigate_to_ginee_chat
from bot.knowledge import load_knowledge_base
from bot.state import bot_state
from bot.utils import cleanup_old_screenshots

log = logging.getLogger(__name__)


def reset_daily_counters_if_needed():
    today = datetime.date.today().isoformat()
    if bot_state.daily_reply_date != today:
        log.info("Resetting daily counters for new date: %s", today)
        bot_state.daily_reply_date = today
        bot_state.daily_reply_counter = 0
        bot_state.daily_skip_count = 0
        bot_state.daily_unanswered_count = 0
        bot_state.daily_ai_replied_count = 0


def cleanup_expired_cache():
    now = time.time()
    expired_keys = [
        k
        for k, timestamp in bot_state.replied_cache.items()
        if now - timestamp > CACHE_EXPIRY_SECONDS
    ]
    for k in expired_keys:
        del bot_state.replied_cache[k]
    if expired_keys:
        log.info("Cleaned up %d expired cache items", len(expired_keys))


async def run_browser_loop():
    """Main Playwright loop with lifetime restart and error recovery."""
    load_knowledge_base()
    consecutive_errors = 0

    while True:
        log.info("Starting new browser session cycle")
        start_time = time.time()
        os.makedirs(PROFILE_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)

        async with async_playwright() as p:
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=PROFILE_DIR,
                    headless=HEADLESS,
                    viewport={"width": 1440, "height": 900},
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                page = context.pages[0] if context.pages else await context.new_page()

                await navigate_to_ginee_chat(page)

                cycle_count = 0
                while True:
                    reset_daily_counters_if_needed()
                    cycle_count += 1

                    # Heartbeat log
                    if cycle_count % HEARTBEAT_CYCLES == 0:
                        log.info(
                            "Heartbeat cycle %d. Daily replies: %d, Cache size: %d",
                            cycle_count,
                            bot_state.daily_reply_counter,
                            len(bot_state.replied_cache),
                        )
                        cleanup_expired_cache()
                        cleanup_old_screenshots(LOG_DIR)

                    # Reload knowledge periodically
                    if cycle_count % KNOWLEDGE_RELOAD_CYCLES == 0:
                        load_knowledge_base()

                    is_logged_in = await check_login_status(page)
                    if not is_logged_in:
                        bot_state.bot_status = "waiting_login"
                        log.warning(
                            "User not logged in or Ginee Chat root not detected. Waiting for manual login..."
                        )
                        await asyncio.sleep(15)
                        continue

                    bot_state.bot_status = "running"

                    # Process unreplied chats
                    await process_unreplied_chats(page)
                    
                    bot_state.last_successful_cycle = time.time()
                    consecutive_errors = 0

                    # Lifetime check (restart every 6 hours)
                    if time.time() - start_time > BROWSER_LIFETIME_SECONDS:
                        log.info("Browser lifetime exceeded limit, restarting session...")
                        break

                    await asyncio.sleep(POLL_INTERVAL_SECONDS)

                await context.close()

            except Exception as e:
                bot_state.bot_status = "error"
                consecutive_errors += 1
                backoff = min(10 * (2 ** consecutive_errors), 300)
                log.error("Unhandled error in browser loop (attempt %d, backoff %ds): %s", consecutive_errors, backoff, e, exc_info=True)
                await asyncio.sleep(backoff)
