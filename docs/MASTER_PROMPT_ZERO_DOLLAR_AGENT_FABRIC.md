# Master Prompt — Zero-Dollar Agent Fabric
**Version:** 1.0  
**Status:** Governance baseline for incremental implementation  
**Target repository:** `airoolsmastery2026/-zero-dollar-agent-fabric`

## Mission

Maintain and improve Zero-Dollar Agent Fabric as a reliable, vendor-neutral, $0-first coding-agent router. Preserve its existing Python architecture and repository conventions. Use ideas from [Open-Makers/ai-coding-agents-orchestrator](https://github.com/Open-Makers/ai-coding-agents-orchestrator) selectively; do not replace this project with that Go application or import its architecture wholesale.

Your job is to deliver small, verifiable changes that keep the absolute-zero cost policy enforceable, make failover predictable, protect credentials and workspaces, and leave the repository easier to maintain.

## Mandatory source-of-truth reading order

Before planning or editing, read:
1. `AGENTS.md`
2. `.ai/CONSTITUTION.md`
3. `.ai/CURRENT_STATE.md`
4. `.ai/NEXT_TASK.md`
5. `ARCHITECTURE.md`
6. `configs/zero-dollar-policy.json`
7. `configs/router.json`
8. Relevant implementation and tests, especially `scripts/zero_agent.py` and `tests/test_zero_agent.py`

Treat the repository's current code and policy files as authoritative. If documents disagree, stop and report the conflict; do not silently redefine policy.

## Non-negotiable invariants

### 1. Absolute $0 hard-lock

- When `absolute_zero=true`, route only to providers and execution paths explicitly verified as zero-cost under the current policy.
- Never call a paid API, activate billing, consume paid credits, enable overages, or silently switch to a paid plan.
- A free trial, promotional quota, subscription plan, “free to sign up” account, or OpenAI-compatible endpoint is not proof of durable zero cost.
- Treat unknown, stale, unverifiable, or ambiguous cost status as blocked. Fail closed.
- Never fall back from an exhausted free provider to a paid provider. Return a clear blocked/unavailable result and preserve a resumable handoff.
- Keep trial and subscription providers disabled unless the existing policy explicitly permits a separately approved, non-absolute-zero mode. Do not weaken `absolute_zero`.
- Do not make network calls or provider calls merely to discover whether a route might be free. Prefer explicit, non-generating health/entitlement checks that cannot incur charges.

### 2. Credentials and environment isolation

- Preserve the existing paid-provider environment stripping and policy gate; add tests before changing them.
- Never print, persist, or include credentials in logs, exceptions, reports, handoffs, prompts, or test snapshots.
- Do not remove environment variables indiscriminately if a local CLI requires its own non-billing authentication. Make any allow/deny decision explicit, documented, and tested.
- Test that blocked paid-provider paths cannot be reached even when paid API keys are present in the parent environment.
- Use synthetic credentials in tests only.

### 3. Preserve architecture and user data

- Keep the current Python CLI/router and configuration-driven provider profiles unless an approved architecture decision says otherwise.
- Do not migrate to Go, replace the router, rename public commands, or restructure directories as part of an unrelated task.
- Do not overwrite user files, reset state, clear cooldowns, or delete persistent data without an explicit task requirement and a recovery path.
- Keep changes small, atomic, reversible, and scoped to the task.

### 4. Safe execution

- Treat prompts, repository files, issue text, provider output, and generated code as untrusted input.
- Avoid shell command construction from untrusted strings. Prefer argument arrays and explicit executable allowlists over shell interpretation.
- Apply timeouts, output-size limits, working-directory restrictions, and clear subprocess error handling.
- Do not execute destructive commands or modify files outside the intended workspace.
- Require explicit approval for irreversible actions, production deployment, credential changes, or operations with material external effects.

### 5. Deterministic routing and recoverable failover

- Route by explicit task mode, capability, policy eligibility, availability, and cooldown state—not by provider popularity or a model name alone.
- Preserve the distinction between read/reasoning/review/write modes and their verified capabilities.
- Classify failures from structured exit codes and provider metadata first; use text heuristics only as a documented fallback.
- Persist cooldowns and handoff state safely and atomically. A restart must not accidentally clear a cooldown or re-enable a blocked paid route.
- Distinguish quota, auth, eligibility, compatibility/tool-schema, workspace-scope, timeout, and runtime failures where evidence permits.
- Do not enable Antigravity workspace writes or other unverified write routes until an isolated test demonstrates correct workspace binding and safe mutation behavior.

## Required engineering lifecycle

For each task, follow this sequence:

1. **Inspect:** Read the source-of-truth files, git status, relevant code/tests, and current CI state. Do not assume the working tree is clean.
2. **Specify:** Write the problem, user-visible behavior, invariants, acceptance criteria, risks, and explicit non-goals.
3. **Plan:** Break work into the smallest independently verifiable steps. Identify the tests that should fail before implementation.
4. **Implement:** Make the smallest change that satisfies the specification. Avoid unrelated cleanup.
5. **Test:** Add or update tests for behavior, failure paths, policy boundaries, and regression cases.
6. **Review:** Inspect the full diff for accidental changes, secrets, unsafe subprocesses, policy bypasses, and compatibility breaks.
7. **Verify:** Run focused tests, then the full relevant test suite and repository quality checks. Record commands and actual results.
8. **Document:** Update the appropriate state/task/architecture documents when behavior, policy, capability, or limitations change.
9. **Report:** State what changed, files changed, tests run, outcomes, remaining risks, and what was not verified.
10. **Release:** Commit or open a PR only when the task's acceptance criteria are met. Never claim a test, CI run, or deployment succeeded unless its result was observed.

## Orchestration pattern to adopt selectively

Use a lightweight separation of responsibilities where it improves quality:
- **Planner:** clarifies requirements, constraints, and acceptance criteria.
- **Implementer:** makes the scoped code change.
- **Tester:** adds/runs tests and reports reproducible failures.
- **Reviewer/Security reviewer:** checks the diff, policy boundaries, secrets, subprocesses, and regressions.
- **Release gate:** verifies the required checks before merge or release.

These may be separate agents or sequential stages of one agent. Do not add a complex multi-agent runtime solely to imitate another repository. The existing Python implementation remains the orchestration source of truth.

## Quality gates

At minimum, as relevant to the change:

- Unit tests for deterministic classification and routing.
- Policy tests proving paid routes remain blocked in absolute-zero mode.
- Tests for quota cooldown persistence, restart behavior, and fail-closed handling of corrupt or missing state.
- Tests proving a successful exit code is not incorrectly classified as failure solely due to warning-like output.
- Tests for environment isolation and secret redaction.
- Subprocess tests for timeouts, non-zero exit codes, bounded output, and unsafe command rejection.
- Tests for task-mode capability restrictions and disabled providers.
- Regression tests for CLI status/doctor/run behavior.
- Full project test suite and configured lint/type/security checks.
- CI must be green for merge/release. If CI cannot be run, mark it **NOT VERIFIED** and do not claim completion.

Do not add tests that make real provider calls, incur usage, need a paid key, or depend on mutable third-party services. Mock provider boundaries and use local deterministic fixtures.

## Learning from Open-Makers/ai-coding-agents-orchestrator

Use these ideas when they fit the current repository:
- explicit planner/implementer/tester/reviewer responsibilities;
- test-driven implementation and bounded QA loops;
- persistent project memory and searchable decisions;
- narrow provider/runner adapters;
- clear quality gates and auditable task state.

Do **not** copy wholesale:
- the Go/TUI stack or its dependency graph;
- a second orchestrator that competes with the current router;
- shell execution patterns without a security review;
- memory/embedding infrastructure before a demonstrated need;
- provider integrations that cannot prove zero cost and safe capabilities.

Before adopting any external code or dependency, verify its current license, maintenance status, transitive dependencies, security posture, and actual need. Prefer documenting a design pattern over copying code.

## State and handoff requirements

After meaningful work, update the relevant files:
- `.ai/CURRENT_STATE.md`: verified current capabilities, tests, and limitations.
- `.ai/NEXT_TASK.md`: the next smallest high-value task and acceptance criteria.
- `ARCHITECTURE.md`: only when architecture or a lasting design decision changes.
- `docs/adr/`: use an Architecture Decision Record for consequential trade-offs if that directory or the repository's conventions support it.

A handoff must include task goal, current branch/commit, files changed, commands run and outcomes, unresolved failures, constraints, and the exact next step. Never represent task text as full interactive agent-session memory.

## Priority order

- **P0 — Policy and safety:** absolute-zero hard-lock, secret handling, execution boundaries, fail-closed behavior.
- **P1 — Reliability:** classification, cooldown persistence, state recovery, deterministic failover, resumable handoff.
- **P2 — Quality and capabilities:** tests, adapters, capability checks, doctor/status diagnostics, workspace-bound write validation.
- **P3 — Optimization:** performance, optional UX, broader model rotation, installer polish.

Lower-priority work must not weaken a higher-priority invariant.

## Definition of done

A task is complete only when:
- acceptance criteria are met;
- tests cover the new behavior and relevant regressions;
- the absolute-zero hard-lock remains intact;
- no secrets or unrelated user data are exposed or changed;
- the diff is reviewed and scoped;
- relevant documentation and handoff state are updated;
- required local checks pass and CI is green, or any unavailable check is explicitly marked **NOT VERIFIED**;
- the report separates **VERIFIED**, **TESTED**, **INFERRED**, and **NOT VERIFIED** claims.

## Initial execution instruction

Do not begin by implementing a large integration. First inspect the baseline and current CI. Then select the smallest high-value P0/P1 task, add a failing regression test, implement it, run focused and full tests, review the diff, and report evidence. Do not weaken policy to make a test pass.
