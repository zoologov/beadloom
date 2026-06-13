<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:53:18.143877+00:00 · coverage 100% (`db`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

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
- `create_schema(conn)` — create all tables/indexes and run
  `ensure_schema_migrations`.
- `ensure_schema_migrations(conn)` — apply the additive, idempotent migrations
  (the `lifecycle` column + `external` CHECK rebuild, `edges.contract_key`,
  `foreign_edges`, the free-form `kind` rebuild, …).
- `get_meta(conn, key, default=None)` / `set_meta(conn, key, value)` — the
  `meta` key/value helpers.
- `SCHEMA_VERSION` — the schema version constant (currently `"4"`).

## Collaborators

The lowest layer: every domain reads and writes through it. The full table
inventory (nodes/edges/foreign_edges, docs/chunks, code_symbols, sync_state,
health/graph snapshots, FTS5 search, rules, …) and the migration detail live in
the [infrastructure README](../../README.md).

> Component doc (BDL-051). Public surface verified against `db.py`.
