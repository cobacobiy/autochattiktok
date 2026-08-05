import logging
import os

def _str2bool(val: str, default: bool = False) -> bool:
    if val is None:
        return default
    v = str(val).strip().lower()
    if v in ("true", "1", "t", "y", "yes"):
        return True
    if v in ("false", "0", "f", "n", "no"):
        return False
    return default

LOG_DIR = os.getenv("LOG_DIR", "/data/logs")
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()

PROFILE_DIR = os.getenv("PROFILE_DIR", "/data/ginee-profile")
GINEE_CHAT_URL = os.getenv("GINEE_CHAT_URL", "https://chat.ginee.com/")
HEADLESS = _str2bool(os.getenv("HEADLESS", "false"), default=False)
DRY_RUN = _str2bool(os.getenv("DRY_RUN", "true"), default=True)

POLL_INTERVAL_SECONDS = max(3, int(os.getenv("POLL_INTERVAL", "8")))
MAX_DAILY_REPLIES = max(1, int(os.getenv("MAX_DAILY_REPLIES", "500")))
MAX_CACHE_SIZE = max(10, int(os.getenv("MAX_CACHE_SIZE", "1000")))

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
for suffix in ["/api/generate", "/api/chat", "/api"]:
    if OLLAMA_URL.endswith(suffix):
        OLLAMA_URL = OLLAMA_URL[:-len(suffix)]
        break
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

UNANSWERED_PATH = os.getenv("UNANSWERED_PATH", "/app/unanswered_questions.txt")
KNOWLEDGE_PATH = os.getenv("KNOWLEDGE_PATH", "/app/store_knowledge.txt")

BROWSER_LIFETIME_SECONDS = int(os.getenv("BROWSER_LIFETIME", "21600"))
CACHE_EXPIRY_SECONDS = 86400
KNOWLEDGE_RELOAD_CYCLES = 120
HEARTBEAT_CYCLES = 60
MAX_CHAT_SCAN_ATTEMPTS = 30
MAX_AI_REPLY_LENGTH = 600

DEFAULT_REPLY = os.getenv("DEFAULT_REPLY", "Ada yang bisa dibantu?")

AUTO_REPLIES = {
    "harga": "Harga sudah tertera di halaman produk. Silakan cek produk kami ya kak 😊",
    "stok": "Stok produk masih tersedia, silakan diorder kak!",
    "ongkir": "Ongkir dihitung otomatis oleh sistem sesuai dengan alamat lokasi pengiriman.",
    "garansi": "Produk bergaransi sesuai syarat dan ketentuan garansi toko kami.",
    "pengiriman": "Pengiriman dilakukan dari Penjaringan, Jakarta Utara.",
    "dari mana": "Pengiriman dari Penjaringan, Jakarta Utara.",
}

SKIP_MESSAGES = {
    "ok", "oke", "baik", "baik kak", "baik ka", "oke kak", "oke ka",
    "siap", "terima kasih", "makasih", "sami sami", "mks", "thx", "ty",
    "ok kak", "ok ka", "sip", "siap kak", "siap ka", "makasih kak", "makasih ka",
    "nuhun", "suwun", "makasih banyak", "terima kasih banyak",
    "tolong kirim sesuai pesanan", "sesuai pesanan ya", "sesuai pesanan",
    "sama sama", "sama2", "samaa2", "sama-sama", "sama2 kak", "sama2 ka",
    "y", "ya", "ya kak", "ya ka", "iya", "iya kak", "iya ka", "y kak", "y ka"
}

ADMIN_KEYWORDS = {
    "instan", "instant", "gojek", "grab", "sameday", "same day", "gosend"
}

if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
    logging.warning("AI_PROVIDER is gemini but GEMINI_API_KEY is not set!")
elif AI_PROVIDER == "claude" and not ANTHROPIC_API_KEY:
    logging.warning("AI_PROVIDER is claude but ANTHROPIC_API_KEY is not set!")
