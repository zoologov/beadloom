"""SQLite database layer: connection management, schema, meta helpers."""

# beadloom:domain=infrastructure

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Schema version — increment on breaking changes
SCHEMA_VERSION = "3"

_SCHEMA_SQL = """\
-- Graph nodes
CREATE TABLE IF NOT EXISTS nodes (
    ref_id  TEXT PRIMARY KEY,
    kind    TEXT NOT NULL CHECK(kind IN ('domain','feature','service','entity','adr')),
    summary TEXT NOT NULL DEFAULT '',
    source  TEXT,
    extra   TEXT DEFAULT '{}',
    lifecycle TEXT NOT NULL DEFAULT 'active'
        CHECK(lifecycle IN ('active','planned','deprecated','dead'))
);

-- Graph edges
-- ``contract_key`` discriminates multiple contracts on the same (src,dst,kind)
-- node pair (BDL-037 #102): defaults to '' for plain edges (so their identity
-- stays effectively (src,dst,kind)), and carries the contract message_type for
-- AMQP contract edges so N message types on one pair don't collapse.
CREATE TABLE IF NOT EXISTS edges (
    src_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,
    dst_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK(kind IN (
        'part_of','depends_on','uses','implements',
        'touches_entity','touches_code','produces','consumes'
    )),
    extra      TEXT DEFAULT '{}',
    lifecycle  TEXT NOT NULL DEFAULT 'active'
        CHECK(lifecycle IN ('active','planned','deprecated','dead')),
    contract_key TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (src_ref_id, dst_ref_id, kind, contract_key)
);

-- Cross-repo (foreign) edges: at least one endpoint is a ``@repo:ref_id``
-- reference to a node in another repo (BDL-037 #100). Kept in a separate table
-- because a foreign endpoint cannot satisfy the ``edges`` FK to local nodes;
-- ``beadloom export`` unions these into the artifact so declared cross-repo
-- links survive to the hub.
CREATE TABLE IF NOT EXISTS foreign_edges (
    src_ref_id TEXT NOT NULL,
    dst_ref_id TEXT NOT NULL,
    kind       TEXT NOT NULL,
    extra      TEXT DEFAULT '{}',
    lifecycle  TEXT NOT NULL DEFAULT 'active'
        CHECK(lifecycle IN ('active','planned','deprecated','dead')),
    contract_key TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (src_ref_id, dst_ref_id, kind, contract_key)
);

-- Documents (Markdown file index)
CREATE TABLE IF NOT EXISTS docs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    path     TEXT NOT NULL UNIQUE,
    kind     TEXT NOT NULL CHECK(kind IN (
        'feature','domain','service','adr','architecture','other'
    )),
    ref_id   TEXT REFERENCES nodes(ref_id) ON DELETE SET NULL,
    metadata TEXT DEFAULT '{}',
    hash     TEXT NOT NULL
);

-- Document chunks
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id      INTEGER NOT NULL REFERENCES docs(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    heading     TEXT NOT NULL DEFAULT '',
    section     TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL,
    node_ref_id TEXT REFERENCES nodes(ref_id) ON DELETE SET NULL
);

-- Code symbols
CREATE TABLE IF NOT EXISTS code_symbols (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT NOT NULL,
    symbol_name TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK(kind IN (
        'function','class','type','route','component'
    )),
    line_start  INTEGER NOT NULL,
    line_end    INTEGER NOT NULL,
    annotations TEXT DEFAULT '{}',
    file_hash   TEXT NOT NULL
);

-- Doc↔code sync state
CREATE TABLE IF NOT EXISTS sync_state (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_path        TEXT NOT NULL,
    code_path       TEXT NOT NULL,
    ref_id          TEXT NOT NULL REFERENCES nodes(ref_id),
    code_hash_at_sync TEXT NOT NULL,
    doc_hash_at_sync  TEXT NOT NULL,
    synced_at       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'ok' CHECK(status IN ('ok','stale')),
    symbols_hash    TEXT DEFAULT '',
    doc_hash_at_last_edit TEXT DEFAULT '',
    UNIQUE(doc_path, code_path)
);

-- Index metadata
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Health snapshots (trend tracking, persists across reindexes)
CREATE TABLE IF NOT EXISTS health_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    taken_at        TEXT NOT NULL,
    nodes_count     INTEGER NOT NULL,
    edges_count     INTEGER NOT NULL,
    docs_count      INTEGER NOT NULL,
    coverage_pct    REAL NOT NULL,
    stale_count     INTEGER NOT NULL,
    isolated_count  INTEGER NOT NULL,
    extra           TEXT DEFAULT '{}'
);

-- File hash index (for incremental reindex)
CREATE TABLE IF NOT EXISTS file_index (
    path       TEXT PRIMARY KEY,
    hash       TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK(kind IN ('graph','doc','code')),
    indexed_at TEXT NOT NULL
);

-- Architecture graph snapshots (point-in-time captures)
CREATE TABLE IF NOT EXISTS graph_snapshots (
    id              INTEGER PRIMARY KEY,
    label           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    nodes_json      TEXT NOT NULL,
    edges_json      TEXT NOT NULL,
    symbols_count   INTEGER NOT NULL DEFAULT 0
);

-- Bundle cache (L2 persistent, survives restarts)
CREATE TABLE IF NOT EXISTS bundle_cache (
    cache_key   TEXT PRIMARY KEY,
    bundle_json TEXT NOT NULL,
    etag        TEXT NOT NULL,
    graph_mtime REAL NOT NULL,
    docs_mtime  REAL NOT NULL,
    created_at  TEXT NOT NULL
);

-- Full-text search index (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    ref_id,
    kind,
    summary,
    content,
    tokenize='porter unicode61'
);

-- Code imports (resolved import relationships)
CREATE TABLE IF NOT EXISTS code_imports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path       TEXT NOT NULL,
    line_number     INTEGER NOT NULL,
    import_path     TEXT NOT NULL,
    resolved_ref_id TEXT,
    file_hash       TEXT NOT NULL,
    UNIQUE(file_path, line_number, import_path)
);

-- Architecture rules (parsed from rules.yml)
CREATE TABLE IF NOT EXISTS rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    rule_type   TEXT NOT NULL CHECK(rule_type IN (
        'deny', 'require', 'forbid_cycles', 'layers',
        'cardinality', 'forbid_import', 'forbid_edge'
    )),
    rule_json   TEXT NOT NULL,
    enabled     INTEGER NOT NULL DEFAULT 1
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_ref_id);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_ref_id);
CREATE INDEX IF NOT EXISTS idx_docs_ref ON docs(ref_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_node ON chunks(node_ref_id);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON code_symbols(file_path);
CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_state(status);
CREATE INDEX IF NOT EXISTS idx_sync_ref ON sync_state(ref_id);
CREATE INDEX IF NOT EXISTS idx_imports_file ON code_imports(file_path);
CREATE INDEX IF NOT EXISTS idx_imports_ref ON code_imports(resolved_ref_id);
"""


