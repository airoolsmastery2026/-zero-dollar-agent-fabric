# Agent Instructions

This repository implements a zero-paid-spend coding-agent router.

## Read order

1. `.ai/START.md`
2. `.ai/CONSTITUTION.md`
3. `.ai/CURRENT_STATE.md`
4. `.ai/NEXT_TASK.md`
5. `ARCHITECTURE.md`

## Non-negotiable rules

- Keep `absolute_zero=true` as the default.
- Never add an automatically reachable paid provider.
- Never commit API keys, billing credentials, tokens, or secrets.
- Free cloud providers are opportunistic; local execution is the continuity layer.
- Provider integrations belong in configuration/adapters, not scattered through orchestration logic.
- Preserve cross-platform behavior where practical.
- Every behavior change requires tests or an explicit reason why a test is not applicable.
- Prefer small, reviewable changes; do not add packages unless they provide clear value.
