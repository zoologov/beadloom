"""Reindex orchestrator: drop + re-create SQLite from Git sources."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from beadloom import __version__
from beadloom.code_indexer import extract_symbols
from beadloom.db import SCHEMA_VERSION, create_schema, open_db, set_meta
from beadloom.doc_indexer import index_docs
from beadloom.graph_loader import load_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

# Tables to drop on reindex (order matters for FK constraints).
_TABLES_TO_DROP = [
    "sync_state",
    "code_symbols",
    "chunks",
    "docs",
    "edges",
    "nodes",
    "meta",
]

# File extensions to scan for code symbols.
_CODE_EXTENSIONS = frozenset({".py"})


@dataclass
class ReindexResult:
    """Summary of a reindex operation."""

    nodes_loaded: int = 0
    edges_loaded: int = 0
    docs_indexed: int = 0
    chunks_indexed: int = 0
    symbols_indexed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _drop_all_tables(conn: sqlite3.Connection) -> None:
    """Drop all application tables to allow a clean re-create."""
    for table in _TABLES_TO_DROP:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()


def _build_doc_ref_map(
    graph_dir: Path,
    project_root: Path,
) -> dict[str, str]:
    """Build a mapping of relative doc path → ref_id from YAML graph nodes.

    Scans YAML graph files for nodes with ``docs`` lists and maps each
    doc path to the node's ref_id.
    """
    import yaml

    ref_map: dict[str, str] = {}
    for yml_path in sorted(graph_dir.glob("*.yml")):
        text = yml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if data is None:
            continue
        for node in data.get("nodes") or []:
            ref_id = node.get("ref_id", "")
            for doc_path_str in node.get("docs") or []:
                # Normalize: if path starts with docs/, strip to make it relative to docs_dir.
                abs_path = project_root / doc_path_str
                docs_root = project_root / "docs"
                if abs_path.is_relative_to(docs_root):
                    rel = str(abs_path.relative_to(docs_root))
                else:
                    rel = doc_path_str
                ref_map[rel] = ref_id
    return ref_map


def _index_code_files(
    project_root: Path,
    conn: sqlite3.Connection,
    seen_ref_ids: set[str],
) -> tuple[int, list[str]]:
    """Scan source files, extract symbols, and insert into SQLite.

    Returns (symbols_indexed, warnings).
    """
    count = 0
    warnings: list[str] = []

    # Scan common source directories.
    scan_dirs = [project_root / "src", project_root / "lib", project_root / "app"]
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for file_path in sorted(scan_dir.rglob("*")):
            if file_path.suffix not in _CODE_EXTENSIONS:
                continue
            if not file_path.is_file():
                continue

            symbols = extract_symbols(file_path)
            rel_path = str(file_path.relative_to(project_root))

            for sym in symbols:
                conn.execute(
                    "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                    "line_start, line_end, annotations, file_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        rel_path,
                        sym["symbol_name"],
                        sym["kind"],
                        sym["line_start"],
                        sym["line_end"],
                        json.dumps(sym["annotations"], ensure_ascii=False),
                        sym["file_hash"],
                    ),
                )
                count += 1

                # Create touches_code edges for annotated symbols.
                annotations: dict[str, Any] = sym["annotations"]
                for _key, ref_id in annotations.items():
                    if ref_id in seen_ref_ids:
                        conn.execute(
                            "INSERT OR IGNORE INTO edges "
                            "(src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
                            (ref_id, ref_id, "touches_code"),
                        )

    conn.commit()
    return count, warnings


def _build_initial_sync_state(conn: sqlite3.Connection) -> None:
    """Populate sync_state table from docs and code_symbols with shared ref_ids."""
    from beadloom.sync_engine import build_sync_state

    now = datetime.now(tz=timezone.utc).isoformat()
    pairs = build_sync_state(conn)
    for pair in pairs:
        conn.execute(
            "INSERT OR IGNORE INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, 'ok')",
            (pair.doc_path, pair.code_path, pair.ref_id,
             pair.code_hash, pair.doc_hash, now),
        )
    conn.commit()


def reindex(project_root: Path) -> ReindexResult:
    """Full reindex: drop all tables, re-create schema, reload everything.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.beadloom/`` lives).

    Returns
    -------
    ReindexResult
        Summary with counts and diagnostics.
    """
    result = ReindexResult()

    db_path = project_root / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = open_db(db_path)

    # Drop + re-create.
    _drop_all_tables(conn)
    create_schema(conn)

    # 1. Load YAML graph.
    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        graph_result = load_graph(graph_dir, conn)
        result.nodes_loaded = graph_result.nodes_loaded
        result.edges_loaded = graph_result.edges_loaded
        result.errors.extend(graph_result.errors)
        result.warnings.extend(graph_result.warnings)

    # Collect known ref_ids for edge creation.
    seen_ref_ids = {
        row[0] for row in conn.execute("SELECT ref_id FROM nodes").fetchall()
    }

    # 2. Index documents.
    docs_dir = project_root / "docs"
    if docs_dir.is_dir():
        ref_map = _build_doc_ref_map(graph_dir, project_root) if graph_dir.is_dir() else {}
        doc_result = index_docs(docs_dir, conn, ref_id_map=ref_map)
        result.docs_indexed = doc_result.docs_indexed
        result.chunks_indexed = doc_result.chunks_indexed

    # 3. Index code symbols.
    symbols_count, sym_warnings = _index_code_files(project_root, conn, seen_ref_ids)
    result.symbols_indexed = symbols_count
    result.warnings.extend(sym_warnings)

    # 4. Build initial sync state.
    _build_initial_sync_state(conn)

    # 5. Set meta.
    now = datetime.now(tz=timezone.utc).isoformat()
    set_meta(conn, "last_reindex_at", now)
    set_meta(conn, "beadloom_version", __version__)
    set_meta(conn, "schema_version", SCHEMA_VERSION)

    conn.close()
    return result
