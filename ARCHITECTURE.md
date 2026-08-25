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

## Free Resource Registry

Infrastructure discovery is separated from deployment eligibility:

```text
free-for-dev / other community catalogs
              │
              ▼
      candidate discovery
              │
              ▼
 normalized resource registry
              │
              ▼
 official provider documentation
              │
      semantic verification
              │
              ▼
 freshness + $0 policy gate
              │
      ┌───────┴────────┐
      │                │
 eligible           blocked
      │
      ▼
 ranking / selection / deploy planning
```

`free-for-dev` is discovery-only. A candidate never becomes deploy-eligible merely because its URL is reachable. Eligibility requires `cost_class=zero`, an official provider source, `verification.status=verified`, a non-stale `verified_at`, and no disallowed billing dependency. The registry CLI is `scripts/free_resource_registry.py`; normalized verified records live in `configs/free-resource-registry.json`; discovery snapshots are runtime state under `.zero/` and are not authoritative configuration.

The registry does not auto-enable cloud resources in the execution router. It provides vetted candidates to higher-level planning while the existing orchestrator retains the final hard-lock and provider failover policy.

## Failure classes

- `quota`: 429, quota exceeded, rate limit, resource exhausted, usage limit
- `auth`: authentication/login failure
- `unavailable`: executable not installed or local daemon/model unavailable
- `runtime`: any other non-zero exit

## Cooldown

Quota failures are placed in cooldown for a configurable duration.
Local profiles normally use a short cooldown; cloud free profiles use a longer cooldown.

## Health probes

Configured Ollama routes query the local `/api/tags` endpoint before execution. A route is usable only when the daemon responds and its required model is advertised. These probes do not generate tokens or bypass the cost-policy gate.

Free Resource Registry `audit --probe` checks only whether an official source is reachable. Reachability can never auto-promote a candidate to `verified` because free-tier semantics must be confirmed from official provider documentation.

## Task classification

When no mode is supplied, deterministic patterns classify the task as `read`, `reasoning`, `review`, or `write`. Mutating verbs select `write`; explicit non-mutating language suppresses `write`. Ambiguous tasks fail toward `read`, and `--mode` remains an explicit override.

## Local model tiers

`qwen2.5-coder:1.5b` is the FAST local route for `read`, `reasoning`, and `review`. It is intentionally excluded from `write`. `qwen2.5-coder:7b` remains the QUALITY model behind the Codex local write-capable route.

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
- promotional-credit-only infrastructure is not a durable dependency
- stale or unofficial resource records are not deploy-eligible
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

Beside the execution path, `free_resource_registry.py` continuously supports discovery and verification of zero-cost infrastructure without weakening the hard-lock.

## Future v0.3+

- model-level health probing
- local multi-model rotation based on RAM/VRAM profile
- repo task queue
- automatic checkpoint/commit before agent handoff
- optional local dashboard
- additional official-free-provider verifier adapters
- scheduled registry re-verification without automatic paid fallback
