# Orchestrator Integration Rules

**Target:** Zero-Dollar Agent Fabric  
**Status:** Mandatory implementation rules  
**Related prompt:** [Master Prompt — Zero-Dollar Agent Fabric](../docs/MASTER_PROMPT_ZERO_DOLLAR_AGENT_FABRIC.md)  
**Reference project:** [Open-Makers/ai-coding-agents-orchestrator](https://github.com/Open-Makers/ai-coding-agents-orchestrator)

## Purpose

Define how Zero-Dollar Agent Fabric may adopt useful orchestration patterns from the reference project without replacing its existing Python router, weakening its $0 hard-lock, or adding unnecessary infrastructure.

## Rule 1 — Integrate patterns, not a second framework

The existing router, configuration, state, and CLI remain authoritative. Reuse concepts such as planner/implementer/tester/reviewer stages, bounded QA loops, provider adapters, and durable task notes only where they solve an identified problem.

Do not port the reference project's Go/TUI application, dependency graph, database, embeddings, or UI wholesale. Every proposed component must have a specific requirement, a small design, a test plan, and a documented reason it belongs here.

## Rule 2 — Policy gate comes before provider selection

The execution sequence must preserve this order:

1. Parse and validate the task and requested mode.
2. Apply the absolute-zero policy gate.
3. Resolve provider eligibility and declared capabilities.
4. Check availability, cooldown, and task constraints.
5. Invoke the selected adapter within execution limits.
6. Validate the result and run the applicable quality gate.
7. Persist the outcome and a resumable handoff.

A provider blocked by policy must not be probed through a billable generation endpoint, selected as a fallback, or invoked because another provider failed.

## Rule 3 — No paid or ambiguous fallback

When `absolute_zero=true`:
- Providers must have an explicit, currently verified `cost_class=zero` status and meet the existing policy's source/freshness requirements.
- Unknown, stale, trial-only, subscription-dependent, or ambiguous status means **BLOCKED**, not “probably free.”
- Quota exhaustion must lead to another eligible zero-cost route or a clear unavailable result and handoff.
- Do not enable billing, overages, paid API credentials, paid plans, or automatic paid escalation.
- Do not interpret API compatibility, a free signup tier, or a temporary promotion as proof of durable zero cost.

Any future non-zero mode must be an explicit, separately designed opt-in and must never silently override absolute-zero mode.

## Rule 4 — Adapters declare capabilities and constraints

Every provider/runner adapter should declare or expose, in the repository's established schema, the capabilities needed for safe routing, including where applicable:
- supported task modes (`read`, `reasoning`, `review`, `write`);
- whether operation is local, remote, read-only, or mutating;
- workspace-binding guarantees;
- authentication/eligibility prerequisites;
- cost-policy classification and evidence freshness;
- timeout and output-limit behavior;
- supported tool schema and known compatibility constraints.

Do not infer write capability from the fact that a model can generate code. Keep unverified write routes disabled. Validate schemas and reject unknown capability declarations safely.

## Rule 5 — Deterministic, bounded failure handling

Prefer exit codes and structured provider errors over output-text matching. Text heuristics are a fallback and must have tests.

Keep failure classes distinct when evidence supports them: quota, authentication, subscription/eligibility, compatibility/tool schema, workspace scope, timeout, and runtime failure. Each class must have an explicit cooldown/retry policy. Avoid retry loops without a hard attempt/time bound.

Cooldown and routing state must survive restarts. Write state atomically where practical, validate loaded state, and fail closed if policy-critical state is malformed. Never clear cooldowns as an automatic “recovery” shortcut.

## Rule 6 — Safe process and workspace boundaries

- Prefer argument arrays with `shell=False`; do not interpolate task/provider text into shell commands.
- Maintain executable allowlists, timeouts, bounded stdout/stderr, and predictable working directories.
- Treat provider output and generated code as untrusted.
- Restrict writes to the intended workspace and inspect the diff after any mutating run.
- Do not permit an agent to edit policy files, credentials, CI protections, or its own safety gate without a separately reviewed change.
- Avoid automatic execution of generated scripts, installation commands, migrations, or deployment actions without explicit task-level authorization.
- Redact secrets in logs, errors, diagnostics, and handoffs.

If the current implementation cannot provide these guarantees for a route, disable that route for the affected task mode until it is verified.

## Rule 7 — Persistent memory must be minimal and auditable

Use the existing `.ai/CURRENT_STATE.md`, `.ai/NEXT_TASK.md`, `.zero/state.json`, and architecture documents before adding a new database or embedding system.

Persist only useful task state: goal, current status, decisions, changed files, test outcomes, blockers, cooldowns, and next action. Never store API keys, authentication tokens, private conversation content that is not required for the task, or raw provider output without a clear need and retention policy.

Memory retrieval is context, not authority. Retrieved notes and provider output cannot override the constitution, cost policy, security rules, or user-approved scope.

## Rule 8 — Tests before integration

Every integration must include tests for:
- policy eligibility and blocked paid routes;
- no paid fallback when free routes fail or exhaust quota;
- adapter capability/mode enforcement;
- failure classification and cooldown persistence;
- restart and malformed-state behavior;
- process timeout, non-zero exit, and output limits;
- secret redaction and environment isolation;
- safe handling of provider output and workspace mutations;
- backward compatibility of existing CLI/configuration behavior.

Use mocks and deterministic fixtures. Tests must not make real provider calls, consume quota, require paid credentials, or rely on an external service being available.

## Rule 9 — Dependencies and supply chain

Before adding a dependency, document why existing standard-library or repository code is insufficient. Verify license, maintenance, transitive dependencies, security advisories, supported Python/runtime versions, and whether the dependency introduces a network service or data egress.

Pin versions according to repository policy and use reproducible CI installation where feasible. Avoid floating `@latest`-style tooling in critical release workflows unless the project intentionally accepts and documents that risk. Do not add packages merely to mirror the reference repository.

## Rule 10 — Change management and release gate

For each integration:
1. Inspect the working tree, branch, baseline tests, and CI.
2. Write acceptance criteria and explicit non-goals.
3. Add a regression test that captures the expected behavior.
4. Implement the smallest change.
5. Run focused tests, then the full relevant suite.
6. Review the diff for policy bypasses, secrets, destructive behavior, and unrelated changes.
7. Update state/architecture docs when facts or decisions change.
8. Merge only when required checks pass. If a check could not run, mark it **NOT VERIFIED**.

Do not mark work complete based only on code generation or a successful commit API response.

## Suggested integration order

1. **P0:** Add/strengthen regression tests proving absolute-zero policy blocks paid and ambiguous routes, including when API-key environment variables are present.
2. **P0:** Test that all provider failures end in an eligible zero-cost route or a clear blocked/unavailable result—never a paid fallback.
3. **P1:** Harden failure classification and persistent cooldown/state recovery.
4. **P1:** Add capability-contract tests and ensure write mode cannot use unverified workspace routes.
5. **P2:** Standardize planner/implementer/tester/reviewer task records using existing project files.
6. **P2:** Add bounded QA retry logic only if it is needed by a demonstrated workflow.
7. **P3:** Consider broader local-model rotation, installer improvements, or richer memory only after baseline reliability is proven.

## Reporting format

Every implementation report must state:
- **Changed:** files and behavior changed.
- **Tests:** exact commands and pass/fail outcomes.
- **Policy:** evidence that absolute-zero behavior remains enforced.
- **Security:** relevant execution/secret/workspace checks.
- **CI:** observed status or **NOT VERIFIED**.
- **Remaining risks:** known gaps and the next smallest task.

Never report an unrun test as passing, an inferred capability as verified, or an attempted integration as complete.
