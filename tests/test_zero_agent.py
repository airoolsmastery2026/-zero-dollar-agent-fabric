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
        self.assertTrue(all(p["cost_class"] == "zero" for p in enabled))

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
