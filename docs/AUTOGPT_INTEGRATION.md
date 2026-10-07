# AutoGPT Integration Reference

Status: **architecture/reference integration only**. This document does not vendor, install, or execute AutoGPT code.

## Decision

Use [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) as an optional workflow/agent-runtime reference behind ZERO-$ Agent Fabric. Keep ZERO-$ as the policy enforcement and provider-selection layer. Do not make AutoGPT the source of truth, mandatory runtime, or an automatic route around the $0 hard-lock.

## Target architecture

```text
Project / DHP-AIOS / UMS
          |
          v
ZERO-$ policy + task handoff
  - absolute_zero hard-lock
  - provider availability and cooldown
  - durable task/repo/git-diff state
          |
          v
Optional AutoGPT adapter (future, opt-in)
  - submit/describe workflow
  - map run status and logs
  - cancel/resume where supported
  - normalize tool/model requirements
          |
          v
AutoGPT self-hosted runtime OR another compatible runtime
          |
          v
Approved provider adapter only
  - local Ollama first for continuity
  - official free quota only when configured and eligible
  - paid routes blocked in absolute_zero mode
```

The adapter must not weaken or duplicate the ZERO-$ policy gate. AutoGPT must never receive paid credentials or unrestricted secrets when absolute_zero=true.

## Integration boundary

Implement a provider-neutral runtime interface before wiring any concrete AutoGPT API:

- validate_config(): fail closed if the runtime endpoint or auth configuration is invalid.
- capabilities(): report supported workflow, tool, persistence, and cancellation capabilities.
- submit(task, context): accept an explicit task, repo reference, constraints, and budget/policy metadata.
- get_run(run_id): return normalized state: queued, running, succeeded, failed, cancelled, or unknown.
- get_events(run_id): return bounded logs/events with secrets redacted.
- cancel(run_id): request cancellation when supported.
- healthcheck(): check runtime availability without generating model usage.

These are proposed internal contracts, not claims about AutoGPT's existing API. Bind them to the actual self-hosted API only after checking the selected release's official docs and OpenAPI/schema.

## $0 hard-lock requirements

1. Preserve absolute_zero=true as the default.
2. Reject paid provider profiles before submitting a workflow.
3. Do not copy paid API keys, billing tokens, or arbitrary parent-process environment variables into the runtime.
4. Treat free hosted quotas as optional and non-durable; local execution remains the continuity layer.
5. Fail closed if cost class, provider identity, or runtime policy cannot be verified.
6. Record estimated/observed usage where available, but never treat a missing cost report as proof that a run was free.
7. Require explicit opt-in for network access, write-capable tools, destructive actions, and external side effects.
8. Redact secrets from logs and persisted task context.
9. Keep task handoff portable: repository + task specification + approved artifacts + git diff, not provider-specific conversation state alone.

## Licensing gate — mandatory before copying code

AutoGPT's repository currently declares two license zones:

- autogpt_platform/: Polyform Shield 1.0.0. Its noncompete condition may restrict building or distributing a competing product/service. Do **not** copy, vendor, or adapt this directory into ZERO-$ without a documented legal review and a clear license decision.
- Outside autogpt_platform/, including classic/, MIT, subject to retaining the required copyright and license notices.

Reference: [AutoGPT LICENSE](https://github.com/Significant-Gravitas/AutoGPT/blob/master/LICENSE), [Polyform Shield 1.0.0](https://polyformproject.org/licenses/shield/1.0.0).

A link, documented integration, or clean-room adapter against a supported public API is preferred over copying platform implementation code. Re-check the exact release and directory license before any future reuse.

## Phased implementation

### Phase 0 — this change
- Record the architecture boundary, license gate, $0 policy invariants, and validation plan.
- No runtime behavior or dependencies change.

### Phase 1 — inspect and prototype
- Pin a reviewed AutoGPT release/commit.
- Read its self-hosting and API docs; identify stable API endpoints and auth.
- Run it separately in an isolated development environment.
- Document resource requirements, data stores, network ports, and operational cost.

### Phase 2 — adapter behind a feature flag
- Initial fail-closed adapter is now present at `scripts/autogpt_adapter.py` with `AUTOGPT_ENABLED=false` by default.
- Health probing is allowed only after explicit network opt-in and verified API-contract flag.
- Task submission remains deliberately disabled until a release-specific execution contract is verified.
- Add a disabled-by-default autogpt runtime profile.
- Validate all provider/model costs before dispatch.
- Add mocked contract tests for success, quota/rate-limit, timeout, cancellation, malformed response, and secret redaction.
- Confirm all failure paths remain within zero-cost routes.

### Phase 3 — gated end-to-end verification
- Test with a non-production repository and a harmless read-only task first.
- Then test a disposable branch with explicit write permissions.
- Verify logs, cancellation, restart recovery, cost-policy enforcement, and rollback.
- Keep disabled by default until every gate passes.

## Acceptance criteria

- Existing router behavior and tests remain unchanged.
- No paid provider becomes reachable in absolute-zero mode.
- No AutoGPT code from the Polyform Shield directory is copied.
- Adapter is optional and disabled by default.
- Unit tests cover policy denial and failure handling before any live runtime test.
- Documentation states which parts are verified versus planned.


## Verified external API binding (2026-10-07)

The adapter now binds to the upstream AutoGPT external API contract without
copying AutoGPT Platform source:

- `POST /external-api/v1/tools/run-agent` — run an explicitly allowlisted marketplace agent.
- `GET /external-api/v1/graphs/{graph_id}/executions/{execution_id}/results` — read execution results.
- Authentication uses the optional `X-API-Key` header when `AUTOGPT_API_KEY` is configured.
- In `absolute_zero=true`, the adapter accepts only loopback AutoGPT endpoints.
- `AUTOGPT_ALLOWED_AGENT_SLUG` is mandatory for submission; unrestricted agent selection is rejected.
- The adapter never falls back to another provider when AutoGPT rejects or cannot execute.
- `AUTOGPT_ENABLED=false` remains the default.

The upstream route implementation was inspected on 2026-10-07. AutoGPT Platform
itself is separately licensed under Polyform Shield, so this repository keeps
the integration at an HTTP boundary and does not vendor or copy Platform code.

### Explicit opt-in

A local test deployment can be enabled with environment variables such as:

```text
AUTOGPT_ENABLED=true
AUTOGPT_ALLOW_NETWORK=true
AUTOGPT_API_CONTRACT_VERIFIED=true
AUTOGPT_COST_CLASS=zero
AUTOGPT_BASE_URL=http://127.0.0.1:8006
AUTOGPT_ALLOWED_AGENT_SLUG=<explicit-local-agent>
AUTOGPT_API_KEY=<local-api-key-if-required>
```

The `zero` cost label is a policy input, not proof that an arbitrary AutoGPT
graph is free. For production use, the selected local agent must be independently
audited so it cannot invoke paid model providers or paid external services.
