# Infrastructure

SQLite database layer, health metrics, reindex orchestrator, doctor validation, and file watcher.

## Specification

### Modules

- **db.py** — `open_db()` opens a SQLite connection with WAL mode and foreign keys enabled, returning a connection with `sqlite3.Row` row factory. `create_schema()` creates all tables and applies incremental migrations via `ensure_schema_migrations()`. `get_meta()`/`set_meta()` for key-value metadata. Exports `SCHEMA_VERSION` constant (currently `"2"`).
- **health.py** — `take_snapshot()` captures current index statistics (node/edge/doc counts, coverage percentage, stale docs, isolated nodes) and persists them to the `health_snapshots` table. `get_latest_snapshots()` retrieves history for trend comparison. `compute_trend()` computes trend indicators (arrows and deltas) between two snapshots.
- **reindex.py** — `reindex(root)` performs full reindex: snapshot sync baselines → drop tables → create schema → load graph YAML → store deep config → index docs → index code → resolve imports → load rules → map tests → analyze git activity → extract API routes → build sync state (with preserved symbol hashes) → populate FTS5 → clear bundle cache → take health snapshot → populate file index → store parser fingerprint. `incremental_reindex(root)` updates only changed files; detects parser availability changes via fingerprint comparison and graph YAML changes via `_graph_yaml_changed()`, triggering full reindex when needed. Internal helpers include `_snapshot_sync_baselines()` for preserving symbol drift baselines, `_store_test_mappings()` for test-to-node mapping, `_store_git_activity()` for git commit analysis, and `_extract_and_store_routes()` for API route extraction.
- **doctor.py** — `run_checks(conn)` validates graph health with 7 checks: empty summaries, unlinked docs, nodes without docs, isolated nodes, symbol drift, stale sync entries, and source coverage gaps (untracked source files).
- **git_activity.py** — `analyze_git_activity()` collects git commit history per source file for activity metrics (hot/warm/cold classification).
- **debt_report.py** — `collect_debt_data()` aggregates architecture health signals from lint, sync-check, doctor, git activity, and test mapper. `compute_debt_score()` applies a weighted formula producing a 0-100 debt score with category breakdown (rule_violations, doc_gaps, complexity, test_gaps), severity classification (clean/low/medium/high/critical), and per-node top offenders. `load_debt_weights()` reads configurable weights from `config.yml` `debt_report` section. `compute_debt_trend()` compares the current debt score against the last graph snapshot, recomputing structural debt from the snapshot's node/edge data and returning per-category deltas. `format_trend_section()` renders trend data as plain text with directional arrows (improved/regressed/unchanged). `format_debt_report()` renders the full report as Rich-formatted terminal output. `compute_top_offenders()` ranks nodes by debt contribution. `format_top_offenders_json()` serializes offender data for JSON output.
- **watcher.py** — Filesystem watcher for live reindex on file changes using `watchfiles`.

### Database Schema

Stored in `.beadloom/beadloom.db` (WAL mode):
- `nodes`, `edges` — architecture graph
- `docs`, `chunks` — document index
- `code_symbols` — code symbol index (includes `annotations` JSON and `file_hash`)
- `code_imports` — resolved import relationships
- `sync_state` — doc-code synchronization (includes `symbols_hash` column for drift detection)
- `file_index` — file hash tracking for incremental reindex (includes `__parser_fingerprint__` sentinel row)
- `health_snapshots` — trend tracking (persists across reindexes)
- `bundle_cache` — L2 persistent bundle cache
- `search_index` — FTS5 full-text search index
- `rules` — architecture rules from `rules.yml`
- `meta` — index metadata

### Parser Fingerprint

`incremental_reindex()` tracks available tree-sitter parsers via a fingerprint (sorted comma-separated `supported_extensions()`). Stored as a sentinel row in `file_index` with `path='__parser_fingerprint__'`. When the fingerprint changes (e.g. after `uv tool install "beadloom[languages]"`), a full code reindex is triggered automatically, ensuring new language parsers are used without requiring `--full`.

## API

