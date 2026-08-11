# Next Task

Target: `v0.2.0 — Local Model Pool`

Priority work:

1. Add explicit health probes for Ollama daemon and installed model availability.
2. Add multiple local model profiles with capability tags (coding, reasoning, lightweight).
3. Add task classification and deterministic routing by capability + availability.
4. Add checkpoint hooks before shell handoff (`git diff` summary + optional safe commit mode).
5. Improve structured failure detection without depending only on output substring matching.
6. Add a portable installer for Codex, Claude Code, and Gemini CLI profile setup.
