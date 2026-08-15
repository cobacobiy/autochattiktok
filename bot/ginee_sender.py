import asyncio
import logging

from bot.config import DRY_RUN
from bot.dom_selectors import MESSAGE_INPUT, SEND_BUTTON, SEND_ERROR_NOTIF, first_visible
from bot.utils import do_human_delay
from bot.ginee_parser import parse_chat_messages

log = logging.getLogger(__name__)

# Single lock per process to ensure only one active send operation
_send_lock = asyncio.Lock()


async def send_ginee_reply(page, reply_text: str) -> bool:
    """Send reply to active Ginee Chat conversation."""
    async with _send_lock:
        if not reply_text.strip():
            log.warning("Empty reply text provided to sender")
            return False

        input_loc, input_sel = await first_visible(
            page, MESSAGE_INPUT, timeout=5000
        )
        if not input_loc:
            log.error("Could not find message input element")
            return False

        log.info("Found message input using selector: %s", input_sel)
        await input_loc.click()
        await do_human_delay(page, min_ms=500, max_ms=1000)

        # Fill text
        tag_name = await input_loc.evaluate("el => el.tagName.toLowerCase()")
        if tag_name in ("textarea", "input"):
            await input_loc.fill(reply_text)
        else:
            await page.keyboard.insert_text(reply_text)

        await do_human_delay(page, min_ms=800, max_ms=1500)

        if DRY_RUN:
            log.info("DRY_RUN=true: Simulating send. Text: '%s'", reply_text)
            return True

        # Mode produksi: cari tombol Kirim / Send
        send_btn, btn_sel = await first_visible(
            page, SEND_BUTTON, timeout=3000
        )
        if send_btn:
            log.info("Clicking send button using selector: %s", btn_sel)
            await send_btn.click()
        else:
            log.info("Send button not found, pressing Enter")
            await page.keyboard.press("Enter")

        await do_human_delay(page, min_ms=2000, max_ms=4000)

        # Check failure notification
        error_loc, err_sel = await first_visible(
            page, SEND_ERROR_NOTIF, timeout=2000
        )
        if error_loc:
            log.error("Send failed notification detected via %s", err_sel)
            return False

        # Verify outgoing bubble appeared
        try:
            verify_msgs = await parse_chat_messages(page)
            if verify_msgs:
                last = verify_msgs[-1]
                if last.direction == "seller" and reply_text[:50] in last.text:
                    log.info("Reply verified: outgoing bubble confirmed")
                    return True
            log.warning("Reply verification: outgoing bubble not confirmed, treating as uncertain success")
        except Exception as e:
            log.warning("Reply verification failed: %s", e)

        log.info("Reply sent successfully (unverified)")
        return True
