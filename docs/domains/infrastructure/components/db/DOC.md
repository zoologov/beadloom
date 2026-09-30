# DB (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/db.py`

---

## Overview

The domain-agnostic SQLite layer: connection management, schema creation, and
the `meta` key/value helpers. Every other domain reads and writes through this
single, lowest-layer module — it owns the database file lifecycle and the table
definitions the rest of Beadloom depends on.

## Public surface

- `open_db(db_path)` — open a SQLite connection with WAL mode, foreign keys,
  and a `sqlite3.Row` row factory.
- `open_db_readonly(db_path)` — open an EXISTING database through the
  `mode=ro` URI with `query_only=ON`, leaving the file byte-identical; raises
  `FileNotFoundError` rather than creating one. `open_db` sets
  `journal_mode=WAL`, which rewrites the header of a database that is not
  already in WAL — so a verb that only reads still changed the artifact it
  reported on (BDL-UX #147).
- `connection(db_path)` / `readonly_connection(db_path)` — context-manager
  wrappers over the two factories.
- `create_schema(conn)` — create all tables/indexes and run
  `ensure_schema_migrations`.
- `ensure_schema_migrations(conn)` — apply the additive, idempotent migrations
  (the `lifecycle` column + `external` CHECK rebuild, `edges.contract_key`,
  `foreign_edges`, the free-form `kind` rebuild of `nodes`, `edges` and, since
  BDL-076 J3, `code_symbols` (row ids kept, `idx_symbols_file` recreated), `sync_state.baseline_source`,
  `sync_state.file_symbols_hash` (added after the table rebuilds, which copy an
  explicit column list and would drop a column added before them),
  the four-verdict `sync_state.status` rebuild, `declared_docs`, the
  `docs.space` column, …). `docs.space` records which documentation space a
  file belongs to — `to_be`, `as_is` or `working` — and defaults to `as_is`,
  which is what every row in a pre-BDL-061 index already was.
- The test-file tables (BDL-074 C1), created by the schema script with
  `CREATE TABLE IF NOT EXISTS`, so they are additive and `SCHEMA_VERSION` is
  unchanged: `test_files(path, kind, ref_id, placement, test_count, file_hash)`,
  `test_imports(file_path, line_number, import_path, resolved_ref_id)` in the
  `code_imports` shape, and `test_overrides(ref_id, prefix)` for the `tests:`
  prefixes a node declares. Indexes `idx_test_files_ref` and
  `idx_test_imports_file`. Tests live here and never in `code_symbols`,
  `code_imports` or `file_index`, so they do not become code.
- `get_meta(conn, key, default=None)` / `set_meta(conn, key, value)` — the
  `meta` key/value helpers.
- `SCHEMA_VERSION` — the schema version constant (currently `"4"`).

## Collaborators

The lowest layer: every domain reads and writes through it. The full table
inventory (nodes/edges/foreign_edges, docs/chunks, declared_docs, code_symbols, sync_state,
test_files/test_imports/test_overrides,
health/graph snapshots, FTS5 search, rules, …) and the migration detail live in
the [infrastructure README](../../README.md).

> Component doc (BDL-051). Public surface verified against `db.py`.
