import os
import tempfile
import unittest
from unittest.mock import patch

from bot import ai_engine
from bot.state import bot_state


class TestAIEngine(unittest.TestCase):

    def setUp(self):
        bot_state.knowledge_answers = {
            "pengiriman": "Penjaringan Jakarta Utara",
            "stok": "Stok ready silakan diorder",
        }

    def test_get_auto_reply(self):
        reply = ai_engine.get_auto_reply("Pengiriman dari mana kak?")
        self.assertEqual(reply, "Pengiriman dilakukan dari Penjaringan, Jakarta Utara.")

    def test_log_unanswered_question(self):
        test_path = os.path.join(tempfile.gettempdir(), "test_unanswered.txt")
        ai_engine.UNANSWERED_PATH = test_path
        if os.path.exists(test_path):
            os.remove(test_path)

        ai_engine.log_unanswered_question("Apa ada diskon?", "hash123", "store:tiktok", "TIDAK_TAHU")
        self.assertTrue(os.path.exists(test_path))

        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Apa ada diskon?", content)
            self.assertIn("hash123", content)

        if os.path.exists(test_path):
            os.remove(test_path)

    @patch("bot.ai_engine.call_ollama")
    def test_generate_ai_reply_tidak_tahu(self, mock_call):
        mock_call.return_value = "TIDAK_TAHU"
        test_path = os.path.join(tempfile.gettempdir(), "test_unanswered_tt.txt")
        ai_engine.UNANSWERED_PATH = test_path
        if os.path.exists(test_path):
            os.remove(test_path)

        reply = ai_engine.generate_ai_reply("Berapa berat paket ini?", "hash_tt", "store:tiktok")
        self.assertEqual(reply, ai_engine.DEFAULT_REPLY)

        if os.path.exists(test_path):
            os.remove(test_path)

    @patch("bot.ai_engine.call_ollama")
    def test_generate_ai_reply_too_long(self, mock_call):
        mock_call.return_value = "A" * 700
        test_path = os.path.join(tempfile.gettempdir(), "test_unanswered_long.txt")
        ai_engine.UNANSWERED_PATH = test_path
        if os.path.exists(test_path):
            os.remove(test_path)

        reply = ai_engine.generate_ai_reply("Tolong jelaskan secara detail", "hash_long", "store:tiktok")
        self.assertEqual(reply, ai_engine.DEFAULT_REPLY)

        if os.path.exists(test_path):
            os.remove(test_path)


if __name__ == "__main__":
    unittest.main()
