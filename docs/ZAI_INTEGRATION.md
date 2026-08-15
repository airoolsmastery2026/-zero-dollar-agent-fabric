# Z.ai Integration

Z.ai is integrated as an optional provider family without changing the UMS architecture.

## Automatic zero-dollar pool

- `glm-4.7-flash`
- `glm-4.5-flash`

Both routes use `scripts/zai_free_chat.py`, which hard-allowlists only these model IDs before making a request.

## GLM-5.2 boundaries

- Trial: opportunistic only, disabled by default, never a durable dependency.
- Coding Plan: optional subscription capacity, disabled by default.
- Paid API: hard-blocked while `absolute_zero=true`.

## ZCode

ZCode is not a dependency of UMS, the web app, or the AI OS. It may be used independently as a developer workstation/tool.

## Secrets

Do not commit provider secrets. Configure Z.ai credentials locally only.
