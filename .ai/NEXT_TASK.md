# Next Task

Target: `v0.2.0 — Automatic Failover Stabilization`

Priority work:

1. Add explicit health probes for Antigravity session readiness and Ollama cloud entitlement; Ollama daemon and configured-model probes are implemented.
2. Add a validated local FAST model profile alongside Qwen2.5-Coder 7B QUALITY.
3. Refine the implemented deterministic task classification as real prompts reveal additional safe patterns.
4. Validate project-scoped Antigravity headless writes before adding `write` to its modes; scratch writes must be treated as `workspace` failures.
5. Add checkpoint hooks before shell handoff (`git diff` summary + optional safe commit mode).
6. Continue structured failure detection beyond the implemented exit-code-first success handling.
7. Add a portable Windows installer/bootstrapper for Ollama, Codex, Antigravity, and optional Claude Code profiles without enabling paid credentials.
8. Add a `$0 doctor` report that clearly labels `zero`, `zero-incremental`, disabled, subscription-required, and local-unlimited routes.
