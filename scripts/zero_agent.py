#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "router.json"
POLICY_PATH = ROOT / "configs" / "zero-dollar-policy.json"
STATE_DIR = Path.cwd() / ".zero"
STATE_PATH = STATE_DIR / "state.json"

QUOTA_PATTERNS = (
    "429", "quota", "rate limit", "rate_limit", "resource exhausted",
    "resource_exhausted", "usage limit", "limit reached", "too many requests",
)
AUTH_PATTERNS = (
    "unauthorized", "authentication", "not logged in", "login required",
    "invalid api key", "invalid_api_key",
)
SUBSCRIPTION_PATTERNS = (
    "requires a subscription", "upgrade for access", "subscription required",
)
ELIGIBILITY_PATTERNS = (
    "account is not eligible", "not eligible for antigravity", "eligibility check failed",
)
COMPATIBILITY_PATTERNS = (
    "invalid tool type", "invalid params", "tool schema", "namespace",
)
WORKSPACE_PATTERNS = (
    "antigravity-cli\\scratch", "antigravity-cli/scratch", "outside workspace",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def now() -> int:
    return int(time.time())


def load_state():
    if not STATE_PATH.exists():
        return {"profiles": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"profiles": {}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def profile_available(profile):
    return all(shutil.which(binary) for binary in profile.get("requires", []))


def classify_failure(text: str, code: int) -> str:
    low = text.lower()
    if any(p in low for p in SUBSCRIPTION_PATTERNS):
        return "subscription"
    if any(p in low for p in ELIGIBILITY_PATTERNS):
        return "eligibility"
    if any(p in low for p in QUOTA_PATTERNS):
        return "quota"
    if any(p in low for p in COMPATIBILITY_PATTERNS):
        return "compatibility"
    if any(p in low for p in AUTH_PATTERNS):
        return "auth"
    if any(p in low for p in WORKSPACE_PATTERNS):
        return "workspace"
    if code == 0:
        return "success"
    return "runtime"


def cooldown_seconds(config, failure):
    if failure == "quota":
        return int(config["quota_cooldown_seconds"])
    if failure == "compatibility":
        return int(config["compatibility_cooldown_seconds"])
    if failure in {"eligibility", "subscription"}:
        return int(config["eligibility_cooldown_seconds"])
    return int(config["runtime_cooldown_seconds"])


def cooldown_active(state, profile_id):
    p = state.setdefault("profiles", {}).setdefault(profile_id, {})
    until = int(p.get("cooldown_until", 0))
    return until > now(), until


def sanitized_env(profile, policy):
    env = os.environ.copy()
    if policy.get("absolute_zero", True):
        for key in policy.get("strip_environment_variables", []):
            env.pop(key, None)
    for k, v in profile.get("env", {}).items():
        env[k] = v
    return env


def render_command(profile, prompt, model):
    return [
        token.replace("{prompt}", prompt).replace("{model}", model)
        for token in profile["command"]
    ]


def profile_allowed(profile, mode, absolute_zero=True, allow_zero_incremental=False):
    if not profile.get("enabled", True):
        return False
    if mode not in profile.get("modes", []):
        return False
    if absolute_zero:
        cost = profile.get("cost_class")
        if cost == "paid":
            return False
        if cost == "zero-incremental" and not allow_zero_incremental:
            return False
        if cost not in {"zero", "zero-incremental"}:
            return False
    return True


def doctor(config):
    print("ZERO-$ Agent Fabric doctor")
    print(f"version={config.get('version')}")
    print(f"absolute_zero={config.get('absolute_zero', True)}")
    print(f"allow_zero_incremental={config.get('allow_zero_incremental', False)}")
    model = os.getenv(config["default_local_model_env"], config["default_local_model"])
    print(f"local_model={model}")
    for p in sorted(config["profiles"], key=lambda x: x["priority"]):
        if not p.get("enabled", True):
            state = "disabled"
        elif not profile_available(p):
            state = "missing dependency"
        elif not profile_allowed(
            p,
            next(iter(p.get("modes", ["read"])), "read"),
            config.get("absolute_zero", True),
            config.get("allow_zero_incremental", False),
        ):
            state = "blocked-by-cost-policy"
        else:
            state = "available"
        modes = ",".join(p.get("modes", [])) or "-"
        print(f"- {p['id']}: {state}; cost={p['cost_class']}; kind={p['kind']}; modes={modes}")


def status():
    print(json.dumps(load_state(), indent=2))


def run_task(prompt, mode=None):
    config = load_json(CONFIG_PATH)
    policy = load_json(POLICY_PATH)
    state = load_state()
    mode = mode or config.get("default_mode", "read")
    model = os.getenv(config["default_local_model_env"], config["default_local_model"])

    candidates = sorted(config["profiles"], key=lambda x: x["priority"])
    for p in candidates:
        if not profile_allowed(
            p,
            mode,
            config.get("absolute_zero", True),
            config.get("allow_zero_incremental", False),
        ):
            continue
        if not profile_available(p):
            continue

        active, _until = cooldown_active(state, p["id"])
        if active:
            continue

        cmd = render_command(p, prompt, model)
        print(f"[zero-$] trying {p['id']} mode={mode}...", file=sys.stderr)
        try:
            proc = subprocess.run(
                cmd,
                cwd=Path.cwd(),
                env=sanitized_env(p, policy),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=int(p.get("timeout_seconds", 600)),
            )
            output = proc.stdout or ""
            if output:
                print(output, end="" if output.endswith("\n") else "\n")

            failure = classify_failure(output, proc.returncode)
            pstate = state.setdefault("profiles", {}).setdefault(p["id"], {})
            pstate.update({"last_used": now(), "last_exit_code": proc.returncode, "last_failure_class": failure})
            state.update({"last_task": prompt, "last_mode": mode, "last_profile": p["id"], "last_updated": now()})

            if proc.returncode == 0 and failure == "success":
                pstate["cooldown_until"] = 0
                save_state(state)
                return 0

            cooldown = cooldown_seconds(config, failure)
            pstate["cooldown_until"] = now() + cooldown
            save_state(state)
            print(f"[zero-$] {p['id']} failed ({failure}); cooldown={cooldown}s; switching...", file=sys.stderr)

        except subprocess.TimeoutExpired:
            pstate = state.setdefault("profiles", {}).setdefault(p["id"], {})
            pstate.update({"last_used": now(), "last_exit_code": 124, "last_failure_class": "timeout", "cooldown_until": now() + int(config["runtime_cooldown_seconds"])})
            save_state(state)
            print(f"[zero-$] {p['id']} timed out; switching...", file=sys.stderr)
        except FileNotFoundError:
            continue
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130

    save_state(state)
    print("[zero-$] No zero-cost profile is currently usable for this mode. No paid provider was invoked.", file=sys.stderr)
    return 2


def main():
    if len(sys.argv) < 2:
        print("usage: zero_agent.py doctor|status|run [--mode read|reasoning|review|write] <task>", file=sys.stderr)
        return 2
    command = sys.argv[1]
    config = load_json(CONFIG_PATH)
    if command == "doctor":
        doctor(config)
        return 0
    if command == "status":
        status()
        return 0
    if command == "run":
        args = sys.argv[2:]
        mode = None
        if len(args) >= 2 and args[0] == "--mode":
            mode = args[1]
            args = args[2:]
        if not args:
            print("usage: zero_agent.py run [--mode MODE] <task>", file=sys.stderr)
            return 2
        return run_task(" ".join(args), mode=mode)
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
