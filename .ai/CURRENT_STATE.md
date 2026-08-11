# Current State

Version: `v0.1.0`

Implemented:

- Config-driven provider profiles.
- `$0` hard-lock policy gate.
- Local Codex and Claude shell profiles targeting a local model endpoint.
- Gemini CLI official free-account profile as opportunistic cloud capacity.
- Quota/runtime failure classification and cooldown.
- Persistent local routing state in `.zero/state.json`.
- Paid API environment-variable stripping for child processes.
- Doctor/status/run CLI commands.
- Unit tests and GitHub Actions validation.

Known limitations:

- Local provider health is executable-based rather than model/endpoint-aware.
- Handoff uses repository state + task text; interactive conversation state is not migrated across shells.
- No local multi-model selection policy yet.
