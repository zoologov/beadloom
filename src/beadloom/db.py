"""SQLite database layer: connection management, schema, meta helpers."""

# beadloom:domain=db

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Schema version — increment on breaking changes
SCHEMA_VERSION = "1"

_SCHEMA_SQL = """\
-- Graph nodes
CREATE TABLE IF NOT EXISTS nodes (
    ref_id  TEXT PRIMARY KEY,
    kind    TEXT NOT NULL CHECK(kind IN ('domain','feature','service','entity','adr')),
    summary TEXT NOT NULL DEFAULT '',
    source  TEXT,
    extra   TEXT DEFAULT '{}'
);

-- Graph edges
CREATE TABLE IF NOT EXISTS edges (
    src_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,
    dst_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK(kind IN (
        'part_of','depends_on','uses','implements',
        'touches_entity','touches_code'
    )),
    extra      TEXT DEFAULT '{}',
    PRIMARY KEY (src_ref_id, dst_ref_id, kind)
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
    UNIQUE(doc_path, code_path)
);

-- Index metadata
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
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


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes if they don't exist.

    Safe to call multiple times (uses IF NOT EXISTS).
    """
    conn.executescript(_SCHEMA_SQL)


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
