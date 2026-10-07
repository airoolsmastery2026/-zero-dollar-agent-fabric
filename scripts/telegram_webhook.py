#!/usr/bin/env python3
"""Minimal stdlib Telegram webhook transport for ZERO-$ Agent Fabric.

Disabled by default. This module only translates Telegram updates into
bot_operator calls and sends text replies via the Bot API. It never accepts
shell commands directly and never stores the bot token.
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bot_operator import BotConfig, BotPolicyError, dispatch_plan, handle_message

MAX_BODY = 256 * 1024
TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
STATE_DIR = Path.cwd() / ".zero"
UPDATE_STATE_PATH = STATE_DIR / "telegram-updates.json"


def _token() -> str:
    token = os.getenv(TOKEN_ENV, "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    return token


def telegram_api(method: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{_token()}/{method}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError) as exc:
        raise RuntimeError(f"Telegram API request failed: {exc}") from exc
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API returned failure: {result}")
    return result


def extract_text_update(update: dict) -> tuple[str, str, str] | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat") or {}
    user = message.get("from") or {}
    text = message.get("text")
    if not isinstance(text, str):
        return None
    if chat.get("id") is None or user.get("id") is None:
        return None
    return str(chat["id"]), str(user["id"]), text


def _claim_update(update_id: int) -> bool:
    """Atomically record Telegram update_id and reject webhook retries."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(UPDATE_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {"processed": []}
    processed = {int(value) for value in state.get("processed", [])}
    if update_id in processed:
        return False
    processed.add(update_id)
    state["processed"] = sorted(processed)[-2048:]
    temp = UPDATE_STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state), encoding="utf-8")
    temp.replace(UPDATE_STATE_PATH)
    return True


def process_update(update: dict, *, config: BotConfig) -> dict | None:
    extracted = extract_text_update(update)
    if extracted is None:
        return None
    update_id = update.get("update_id")
    if not isinstance(update_id, int):
        raise BotPolicyError("missing Telegram update_id")
    if not _claim_update(update_id):
        return {"status": "duplicate", "update_id": update_id}
    chat_id, user_id, text = extracted
    try:
        result = handle_message(
            text,
            config=config,
            chat_id=chat_id,
            user_id=user_id,
        )
        if result["status"] == "planned":
            execution = dispatch_plan(result["plan"])
            reply = json.dumps(execution, ensure_ascii=False)
            result = {"status": "executed", "plan": result["plan"], "execution": execution}
        elif result["status"] == "approval_required":
            reply = f"Approval required: {result['approval_id']}"
        else:
            reply = f"Blocked: {result.get('reason', 'policy')}"
    except BotPolicyError as exc:
        reply = f"Denied: {exc}"
        result = {"status": "denied", "error": str(exc)}
    if result.get("status") != "duplicate":
        telegram_api("sendMessage", {"chat_id": chat_id, "text": reply[:4096]})
    return result


def make_handler(config: BotConfig):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if config.webhook_secret:
                supplied = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
                if not secrets.compare_digest(supplied, config.webhook_secret):
                    self.send_response(403)
                    self.end_headers()
                    return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY:
                    raise ValueError("invalid body size")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                process_update(payload, config=config)
                self.send_response(200)
            except Exception:
                self.send_response(400)
            self.end_headers()

        def do_GET(self):
            self.send_response(404)
            self.end_headers()

        def log_message(self, *_args):
            return

    return Handler


def main() -> int:
    config = BotConfig.from_env()
    if not config.enabled:
        raise SystemExit("Telegram bot transport is disabled; set ZERO_BOT_ENABLED=true")
    server = HTTPServer(
        (os.getenv("ZERO_BOT_BIND", "127.0.0.1"), int(os.getenv("ZERO_BOT_PORT", "8443"))),
        make_handler(config),
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
