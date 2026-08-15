import threading
from dataclasses import dataclass, field


@dataclass
class BotState:
    daily_reply_date: str = ""
    daily_reply_counter: int = 0
    daily_skip_count: int = 0
    daily_unanswered_count: int = 0
    daily_ai_replied_count: int = 0
    has_setup_tabs: bool = False
    replied_cache: dict[str, float] = field(default_factory=dict)
    sent_messages: dict[str, set[str]] = field(default_factory=dict)
    knowledge_base: str = ""
    knowledge_answers: dict = field(default_factory=dict)

    # State fields for health monitoring and browser loop
    bot_status: str = "starting"
    last_error: str = ""
    last_successful_cycle: float = 0.0
    last_unreplied_filter_check: float = 0.0

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict:
        """Thread-safe snapshot for health endpoint."""
        with self._lock:
            return {
                "status": self.bot_status,
                "last_error": self.last_error,
                "last_successful_cycle": self.last_successful_cycle,
                "daily_replies": self.daily_reply_counter,
                "daily_skips": self.daily_skip_count,
                "daily_unanswered": self.daily_unanswered_count,
                "daily_ai_replied": self.daily_ai_replied_count,
                "cache_size": len(self.replied_cache),
                "knowledge_loaded": bool(self.knowledge_base),
                "knowledge_entries": len(self.knowledge_answers),
            }


bot_state = BotState()
