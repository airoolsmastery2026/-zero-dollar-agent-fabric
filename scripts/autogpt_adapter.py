#!/usr/bin/env python3
"""Zero-$ guarded adapter for a self-hosted AutoGPT Platform API.

The adapter talks only to an explicitly configured AutoGPT HTTP endpoint.
In absolute-zero mode it requires a loopback endpoint, zero cost class,
explicit network opt-in, and an explicit contract verification flag.

Verified upstream contract (AutoGPT master, inspected 2026-10-07):
  POST /external-api/v1/tools/run-agent
  GET  /external-api/v1/graphs/{graph_id}/executions/{execution_id}/results

This file implements only the HTTP boundary; it does not vendor AutoGPT
platform code or assume that AutoGPT itself is cost-free.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY_PATH = os.path.join(ROOT, "configs", "zero-dollar-policy.json")
VERIFIED_CONTRACT = "autogpt-external-api-v1-tools-run-agent@2026-10-07"


@dataclass(frozen=True)
class AutoGPTConfig:
    base_url: str = "http://127.0.0.1:8006"
    enabled: bool = False
    allow_network: bool = False
    cost_class: str = "zero"
    api_contract_verified: bool = False
    api_key: str = ""
    allowed_agent_slug: str = ""


class AutoGPTPolicyError(RuntimeError):
    pass


def load_policy() -> dict:
    with open(POLICY_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def config_from_env() -> AutoGPTConfig:
    return AutoGPTConfig(
        base_url=os.getenv("AUTOGPT_BASE_URL", "http://127.0.0.1:8006").rstrip("/"),
        enabled=os.getenv("AUTOGPT_ENABLED", "false").lower() == "true",
        allow_network=os.getenv("AUTOGPT_ALLOW_NETWORK", "false").lower() == "true",
        cost_class=os.getenv("AUTOGPT_COST_CLASS", "zero"),
        api_contract_verified=os.getenv("AUTOGPT_API_CONTRACT_VERIFIED", "false").lower() == "true",
        api_key=os.getenv("AUTOGPT_API_KEY", ""),
        allowed_agent_slug=os.getenv("AUTOGPT_ALLOWED_AGENT_SLUG", "").strip(),
    )


def _is_loopback(url: str) -> bool:
    from urllib.parse import urlparse

    host = urlparse(url).hostname
    return host in {"127.0.0.1", "::1", "localhost"}


def validate(config: AutoGPTConfig, policy: dict) -> None:
    if not config.enabled:
        raise AutoGPTPolicyError("AutoGPT adapter is disabled by default.")
    if policy.get("absolute_zero", True) and config.cost_class != "zero":
        raise AutoGPTPolicyError("AutoGPT runtime rejected: cost class is not zero.")
    if not config.allow_network:
        raise AutoGPTPolicyError("AutoGPT network access is disabled by default.")
    if not config.api_contract_verified:
        raise AutoGPTPolicyError(
            "AutoGPT execution API contract is not verified; refusing to guess an endpoint."
        )
    if policy.get("absolute_zero", True) and not _is_loopback(config.base_url):
        raise AutoGPTPolicyError(
            "Absolute-zero mode only permits a loopback self-hosted AutoGPT endpoint."
        )
    if not config.allowed_agent_slug:
        raise AutoGPTPolicyError(
            "No AUTOGPT_ALLOWED_AGENT_SLUG configured; refusing unrestricted agent execution."
        )


def _headers(config: AutoGPTConfig) -> dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if config.api_key:
        headers["X-API-Key"] = config.api_key
    return headers


def _json_request(config: AutoGPTConfig, method: str, path: str, payload=None, opener=urlopen, timeout: float = 30.0):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{config.base_url}{path}",
        data=body,
        headers=_headers(config),
        method=method,
    )
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw
        return exc.code, {"error": detail}
    except (URLError, OSError) as exc:
        raise AutoGPTPolicyError(f"AutoGPT connection failed: {exc}") from exc


def healthcheck(config: AutoGPTConfig, opener=urlopen, timeout: float = 3.0) -> dict:
    """Probe the configured host without submitting a model task."""
    request = Request(config.base_url, headers={"Accept": "text/html,application/json"})
    try:
        with opener(request, timeout=timeout) as response:
            return {"ok": 200 <= response.status < 400, "status": response.status}
    except HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": "http"}
    except (URLError, OSError) as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def submit(
    task: str,
    *,
    inputs: dict | None = None,
    use_defaults: bool = False,
    config: AutoGPTConfig | None = None,
    policy: dict | None = None,
    opener=urlopen,
) -> dict:
    """Run the explicitly allowlisted AutoGPT marketplace agent.

    AutoGPT's API performs its own setup flow and may return missing-input or
    missing-credential information instead of starting execution. The adapter
    returns that response without attempting another provider or billing path.
    """
    config = config or config_from_env()
    policy = policy or load_policy()
    validate(config, policy)

    payload = {
        "username_agent_slug": config.allowed_agent_slug,
        "inputs": inputs or {},
        "use_defaults": bool(use_defaults),
    }
    status, result = _json_request(
        config,
        "POST",
        "/external-api/v1/tools/run-agent",
        payload,
        opener=opener,
    )
    if status >= 400:
        raise AutoGPTPolicyError(
            f"AutoGPT run-agent rejected request (HTTP {status}): {result}"
        )
    return result


def get_execution_results(
    graph_id: str,
    execution_id: str,
    *,
    config: AutoGPTConfig | None = None,
    policy: dict | None = None,
    opener=urlopen,
) -> dict:
    """Fetch results for an execution returned by the verified API."""
    config = config or config_from_env()
    policy = policy or load_policy()
    validate(config, policy)
    status, result = _json_request(
        config,
        "GET",
        f"/external-api/v1/graphs/{graph_id}/executions/{execution_id}/results",
        opener=opener,
    )
    if status >= 400:
        raise AutoGPTPolicyError(
            f"AutoGPT execution result request failed (HTTP {status}): {result}"
        )
    return result


def main(argv: list[str]) -> int:
    config = config_from_env()
    policy = load_policy()
    if len(argv) != 2 or argv[1] != "health":
        print("usage: autogpt_adapter.py health", file=sys.stderr)
        return 2
    try:
        validate(config, policy)
    except AutoGPTPolicyError as exc:
        print(f"[zero-$] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(healthcheck(config)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
