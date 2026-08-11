# Task handoff

When an agent shell fails or hits quota, the next agent must:

1. Read repository instructions and the current Git diff.
2. Read the original task from `.zero/state.json` when it exists.
3. Preserve valid work from the previous agent; do not reset or overwrite it casually.
4. Run the tests, lint, or build checks relevant to the changed area.
5. Record blockers instead of enabling a paid provider.
