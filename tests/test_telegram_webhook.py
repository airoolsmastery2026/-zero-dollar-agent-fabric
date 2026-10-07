import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("telegram_webhook", ROOT / "scripts" / "telegram_webhook.py")
tg = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(tg)


class TelegramWebhookTests(unittest.TestCase):
    def test_extract_text_update(self):
        update = {"message": {"chat": {"id": 10}, "from": {"id": 20}, "text": "/status"}}
        self.assertEqual(tg.extract_text_update(update), ("10", "20", "/status"))

    def test_ignores_non_message_update(self):
        self.assertIsNone(tg.extract_text_update({"callback_query": {}}))

    def test_update_claim_rejects_duplicate(self):
        import tempfile
        tg.STATE_DIR = Path(tempfile.mkdtemp())
        tg.UPDATE_STATE_PATH = tg.STATE_DIR / "telegram-updates.json"
        self.assertTrue(tg._claim_update(123))
        self.assertFalse(tg._claim_update(123))

    def test_webhook_handler_is_created(self):
        handler = tg.make_handler(
            tg.BotConfig(
                allowed_chat_ids=frozenset({"10"}),
                allowed_user_ids=frozenset({"20"}),
                webhook_secret="s",
                enabled=True,
            )
        )
        self.assertTrue(issubclass(handler, tg.BaseHTTPRequestHandler))


if __name__ == "__main__":
    unittest.main()
