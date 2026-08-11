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
    "429",
    "quota",
    "rate limit",
    "rate_limit",
    "resource exhausted",
    "resource_exhausted",
    "usage limit",
    "limit reached",
    "too many requests",
)

AUTH_PATTERNS = (
    "unauthorized",
    "authentication",
    "not logged in",
    "login required",
    "invalid api key",
    "invalid_api_key",
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
    if any(p in low for p in QUOTA_PATTERNS):
        return "quota"
    if any(p in low for p in AUTH_PATTERNS):
        return "auth"
    if code == 0:
        return "success"
    return "runtime"


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
    out = []
    for token in profile["command"]:
        out.append(token.replace("{prompt}", prompt).replace("{model}", model))
    return out


def doctor(config):
    print("ZERO-$ Agent Fabric doctor")
    print(f"absolute_zero={config.get('absolute_zero', True)}")
    model = os.getenv(config["default_local_model_env"], config["default_local_model"])
    print(f"local_model={model}")
    for p in sorted(config["profiles"], key=lambda x: x["priority"]):
        if not p.get("enabled", True):
            state = "disabled"
        elif not profile_available(p):
            state = "missing dependency"
        else:
            state = "available"
        print(f"- {p['id']}: {state}; cost={p['cost_class']}; kind={p['kind']}")


def status():
    state = load_state()
    print(json.dumps(state, indent=2))


def run_task(prompt):
    config = load_json(CONFIG_PATH)
    policy = load_json(POLICY_PATH)
    state = load_state()
    model = os.getenv(config["default_local_model_env"], config["default_local_model"])

    candidates = sorted(config["profiles"], key=lambda x: x["priority"])

    for p in candidates:
        if not p.get("enabled", True):
            continue
        if config.get("absolute_zero", True) and p.get("cost_class") != "zero":
            continue
        if not profile_available(p):
            continue

        active, _until = cooldown_active(state, p["id"])
        if active:
            continue

        if "{model}" in " ".join(p.get("command", [])) and model == "CHANGE_ME":
            print(
                f"[skip] {p['id']}: set {config['default_local_model_env']} "
                "to an installed Ollama model.",
                file=sys.stderr,
            )
            continue

        cmd = render_command(p, prompt, model)
        print(f"[zero-$] trying {p['id']}...", file=sys.stderr)

        try:
            proc = subprocess.run(
                cmd,
                cwd=Path.cwd(),
                env=sanitized_env(p, policy),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            output = proc.stdout or ""
            if output:
                print(output, end="" if output.endswith("\n") else "\n")

            failure = classify_failure(output, proc.returncode)
            pstate = state.setdefault("profiles", {}).setdefault(p["id"], {})
            pstate.update(
                {
                    "last_used": now(),
                    "last_exit_code": proc.returncode,
                    "last_failure_class": failure,
                }
            )

            state["last_task"] = prompt
            state["last_profile"] = p["id"]
            state["last_updated"] = now()

            if proc.returncode == 0:
                pstate["cooldown_until"] = 0
                save_state(state)
                return 0

            cooldown = (
                config["quota_cooldown_seconds"]
                if failure == "quota"
                else config["runtime_cooldown_seconds"]
            )
            pstate["cooldown_until"] = now() + cooldown
            save_state(state)
            print(
                f"[zero-$] {p['id']} failed ({failure}); "
                f"cooldown={cooldown}s; switching...",
                file=sys.stderr,
            )

        except FileNotFoundError:
            continue
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130

    save_state(state)
    print(
        "[zero-$] No zero-cost profile is currently usable. "
        "No paid provider was invoked.",
        file=sys.stderr,
    )
    return 2


def main():
    if len(sys.argv) < 2:
        print("usage: zero_agent.py doctor|status|run <task>", file=sys.stderr)
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
        if len(sys.argv) < 3:
            print("usage: zero_agent.py run <task>", file=sys.stderr)
            return 2
        return run_task(" ".join(sys.argv[2:]))

    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
