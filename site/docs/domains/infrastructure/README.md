<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-02T14:35:00.546836+00:00 · coverage 100% (`infrastructure`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Infrastructure

Domain-agnostic SQLite database layer, health metrics, and git activity analysis.

> Note: the cross-domain orchestrators (`reindex`, `doctor`, `debt_report`, `watcher`)
> live in the [application](../application/README.md) layer, not here, so that
> `infrastructure` never imports a domain (the DDD Dependency Rule).

## Specification

### Modules

- **db.py** — `open_db()` opens a SQLite connection with WAL mode and foreign keys enabled, returning a connection with `sqlite3.Row` row factory. `create_schema()` creates all tables and applies incremental migrations via `ensure_schema_migrations()`. `get_meta()`/`set_meta()` for key-value metadata. Exports `SCHEMA_VERSION` constant (currently `"4"` — BDL-038 G7 added `external` to the `nodes`/`edges`/`foreign_edges` `lifecycle` CHECK). The `rules` table CHECK constraint covers all 7 rule types: `deny`, `require`, `forbid_cycles`, `layers`, `cardinality`, `forbid_import`, `forbid_edge`.
- **health.py** — `take_snapshot()` captures current index statistics (node/edge/doc counts, coverage percentage, stale docs, isolated nodes) and persists them to the `health_snapshots` table. `get_latest_snapshots()` retrieves history for trend comparison. `compute_trend()` computes trend indicators (arrows and deltas) between two snapshots.
- **git_activity.py** — `GitActivity` frozen dataclass holds per-node metrics: `commits_30d`, `commits_90d`, `last_commit_date`, `top_contributors`, `activity_level`. `analyze_git_activity()` runs `git log --since=90 days ago`, parses output, maps changed files to nodes via longest source-prefix match, and classifies activity (hot: >20 commits/30d, warm: 5-20, cold: 1-4, dormant: 0 commits/90d).
- **mcp_tools.py** — single-source catalog of MCP tool metadata used by AGENTS.md generation. `McpToolDoc` describes one tool; `mcp_tool_names()` returns the canonical tool-name list (pinned to the live MCP `_TOOLS` registry by a drift-guard test) so the documented tool count cannot drift.

### Database Schema

Stored in `.beadloom/beadloom.db` (WAL mode):
- `nodes`, `edges` — architecture graph. Their `kind` columns are **free-form `TEXT` (no CHECK)** so any paradigm's vocabulary (DDD `domain`/`service`, FSD `page`/`widget`/`repository`, …) is stored and federated faithfully — Beadloom is paradigm-agnostic, not DDD-only (BDL-038 / U1). Both carry a `lifecycle` column (`active`/`planned`/`deprecated`/`dead`/`external`, default `active`; BDL-037 + BDL-038 G7 `external`). `edges` also carries a `contract_key` column (default `''`) that is part of its primary key, so multiple AMQP contracts (`produces`/`consumes`) on the same `(src,dst,kind)` pair do not collapse (BDL-037 #102)
- `foreign_edges` — cross-repo edges whose at least one endpoint is a `@repo:ref_id` reference to a node in another repo; kept separate because a foreign endpoint cannot satisfy the `edges` FK to local nodes (BDL-037 #100). Carries the same `lifecycle` CHECK (incl. `external`)
- `docs`, `chunks` — document index
- `code_symbols` — code symbol index (includes `annotations` JSON and `file_hash`)
- `code_imports` — resolved import relationships
- `sync_state` — doc-code synchronization (includes `symbols_hash` column for drift detection and `doc_hash_at_last_edit` column for two-phase sync that survives reindex)
- `file_index` — file hash tracking for incremental reindex (includes `__parser_fingerprint__` sentinel row)
- `health_snapshots` — trend tracking (persists across reindexes)
- `graph_snapshots` — point-in-time architecture graph captures (nodes_json, edges_json, symbols_count, label)
- `bundle_cache` — L2 persistent bundle cache
- `search_index` — FTS5 full-text search index
- `rules` — architecture rules from `rules.yml`
- `meta` — index metadata

### Parser Fingerprint

`incremental_reindex()` tracks available tree-sitter parsers via a fingerprint (sorted comma-separated `supported_extensions()`). Stored as a sentinel row in `file_index` with `path='__parser_fingerprint__'`. When the fingerprint changes (e.g. after `uv tool install "beadloom[languages]"`), a full code reindex is triggered automatically, ensuring new language parsers are used without requiring `--full`.

## API

Module `src/beadloom/infrastructure/db.py`:
- `SCHEMA_VERSION` — schema version constant (currently `"4"`; v3 → v4 rebuilt the `lifecycle` CHECK to admit `external`)
- `open_db(db_path: Path)` -> `sqlite3.Connection` — opens DB with WAL mode, foreign keys, and `Row` factory
- `ensure_schema_migrations(conn)` — applies incremental schema migrations (e.g. `symbols_hash` column, `doc_hash_at_last_edit` column for two-phase sync, the `lifecycle` column on `nodes`/`edges`, the `edges.contract_key` rebuild, the `foreign_edges` table for BDL-037 federation, the BDL-038 / U1 rebuild that drops the legacy DDD-only `kind` CHECK on `nodes`/`edges` so `kind` is free-form, and the BDL-038 / G7 rebuild (`_migrate_lifecycle_external`, v3 → v4) that adds `external` to the `nodes`/`edges`/`foreign_edges` `lifecycle` CHECK — all additive + idempotent, guarded on the stored DDL/columns; the rebuild uses `PRAGMA legacy_alter_table=ON` so renaming a rebuilt table does not dangle dependent FK references)
- `create_schema(conn)` — creates all tables and indexes, calls `ensure_schema_migrations()`
- `get_meta(conn, key, default=None)` -> `str | None`
- `set_meta(conn, key, value)` — upserts a key in the `meta` table

Module `src/beadloom/infrastructure/health.py`:
- `HealthSnapshot` — frozen dataclass with `taken_at`, `nodes_count`, `edges_count`, `docs_count`, `coverage_pct`, `stale_count`, `isolated_count`
- `take_snapshot(conn)` -> `HealthSnapshot` — computes and persists health metrics
- `get_latest_snapshots(conn, n=2)` -> `list[HealthSnapshot]`
- `compute_trend(current, previous)` -> `dict[str, str]` — computes trend indicators between two snapshots

Module `src/beadloom/infrastructure/git_activity.py`:
- `GitActivity` — frozen dataclass: `commits_30d`, `commits_90d`, `last_commit_date`, `top_contributors`, `activity_level`
- `analyze_git_activity(project_root, source_dirs)` -> `dict[str, GitActivity]` — parses `git log` for 90 days, maps files to nodes, classifies activity level (hot/warm/cold/dormant)

> The orchestrator modules `reindex`, `doctor`, `debt_report`, and `watcher` were
> relocated to the [application](../application/README.md) layer. Their API and
> tests are documented there.

## Testing

Tests: `tests/test_db.py`, `tests/test_health.py`, `tests/test_reindex_activity.py`