def open_db(db_path: Path) -> sqlite3.Connection:
    """Open (or create) a SQLite database with proper PRAGMAs.

    Sets WAL journal mode (persistent per-file) and enables foreign keys
    (per-connection, required on every open).

    Returns a connection with ``sqlite3.Row`` row factory.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the column names of *table* (empty set if it does not exist)."""
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """True when *table* exists in the database."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    """Apply incremental schema migrations for new columns and tables.

    Handles the case where tables already exist but lack newer columns
    (e.g. ``symbols_hash`` added in BEAD-08, ``doc_hash_at_last_edit``
    added for two-phase sync in BDL-034 #70, the ``lifecycle`` column and the
    BDL-037 federation migrations).  Safe to call multiple times and on a
    partially-created schema (each step guards on the table/column existing).
    """
    sync_columns = _table_columns(conn, "sync_state")
    if sync_columns:
        if "symbols_hash" not in sync_columns:
            conn.execute("ALTER TABLE sync_state ADD COLUMN symbols_hash TEXT DEFAULT ''")
            conn.commit()
        if "doc_hash_at_last_edit" not in sync_columns:
            conn.execute(
                "ALTER TABLE sync_state ADD COLUMN doc_hash_at_last_edit TEXT DEFAULT ''"
            )
            conn.commit()

    # lifecycle column on nodes/edges (BDL-037 Principle 8). Additive: existing
    # DBs upgrade cleanly and existing rows default to 'active' (no regression).
    node_columns = _table_columns(conn, "nodes")
    if node_columns and "lifecycle" not in node_columns:
        conn.execute(
            "ALTER TABLE nodes ADD COLUMN lifecycle TEXT NOT NULL DEFAULT 'active' "
            "CHECK(lifecycle IN ('active','planned','deprecated','dead'))"
        )
        conn.commit()
    edge_columns = _table_columns(conn, "edges")
    if edge_columns and "lifecycle" not in edge_columns:
        conn.execute(
            "ALTER TABLE edges ADD COLUMN lifecycle TEXT NOT NULL DEFAULT 'active' "
            "CHECK(lifecycle IN ('active','planned','deprecated','dead'))"
        )
        conn.commit()

    _migrate_edges_contract_kinds(conn)
    _ensure_foreign_edges_table(conn)


def _migrate_edges_contract_kinds(conn: sqlite3.Connection) -> None:
    """Rebuild the ``edges`` table to add contract kinds + ``contract_key`` (#101/#102).

    SQLite cannot ALTER a CHECK constraint or a PRIMARY KEY, so a table that
    predates the federation changes must be rebuilt. The migration is additive:
    every existing row is copied with ``contract_key=''`` (preserving its
    ``(src,dst,kind)`` identity), and the new schema then also allows
    ``produces``/``consumes`` kinds and multiple contracts per node pair.
    """
    edge_columns = _table_columns(conn, "edges")
    if not edge_columns or "contract_key" in edge_columns:
        return
    conn.executescript(
        """
        PRAGMA foreign_keys=OFF;
        ALTER TABLE edges RENAME TO edges_old;
        CREATE TABLE edges (
            src_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,
            dst_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,
            kind       TEXT NOT NULL CHECK(kind IN (
                'part_of','depends_on','uses','implements',
                'touches_entity','touches_code','produces','consumes'
            )),
            extra      TEXT DEFAULT '{}',
            lifecycle  TEXT NOT NULL DEFAULT 'active'
                CHECK(lifecycle IN ('active','planned','deprecated','dead')),
            contract_key TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (src_ref_id, dst_ref_id, kind, contract_key)
        );
        INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra, lifecycle)
            SELECT src_ref_id, dst_ref_id, kind, extra, lifecycle FROM edges_old;
        DROP TABLE edges_old;
        CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_ref_id);
        CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_ref_id);
        PRAGMA foreign_keys=ON;
        """
    )
    conn.commit()


def _ensure_foreign_edges_table(conn: sqlite3.Connection) -> None:
    """Create the ``foreign_edges`` table on older DBs that predate it (#100)."""
    if _table_exists(conn, "foreign_edges"):
        return
    conn.execute(
        "CREATE TABLE foreign_edges ("
        "  src_ref_id TEXT NOT NULL,"
        "  dst_ref_id TEXT NOT NULL,"
        "  kind TEXT NOT NULL,"
        "  extra TEXT DEFAULT '{}',"
        "  lifecycle TEXT NOT NULL DEFAULT 'active'"
        "    CHECK(lifecycle IN ('active','planned','deprecated','dead')),"
        "  contract_key TEXT NOT NULL DEFAULT '',"
        "  PRIMARY KEY (src_ref_id, dst_ref_id, kind, contract_key)"
        ")"
    )
    conn.commit()


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes if they don't exist.

    Safe to call multiple times (uses IF NOT EXISTS).
    """
    conn.executescript(_SCHEMA_SQL)
    ensure_schema_migrations(conn)


def get_meta(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    """Read a value from the ``meta`` table.

    Returns *default* (``None``) if the key doesn't exist.
    """
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return str(row[0])


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Insert or update a key in the ``meta`` table."""
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
