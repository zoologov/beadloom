# CONTEXT: BDL-005 — Phase 4: Performance & Agent-Native Evolution (v0.6.0)

> **Last updated:** 2026-02-11
> **Phase:** Strategy Phase 4
> **Status:** COMPLETE
> **Version:** 0.6.0
> **Depends on:** BDL-004 (v0.5.0 complete)

---

## Goal

Make Beadloom fast, searchable, and fully agent-native — with no LLM API dependency.

## Design Principle

**Beadloom = data infrastructure. Agent = intelligence.** No duplicate LLM calls.

## Deliverables

| # | Item | Status | Bead |
|---|------|--------|------|
| 4.1 | L1 cache integration in MCP | DONE | beadloom-oaz |
| 4.2 | Incremental reindex | DONE | beadloom-6km |
| 4.3 | Auto-reindex in MCP | DONE | beadloom-9lr |
| 4.4 | Bundle caching in SQLite (L2) | DONE | beadloom-p5q |
| 4.5 | MCP write tools (update_node, mark_synced, search) | DONE | beadloom-gjh |
| 4.6 | Semantic search (FTS5 + sqlite-vec) | DONE | beadloom-vg5 |
| 4.7 | Remove --auto + LLM API | DONE | beadloom-v6b |
| 4.8 | AGENTS.md cleanup & update | DONE | beadloom-21b |

## Key Decisions

| Decision | Reason |
|----------|--------|
| **Agent-native, no LLM API** | Agent IS the LLM; Beadloom provides data, not intelligence |
| **Remove `--auto` entirely** | Deprecated since v0.3, non-functional; agent does updates directly |
| **Incremental reindex by default** | `file_index` table tracks hashes; `--full` for escape hatch |
| **Two-tier cache (L1 + L2)** | L1 = in-memory (per-process), L2 = SQLite (persistent across restarts) |
| **FTS5 as built-in search** | Zero new dependencies; sqlite-vec + fastembed optional |
| **sqlite-vec + fastembed** | Lightweight local embeddings (~80MB), no API calls |
| **MCP write tools** | Agent needs mutation capability to complete agent-native workflow |
| **Additive schema only** | No SCHEMA_VERSION bump, backward compatible |
| **Graph YAML change → full reindex** | Pragmatic escape hatch; incremental graph is complex |
| **L2 returns full bundle** | Agent in new session needs data; L1 returns short cached response |

## Implementation Summary

| Component | Files Changed | Tests Added |
|-----------|---------------|-------------|
| L1 cache + etag | `cache.py`, `mcp_server.py` | 8 |
| Incremental reindex | `reindex.py`, `db.py`, `cli.py` | 10 |
| Auto-reindex | `mcp_server.py` | 3 |
| L2 SQLite cache | `cache.py`, `db.py`, `mcp_server.py` | 8 |
| MCP write tools | `mcp_server.py`, `graph_loader.py`, `sync_engine.py` | 9 |
| FTS5 search | `search.py` (new), `db.py`, `reindex.py`, `cli.py`, `mcp_server.py` | 23 |
| Remove --auto | `cli.py`, `test_cli_sync_update.py` | 1 |
| AGENTS.md | `AGENTS.md` | 0 |

**Total:** 398 → 464 tests (+66), mypy strict clean, ruff clean

## New Schema Tables

| Table | Type | Drops on reindex? |
|-------|------|-------------------|
| `file_index` | Regular | No (updated incrementally) |
| `bundle_cache` | Regular | No (cleared, not dropped) |
| `search_index` | FTS5 virtual | Yes (rebuilt from nodes+chunks) |

## New/Updated Modules

| Module | Purpose |
|--------|---------|
| `search.py` (NEW) | FTS5 query builder, populate_search_index, has_fts5 |
| `cache.py` | Added `SqliteCache` L2 class, `compute_etag()` |
| `reindex.py` | Added `incremental_reindex()`, file hash diffing |
| `mcp_server.py` | 8 tools (5→8), two-tier cache, auto-reindex |
| `graph_loader.py` | Added `update_node_in_yaml()` |
| `sync_engine.py` | Added `mark_synced_by_ref()` |
