# Current State

Version: `v0.2.0-dev`

Implemented:

- Config-driven provider profiles and task modes (`read`, `reasoning`, `review`, `write`).
- `$0` hard-lock policy gate; paid profiles remain disabled.
- Antigravity headless as a non-mutating cloud/session route for read/reasoning/review only.
- MiniMax M3 through Ollama Free as a non-mutating reasoning/review fallback.
- Codex + local Ollama as the verified write-capable continuity route.
- Claude-local profile retained but disabled until end-to-end validation.
- Failure classes learned from real tests: quota, subscription, eligibility, compatibility/tool-schema, auth, workspace-scope, timeout, runtime.
- Per-failure cooldowns and persistent routing state in `.zero/state.json`.
- Paid API environment-variable stripping for child processes.
- Doctor/status/run CLI commands with `--mode` support.
- Unit tests and GitHub Actions validation.

Safety/cost invariants:

- `write` mode does not route through Antigravity headless because project-scoped headless writes are not yet verified.
- MiniMax M3 is not used through Codex tool calls after observed `invalid tool type: namespace` incompatibility.
- Subscription-required and eligibility failures are cooled down for a long interval rather than retried repeatedly.
- No profile is allowed to silently escalate to a paid API or overage path.

Known limitations:

- Local provider health is executable-based rather than model/endpoint-aware.
- Local Qwen2.5-Coder 7B is reliable but slow on CPU-only hardware.
- No validated local FAST model pool yet.
- Headless Antigravity workspace binding requires further validation before enabling write mode.
- Handoff uses repository state + task text; interactive conversation state is not migrated across shells.
