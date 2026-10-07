import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bot_operator", ROOT / "scripts" / "bot_operator.py")
bot = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bot)


class BotOperatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        bot.STATE_DIR = Path(self.tmp.name)
        bot.AUDIT_PATH = bot.STATE_DIR / "bot-audit.jsonl"
        bot.APPROVAL_PATH = bot.STATE_DIR / "bot-approvals.json"

    def config(self, **kwargs):
        values = {
            "allowed_chat_ids": frozenset({"chat-1"}),
            "allowed_user_ids": frozenset({"user-1"}),
            "webhook_secret": "secret",
            "enabled": True,
        }
        values.update(kwargs)
        return bot.BotConfig(**values)

    def test_disabled_by_default(self):
        with self.assertRaisesRegex(bot.BotPolicyError, "disabled"):
            bot.verify_operator(bot.BotConfig(), chat_id="chat-1", user_id="user-1")

    def test_allowlist_required(self):
        with self.assertRaisesRegex(bot.BotPolicyError, "allowlist"):
            bot.verify_operator(
                self.config(allowed_chat_ids=frozenset(), allowed_user_ids=frozenset()),
                chat_id="chat-1",
                user_id="user-1",
            )

    def test_rejects_unknown_operator(self):
        with self.assertRaisesRegex(bot.BotPolicyError, "not allowlisted"):
            bot.verify_operator(self.config(), chat_id="other", user_id="user-1")

    def test_webhook_secret(self):
        bot.verify_webhook_secret(self.config(), "secret")
        with self.assertRaisesRegex(bot.BotPolicyError, "invalid"):
            bot.verify_webhook_secret(self.config(), "wrong")

    def test_parse_and_plan_safe_task(self):
        plan = bot.plan_message("/run research current repo structure")
        self.assertEqual(plan["action"], "safe_execute")

    def test_write_task_requires_approval(self):
        plan = bot.plan_message("/run update README")
        self.assertEqual(plan["action"], "approval_required")

    def test_destructive_task_is_disabled(self):
        plan = bot.plan_message("/run delete credentials")
        self.assertEqual(plan["action"], "disabled")

    def test_queue_and_resolve_approval(self):
        plan = bot.plan_message("/run commit the verified changes")
        item = bot.queue_approval(plan, chat_id="chat-1", user_id="user-1")
        self.assertEqual(item["status"], "pending")
        resolved = bot.resolve_approval(item["approval_id"], "approve", chat_id="chat-1", user_id="user-1")
        self.assertEqual(resolved["status"], "approved")

    def test_handle_message_never_executes(self):
        result = bot.handle_message(
            "/run create a report",
            config=self.config(),
            chat_id="chat-1",
            user_id="user-1",
        )
        self.assertEqual(result["status"], "approval_required")
        self.assertTrue(bot.APPROVAL_PATH.exists())
        self.assertTrue(bot.AUDIT_PATH.exists())


if __name__ == "__main__":
    unittest.main()
