import hashlib
import logging

from bot.config import ADMIN_KEYWORDS, SKIP_MESSAGES
from bot.selectors import CHAT_ITEM, CHAT_PANEL
from bot.utils import is_assistant_ai_msg

log = logging.getLogger(__name__)


class ConversationSummary:

    def __init__(
        self,
        conversation_id: str,
        buyer_name: str,
        store_name: str,
        channel: str,
        preview: str,
        unread: bool = False,
        unreplied: bool = False,
        element=None,
    ):
        self.conversation_id = conversation_id
        self.buyer_name = buyer_name
        self.store_name = store_name
        self.channel = channel
        self.preview = preview
        self.unread = unread
        self.unreplied = unreplied
        self.element = element

    def __repr__(self):
        return (
            f"<ConversationSummary id={self.conversation_id} buyer='{self.buyer_name}' "
            f"store='{self.store_name}' channel='{self.channel}'>"
        )


class ChatMessage:

    def __init__(
        self,
        message_id: str | None,
        text: str,
        direction: str,  # "buyer", "seller", "system", "unknown"
        sent_at: str | None = None,
    ):
        self.message_id = message_id
        self.text = text
        self.direction = direction
        self.sent_at = sent_at

    def __repr__(self):
        return f"<ChatMessage dir={self.direction} text='{self.text[:30]}'>"


def build_conversation_hash(
    store_name: str, channel: str, conversation_id: str, last_message_text: str
) -> str:
    """Build unique SHA256 cache key for deduplication."""
    norm_text = last_message_text.strip().lower()
    raw = f"{store_name}|{channel}|{conversation_id}|{norm_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def parse_conversation_list(page) -> list[ConversationSummary]:
    """Parse up to top 5 unreplied conversation items from sidebar."""
    conversations = []
    for selector in CHAT_ITEM:
        items = await page.locator(selector).all()
        if items:
            for item in items[:5]:
                try:
                    text = await item.inner_text()
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    buyer_name = lines[0] if len(lines) > 0 else "unknown_buyer"
                    store_name = lines[1] if len(lines) > 1 else "default_store"
                    channel = lines[2] if len(lines) > 2 else "ginee"
                    preview = lines[3] if len(lines) > 3 else ""

                    conv_id = (
                        await item.get_attribute("data-id")
                        or await item.get_attribute("id")
                        or f"{store_name}_{channel}_{buyer_name}"
                    )

                    conversations.append(
                        ConversationSummary(
                            conversation_id=conv_id,
                            buyer_name=buyer_name,
                            store_name=store_name,
                            channel=channel,
                            preview=preview,
                            unreplied=True,
                            element=item,
                        )
                    )
                except Exception as e:
                    log.warning("Failed to parse conversation item: %s", e)
            if conversations:
                break
    return conversations


async def parse_chat_messages(page) -> list[ChatMessage]:
    """Parse recent chat messages from active chat panel."""
    messages = []
    panel_loc = None
    for cand in CHAT_PANEL:
        loc = page.locator(cand).first
        if await loc.is_visible(timeout=1000):
            panel_loc = loc
            break

    scope = panel_loc if panel_loc else page

    # Look for message bubbles
    bubble_locs = await scope.locator(
        "div[class*='bubble'], div[class*='message-item'], div[class*='msg-item']"
    ).all()
    for loc in bubble_locs[-10:]:  # take last 10 messages
        try:
            text = (await loc.inner_text()).strip()
            if not text:
                continue

            cls = (await loc.get_attribute("class") or "").lower()
            dir_attr = (
                await loc.get_attribute("data-direction") or ""
            ).lower()

            if dir_attr == "buyer" or "left" in cls or "buyer" in cls:
                direction = "buyer"
            elif (
                dir_attr == "seller"
                or "right" in cls
                or "seller" in cls
                or is_assistant_ai_msg(text)
            ):
                direction = "seller"
            elif "system" in cls or "notice" in cls:
                direction = "system"
            else:
                direction = "unknown"

            msg_id = await loc.get_attribute("data-msg-id")

            messages.append(
                ChatMessage(
                    message_id=msg_id,
                    text=text,
                    direction=direction,
                )
            )
        except Exception as e:
            log.warning("Failed to parse message bubble: %s", e)

    return messages


def should_skip_buyer_message(text: str) -> tuple[bool, str]:
    """Check if buyer message should be skipped."""
    t = text.strip().lower()
    if t in SKIP_MESSAGES:
        return True, "skip_short_ack"
    for kw in ADMIN_KEYWORDS:
        if kw in t:
            return True, f"admin_keyword_{kw}"
    return False, ""
