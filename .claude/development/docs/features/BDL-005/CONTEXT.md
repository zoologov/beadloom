# CONTEXT: BDL-005 — Phase 4: Performance & Agent-Native Evolution (v0.6.0)

> **Last updated:** 2026-02-11
> **Phase:** Strategy Phase 4
> **Status:** ACCEPTED
> **Depends on:** BDL-004 (v0.5.0 complete)

---

## Goal

Make Beadloom fast, searchable, and fully agent-native — with no LLM API dependency.

## Design Principle

**Beadloom = data infrastructure. Agent = intelligence.** No duplicate LLM calls.

## Deliverables

| # | Item | Status | Bead |
|---|------|--------|------|
| 4.1 | L1 cache integration in MCP | TODO | — |
| 4.7 | Remove --auto + LLM API | TODO | — |
| 4.2 | Incremental reindex | TODO | — |
| 4.5 | MCP write tools (update_node, mark_synced) | TODO | — |
| 4.3 | Auto-reindex in MCP | TODO | — |
| 4.4 | Bundle caching in SQLite | TODO | — |
| 4.8 | AGENTS.md update | TODO | — |
| 4.6 | Semantic search (FTS5 + sqlite-vec) | TODO | — |

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

## Existing Infrastructure (validated)

| Component | Status | Location |
|-----------|--------|----------|
| `ContextCache` class | EXISTS (unused) | `cache.py:1-98` |
| `--auto` flag (hidden, deprecated) | EXISTS | `cli.py:675` |
| `reindex()` (full rebuild) | EXISTS | `reindex.py:45-278` |
| `file_hash` in code_symbols | EXISTS | `code_symbols.file_hash` |
| `docs.hash` | EXISTS | `docs.hash` |
| `meta.last_reindex_at` | EXISTS | `meta` table |
| Stale index warning in MCP | EXISTS | `mcp_server.py` |
| Levenshtein suggestions | EXISTS | `context_builder.py:suggest_ref_id()` |
| `mark_synced()` in sync_engine | EXISTS (partial) | `sync_engine.py` |
| `health_snapshots` table | EXISTS | `db.py` |
| YAML graph loader | EXISTS | `graph_loader.py` |
| MCP server (5 tools) | EXISTS | `mcp_server.py` |
