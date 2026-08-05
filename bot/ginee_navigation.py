import logging

from bot.config import GINEE_CHAT_URL
from bot.selectors import UNREAD_TAB, UNREPLIED_TAB, first_visible

log = logging.getLogger(__name__)


async def navigate_to_ginee_chat(page):
    """Navigate to Ginee Chat and wait for initial loading."""
    log.info("Navigating to Ginee Chat: %s", GINEE_CHAT_URL)
    await page.goto(GINEE_CHAT_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)


async def check_login_status(page) -> bool:
    """Check if user is logged into Ginee Chat."""
    url = page.url.lower()
    if "login" in url or "accounts" in url or "passport" in url:
        log.warning("Redirected to login page: %s", page.url)
        return False

    # Check for unreplied tab or chat root
    tab_loc, _ = await first_visible(page, UNREPLIED_TAB, timeout=5000)
    if tab_loc:
        return True

    unread_loc, _ = await first_visible(page, UNREAD_TAB, timeout=5000)
    if unread_loc:
        return True

    # If URL is ginee chat root
    if "chat.ginee.com" in url:
        return True

    return False


async def open_unreplied_tab(page) -> bool:
    """Click on 'Belum Dibalas' tab, fallback to 'Belum Dibaca'."""
    tab_loc, selector_name = await first_visible(page, UNREPLIED_TAB, timeout=5000)
    if tab_loc:
        log.info("Clicking Unreplied tab using %s", selector_name)
        await tab_loc.click()
        await page.wait_for_timeout(2000)
        return True

    unread_loc, selector_name = await first_visible(page, UNREAD_TAB, timeout=5000)
    if unread_loc:
        log.info("Fallback: Clicking Unread tab using %s", selector_name)
        await unread_loc.click()
        await page.wait_for_timeout(2000)
        return True

    log.warning("Could not locate Unreplied or Unread tab")
    return False
