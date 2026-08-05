import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from bot import ginee_sender


class TestGineeSender(unittest.TestCase):

    @patch("bot.ginee_sender.first_visible")
    def test_send_empty_reply(self, mock_first_visible):
        async def run_test():
            page = MagicMock()
            page.wait_for_timeout = AsyncMock()
            result = await ginee_sender.send_ginee_reply(page, "")
            self.assertFalse(result)

        import asyncio
        asyncio.run(run_test())

    @patch("bot.ginee_sender.first_visible")
    def test_send_dry_run_simulation(self, mock_first_visible):
        async def run_test():
            page = MagicMock()
            page.wait_for_timeout = AsyncMock()
            input_loc = AsyncMock()
            input_loc.evaluate = AsyncMock(return_value="textarea")
            mock_first_visible.side_effect = [(input_loc, "textarea")]

            with patch("bot.ginee_sender.DRY_RUN", True):
                result = await ginee_sender.send_ginee_reply(page, "Tes Balasan")
                self.assertTrue(result)

        import asyncio
        asyncio.run(run_test())

    @patch("bot.ginee_sender.first_visible")
    def test_send_production_success(self, mock_first_visible):
        async def run_test():
            page = MagicMock()
            page.wait_for_timeout = AsyncMock()
            page.keyboard.insert_text = AsyncMock()
            input_loc = AsyncMock()
            input_loc.evaluate = AsyncMock(return_value="div")

            send_btn = AsyncMock()
            send_btn.click = AsyncMock()

            # First call returns input, second call returns send button, third call returns no error
            mock_first_visible.side_effect = [
                (input_loc, "input"),
                (send_btn, "button"),
                (None, None),
            ]

            with patch("bot.ginee_sender.DRY_RUN", False):
                result = await ginee_sender.send_ginee_reply(page, "Halo kak")
                self.assertTrue(result)
                send_btn.click.assert_called_once()

        import asyncio
        asyncio.run(run_test())

    @patch("bot.ginee_sender.first_visible")
    def test_send_production_failure_notification(self, mock_first_visible):
        async def run_test():
            page = MagicMock()
            page.wait_for_timeout = AsyncMock()
            page.keyboard.insert_text = AsyncMock()
            input_loc = AsyncMock()
            input_loc.evaluate = AsyncMock(return_value="div")

            send_btn = AsyncMock()
            send_btn.click = AsyncMock()

            err_loc = AsyncMock()

            mock_first_visible.side_effect = [
                (input_loc, "input"),
                (send_btn, "button"),
                (err_loc, "error_notif"),
            ]

            with patch("bot.ginee_sender.DRY_RUN", False):
                result = await ginee_sender.send_ginee_reply(page, "Halo kak")
                self.assertFalse(result)

        import asyncio
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
