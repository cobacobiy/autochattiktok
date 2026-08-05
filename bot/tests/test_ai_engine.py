import os
import unittest

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
        test_path = "/tmp/test_unanswered.txt"
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


if __name__ == "__main__":
    unittest.main()
