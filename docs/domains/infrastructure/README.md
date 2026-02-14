# Infrastructure

SQLite database layer, health metrics, and reindex orchestrator.

## Specification

### Modules

- **db.py** — `open_db()` opens a SQLite connection with WAL mode and foreign keys enabled. `create_schema()` creates all tables. `get_meta()`/`set_meta()` for key-value metadata.
- **health.py** — `take_snapshot()` captures current index statistics (node/edge/doc/symbol counts, coverage, stale docs). `get_latest_snapshots()` retrieves history for trend comparison.
- **reindex.py** — `reindex(root)` performs full reindex: drop tables → create schema → load graph YAML → index docs → index code → build sync state → take health snapshot. Stores parser fingerprint for change detection. `incremental_reindex(root)` updates only changed files; detects parser availability changes via fingerprint comparison and triggers full code reindex when new parsers become available.
- **doctor.py** — `run_checks(conn)` validates graph health: empty summaries, unlinked docs, nodes without docs, isolated nodes.
- **watcher.py** — Filesystem watcher for live reindex on file changes.

### Database Schema

Stored in `.beadloom/beadloom.db` (WAL mode):
- `nodes`, `edges` — architecture graph
- `docs`, `chunks` — document index
- `code_symbols` — code symbol index
- `code_imports` — resolved import relationships
- `sync_state` — doc↔code synchronization
- `file_index` — file hash tracking for incremental reindex (includes `__parser_fingerprint__` sentinel row)
- `meta` — index metadata

### Parser Fingerprint

`incremental_reindex()` tracks available tree-sitter parsers via a fingerprint (sorted comma-separated `supported_extensions()`). Stored as a sentinel row in `file_index` with `path='__parser_fingerprint__'`. When the fingerprint changes (e.g. after `uv tool install "beadloom[languages]"`), a full code reindex is triggered automatically, ensuring new language parsers are used without requiring `--full`.

## API

Module `src/beadloom/infrastructure/db.py`:
- `open_db(path)` → `sqlite3.Connection`
- `create_schema(conn)` — create all tables
- `get_meta(conn, key)` / `set_meta(conn, key, value)`

Module `src/beadloom/infrastructure/health.py`:
- `take_snapshot(conn)` → `HealthSnapshot`
- `get_latest_snapshots(conn, n)` → `list[HealthSnapshot]`

Module `src/beadloom/infrastructure/reindex.py`:
- `reindex(root)` — full reindex, stores parser fingerprint
- `incremental_reindex(root)` — incremental reindex with parser fingerprint comparison

Module `src/beadloom/infrastructure/doctor.py`:
- `run_checks(conn)` → `list[Check]` — 4 health checks

## Testing

Tests: `tests/test_db.py`, `tests/test_health.py`, `tests/test_reindex.py`, `tests/test_cli_reindex.py`, `tests/test_bead06_misc_fixes.py`
