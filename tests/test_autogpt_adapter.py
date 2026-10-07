import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("autogpt_adapter", ROOT / "scripts" / "autogpt_adapter.py")
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(adapter)


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status = status
        self.payload = payload or {}

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class AutoGPTAdapterTests(unittest.TestCase):
    def policy(self):
        return json.loads(
            (ROOT / "configs" / "zero-dollar-policy.json").read_text()
        )

    def zero_config(self, **overrides):
        values = {
            "enabled": True,
            "allow_network": True,
            "api_contract_verified": True,
            "cost_class": "zero",
            "allowed_agent_slug": "local/calculator",
        }
        values.update(overrides)
        return adapter.AutoGPTConfig(**values)

    def test_disabled_by_default(self):
        with self.assertRaises(adapter.AutoGPTPolicyError):
            adapter.validate(adapter.AutoGPTConfig(), self.policy())

    def test_network_is_explicit(self):
        config = self.zero_config(allow_network=False)
        with self.assertRaisesRegex(adapter.AutoGPTPolicyError, "network"):
            adapter.validate(config, self.policy())

    def test_unverified_api_contract_fails_closed(self):
        config = self.zero_config(api_contract_verified=False)
        with self.assertRaisesRegex(adapter.AutoGPTPolicyError, "contract"):
            adapter.validate(config, self.policy())

    def test_nonzero_cost_is_blocked(self):
        config = self.zero_config(cost_class="paid")
        with self.assertRaisesRegex(adapter.AutoGPTPolicyError, "cost class"):
            adapter.validate(config, self.policy())

    def test_remote_endpoint_is_blocked_in_absolute_zero(self):
        config = self.zero_config(base_url="https://backend.agpt.co")
        with self.assertRaisesRegex(adapter.AutoGPTPolicyError, "loopback"):
            adapter.validate(config, self.policy())

    def test_verified_zero_config_passes(self):
        adapter.validate(self.zero_config(), self.policy())

    def test_submission_requires_allowlisted_agent(self):
        config = self.zero_config(allowed_agent_slug="")
        with self.assertRaisesRegex(adapter.AutoGPTPolicyError, "ALLOW"):
            adapter.validate_submission(config, self.policy())

    def test_healthcheck_does_not_submit_task(self):
        config = self.zero_config()
        result = adapter.healthcheck(
            config,
            opener=lambda _request, timeout: FakeResponse(200),
        )
        self.assertEqual(result, {"ok": True, "status": 200})

    def test_submit_uses_verified_run_agent_route(self):
        config = self.zero_config()
        seen = {}

        def opener(request, timeout):
            seen["method"] = request.method
            seen["url"] = request.full_url
            seen["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse(200, {"execution_started": True})

        result = adapter.submit(
            "ignored",
            inputs={"x": 2},
            use_defaults=True,
            config=config,
            policy=self.policy(),
            opener=opener,
        )
        self.assertEqual(result, {"execution_started": True})
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(
            seen["url"],
            "http://127.0.0.1:8006/external-api/v1/tools/run-agent",
        )
        self.assertEqual(seen["body"]["username_agent_slug"], "local/calculator")
        self.assertTrue(seen["body"]["use_defaults"])

    def test_execution_results_uses_verified_route(self):
        config = self.zero_config()
        seen = {}

        def opener(request, timeout):
            seen["method"] = request.method
            seen["url"] = request.full_url
            return FakeResponse(200, {"status": "COMPLETED", "output": [{"answer": 4}]})

        result = adapter.get_execution_results(
            "graph-1",
            "exec-1",
            config=config,
            policy=self.policy(),
            opener=opener,
        )
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(seen["method"], "GET")
        self.assertEqual(
            seen["url"],
            "http://127.0.0.1:8006/external-api/v1/graphs/graph-1/executions/exec-1/results",
        )


if __name__ == "__main__":
    unittest.main()
