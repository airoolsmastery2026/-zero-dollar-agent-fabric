import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("autogpt_adapter", ROOT / "scripts" / "autogpt_adapter.py")
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(adapter)


class FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class AutoGPTAdapterTests(unittest.TestCase):
    def policy(self):
        return json.loads((ROOT / "configs" / "zero-dollar-policy.json").read_text())

    def test_disabled_by_default(self):
        config = adapter.AutoGPTConfig()
        with self.assertRaises(adapter.AutoGPTPolicyError):
            adapter.validate(config, self.policy())

    def test_network_is_explicit(self):
        config = adapter.AutoGPTConfig(
            enabled=True, allow_network=False, api_contract_verified=True
        )
        with self.assertRaisesRegex(adapter.AutoGPTPolicyError, "network"):
            adapter.validate(config, self.policy())

    def test_unverified_api_contract_fails_closed(self):
        config = adapter.AutoGPTConfig(
            enabled=True, allow_network=True, api_contract_verified=False
        )
        with self.assertRaisesRegex(adapter.AutoGPTPolicyError, "contract"):
            adapter.validate(config, self.policy())

    def test_nonzero_cost_is_blocked(self):
        config = adapter.AutoGPTConfig(
            enabled=True,
            allow_network=True,
            api_contract_verified=True,
            cost_class="paid",
        )
        with self.assertRaisesRegex(adapter.AutoGPTPolicyError, "cost class"):
            adapter.validate(config, self.policy())

    def test_verified_zero_config_passes(self):
        config = adapter.AutoGPTConfig(
            enabled=True,
            allow_network=True,
            api_contract_verified=True,
            cost_class="zero",
        )
        adapter.validate(config, self.policy())

    def test_healthcheck_does_not_submit_task(self):
        config = adapter.AutoGPTConfig(
            enabled=True, allow_network=True, api_contract_verified=True
        )
        result = adapter.healthcheck(
            config,
            opener=lambda _request, timeout: FakeResponse(200),
        )
        self.assertEqual(result, {"ok": True, "status": 200})

    def test_submit_is_fail_closed(self):
        with self.assertRaises(adapter.AutoGPTPolicyError):
            adapter.submit("test task")


if __name__ == "__main__":
    unittest.main()
