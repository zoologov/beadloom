# /review — Reviewer Role

> **Canonical definition:** `.claude/agents/review.md` (single source of truth — keep this wrapper thin)

Adopt the **Reviewer** role and follow the protocol in `.claude/agents/review.md`:
correctness, architecture (boundaries / cycles — see the §E note), security, doc freshness. Post findings to bead comments; do NOT edit code; return OK / ISSUES.

The coordinator launches this role as a subagent (`subagent_type: review`). Invoked interactively (`/review`), apply the same protocol in the current session.
