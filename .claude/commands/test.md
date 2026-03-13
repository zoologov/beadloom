# /test — Tester Role

> **Canonical definition:** `.claude/agents/test.md` (single source of truth — keep this wrapper thin)

Adopt the **Tester** role and follow the protocol in `.claude/agents/test.md`:
pytest, AAA pattern, behavior-focused assertions (NOT private attributes), edge cases, coverage >= 80%.

The coordinator launches this role as a subagent (`subagent_type: test`). Invoked interactively (`/test`), apply the same protocol in the current session.
