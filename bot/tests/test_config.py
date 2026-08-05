import unittest

from bot import config


class TestConfig(unittest.TestCase):

    def test_default_values(self):
        self.assertEqual(config.GINEE_CHAT_URL, "https://chat.ginee.com/")
        self.assertTrue(config.DRY_RUN)
        self.assertFalse(config.HEADLESS)
        self.assertGreaterEqual(config.POLL_INTERVAL_SECONDS, 3)
        self.assertGreater(config.MAX_DAILY_REPLIES, 0)
        self.assertLessEqual(config.MAX_AI_REPLY_LENGTH, 600)

    def test_str2bool(self):
        self.assertTrue(config._str2bool("true"))
        self.assertTrue(config._str2bool("1"))
        self.assertTrue(config._str2bool("YES"))
        self.assertFalse(config._str2bool("false"))
        self.assertFalse(config._str2bool("0"))
        self.assertFalse(config._str2bool("NO"))


if __name__ == "__main__":
    unittest.main()
