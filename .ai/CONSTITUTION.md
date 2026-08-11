# Constitution

## Mission

Provide a durable, local-first orchestration layer that can rotate between zero-cost coding-agent paths without ever auto-spending money.

## Invariants

1. **$0 hard lock:** a profile with `cost_class != "zero"` is never invoked while `absolute_zero=true`.
2. **Local continuity:** at least one local route must remain possible in the supported architecture.
3. **No vendor lock-in:** shells and providers are replaceable through configuration/adapters.
4. **No secret leakage:** paid/cloud credentials are not committed and common paid API variables are stripped from child processes in hard-lock mode.
5. **Durable state:** cooldown and handoff state are persisted outside source control.
6. **Fail closed:** if no zero-cost route is usable, exit without spending rather than silently upgrading.
7. **Test first for policy:** cost gates, cooldown behavior, failure classification, and environment sanitization must remain covered by automated tests.
