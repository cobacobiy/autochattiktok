import hashlib
import logging

from bot.config import ADMIN_KEYWORDS, SKIP_MESSAGES
from bot.dom_selectors import CHAT_ITEM, CHAT_PANEL
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
                    title_el = item.locator(".ant-list-item-meta-title")
                    buyer_name = (await title_el.inner_text()).strip() if await title_el.count() > 0 else ""

                    desc_el = item.locator(".ant-list-item-meta-description")
                    preview = (await desc_el.inner_text()).strip() if await desc_el.count() > 0 else ""

                    shop_el = item.locator(".shop-name")
                    store_name = (await shop_el.inner_text()).strip() if await shop_el.count() > 0 else "default_store"

                    if not buyer_name:
                        text = await item.inner_text()
                        lines = [line.strip() for line in text.splitlines() if line.strip()]
                        buyer_name = lines[0] if len(lines) > 0 else "unknown_buyer"
                        if len(lines) > 1 and store_name == "default_store":
                            store_name = lines[1]
                        preview = lines[3] if len(lines) > 3 else (lines[2] if len(lines) > 2 else preview)

                    channel = "ginee"
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
    bubble_locs = await page.locator(
        ".message-content, div[class*='message-content'], div[class*='bubble'], div[class*='message-item']"
    ).all()

    for loc in bubble_locs[-10:]:  # take last 10 messages
        try:
            text = (await loc.inner_text()).strip()
            if not text:
                continue

            style = (await loc.get_attribute("style") or "").lower()
            parent_style = ""
            try:
                parent_style = (await loc.locator("xpath=..").get_attribute("style") or "").lower()
            except Exception:
                pass

            grandparent_style = ""
            try:
                grandparent_style = (await loc.locator("xpath=../..").get_attribute("style") or "").lower()
            except Exception:
                pass

            combined_style = f"{style} {parent_style} {grandparent_style}"

            # Ensure we check the parent container's text as well to catch "[Balasan Otomatis]" labels placed outside the bubble
            full_check_text = text
            try:
                parent_text = (await loc.locator("xpath=..").inner_text()).strip()
                full_check_text += f" {parent_text}"
            except Exception:
                pass

            if "flex-start" in combined_style or "242, 245, 247" in combined_style:
                direction = "buyer"
            elif is_assistant_ai_msg(full_check_text):
                direction = "auto_reply"
            elif "flex-end" in combined_style or "238, 237, 254" in combined_style:
                direction = "seller"
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
