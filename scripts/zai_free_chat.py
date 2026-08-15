#!/usr/bin/env python3
"""Minimal Z.ai free-model adapter for Zero-Dollar Agent Fabric.

Reads ZAI_API_KEY from the environment. The model is hard-allowlisted to the
currently approved zero-dollar Z.ai models; GLM-5.2 and every other model are
rejected before any network request is made.
"""

import json
import os
import sys
import urllib.error
import urllib.request

ALLOWED_MODELS = {"glm-4.7-flash", "glm-4.5-flash"}
BASE_URL = os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4").rstrip("/")


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: zai_free_chat.py <model> <prompt>", file=sys.stderr)
        return 2

    model, prompt = sys.argv[1], sys.argv[2]
    if model not in ALLOWED_MODELS:
        print(f"blocked non-zero or unapproved Z.ai model: {model}", file=sys.stderr)
        return 64

    api_key = os.environ.get("ZAI_API_KEY", "").strip()
    if not api_key:
        print("ZAI_API_KEY is not configured", file=sys.stderr)
        return 65

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Z.ai HTTP {exc.code}: {body}", file=sys.stderr)
        return 75 if exc.code == 429 else 1
    except Exception as exc:
        print(f"Z.ai request failed: {exc}", file=sys.stderr)
        return 1

    try:
        print(data["choices"][0]["message"]["content"])
    except Exception:
        print(json.dumps(data, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
