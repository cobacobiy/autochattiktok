import unittest

from bot import knowledge
from bot.state import bot_state


class TestKnowledge(unittest.TestCase):

    def setUp(self):
        bot_state.knowledge_base = ""
        bot_state.knowledge_answers.clear()

    def test_parse_t_j_format(self):
        bot_state.knowledge_base = (
            "T: jam operasional\nJ: 08.00 - 17.00 WIB\n\nT: garansi\nJ: 30 hari"
        )
        knowledge.parse_knowledge_answers()
        self.assertIn("jam operasional", bot_state.knowledge_answers)
        self.assertEqual(
            bot_state.knowledge_answers["jam operasional"], "08.00 - 17.00 WIB"
        )
        self.assertEqual(bot_state.knowledge_answers["garansi"], "30 hari")

    def test_parse_pipe_format(self):
        bot_state.knowledge_base = (
            "lokasi toko | Jakarta Utara\nmetode bayar | COD & Transfer"
        )
        knowledge.parse_knowledge_answers()
        self.assertEqual(
            bot_state.knowledge_answers["lokasi toko"], "Jakarta Utara"
        )
        self.assertEqual(
            bot_state.knowledge_answers["metode bayar"], "COD & Transfer"
        )


if __name__ == "__main__":
    unittest.main()
