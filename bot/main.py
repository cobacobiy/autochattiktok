import asyncio
import logging
import os

from bot.browser_loop import run_browser_loop
from bot.config import DRY_RUN, GINEE_CHAT_URL, LOG_DIR, LOG_FORMAT
from bot.health import start_health_server


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "bot.log")

    if LOG_FORMAT == "json":
        fmt = '{"time":"%(asctime)s", "level":"%(levelname)s", "module":"%(module)s", "message":"%(message)s"}'
    else:
        fmt = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main():
    setup_logging()
    logging.info("==========================================")
    logging.info(" Starting Ginee Chat Auto-Reply AI Bot   ")
    logging.info(" Target URL: %s", GINEE_CHAT_URL)
    logging.info(" Safety Mode DRY_RUN: %s", DRY_RUN)
    logging.info("==========================================")

    start_health_server(port=8080)

    try:
        asyncio.run(run_browser_loop())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")


if __name__ == "__main__":
    main()
