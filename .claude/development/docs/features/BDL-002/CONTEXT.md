# CONTEXT: BDL-002 — Phase 1: Foundation & Agent-Native Pivot (v0.3)

> **Last updated:** 2026-02-10
> **Phase:** Strategy Phase 1
> **Status:** COMPLETE
> **Depends on:** BDL-001 (v0.2.0 complete)

---

## Goal

Establish the agent-native architecture and clean up the codebase before building new features. Foundational items that won't need revision as features evolve.

## Design Principle

**Beadloom = data + rules + tracking. Agent = intelligence + action.**

Beadloom does NOT call LLM APIs. The agent the developer already uses (Claude Code, Cursor, Codex) provides the intelligence. Beadloom teaches agents how to work with it via `.beadloom/AGENTS.md`.

## Deliverables

| # | Item | Status |
|---|------|--------|
| 1.1 | README rewrite | DONE |
| 1.2 | README.ru.md | DONE |
| 1.3 | Deprecate `--auto`, remove `llm_updater.py` | DONE |
| 1.4 | Create `.beadloom/AGENTS.md` generation in init | DONE |
| 1.5 | Update cli-reference.md | DONE |

**Deferred to Phase 6 (post-dev):** Use-case guides, demo GIF, README.ru.md final update.

## Key Decisions

| Decision | Reason |
|----------|--------|
| **Agent-native, not agent-replacement** | Agents already have LLM access; no need for separate API keys/costs |
| **Deprecate `--auto` LLM integration** | Redundant when agent is already running; removes SDK deps and config |
| **AGENTS.md instruction file** | Follows beads/CLAUDE.md pattern; agents pick it up automatically |
| **Guides deferred to Phase 6** | Guides describe workflows with real output — writing them before features stabilize means rewriting after every phase |
| **README stays as-is** | Positioning doesn't describe features — won't go stale |

## What Changed

| File | Change |
|------|--------|
| `src/beadloom/llm_updater.py` | DELETED — LLM API integration removed |
| `src/beadloom/cli.py` | `--auto` → deprecation warning; `_handle_auto_sync()` removed |
| `src/beadloom/onboarding.py` | Added `generate_agents_md()` + `_AGENTS_MD_TEMPLATE` |
| `.beadloom/_graph/services.yml` | Removed `llm-updater` node and edges |
| `docs/cli-reference.md` | Updated sync-update section, added agent-native note |
| `README.md` / `README.ru.md` | Removed `--auto` mention from CLI table |
| `tests/test_llm_updater.py` | DELETED |
| `tests/test_cli_sync_auto.py` | DELETED |
| `tests/test_cli_sync_update.py` | Replaced LLM tests with deprecation warning test |
| `tests/test_onboarding.py` | Added tests for AGENTS.md generation |
