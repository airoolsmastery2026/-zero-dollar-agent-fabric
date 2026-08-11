# ZERO-$ Agent Fabric v0.1.0

[![CI](https://github.com/airoolsmastery2026/-zero-dollar-agent-fabric/actions/workflows/ci.yml/badge.svg)](https://github.com/airoolsmastery2026/-zero-dollar-agent-fabric/actions/workflows/ci.yml)

A local-first, multi-agent coding fabric designed to keep **paid API spend at exactly $0** while continuing to work when free cloud quotas are exhausted.

## Core invariant

> Free cloud capacity is opportunistic. Local Ollama is the continuity layer. Paid fallbacks are disabled by policy.

## Supported agent shells

- Codex CLI
- Claude Code
- Gemini CLI
- Future shells through config-driven profiles

## Default routing

```text
TASK
  │
  ▼
ZERO-$ ORCHESTRATOR
  │
  ├─ policy gate: paid → BLOCK
  ├─ availability gate
  ├─ cooldown gate
  │
  ├─ Codex CLI + Ollama
  ├─ Claude Code + Ollama
  └─ Gemini CLI + official free-account quota
          │
     quota / 429 / error
          │
          ▼
     next zero-cost route
          │
          ▼
      local fallback
```

## What `$0 hard-lock` means

When `absolute_zero=true`:

- Profiles with `cost_class != "zero"` are never launched.
- Common paid API-key environment variables are stripped from child processes.
- The router never auto-upgrades, attaches billing, or falls through to a paid API.
- If every zero-cost route is unavailable, the command exits instead of spending money.

Electricity, hardware, internet access, or an existing subscription are outside the router's accounting boundary.

## Quick start

### 1. Clone

```bash
git clone https://github.com/airoolsmastery2026/-zero-dollar-agent-fabric.git
cd ./-zero-dollar-agent-fabric
```

### 2. Install the agent shells you want

Install Ollama plus any combination of Codex CLI, Claude Code, and Gemini CLI using their official installation instructions.

### 3. Prepare a local Ollama model

Set the model name already installed on your machine:

```bash
export ZERO_LOCAL_MODEL="YOUR_OLLAMA_MODEL"
```

PowerShell:

```powershell
$env:ZERO_LOCAL_MODEL="YOUR_OLLAMA_MODEL"
```

### 4. Authenticate optional free cloud capacity

For Gemini CLI, sign in with a personal Google account if you want to use its official free quota. Free quotas are treated as temporary capacity, never as the continuity layer.

### 5. Run diagnostics

```bash
python scripts/zero_agent.py doctor
```

### 6. Run a task

```bash
python scripts/zero_agent.py run "Inspect this repo, fix the failing tests, then run the relevant test suite."
```

### 7. Inspect routing state

```bash
python scripts/zero_agent.py status
```

Runtime state is stored in `.zero/state.json` and ignored by Git.

## Repository map

```text
.ai/                         Agent governance and roadmap
.zero/TASK_HANDOFF.md        Cross-agent handoff contract
configs/router.json          Provider priority and commands
configs/zero-dollar-policy.json
configs/codex-local.toml     Codex local example
configs/claude-local.env     Claude Code local example
scripts/zero_agent.py        Failover launcher
tests/test_zero_agent.py     Policy and router tests
.github/workflows/ci.yml     Free GitHub Actions validation
AGENTS.md                    Instructions for coding agents
ARCHITECTURE.md              System design
```

## Development checks

No third-party Python dependency is required for v0.1.0.

```bash
python -m py_compile scripts/zero_agent.py
python -m unittest discover -s tests -v
```

CI validates Python 3.11, 3.12, and 3.13 plus JSON configuration syntax.

## Design rules

1. `$0 hard-lock` stays enabled by default.
2. Local execution is the final continuity layer.
3. Cloud-free providers are accelerators, not dependencies.
4. Provider integrations stay behind configuration/adapters.
5. Secrets never enter source control.
6. Quota failures enter cooldown and rotate to another zero-cost route.
7. No paid escape hatch is automatically reachable.

## Roadmap

### v0.2 — Local Model Pool

- Ollama daemon/model health probes
- Multiple local models with capability tags
- Task classification and capability-based routing
- Checkpoints before agent handoff
- Structured error detection
- Portable setup installer

### v1.0 — Golden Framework Integration

- Reusable skill pack
- Project bootstrap templates
- Backup/restore and data portability rules
- Optional local dashboard
- Provider plugin interface
- Reference project proving end-to-end `$0` operation

## License

MIT