Module `src/beadloom/infrastructure/db.py`:
- `SCHEMA_VERSION` — schema version constant (currently `"2"`)
- `open_db(db_path: Path)` -> `sqlite3.Connection` — opens DB with WAL mode, foreign keys, and `Row` factory
- `ensure_schema_migrations(conn)` — applies incremental schema migrations (e.g. `symbols_hash` column)
- `create_schema(conn)` — creates all tables and indexes, calls `ensure_schema_migrations()`
- `get_meta(conn, key, default=None)` -> `str | None`
- `set_meta(conn, key, value)` — upserts a key in the `meta` table

Module `src/beadloom/infrastructure/health.py`:
- `HealthSnapshot` — frozen dataclass with `taken_at`, `nodes_count`, `edges_count`, `docs_count`, `coverage_pct`, `stale_count`, `isolated_count`
- `take_snapshot(conn)` -> `HealthSnapshot` — computes and persists health metrics
- `get_latest_snapshots(conn, n=2)` -> `list[HealthSnapshot]`
- `compute_trend(current, previous)` -> `dict[str, str]` — computes trend indicators between two snapshots

Module `src/beadloom/infrastructure/reindex.py`:
- `ReindexResult` — dataclass with counts, `nothing_changed` flag, `errors`, and `warnings`
- `reindex(project_root, *, docs_dir=None)` -> `ReindexResult` — full reindex with sync baseline preservation
- `incremental_reindex(project_root, *, docs_dir=None)` -> `ReindexResult` — incremental reindex with parser fingerprint and graph YAML change detection
- `resolve_scan_paths(project_root)` -> `list[str]` — resolves source scan directories from config

Module `src/beadloom/infrastructure/debt_report.py`:
- `DebtWeights` — frozen dataclass with per-item weights and thresholds (configurable via `config.yml`)
- `DebtData` — frozen dataclass with raw counts from all data sources and per-node issue tracking
- `CategoryScore` — frozen dataclass: `name`, `score`, `details`
- `NodeDebt` — frozen dataclass: `ref_id`, `score`, `reasons`
- `DebtTrend` — frozen dataclass: `previous_snapshot`, `previous_score`, `delta`, `category_deltas`
- `DebtReport` — frozen dataclass: `debt_score` (0-100), `severity`, `categories`, `top_offenders`, `trend`
- `load_debt_weights(project_root)` -> `DebtWeights` — loads from `config.yml` `debt_report` section, defaults on missing
- `collect_debt_data(conn, project_root, weights=None)` -> `DebtData` — aggregates from all data sources
- `compute_debt_score(data, weights=None)` -> `DebtReport` — applies weighted formula, caps at 100
- `compute_top_offenders(data, weights, limit=10)` -> `list[NodeDebt]` — ranks nodes by debt contribution
- `compute_debt_trend(conn, current_report, project_root, weights=None)` -> `DebtTrend | None` — compares current debt against last snapshot, returns `None` if no snapshot exists
- `format_trend_section(trend)` -> `str` — renders trend as plain text with arrows (improved/regressed/unchanged)
- `format_debt_report(report)` -> `str` — renders full report as Rich-formatted terminal string
- `format_top_offenders_json(offenders)` -> `list[dict]` — serializes `NodeDebt` list for JSON output

Module `src/beadloom/infrastructure/doctor.py`:
- `Severity` — enum: `OK`, `INFO`, `WARNING`, `ERROR`
- `Check` — dataclass: `name`, `severity`, `description`
- `run_checks(conn)` -> `list[Check]` — runs 7 validation checks

## Testing

Tests: `tests/test_db.py`, `tests/test_health.py`, `tests/test_reindex.py`, `tests/test_reindex_config.py`, `tests/test_reindex_tests.py`, `tests/test_reindex_activity.py`, `tests/test_reindex_routes.py`, `tests/test_cli_reindex.py`, `tests/test_doctor.py`, `tests/test_doctor_drift.py`, `tests/test_watcher.py`, `tests/test_bead06_misc_fixes.py`, `tests/test_debt_report.py`
