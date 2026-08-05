import logging
import time

from bot.ai_engine import generate_ai_reply
from bot.config import DRY_RUN, MAX_DAILY_REPLIES
from bot.ginee_navigation import open_unreplied_tab
from bot.ginee_parser import (
    build_conversation_hash,
    parse_chat_messages,
    parse_conversation_list,
    should_skip_buyer_message,
)
from bot.ginee_sender import send_ginee_reply
from bot.state import bot_state
from bot.utils import do_human_delay

log = logging.getLogger(__name__)


async def process_unreplied_chats(page) -> int:
    """Process top unreplied chat conversations."""
    if bot_state.daily_reply_counter >= MAX_DAILY_REPLIES:
        log.warning("Daily reply limit reached (%d)", MAX_DAILY_REPLIES)
        return 0

    await open_unreplied_tab(page)
    conversations = await parse_conversation_list(page)
    if not conversations:
        log.debug("No unreplied conversations found")
        return 0

    processed_count = 0
    for conv in conversations:
        if bot_state.daily_reply_counter >= MAX_DAILY_REPLIES:
            break

        try:
            log.info("Processing conversation: %r", conv)
            if conv.element:
                await conv.element.click()
                await do_human_delay(page, min_ms=1500, max_ms=3000)

            messages = await parse_chat_messages(page)
            if not messages:
                log.info("No messages found in detail panel for %s", conv.conversation_id)
                continue

            last_msg = messages[-1]
            if last_msg.direction != "buyer":
                log.info(
                    "Skipping: Last message is not from buyer (direction=%s)",
                    last_msg.direction,
                )
                continue

            # Check skip rules (ack, admin keywords)
            skip, reason = should_skip_buyer_message(last_msg.text)
            if skip:
                log.info("Skipping buyer message (%s): '%s'", reason, last_msg.text)
                bot_state.daily_skip_count += 1
                continue

            # Deduplication key check
            conv_hash = build_conversation_hash(
                conv.store_name, conv.channel, conv.conversation_id, last_msg.text
            )
            if conv_hash in bot_state.replied_cache:
                log.info("Skipping: Conversation key already in replied cache")
                continue

            # Generate AI reply
            store_channel_info = f"{conv.store_name}:{conv.channel}"
            reply_text = generate_ai_reply(
                last_msg.text,
                conversation_hash=conv_hash,
                store_channel=store_channel_info,
            )

            if not reply_text:
                log.info("AI did not yield a valid reply text")
                continue

            # Double check before sending: re-parse last message
            recent_msgs = await parse_chat_messages(page)
            if recent_msgs and recent_msgs[-1].direction != "buyer":
                log.warning("Abort send: Seller or system replied since initial snapshot")
                continue

            # Send reply
            success = await send_ginee_reply(page, reply_text)
            if success:
                bot_state.replied_cache[conv_hash] = time.time()
                if not DRY_RUN:
                    bot_state.daily_reply_counter += 1
                processed_count += 1
                log.info("Successfully processed conversation %s", conv.conversation_id)

        except Exception as e:
            log.error("Error processing conversation %s: %s", conv.conversation_id, e)

    return processed_count
