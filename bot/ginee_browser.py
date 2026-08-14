import logging
import time

from bot.ai_engine import generate_ai_reply
from bot.config import (
    DRY_RUN,
    MAX_DAILY_REPLIES,
    UNREPLIED_CHECK_INTERVAL_SECONDS,
)
from bot.ginee_navigation import (
    ensure_unified_chat_layout,
    select_filter_semua_pesan,
    select_filter_unreplied,
)
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

_last_unreplied_filter_check_time = 0.0


async def _process_conversations_in_current_view(page) -> int:
    """Helper function to parse and process buyer chats in active filter view without unnecessary clicking."""
    conversations = await parse_conversation_list(page)
    if not conversations:
        log.debug("No conversations found in current view")
        return 0

    processed_count = 0
    for conv in conversations:
        if bot_state.daily_reply_counter >= MAX_DAILY_REPLIES:
            break

        # Check preliminary hash from list view preview BEFORE clicking
        prelim_hash = build_conversation_hash(
            conv.store_name, conv.channel, conv.conversation_id, conv.preview
        )
        if prelim_hash in bot_state.replied_cache:
            log.debug("Skipping click for %s: preliminary snippet already in cache", conv.buyer_name)
            continue

        try:
            log.info("Processing buyer conversation: %r", conv)
            if conv.element:
                await conv.element.click(force=True)
                await do_human_delay(page, min_ms=1500, max_ms=3000)

            messages = await parse_chat_messages(page)
            if not messages:
                log.info("No messages found in detail panel for %s", conv.conversation_id)
                bot_state.replied_cache[prelim_hash] = time.time()
                continue

            last_msg = messages[-1]
            if last_msg.direction != "buyer":
                log.info(
                    "Skipping: Last message is not from buyer (direction=%s)",
                    last_msg.direction,
                )
                bot_state.replied_cache[prelim_hash] = time.time()
                continue

            # Check skip rules (ack, admin keywords)
            skip, reason = should_skip_buyer_message(last_msg.text)
            if skip:
                log.info("Skipping buyer message (%s): '%s'", reason, last_msg.text)
                bot_state.daily_skip_count += 1
                bot_state.replied_cache[prelim_hash] = time.time()
                continue

            # Deduplication key check
            conv_hash = build_conversation_hash(
                conv.store_name, conv.channel, conv.conversation_id, last_msg.text
            )
            if conv_hash in bot_state.replied_cache:
                log.info("Skipping: Conversation key already in replied cache")
                bot_state.replied_cache[prelim_hash] = time.time()
                continue

            # Compile all recent buyer requests and full chat thread context
            buyer_requests = [m.text for m in messages[-10:] if m.direction == "buyer" and m.text.strip()]
            chat_history_lines = []
            for msg in messages[-8:]:
                role = "Pembeli" if msg.direction == "buyer" else "CS"
                chat_history_lines.append(f"{role}: {msg.text}")

            prompt_context = (
                f"Permintaan Pembeli: {' | '.join(buyer_requests)}\n\n"
                "Riwayat Chat:\n" + "\n".join(chat_history_lines)
            )

            # Generate AI reply
            store_channel_info = f"{conv.store_name}:{conv.channel}"
            reply_text = generate_ai_reply(
                prompt_context,
                conversation_hash=conv_hash,
                store_channel=store_channel_info,
            )

            if not reply_text:
                log.info("AI did not yield a valid reply text")
                bot_state.replied_cache[prelim_hash] = time.time()
                continue

            # Double check before sending: re-parse last message
            recent_msgs = await parse_chat_messages(page)
            if recent_msgs and recent_msgs[-1].direction != "buyer":
                log.warning("Abort send: Seller or system replied since initial snapshot")
                bot_state.replied_cache[prelim_hash] = time.time()
                continue

            # Send reply
            success = await send_ginee_reply(page, reply_text)
            if success:
                bot_state.replied_cache[conv_hash] = time.time()
                bot_state.replied_cache[prelim_hash] = time.time()
                if not DRY_RUN:
                    bot_state.daily_reply_counter += 1
                processed_count += 1
                log.info("Successfully processed conversation %s", conv.conversation_id)

        except Exception as e:
            log.error("Error processing conversation %s: %s", conv.conversation_id, e)

    return processed_count


async def process_unreplied_chats(page) -> int:
    """Process chats: Standby on 'Semua Pesan', and check 'Belum Dibalas' filter once every 15 minutes."""
    global _last_unreplied_filter_check_time
    if bot_state.daily_reply_counter >= MAX_DAILY_REPLIES:
        log.warning("Daily reply limit reached (%d)", MAX_DAILY_REPLIES)
        return 0

    await ensure_unified_chat_layout(page)
    total_processed = 0
    now = time.time()

    # --- Scheduled Check: Select "Belum Dibalas" only once every 15 minutes (900s) ---
    if now - _last_unreplied_filter_check_time >= UNREPLIED_CHECK_INTERVAL_SECONDS or _last_unreplied_filter_check_time == 0.0:
        log.info("--- Pass 1: Scheduled 15-minute check on 'Belum Dibalas' filter ---")
        await select_filter_unreplied(page)
        processed_p1 = await _process_conversations_in_current_view(page)
        total_processed += processed_p1
        _last_unreplied_filter_check_time = now

        log.info("--- Pass 2: Switching filter back to 'Semua Pesan' ---")
        await select_filter_semua_pesan(page)
        processed_p2 = await _process_conversations_in_current_view(page)
        total_processed += processed_p2
    else:
        # Regular standby cycle on "Semua Pesan"
        processed_p2 = await _process_conversations_in_current_view(page)
        total_processed += processed_p2

    log.debug("Completed processing cycle. Standby active on 'Semua Pesan' filter.")
    return total_processed
