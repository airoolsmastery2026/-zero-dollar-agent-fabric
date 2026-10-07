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
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bot_operator import BotConfig, BotPolicyError, handle_message

MAX_BODY = 256 * 1024
TOKEN_ENV = "TELEGRAM_BOT_TOKEN"


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


def process_update(update: dict, *, config: BotConfig) -> dict | None:
    extracted = extract_text_update(update)
    if extracted is None:
        return None
    chat_id, user_id, text = extracted
    try:
        result = handle_message(
            text,
            config=config,
            chat_id=chat_id,
            user_id=user_id,
        )
        if result["status"] == "planned":
            reply = json.dumps(result["plan"], ensure_ascii=False)
        elif result["status"] == "approval_required":
            reply = f"Approval required: {result['approval_id']}"
        else:
            reply = f"Blocked: {result.get('reason', 'policy')}"
    except BotPolicyError as exc:
        reply = f"Denied: {exc}"
        result = {"status": "denied", "error": str(exc)}
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
