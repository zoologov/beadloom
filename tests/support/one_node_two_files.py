"""One node whose one document is paired with two code files, written by hand into an index.

Moved out of ``test_sibling_symbol_baseline.py`` when BDL-074 ``beadloom-2mj3.7``
split it by node: the sync engine's per-file verdicts and the reindex's rebuild of
the sync baseline read the same index, and a helper several test modules share
lives here rather than in either of them.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from beadloom.doc_sync.engine import _compute_symbols_hash

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def annotated_function(ref: str, name: str) -> str:
    return f"# beadloom:feature={ref}\ndef {name}():\n    pass\n"


def one_node_two_files(conn: sqlite3.Connection, project: Path) -> None:
    """A single node whose ONE document is paired with TWO code files.

    This is the shape #182 was measured on: `application/README.md` against
    every module of the domain.
    """
    doc = "# Domain\n\nWhat the domain does.\n"
    (project / "docs" / "readme.md").write_text(doc)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("D1", "domain", "Domain 1"),
    )
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("readme.md", "domain", "D1", content_hash(doc)),
    )
    for name in ("alpha", "beta"):
        body = annotated_function("D1", name)
        (project / "src" / f"{name}.py").write_text(body)
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                f"src/{name}.py",
                name,
                "function",
                1,
                3,
                json.dumps({"feature": "D1"}),
                content_hash(body),
            ),
        )
    conn.commit()


def record_baseline(conn: sqlite3.Connection, project: Path, *, per_file: bool = True) -> None:
    """Record the sync baseline for both pairs, as a reindex would."""
    node_hash = _compute_symbols_hash(conn, "D1")
    for name in ("alpha", "beta"):
        code_path = f"src/{name}.py"
        file_hash = _compute_symbols_hash(conn, "D1", file_path=code_path) if per_file else ""
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status, symbols_hash, file_symbols_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, 'ok', ?, ?)",
            (
                "readme.md",
                code_path,
                "D1",
                content_hash((project / "src" / f"{name}.py").read_text(encoding="utf-8")),
                content_hash((project / "docs" / "readme.md").read_text(encoding="utf-8")),
                "2025-01-01",
                node_hash,
                file_hash,
            ),
        )
    conn.commit()


def move_alpha_symbols(conn: sqlite3.Connection, project: Path) -> None:
    """Rename alpha's symbol AND rewrite its file, as a real edit would."""
    body = "# beadloom:feature=D1\ndef alpha_renamed():\n    pass\n"
    (project / "src" / "alpha.py").write_text(body)
    conn.execute(
        "UPDATE code_symbols SET symbol_name = ?, file_hash = ? WHERE file_path = ?",
        ("alpha_renamed", content_hash(body), "src/alpha.py"),
    )
    conn.commit()


def by_code_path(results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(r["code_path"]): r for r in results if r.get("code_path")}
