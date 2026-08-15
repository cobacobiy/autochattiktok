import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from bot.config import AI_PROVIDER, ANTHROPIC_MODEL, GEMINI_MODEL, OLLAMA_MODEL
from bot.state import bot_state

log = logging.getLogger(__name__)
BOT_START_TIME = time.time()


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        def _get_current_model():
            if AI_PROVIDER == "ollama":
                return OLLAMA_MODEL
            if AI_PROVIDER == "gemini":
                return GEMINI_MODEL
            return ANTHROPIC_MODEL

        state_snap = bot_state.snapshot()
        status = {
            "uptime_seconds": int(time.time() - BOT_START_TIME),
            "ai_provider": AI_PROVIDER,
            "ai_model": _get_current_model(),
        }
        status.update(state_snap)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())

    def log_message(self, format, *args):
        pass


def start_health_server(port: int = 8080):
    def _serve():
        try:
            server = HTTPServer(("0.0.0.0", port), HealthHandler)
            log.info("Started Health HTTP server on port %d", port)
            server.serve_forever()
        except Exception as e:
            log.error("Failed to start health server: %s", e)

    threading.Thread(target=_serve, daemon=True).start()
