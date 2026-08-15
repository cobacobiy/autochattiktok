import logging
import os
import random
import time

log = logging.getLogger(__name__)


def cleanup_old_screenshots(log_dir: str, hours: int = 24):
    """Remove diagnostic screenshots older than specified hours."""
    try:
        if not os.path.exists(log_dir):
            return
        now = time.time()
        for f in os.listdir(log_dir):
            if f.endswith(".png"):
                filepath = os.path.join(log_dir, f)
                if os.stat(filepath).st_mtime < now - hours * 3600:
                    os.remove(filepath)
    except Exception as e:
        log.warning("Failed to clean up screenshots: %s", e)


def is_assistant_ai_msg(text: str) -> bool:
    """Check if the text indicates it's from Assistant AI or an Auto-Reply."""
    t = text.lower()
    return (
        "[asisten ai" in t
        or "asisten ai toko" in t
        or "ai asistent toko" in t
        or "asistent ai" in t
        or "dikirim oleh asisten ai" in t
        or "dikirim oleh asisten" in t
        or "shop ai assistant" in t
        or "[shop ai" in t
        or "sent by ai assistant" in t
        or "sent by shop ai" in t
        or "auto-reply" in t
        or "auto reply" in t
        or "balasan otomatis" in t
        or "kami akan segera membalas" in t
        or "we will reply shortly" in t
    )


async def do_human_delay(page, min_ms: int = 2000, max_ms: int = 4500):
    """Introduce randomized delay to emulate natural human behavior."""
    delay = random.randint(min_ms, max_ms)
    await page.wait_for_timeout(delay)
