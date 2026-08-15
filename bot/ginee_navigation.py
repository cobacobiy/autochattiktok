import asyncio
import logging
import random

from bot.config import GINEE_CHAT_URL
from bot.dom_selectors import (
    DROPDOWN_TRIGGER,
    POPUP_DISMISS_BUTTONS,
    SEMUA_PESAN_TAB,
    UNREAD_TAB,
    UNREPLIED_TAB,
    first_visible,
)
from bot.utils import do_human_delay

log = logging.getLogger(__name__)


async def dismiss_ginee_popups(page) -> bool:
    """Dismiss Ginee Chat onboarding/desktop promo popups if present."""
    dismissed = False
    loc, selector_name = await first_visible(page, POPUP_DISMISS_BUTTONS, timeout=2000)
    if loc:
        log.info("Dismissing Ginee Chat popup ('Tidak perlu...') using selector %s", selector_name)
        try:
            await loc.click()
            await page.wait_for_timeout(1000)
            dismissed = True
        except Exception as e:
            log.warning("Failed to click popup dismiss button: %s", e)

    try:
        await page.evaluate("""() => {
            const modals = document.querySelectorAll('.ant-modal-root, .ant-modal-wrap, .ant-modal-mask');
            modals.forEach(el => el.remove());
        }""")
    except Exception:
        pass

    return dismissed


async def is_single_marketplace_layout(page) -> bool:
    """Check if page loaded in Single Marketplace layout (Gambar 2)."""
    try:
        menu_items = await page.locator(".ant-menu-item").all()
        if not menu_items:
            return False

        first_html = (await menu_items[0].inner_html()).lower()
        # In Unified All-Chat layout (Gambar 1), menu item 0 contains 'polymerization' icon
        if "polymerization" in first_html:
            return False

        # If polymerization icon is missing or single channel icon is active
        return True
    except Exception as e:
        log.debug("Error checking single marketplace layout: %s", e)
    return False


async def ensure_unified_chat_layout(page, max_retries=5) -> bool:
    """Ensure page is in Unified All-Chat layout (Gambar 1). Refresh randomly if in Gambar 2."""
    for attempt in range(1, max_retries + 1):
        await dismiss_ginee_popups(page)

        if await is_single_marketplace_layout(page):
            delay = round(random.uniform(2.0, 5.0), 2)
            log.warning(
                "Detected Single Marketplace layout (Gambar 2) on attempt %d/%d. Sleeping %.2fs and refreshing to switch to Unified All-Chat layout (Gambar 1)...",
                attempt,
                max_retries,
                delay,
            )
            await asyncio.sleep(delay)
            try:
                await page.reload(wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                await dismiss_ginee_popups(page)
            except Exception as e:
                log.warning("Failed to reload page: %s", e)
        else:
            log.info("Verified Unified All-Chat layout (Gambar 1)")
            return True

    log.warning("Max retries reached checking layout mode. Proceeding with current view.")
    return False


async def navigate_to_ginee_chat(page):
    """Navigate to Ginee Chat, ensure Unified All-Chat layout, and dismiss any popup."""
    log.info("Navigating to Ginee Chat: %s", GINEE_CHAT_URL)
    await page.goto(GINEE_CHAT_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)
    await ensure_unified_chat_layout(page)


async def auto_login_ginee(page) -> bool:
    """Auto-fill and submit Ginee login form with human-like delays if credentials exist."""
    from bot.config import GINEE_PASSWORD, GINEE_USERNAME
    if not GINEE_USERNAME or not GINEE_PASSWORD:
        return False

    url = page.url.lower()
    if "login" in url or "accounts" in url or "passport" in url:
        log.info("Attempting auto-login for user %s on %s", GINEE_USERNAME, page.url)
        try:
            # Human pause before filling credentials
            await do_human_delay(page, min_ms=1500, max_ms=3000)

            user_input = page.locator(
                "input#account, input[placeholder*='email' i], input[placeholder*='phone' i]"
            ).first
            if await user_input.is_visible(timeout=3000):
                await user_input.click()
                await page.wait_for_timeout(500)
                await user_input.fill(GINEE_USERNAME)
                await do_human_delay(page, min_ms=800, max_ms=1500)

            pass_input = page.locator("input#password, input[type='password'], input[name*='password']").first
            if await pass_input.is_visible(timeout=3000):
                await pass_input.click()
                await page.wait_for_timeout(500)
                await pass_input.fill(GINEE_PASSWORD)
                await do_human_delay(page, min_ms=1000, max_ms=2000)

            submit_btn = page.locator("button[type='submit'], button:has-text('Masuk'), button:has-text('Login')").first
            if await submit_btn.is_visible(timeout=3000):
                await submit_btn.click()
                log.info("Clicked login button. Waiting 5s for authentication redirect...")
                await page.wait_for_timeout(5000)
                await dismiss_ginee_popups(page)
                return True
        except Exception as e:
            log.warning("Auto-login attempt failed: %s", e)
    return False


async def check_login_status(page) -> bool:
    """Check if user is logged into Ginee Chat and attempt auto-login if credentials exist."""
    url = page.url.lower()
    if "login" in url or "accounts" in url or "passport" in url:
        log.warning("Redirected to login page: %s", page.url)
        if await auto_login_ginee(page):
            await page.wait_for_timeout(3000)
            if "chat.ginee.com" in page.url.lower():
                return True
        return False

    await dismiss_ginee_popups(page)

    # Check for list items, dropdown trigger, or chat root
    list_item = page.locator("li.ant-list-item, .ant-list-item").first
    if await list_item.is_visible(timeout=3000):
        return True

    trigger_loc, _ = await first_visible(page, DROPDOWN_TRIGGER, timeout=2000)
    if trigger_loc:
        return True

    if "chat.ginee.com" in url:
        return True

    return False


async def select_filter_option(page, target_options) -> bool:
    """Switch dropdown filter by clicking active filter select and target option."""
    await dismiss_ginee_popups(page)
    selects = await page.locator(".ant-select").all()
    for s in selects:
        if await s.is_visible():
            txt = await s.inner_text()
            if any(k in txt for k in ["Message", "Pesan", "Unreplied", "Belum Dibalas", "All"]):
                log.info("Clicking filter select trigger with text: %r", txt)
                inp = s.locator("input, .ant-select-selection-search-input, .ant-select-selector").first
                if await inp.is_visible():
                    await inp.click(force=True)
                else:
                    await s.click(force=True)
                await page.wait_for_timeout(1000)

                for target in target_options:
                    opt = page.locator(
                        f".ant-select-dropdown :text('{target}'), .ant-select-item:has-text('{target}'), div:has-text('{target}')"
                    ).last
                    if await opt.is_visible():
                        log.info("Clicking target filter option: %r", target)
                        await opt.click(force=True)
                        await page.wait_for_timeout(1500)
                        return True
    return False


async def select_filter_unreplied(page) -> bool:
    """Switch dropdown filter specifically to 'Belum Dibalas' / 'Unreplied'."""
    return await select_filter_option(page, ["Belum Dibalas", "Unreplied"])


async def select_filter_semua_pesan(page) -> bool:
    """Switch dropdown filter specifically to 'Semua Pesan' / 'All Message'."""
    return await select_filter_option(page, ["Semua Pesan", "All Message", "All"])
