import importlib.util
import json
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("zero_agent", ROOT / "scripts" / "zero_agent.py")
zero_agent = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(zero_agent)


class ZeroAgentTests(unittest.TestCase):
    def test_failure_classification(self):
        self.assertEqual(zero_agent.classify_failure("HTTP 429 quota exceeded", 1), "quota")
        self.assertEqual(zero_agent.classify_failure("authentication required", 1), "auth")
        self.assertEqual(zero_agent.classify_failure("requires a subscription, upgrade for access", 1), "subscription")
        self.assertEqual(zero_agent.classify_failure("account is not eligible", 1), "eligibility")
        self.assertEqual(zero_agent.classify_failure("invalid tool type: namespace", 1), "compatibility")
        self.assertEqual(zero_agent.classify_failure("C:/Users/u/.gemini/antigravity-cli/scratch/x.ts", 0), "workspace")
        self.assertEqual(zero_agent.classify_failure("boom", 1), "runtime")
        self.assertEqual(zero_agent.classify_failure("ok", 0), "success")

    def test_render_command(self):
        profile = {"command": ["agent", "--model", "{model}", "{prompt}"]}
        self.assertEqual(
            zero_agent.render_command(profile, "fix tests", "local-model"),
            ["agent", "--model", "local-model", "fix tests"],
        )

    def test_hard_lock_configuration(self):
        config = json.loads((ROOT / "configs" / "router.json").read_text())
        self.assertTrue(config["absolute_zero"])
        enabled = [p for p in config["profiles"] if p.get("enabled", True)]
        self.assertTrue(enabled)
        self.assertTrue(
            all(p["cost_class"] in zero_agent.ALLOWED_ZERO_COST_CLASSES for p in enabled)
        )
        self.assertFalse(any(p["cost_class"] == "paid" and p.get("enabled", True) for p in config["profiles"]))

    def test_write_mode_excludes_unverified_cloud_editors(self):
        config = json.loads((ROOT / "configs" / "router.json").read_text())
        profiles = {p["id"]: p for p in config["profiles"]}
        self.assertNotIn("write", profiles["antigravity-headless"]["modes"])
        self.assertNotIn("write", profiles["minimax-m3-free"]["modes"])
        self.assertIn("write", profiles["codex-local"]["modes"])

    def test_profile_allowed_respects_mode_and_cost(self):
        zero_read = {"enabled": True, "modes": ["read"], "cost_class": "zero"}
        paid_read = {"enabled": True, "modes": ["read"], "cost_class": "paid"}
        self.assertTrue(zero_agent.profile_allowed(zero_read, "read", True))
        self.assertFalse(zero_agent.profile_allowed(zero_read, "write", True))
        self.assertFalse(zero_agent.profile_allowed(paid_read, "read", True))

    def test_sanitized_env_strips_paid_keys(self):
        policy = json.loads((ROOT / "configs" / "zero-dollar-policy.json").read_text())
        previous = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "must-not-leak"
        try:
            env = zero_agent.sanitized_env({"env": {"LOCAL_ONLY": "1"}}, policy)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertEqual(env["LOCAL_ONLY"], "1")
        finally:
            if previous is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
