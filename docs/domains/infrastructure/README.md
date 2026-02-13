# Infrastructure

SQLite database layer, health metrics, and reindex orchestrator.

## Specification

### Modules

- **db.py** — `open_db()` opens a SQLite connection with WAL mode and foreign keys enabled. `create_schema()` creates all tables. `get_meta()`/`set_meta()` for key-value metadata.
- **health.py** — `take_snapshot()` captures current index statistics (node/edge/doc/symbol counts, coverage, stale docs). `get_latest_snapshots()` retrieves history for trend comparison.
- **reindex.py** — `reindex(root)` performs full reindex: drop tables → create schema → load graph YAML → index docs → index code → build sync state → take health snapshot. `incremental_reindex(root)` updates only changed files.

### Database Schema

Stored in `.beadloom/beadloom.db` (WAL mode):
- `nodes`, `edges` — knowledge graph
- `docs`, `chunks` — document index
- `code_symbols` — code symbol index
- `sync_state` — doc↔code synchronization
- `meta` — index metadata

## API

Module `src/beadloom/infrastructure/db.py`:
- `open_db(path)` → `sqlite3.Connection`
- `create_schema(conn)` — create all tables
- `get_meta(conn, key)` / `set_meta(conn, key, value)`

Module `src/beadloom/infrastructure/health.py`:
- `take_snapshot(conn)` → `HealthSnapshot`
- `get_latest_snapshots(conn, n)` → `list[HealthSnapshot]`

Module `src/beadloom/infrastructure/reindex.py`:
- `reindex(root)` — full reindex
- `incremental_reindex(root)` — incremental reindex

## Testing

Tests: `tests/test_db.py`, `tests/test_health.py`, `tests/test_reindex.py`
