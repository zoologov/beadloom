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
  `foreign_edges`, the free-form `kind` rebuild, `sync_state.baseline_source`,
  the four-verdict `sync_state.status` rebuild, `declared_docs`, …).
- `get_meta(conn, key, default=None)` / `set_meta(conn, key, value)` — the
  `meta` key/value helpers.
- `SCHEMA_VERSION` — the schema version constant (currently `"4"`).

## Collaborators

The lowest layer: every domain reads and writes through it. The full table
inventory (nodes/edges/foreign_edges, docs/chunks, declared_docs, code_symbols, sync_state,
health/graph snapshots, FTS5 search, rules, …) and the migration detail live in
the [infrastructure README](../../README.md).

> Component doc (BDL-051). Public surface verified against `db.py`.
