# Architecture

## Core invariant

```text
TASK
 │
 ▼
ZERO-$ ORCHESTRATOR
 │
 ├─ policy gate: paid? → BLOCK
 ├─ availability gate
 ├─ cooldown gate
 └─ execution
      │
      ├─ Codex CLI + Ollama ───────────────┐
      ├─ Claude Code + Ollama ─────────────┤ local continuity
      └─ Gemini CLI + Google free quota ───┤ opportunistic cloud
                                           │
failure / quota / 429                      │
      │                                    │
      └─ mark cooldown → next profile ─────┘
```

## Failure classes

- `quota`: 429, quota exceeded, rate limit, resource exhausted, usage limit
- `auth`: authentication/login failure
- `unavailable`: executable not installed or local daemon/model unavailable
- `runtime`: any other non-zero exit

## Cooldown

Quota failures are placed in cooldown for a configurable duration.
Local profiles normally use a short cooldown; cloud free profiles use a longer cooldown.

## State continuity

The wrapper stores:

- last task
- last selected profile
- per-profile cooldown-until
- last exit code
- last failure class
- timestamp

in `.zero/state.json`.

This does not pretend to migrate an interactive conversation perfectly. The durable unit of work is the repo + git diff + task text, so another agent shell can resume the same task safely.

## Hard-lock

With `absolute_zero=true`:

- profiles with `cost_class != "zero"` are never launched
- common paid API environment variables are removed from child processes
- API-key based paid fallbacks are not configured
- if no zero-cost provider is available, the tool exits instead of spending money

## Recommended long-term topology

```text
                ┌──────────────────────┐
                │  project repository  │
                └──────────┬───────────┘
                           │
                    zero_agent.py
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
       Codex shell    Claude shell    Gemini shell
             │             │             │
             └──────┬──────┘             │
                    ▼                    ▼
                  Ollama           Google free quota
                    │
                    ▼
              local model(s)

No paid path exists in absolute-zero mode.
```

## Future v0.2

- model-level health probing
- local multi-model rotation based on RAM/VRAM profile
- repo task queue
- automatic checkpoint/commit before agent handoff
- optional local dashboard
- official-free-provider plugins
