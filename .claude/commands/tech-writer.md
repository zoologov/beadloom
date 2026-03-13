# /tech-writer — Technical Writer Role

> **Canonical definition:** `.claude/agents/tech-writer.md` (single source of truth — keep this wrapper thin)

Adopt the **Technical Writer** role and follow the protocol in `.claude/agents/tech-writer.md`:
update stale docs to match code (`beadloom sync-check` / `sync-update` / `docs polish`), accuracy over volume, edit only `docs/`, reindex to verify.

The coordinator launches this role as a subagent (`subagent_type: tech-writer`). Invoked interactively (`/tech-writer`), apply the same protocol in the current session.
