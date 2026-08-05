import logging
import os

from bot.config import KNOWLEDGE_PATH
from bot.state import bot_state

log = logging.getLogger(__name__)


def parse_knowledge_answers():
    """Parse knowledge base into key-value pairs for quick matching."""
    bot_state.knowledge_answers.clear()
    lines = bot_state.knowledge_base.splitlines()

    # Format 1: T: / J:
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("T:"):
            question_parts = [line[2:].strip()]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if next_line.startswith("J:"):
                    answer = next_line[2:].strip()
                    question = " ".join(p for p in question_parts if p).lower()
                    if question and answer:
                        bot_state.knowledge_answers[question] = answer
                    break
                elif next_line.startswith(("T:", "#")):
                    break
                else:
                    if next_line:
                        question_parts.append(next_line)
                j += 1
        elif "|" in line and not line.startswith("#"):
            parts = line.split("|", 1)
            q = parts[0].strip().lower()
            a = parts[1].strip()
            if q and a:
                bot_state.knowledge_answers[q] = a
        i += 1


def load_knowledge_base():
    """Load store_knowledge.txt from disk."""
    if not os.path.exists(KNOWLEDGE_PATH):
        log.warning("Knowledge file not found at %s", KNOWLEDGE_PATH)
        bot_state.knowledge_base = ""
        bot_state.knowledge_answers.clear()
        return

    try:
        with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            bot_state.knowledge_base = content
            parse_knowledge_answers()
            log.info(
                "Knowledge base loaded (%d bytes, %d answers)",
                len(content),
                len(bot_state.knowledge_answers),
            )
    except Exception as e:
        log.error("Failed to load knowledge base: %s", e)
