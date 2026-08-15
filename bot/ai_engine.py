import datetime
import json
import logging
import os
import shutil

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
    DEFAULT_REPLY,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MAX_AI_REPLY_LENGTH,
    OLLAMA_MODEL,
    OLLAMA_URL,
    UNANSWERED_PATH,
)
from bot.state import bot_state

log = logging.getLogger(__name__)

_http_client: httpx.Client | None = None

def _get_http_client() -> httpx.Client:
    """Get or create reusable httpx client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(timeout=120.0)
    return _http_client

MAX_UNANSWERED_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def get_auto_reply(message: str) -> str:
    """Fallback static reply when AI fails or exact match found."""
    msg = message.lower().strip()
    if not msg:
        return ""
            
    for q, a in bot_state.knowledge_answers.items():
        # Match if the question is in the buyer message
        if q in msg:
            return a
        # Or if the buyer message is significantly long and is part of a question
        if len(msg) > 10 and msg in q:
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
        parent_dir = os.path.dirname(UNANSWERED_PATH)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        if os.path.exists(UNANSWERED_PATH):
            size = os.path.getsize(UNANSWERED_PATH)
            if size > MAX_UNANSWERED_FILE_SIZE:
                backup = UNANSWERED_PATH + ".old"
                shutil.move(UNANSWERED_PATH, backup)
                log.info("Rotated unanswered file (%d bytes) to %s", size, backup)

        with open(UNANSWERED_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        bot_state.daily_unanswered_count += 1
        log.info("Logged unanswered question (reason: %s)", reason)
    except Exception as e:
        log.error("Failed to log unanswered question: %s", e)


def _build_system_prompt(store_channel: str = "") -> str:
    kb_str = (
        bot_state.knowledge_base
        if bot_state.knowledge_base
        else "Belum ada informasi tambahan."
    )
    store_info = f"\nAnda sedang menjawab chat untuk toko: {store_channel}\n" if store_channel else ""
    return (
        "Anda adalah Customer Service resmi toko online di Ginee Chat.\n"
        f"{store_info}"
        "Tugas Anda: Jawab pertanyaan pembeli secara to the point, singkat, dan tanpa basa-basi.\n\n"
        "ATURAN KETAT:\n"
        "1. Hanya gunakan fakta dari KNOWLEDGE BASE di bawah.\n"
        "2. Jika jawaban tidak ada di Knowledge Base, JANGAN MENGARANG! Keluarkan persis token: TIDAK_TAHU\n"
        "3. Jangan pernah memberikan janji stok, harga, resi, atau garansi jika tidak tertulis di Knowledge Base.\n"
        "4. Jawab langsung ke inti (to the point) dan singkat. DILARANG menggunakan salam/basa-basi seperti 'Halo', 'Selamat datang', atau kata pembuka/penutup berlebihan.\n"
        "5. Jawab maksimal 600 karakter. Jangan sertakan awalan seperti 'Jawaban:' atau 'CS:'.\n"
        "6. Jangan pernah meminta password, OTP, atau data keuangan pribadi.\n\n"
        f"--- KNOWLEDGE BASE ---\n{kb_str}\n----------------------"
    )


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=4),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def call_ollama(prompt: str, store_channel: str = "") -> str:
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{_build_system_prompt(store_channel)}\n\nRiwayat Percakapan Chat:\n{prompt}\n\nJawaban CS:",
        "stream": False,
        "keep_alive": -1,
        "options": {"temperature": 0.2, "num_predict": 250},
    }
    resp = _get_http_client().post(url, json=payload)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=4),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def call_gemini(prompt: str, store_channel: str = "") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    payload = {
        "system_instruction": {"parts": [{"text": _build_system_prompt(store_channel)}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 250},
    }
    resp = _get_http_client().post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates", [])
    if candidates and "content" in candidates[0]:
        parts = candidates[0]["content"].get("parts", [])
        if parts:
            return parts[0].get("text", "").strip()
    return ""


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=4),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def call_claude(prompt: str, store_channel: str = "") -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 250,
        "system": _build_system_prompt(store_channel),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    resp = _get_http_client().post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    content = data.get("content", [])
    if content and "text" in content[0]:
        return content[0]["text"].strip()
    return ""


def generate_ai_reply(
    prompt_context: str, 
    conversation_hash: str = "", 
    store_channel: str = "",
    buyer_message: str = ""
) -> str:
    """Generate reply using configured AI provider with strict safety checks."""
    if not prompt_context.strip():
        return ""

    # Check static auto replies first (only against the actual buyer message)
    static_reply = get_auto_reply(buyer_message)
    if static_reply:
        log.info("Matched static reply from knowledge base")
        return static_reply

    raw_response = ""
    try:
        if AI_PROVIDER == "ollama":
            raw_response = call_ollama(prompt_context, store_channel)
        elif AI_PROVIDER == "gemini":
            raw_response = call_gemini(prompt_context, store_channel)
        elif AI_PROVIDER == "claude":
            raw_response = call_claude(prompt_context, store_channel)
        else:
            log.error("Unknown AI_PROVIDER: %s", AI_PROVIDER)
            return ""
    except Exception as e:
        log.error("AI Provider call failed: %s", e)
        log_unanswered_question(
            buyer_message or prompt_context, conversation_hash, store_channel, reason="AI_ERROR"
        )
        return DEFAULT_REPLY

    response = raw_response.strip()
    for prefix in ["Jawaban CS:", "CS:", "Jawaban:"]:
        if response.startswith(prefix):
            response = response[len(prefix):].strip()

    # Safety checks: Strict TIDAK_TAHU enforcement
    if "TIDAK_TAHU" in response or not response:
        log.info("AI returned TIDAK_TAHU or empty response. Falling back to DEFAULT_REPLY.")
        log_unanswered_question(
            buyer_message or prompt_context, conversation_hash, store_channel, reason="TIDAK_TAHU"
        )
        return DEFAULT_REPLY

    if len(response) > MAX_AI_REPLY_LENGTH:
        log.warning(
            "AI response exceeded max length (%d > %d). Falling back to DEFAULT_REPLY.",
            len(response),
            MAX_AI_REPLY_LENGTH,
        )
        log_unanswered_question(
            buyer_message or prompt_context, conversation_hash, store_channel, reason="TOO_LONG"
        )
        return DEFAULT_REPLY

    bot_state.daily_ai_replied_count += 1
    return response
