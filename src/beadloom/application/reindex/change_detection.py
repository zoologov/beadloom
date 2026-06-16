# beadloom:domain=application
# beadloom:feature=reindex
"""Reindex change detection: file-index hashing, diffing, and parser fingerprint.

This module owns deciding *what changed* for the incremental path: scanning the
project (graph YAML + docs + code) into a ``{path: (sha256, kind)}`` map,
reading/writing the persisted ``file_index``, diffing current vs stored, and
the parser fingerprint that forces a full reindex when the available
tree-sitter grammars change. It holds the change-detection logic only — no
indexing or orchestration.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from beadloom.application.reindex.models import _CODE_EXTENSIONS, _is_missing_table_error
from beadloom.infrastructure.scan_paths import resolve_scan_paths

if TYPE_CHECKING:
    from pathlib import Path


def _compute_parser_fingerprint() -> str:
    """Compute a fingerprint of currently available tree-sitter parsers.

    Returns a sorted, comma-separated string of supported extensions.
    When new parser packages are installed, this string changes, signalling
    that a full code reindex is needed.

    ``supported_extensions`` is looked up on the package namespace at call time
    (``beadloom.application.reindex.supported_extensions``) so tests can patch
    it there.
    """
    from beadloom.application import reindex as _pkg

    exts = _pkg.supported_extensions()
    return ",".join(sorted(exts))


def _get_stored_parser_fingerprint(conn: sqlite3.Connection) -> str | None:
    """Read the stored parser fingerprint from file_index.

    Uses a sentinel row with ``path='__parser_fingerprint__'``.
    Returns ``None`` if not stored.
    """
    try:
        row = conn.execute(
            "SELECT hash FROM file_index WHERE path = '__parser_fingerprint__'"
        ).fetchone()
    except sqlite3.OperationalError as exc:  # file_index may not exist on first run
        if _is_missing_table_error(exc):
            return None
        raise
    return row["hash"] if row else None


def _store_parser_fingerprint(conn: sqlite3.Connection, fingerprint: str) -> None:
    """Store the parser fingerprint in file_index as a sentinel row."""
    now = datetime.now(tz=timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) "
        "VALUES ('__parser_fingerprint__', ?, 'code', ?) "
        "ON CONFLICT(path) DO UPDATE SET hash=excluded.hash, "
        "indexed_at=excluded.indexed_at",
        (fingerprint, now),
    )
    conn.commit()


def _compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scan_project_files(
    project_root: Path,
    docs_dir: Path,
) -> dict[str, tuple[str, str]]:
    """Scan project files and return ``{relative_path: (sha256, kind)}``."""
    files: dict[str, tuple[str, str]] = {}

    # Graph YAML files
    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        for f in sorted(graph_dir.glob("*.yml")):
            rel = str(f.relative_to(project_root))
            files[rel] = (_compute_file_hash(f), "graph")

    # Doc files
    if docs_dir.is_dir():
        for f in sorted(docs_dir.rglob("*.md")):
            rel = str(f.relative_to(project_root))
            files[rel] = (_compute_file_hash(f), "doc")

    # Code files
    for dirname in resolve_scan_paths(project_root):
        scan_dir = project_root / dirname
        if not scan_dir.is_dir():
            continue
        for f in sorted(scan_dir.rglob("*")):
            if f.suffix not in _CODE_EXTENSIONS or not f.is_file():
                continue
            rel = str(f.relative_to(project_root))
            files[rel] = (_compute_file_hash(f), "code")

    return files


def _get_stored_file_index(
    conn: sqlite3.Connection,
) -> dict[str, tuple[str, str]]:
    """Read file_index from DB. Returns ``{path: (hash, kind)}``."""
    try:
        rows = conn.execute("SELECT path, hash, kind FROM file_index").fetchall()
    except sqlite3.OperationalError as exc:  # file_index may not exist on first run
        if _is_missing_table_error(exc):
            return {}
        raise
    return {
        row["path"]: (row["hash"], row["kind"]) for row in rows if not row["path"].startswith("__")
    }


def _diff_files(
    current: dict[str, tuple[str, str]],
    stored: dict[str, tuple[str, str]],
) -> tuple[set[str], set[str], set[str]]:
    """Compare current vs stored files. Returns ``(changed, added, deleted)``."""
    changed: set[str] = set()
    added: set[str] = set()

    for path, (hash_, _kind) in current.items():
        if path not in stored:
            added.add(path)
        elif stored[path][0] != hash_:
            changed.add(path)

    deleted = stored.keys() - current.keys()
    return changed, added, deleted


def _graph_yaml_changed(
    current_files: dict[str, tuple[str, str]],
    stored_files: dict[str, tuple[str, str]],
) -> bool:
    """Check whether any graph YAML file was added, removed, or modified.

    This is a direct comparison of hashes for files with ``kind == "graph"``
    in *current_files* vs *stored_files*.  Unlike :func:`_diff_files` (which
    relies on ``file_index`` being perfectly in sync), this function
    explicitly filters by kind so that graph changes are never missed — even
    when ``file_index`` is stale or partially populated.
    """
    current_graph = {p: h for p, (h, k) in current_files.items() if k == "graph"}
    stored_graph = {p: h for p, (h, k) in stored_files.items() if k == "graph"}

    # Different set of graph files → change.
    if current_graph.keys() != stored_graph.keys():
        return True

    # Same set — compare hashes.
    return any(current_graph[p] != stored_graph[p] for p in current_graph)


def _populate_file_index(
    conn: sqlite3.Connection,
    current_files: dict[str, tuple[str, str]],
) -> None:
    """Replace the entire file_index with *current_files*."""
    conn.execute("DELETE FROM file_index")
    now = datetime.now(tz=timezone.utc).isoformat()
    for path, (hash_, kind) in current_files.items():
        conn.execute(
            "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
            (path, hash_, kind, now),
        )
    conn.commit()


def _update_file_index(
    conn: sqlite3.Connection,
    current_files: dict[str, tuple[str, str]],
    changed: set[str],
    added: set[str],
    deleted: set[str],
) -> None:
    """Incrementally update file_index for affected paths."""
    now = datetime.now(tz=timezone.utc).isoformat()
    for path in deleted:
        conn.execute("DELETE FROM file_index WHERE path = ?", (path,))
    for path in changed | added:
        hash_, kind = current_files[path]
        conn.execute(
            "INSERT INTO file_index (path, hash, kind, indexed_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(path) DO UPDATE SET hash=excluded.hash, "
            "indexed_at=excluded.indexed_at",
            (path, hash_, kind, now),
        )
    conn.commit()
