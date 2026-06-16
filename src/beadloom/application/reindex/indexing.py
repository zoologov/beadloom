# beadloom:domain=application
# beadloom:feature=reindex
"""Reindex content indexing: scan docs and source files into the DB tables.

This module owns turning files on disk into ``docs``/``chunks`` and
``code_symbols`` rows: resolving the docs directory, building the doc-path ->
ref_id map from the YAML graph, and extracting symbols (bulk for full reindex,
single-file for the incremental path). It also creates the ``touches_code``
self-edges for annotated symbols.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from beadloom.application.reindex.models import _CODE_EXTENSIONS
from beadloom.context_oracle.code_indexer import extract_symbols
from beadloom.doc_sync.doc_indexer import chunk_markdown
from beadloom.infrastructure.scan_paths import resolve_scan_paths

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _resolve_docs_dir(project_root: Path) -> Path:
    """Resolve docs directory from config.yml or use default ``docs``.

    Checks ``.beadloom/config.yml`` for a ``docs_dir`` key.  If present,
    returns ``project_root / <value>``.  Otherwise falls back to
    ``project_root / "docs"``.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if config_path.exists():
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        docs_path = config.get("docs_dir")
        if isinstance(docs_path, str) and docs_path:
            return project_root / docs_path
    return project_root / "docs"


def _build_doc_ref_map(
    graph_dir: Path,
    project_root: Path,
    docs_dir: Path,
) -> tuple[dict[str, str], list[str]]:
    """Build a mapping of relative doc path → ref_id from YAML graph nodes.

    Scans YAML graph files for nodes with ``docs`` lists and maps each
    doc path to the node's ref_id.

    Parameters
    ----------
    graph_dir:
        Path to ``.beadloom/_graph`` directory containing YAML files.
    project_root:
        Root of the project.
    docs_dir:
        Resolved documentation directory (absolute path).

    Returns
    -------
    tuple[dict[str, str], list[str]]
        ``(ref_map, warnings)`` where *warnings* lists any doc path conflicts
        (i.e. a doc referenced by more than one node).
    """
    import yaml

    ref_map: dict[str, str] = {}
    warnings: list[str] = []
    for yml_path in sorted(graph_dir.glob("*.yml")):
        text = yml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if data is None:
            continue
        for node in data.get("nodes") or []:
            ref_id = node.get("ref_id", "")
            for doc_path_str in node.get("docs") or []:
                # Normalize: if path starts with docs dir prefix, strip to make it relative.
                abs_path = project_root / doc_path_str
                if abs_path.is_relative_to(docs_dir):
                    rel = str(abs_path.relative_to(docs_dir))
                else:
                    rel = doc_path_str
                if rel in ref_map and ref_map[rel] != ref_id:
                    warnings.append(
                        f"Doc '{rel}' referenced by both '{ref_map[rel]}' and '{ref_id}'; "
                        f"keeping '{ref_map[rel]}'"
                    )
                else:
                    ref_map[rel] = ref_id
    return ref_map, warnings


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

    # Scan directories from config.yml (or defaults).
    scan_dirs = [project_root / d for d in resolve_scan_paths(project_root)]
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


def _index_single_doc(
    conn: sqlite3.Connection,
    md_path: Path,
    docs_dir: Path,
    ref_map: dict[str, str],
) -> tuple[int, int]:
    """Index one doc file. Returns ``(docs_count, chunks_count)``."""
    content = md_path.read_text(encoding="utf-8")
    rel_path = str(md_path.relative_to(docs_dir))
    file_hash = hashlib.sha256(content.encode()).hexdigest()
    ref_id = ref_map.get(rel_path)

    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        (rel_path, "other", ref_id, file_hash),
    )
    doc_id = conn.execute("SELECT id FROM docs WHERE path = ?", (rel_path,)).fetchone()[0]

    chunks = chunk_markdown(content)
    for chunk in chunks:
        conn.execute(
            "INSERT INTO chunks (doc_id, chunk_index, heading, section, "
            "content, node_ref_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                doc_id,
                chunk["chunk_index"],
                chunk["heading"],
                chunk["section"],
                chunk["content"],
                ref_id,
            ),
        )
    conn.commit()
    return 1, len(chunks)


def _index_single_code_file(
    conn: sqlite3.Connection,
    file_path: Path,
    project_root: Path,
    seen_ref_ids: set[str],
) -> int:
    """Index one code file. Returns symbol count."""
    symbols = extract_symbols(file_path)
    rel_path = str(file_path.relative_to(project_root))
    count = 0

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

        annotations: dict[str, Any] = sym["annotations"]
        for _key, ref_id in annotations.items():
            if ref_id in seen_ref_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
                    (ref_id, ref_id, "touches_code"),
                )

    conn.commit()
    return count
