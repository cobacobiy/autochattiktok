import logging
import re

log = logging.getLogger(__name__)

# Fallback UI candidates for Ginee Chat UI
ROOT_CONTAINER = ["#root", "#app", "main", "body"]

POPUP_DISMISS_BUTTONS = [
    "button:has-text('Tidak perlu')",
    "span:has-text('Tidak perlu')",
    "div:has-text('Tidak perlu')",
    "text=Tidak perlu, saya sudah familiar dengan Ginee Chat",
    "text=Tidak perlu",
    ".ant-modal-close",
]

SEMUA_PESAN_TAB = [
    ".ant-dropdown-menu-item:has-text('Semua Pesan')",
    ".ant-menu-item:has-text('Semua Pesan')",
    "li:has-text('Semua Pesan')",
    "span:has-text('Semua Pesan')",
    "div:has-text('Semua Pesan')",
    "text=Semua Pesan",
]

UNREPLIED_TAB = [
    ".ant-dropdown-menu-item:has-text('Belum Dibalas')",
    ".ant-menu-item:has-text('Belum Dibalas')",
    "li:has-text('Belum Dibalas')",
    "span:has-text('Belum Dibalas')",
    "div:has-text('Belum Dibalas')",
    "text=Belum Dibalas",
]

DROPDOWN_TRIGGER = [
    ".ant-dropdown-trigger",
    ".select-filter",
    "div[class*='select-filter']",
]

UNREAD_TAB = [
    ".ant-dropdown-menu-item:has-text('Belum Dibaca')",
    ".ant-menu-item:has-text('Belum Dibaca')",
    "li:has-text('Belum Dibaca')",
    "span:has-text('Belum Dibaca')",
    "div:has-text('Belum Dibaca')",
]

CHAT_ITEM = [
    ".ant-list-item:has(.ant-list-item-meta-description)",
    "li.ant-list-item:has(.ant-list-item-meta-description)",
    "li[class*='ant-list-item']:has(.ant-list-item-meta-description)",
    "[data-testid='conversation-item']",
    ".ginee-chat-item",
    ".conversation-item",
    "div[class*='chat-item']",
    "div[class*='conversationItem']",
]

CHAT_PANEL = [
    "[data-testid='chat-panel']",
    ".ginee-chat-panel",
    ".chat-detail-panel",
    "div[class*='chatPanel']",
    "div[class*='conversation-detail']",
]

MESSAGE_INPUT = [
    "textarea[placeholder*='Masukkan pesan']",
    "textarea[placeholder*='Type a message']",
    "textarea[placeholder*='Ketik pesan']",
    "textarea",
    "[contenteditable='true'][role='textbox']",
    "[contenteditable='true']",
]

SEND_BUTTON = [
    "button:has-text('Kirim')",
    "button:has-text('Send')",
    "button[type='submit']",
    "button[aria-label*='Send']",
    "button[aria-label*='Kirim']",
    "button[class*='send']",
]

SEND_ERROR_NOTIF = [
    "text=Gagal mengirim pesan",
    "text=Failed to send message",
    "div[class*='error-message']",
]

EMPTY_CHAT_STATE = [
    "text=Belum ada pesan",
    "text=No messages",
    "text=Tidak ada percakapan",
]


async def first_visible(scope, candidates, timeout=3000):
    """Find the first matching and visible element from candidates."""
    for cand in candidates:
        try:
            if isinstance(cand, str):
                loc = scope.locator(cand).first
                if await loc.is_visible(timeout=timeout):
                    return loc, cand
            elif isinstance(cand, dict):
                role = cand.get("role")
                name = cand.get("name")
                text = cand.get("text")
                if role and name:
                    loc = scope.get_by_role(role, name=name).first
                elif text:
                    loc = scope.get_by_text(text).first
                else:
                    continue
                if await loc.is_visible(timeout=timeout):
                    return loc, str(cand)
        except Exception:
            continue
    return None, None
