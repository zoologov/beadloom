# /dev — Developer Role

> **Canonical definition:** `.claude/agents/dev.md` (single source of truth — keep this wrapper thin)

Adopt the **Developer** role and follow the protocol in `.claude/agents/dev.md`:
TDD (RED→GREEN→REFACTOR), DDD boundaries, claim → implement → verify (`uv run pytest` / `ruff` / `mypy` + `beadloom reindex`/`sync-check`/`lint`) → checkpoint → `bd close --suggest-next`.

The coordinator launches this role as a subagent (`subagent_type: dev`). Invoked interactively (`/dev`), apply the same protocol in the current session.
