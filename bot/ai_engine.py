import datetime
import json
import logging
import os
import re

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bot.config import (
    AI_PROVIDER,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    AUTO_REPLIES,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MAX_AI_REPLY_LENGTH,
    OLLAMA_MODEL,
    OLLAMA_URL,
    UNANSWERED_PATH,
)
from bot.state import bot_state

log = logging.getLogger(__name__)


def get_auto_reply(message: str) -> str:
    """Fallback static reply when AI fails or exact match found."""
    msg = message.lower()
    for key, reply in AUTO_REPLIES.items():
        if key in msg:
            return reply
    for q, a in bot_state.knowledge_answers.items():
        if q in msg or msg in q:
            return a
    return ""


def log_unanswered_question(
    question: str,
    conversation_hash: str = "",
    store_channel: str = "",
    reason: str = "TIDAK_TAHU",
):
    """Write unanswered question to JSON Lines file without sensitive PII."""
    try:
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "store_channel": store_channel,
            "conversation_hash": conversation_hash,
            "reason": reason,
            "question": question[:200],  # truncate long prompts
        }
        os.makedirs(os.path.dirname(UNANSWERED_PATH), exist_ok=True)
        with open(UNANSWERED_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        bot_state.daily_unanswered_count += 1
        log.info("Logged unanswered question (reason: %s)", reason)
    except Exception as e:
        log.error("Failed to log unanswered question: %s", e)


def _build_system_prompt() -> str:
    kb_str = (
        bot_state.knowledge_base
        if bot_state.knowledge_base
        else "Belum ada informasi tambahan."
    )
    return (
        "Anda adalah Customer Service resmi toko online di Ginee Chat.\n"
        "Tugas Anda: Jawab pertanyaan pembeli secara ramah, sopan, dan singkat.\n\n"
        "ATURAN KETAT:\n"
        "1. Hanya gunakan fakta dari KNOWLEDGE BASE di bawah.\n"
        "2. Jika jawaban tidak ada di Knowledge Base, JANGAN MENGARANG! Keluarkan persis token: TIDAK_TAHU\n"
        "3. Jangan pernah memberikan janji stok, harga, resi, atau garansi jika tidak tertulis di Knowledge Base.\n"
        "4. Jawab maksimal 600 karakter. Jangan sertakan awalan seperti 'Jawaban:' atau 'CS:'.\n"
        "5. Jangan pernah meminta password, OTP, atau data keuangan pribadi.\n\n"
        f"--- KNOWLEDGE BASE ---\n{kb_str}\n----------------------"
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def call_ollama(prompt: str) -> str:
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{_build_system_prompt()}\n\nPembeli: {prompt}\nCS:",
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 250},
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def call_gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": _build_system_prompt()}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 250},
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        return ""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def call_claude(prompt: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 250,
        "system": _build_system_prompt(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        if content and "text" in content[0]:
            return content[0]["text"].strip()
        return ""


def generate_ai_reply(
    buyer_message: str, conversation_hash: str = "", store_channel: str = ""
) -> str:
    """Generate reply using configured AI provider with strict safety checks."""
    if not buyer_message.strip():
        return ""

    # Check static auto replies first
    static_reply = get_auto_reply(buyer_message)
    if static_reply:
        log.info("Matched static reply from knowledge base")
        return static_reply

    raw_response = ""
    try:
        if AI_PROVIDER == "ollama":
            raw_response = call_ollama(buyer_message)
        elif AI_PROVIDER == "gemini":
            raw_response = call_gemini(buyer_message)
        elif AI_PROVIDER == "claude":
            raw_response = call_claude(buyer_message)
        else:
            log.error("Unknown AI_PROVIDER: %s", AI_PROVIDER)
            return ""
    except Exception as e:
        log.error("AI Provider call failed: %s", e)
        log_unanswered_question(
            buyer_message, conversation_hash, store_channel, reason="AI_ERROR"
        )
        return ""

    response = raw_response.strip()

    # Safety checks
    if "TIDAK_TAHU" in response or not response:
        log.info("AI returned TIDAK_TAHU or empty response")
        log_unanswered_question(
            buyer_message, conversation_hash, store_channel, reason="TIDAK_TAHU"
        )
        return ""

    if len(response) > MAX_AI_REPLY_LENGTH:
        log.warning(
            "AI response exceeded max length (%d > %d)",
            len(response),
            MAX_AI_REPLY_LENGTH,
        )
        log_unanswered_question(
            buyer_message, conversation_hash, store_channel, reason="TOO_LONG"
        )
        return ""

    bot_state.daily_ai_replied_count += 1
    return response
