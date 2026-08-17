import os
import tempfile
import unittest

from bot.browser_loop import cleanup_chromium_locks
from bot.config import DEFAULT_REPLY
from bot.ginee_parser import ChatMessage


class TestGineeBrowserHandover(unittest.TestCase):

    def test_cleanup_chromium_locks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lock1 = os.path.join(tmpdir, "SingletonLock")
            lock2 = os.path.join(tmpdir, "SingletonSocket")
            with open(lock1, "w") as f:
                f.write("test")
            os.symlink(lock1, lock2)

            self.assertTrue(os.path.exists(lock1))
            cleanup_chromium_locks(tmpdir)
            self.assertFalse(os.path.exists(lock1))
            self.assertFalse(os.path.lexists(lock2))

    def test_detect_previous_default_reply(self):
        messages = [
            ChatMessage("1", "Kak kira kira sampe kpn", "buyer"),
            ChatMessage("2", DEFAULT_REPLY, "seller"),
            ChatMessage("3", "Kak kira kira sampe kapan", "buyer"),
        ]
        has_previous_default = any(
            m.direction in ("seller", "auto_reply")
            and DEFAULT_REPLY.strip().lower() in m.text.strip().lower()
            for m in messages
        )
        self.assertTrue(has_previous_default)


if __name__ == "__main__":
    unittest.main()
