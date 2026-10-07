#!/usr/bin/env python3
"""Deterministic control-plane boundary for operating ZERO-$ Agent Fabric from a bot.

This module intentionally has no Telegram SDK and no shell execution. It converts
an authorized operator message into a typed operation, applies the autonomy gate,
and persists an auditable approval/event record. A transport (Telegram webhook,
CLI, etc.) can call these functions later without bypassing zero_agent.py.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "configs" / "zero-dollar-policy.json"
STATE_DIR = Path.cwd() / ".zero"
AUDIT_PATH = STATE_DIR / "bot-audit.jsonl"
APPROVAL_PATH = STATE_DIR / "bot-approvals.json"

COMMANDS = {
    "/status": "observe",
    "/doctor": "observe",
    "/run": "safe_execute",
    "/autogpt": "safe_execute",
    "/result": "observe",
    "/stop": "approval_required",
    "/approve": "approval_required",
    "/deny": "approval_required",
}

WRITE_WORDS = re.compile(
    r"\b(?:add|build|commit|create|delete|edit|fix|implement|migrate|modify|patch|"
    r"remove|rename|replace|update|upgrade|write|deploy|send|publish)\b",
    re.IGNORECASE,
)
DESTRUCTIVE_WORDS = re.compile(
    r"\b(?:delete|destroy|wipe|drop|reset|purge|credential|billing|payment|"
    r"provider key|api key|secret)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BotConfig:
    allowed_chat_ids: frozenset[str]
    allowed_user_ids: frozenset[str]
    webhook_secret: str = ""
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "BotConfig":
        return cls(
            allowed_chat_ids=frozenset(_csv_env("ZERO_BOT_ALLOWED_CHAT_IDS")),
            allowed_user_ids=frozenset(_csv_env("ZERO_BOT_ALLOWED_USER_IDS")),
            webhook_secret=os.getenv("ZERO_BOT_WEBHOOK_SECRET", ""),
            enabled=os.getenv("ZERO_BOT_ENABLED", "false").lower() == "true",
        )


class BotPolicyError(RuntimeError):
    pass


def _csv_env(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_json_write(path: Path, payload: dict) -> None:
    _ensure_state_dir()
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def _load_approvals() -> dict:
    if not APPROVAL_PATH.exists():
        return {"pending": {}}
    try:
        return json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"pending": {}}


def _audit(event: str, **fields) -> dict:
    record = {
        "event_id": uuid.uuid4().hex,
        "ts": int(time.time()),
        "event": event,
        **fields,
    }
    _ensure_state_dir()
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def verify_operator(config: BotConfig, *, chat_id: str, user_id: str) -> None:
    if not config.enabled:
        raise BotPolicyError("bot control plane is disabled")
    if not config.allowed_chat_ids and not config.allowed_user_ids:
        raise BotPolicyError("no operator allowlist configured")
    if config.allowed_chat_ids and str(chat_id) not in config.allowed_chat_ids:
        raise BotPolicyError("chat is not allowlisted")
    if config.allowed_user_ids and str(user_id) not in config.allowed_user_ids:
        raise BotPolicyError("user is not allowlisted")


def verify_webhook_secret(config: BotConfig, received_secret: str) -> None:
    if not config.webhook_secret:
        raise BotPolicyError("webhook secret is not configured")
    if received_secret != config.webhook_secret:
        raise BotPolicyError("invalid webhook secret")


def classify_task(task: str) -> str:
    if DESTRUCTIVE_WORDS.search(task):
        return "disabled"
    if WRITE_WORDS.search(task):
        return "approval_required"
    return "safe_execute"


def parse_command(text: str) -> tuple[str, str]:
    raw = text.strip()
    if not raw:
        raise BotPolicyError("empty command")
    parts = raw.split(maxsplit=1)
    command = parts[0].lower()
    if command not in COMMANDS:
        raise BotPolicyError(f"unsupported command: {command}")
    return command, parts[1].strip() if len(parts) == 2 else ""


def plan_message(text: str) -> dict:
    command, argument = parse_command(text)
    action = COMMANDS[command]
    if command in {"/run", "/autogpt"}:
        if not argument:
            raise BotPolicyError(f"{command} requires a task")
        task_mode = classify_task(argument)
        if task_mode == "disabled":
            return {"command": command, "action": "disabled", "reason": "destructive_or_credential_operation"}
        if task_mode == "approval_required":
            action = "approval_required"
        return {"command": command, "action": action, "task": argument}
    if command in {"/result", "/stop", "/approve", "/deny"} and not argument:
        raise BotPolicyError(f"{command} requires an execution or approval id")
    return {"command": command, "action": action, "argument": argument}


def queue_approval(plan: dict, *, chat_id: str, user_id: str) -> dict:
    if plan.get("action") != "approval_required":
        raise BotPolicyError("plan does not require approval")
    approvals = _load_approvals()
    approval_id = "ap_" + uuid.uuid4().hex[:16]
    item = {
        "approval_id": approval_id,
        "status": "pending",
        "created_at": int(time.time()),
        "chat_id": str(chat_id),
        "user_id": str(user_id),
        "plan": plan,
        "task_hash": hashlib.sha256(plan.get("task", "").encode("utf-8")).hexdigest(),
    }
    approvals.setdefault("pending", {})[approval_id] = item
    _atomic_json_write(APPROVAL_PATH, approvals)
    _audit("approval_queued", approval_id=approval_id, command=plan["command"], task_hash=item["task_hash"])
    return item


def resolve_approval(approval_id: str, decision: str, *, chat_id: str, user_id: str) -> dict:
    if decision not in {"approve", "deny"}:
        raise BotPolicyError("decision must be approve or deny")
    approvals = _load_approvals()
    item = approvals.setdefault("pending", {}).get(approval_id)
    if not item:
        raise BotPolicyError("approval not found")
    item["status"] = "approved" if decision == "approve" else "denied"
    item["resolved_at"] = int(time.time())
    item["resolved_by"] = {"chat_id": str(chat_id), "user_id": str(user_id)}
    _atomic_json_write(APPROVAL_PATH, approvals)
    _audit("approval_resolved", approval_id=approval_id, decision=decision)
    return item


def handle_message(text: str, *, config: BotConfig, chat_id: str, user_id: str) -> dict:
    verify_operator(config, chat_id=chat_id, user_id=user_id)
    plan = plan_message(text)
    _audit(
        "command_received",
        command=plan["command"],
        chat_id=str(chat_id),
        user_id=str(user_id),
        action=plan["action"],
    )
    if plan["action"] == "approval_required":
        item = queue_approval(plan, chat_id=chat_id, user_id=user_id)
        return {"status": "approval_required", "approval_id": item["approval_id"], "plan": plan}
    if plan["action"] == "disabled":
        return {"status": "blocked", "reason": plan["reason"], "plan": plan}
    return {"status": "planned", "plan": plan}


if __name__ == "__main__":
    raise SystemExit("Library module: connect it to an authenticated transport; no direct bot polling is implemented.")
