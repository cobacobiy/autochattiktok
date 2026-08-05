import unittest

from bot.ginee_parser import (
    build_conversation_hash,
    should_skip_buyer_message,
)


class TestGineeParser(unittest.TestCase):

    def test_build_conversation_hash(self):
        h1 = build_conversation_hash("StoreA", "TikTok", "c101", "Ready stok?")
        h2 = build_conversation_hash("StoreA", "TikTok", "c101", "ready stok? ")
        self.assertEqual(h1, h2)

        h3 = build_conversation_hash("StoreB", "TikTok", "c101", "Ready stok?")
        self.assertNotEqual(h1, h3)

    def test_should_skip_buyer_message(self):
        skip, reason = should_skip_buyer_message("ok kak")
        self.assertTrue(skip)
        self.assertEqual(reason, "skip_short_ack")

        skip_admin, reason_admin = should_skip_buyer_message("bisa kirim via grab instant?")
        self.assertTrue(skip_admin)
        self.assertIn("admin_keyword", reason_admin)

        skip_normal, _ = should_skip_buyer_message("Apakah warna hitam tersedia?")
        self.assertFalse(skip_normal)


if __name__ == "__main__":
    unittest.main()
