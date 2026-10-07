#!/usr/bin/env python3
"""Fail-closed AutoGPT runtime adapter for ZERO-$ Agent Fabric.

This adapter deliberately does not guess AutoGPT's execution endpoints.
It provides the stable policy boundary and health probe; a concrete submit
implementation must be bound to a verified AutoGPT API contract.
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


@dataclass(frozen=True)
class AutoGPTConfig:
    base_url: str = "http://127.0.0.1:8006"
    enabled: bool = False
    allow_network: bool = False
    cost_class: str = "zero"
    api_contract_verified: bool = False


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
    )


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


def submit(*_args, **_kwargs):
    raise AutoGPTPolicyError(
        "Submission is intentionally unavailable until the selected AutoGPT "
        "release exposes a verified execution API contract."
    )


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
