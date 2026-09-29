"""An index holding a graph and a test suite, built row by row for the suite rules.

The three rules that judge the test suite against the graph (`test_binding`,
`test_import_boundary`, `scenario_binding`) read the node, edge, test-file and
test-import tables a reindex writes. Building those rows by hand, rather than
reindexing a project, keeps each fixture to the facts its test is about: a file's
placement is stated, not derived, so a test of the rule cannot pass or fail on
the binding's own logic.

Every name here is invented (`ledger`, `billing`, `vault`), so a rule that passed
by recognising this repository's own graph would fail these fixtures.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@dataclass(frozen=True)
class SuiteNode:
    """One graph node: its id, its kind, its containers and its own tags."""

    ref_id: str
    kind: str = "feature"
    part_of: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class SuiteFile:
    """One indexed test file, with the binding and placement the reindex recorded."""

    path: str
    ref_id: str | None = None
    placement: str = "mirror"
    kind: str | None = "unit"
    imports: tuple[str, ...] = ()


@dataclass
class SuiteIndex:
    """The rows to write; :meth:`build` writes them into a fresh index and returns it."""

    nodes: list[SuiteNode] = field(default_factory=list)
    files: list[SuiteFile] = field(default_factory=list)

    def build(self, directory: Path) -> sqlite3.Connection:
        conn = open_db(directory / "suite.db")
        create_schema(conn)
        for node in self.nodes:
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, '', ?)",
                (node.ref_id, node.kind, json.dumps({"tags": list(node.tags)})),
            )
        for node in self.nodes:
            for parent in node.part_of:
                conn.execute(
                    "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, 'part_of')",
                    (node.ref_id, parent),
                )
        for test_file in self.files:
            conn.execute(
                "INSERT INTO test_files (path, kind, ref_id, placement, test_count, file_hash) "
                "VALUES (?, ?, ?, ?, 1, '')",
                (test_file.path, test_file.kind, test_file.ref_id, test_file.placement),
            )
            for line, import_path in enumerate(test_file.imports, start=1):
                conn.execute(
                    "INSERT INTO test_imports (file_path, line_number, import_path) "
                    "VALUES (?, ?, ?)",
                    (test_file.path, line, import_path),
                )
        conn.commit()
        return conn


def write_feature(root: Path, relative: str, text: str) -> None:
    """Write one `.feature` file under *root*, creating its folders."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_rules(root: Path, body: str) -> Path:
    """Write a `rules.yml` holding *body* under `version: 3` and return its path."""
    path = root / "rules.yml"
    path.write_text("version: 3\nrules:\n" + body, encoding="utf-8")
    return path
