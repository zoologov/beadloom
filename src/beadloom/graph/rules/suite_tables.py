# beadloom:domain=graph
# beadloom:feature=rule-engine
"""The test suite as the index records it, read for the rules that judge it.

**One responsibility:** read the ``test_files`` and ``test_imports`` tables the
reindex writes (BDL-074 C1) and the graph facts a suite rule selects them by —
which nodes a matcher names, and whether a test file's node or one of its
``part_of`` containers is among them. ``test_binding`` and
``test_import_boundary`` both ask these questions; answering them twice is how
two rules come to disagree about one file.

Reads are positional (``row[0]``), not by column name, so a connection opened
without ``sqlite3.Row`` answers the same as one opened with it.

**An index older than the test tables is not an empty suite.** Every reader
returns ``None`` for an absent table, so a rule can say "reindex" rather than
report every node untested.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.graph.rules.layer_reach import part_of_parents
from beadloom.graph.rules.layers import part_of_ancestors
from beadloom.graph.rules.node_tags import node_tags

if TYPE_CHECKING:
    from beadloom.graph.rules.types import NodeMatcher


@dataclass(frozen=True)
class IndexedTestFile:
    """One test file as the reindex recorded it: its path, its node and its placement."""

    __test__ = False  # a product type, not a pytest test class

    path: str
    ref_id: str | None
    placement: str


@dataclass(frozen=True)
class TestImport:
    """One import a test file makes, in the ``code_imports`` shape."""

    __test__ = False  # a product type, not a pytest test class

    file_path: str
    line_number: int
    import_path: str


def read_test_files(conn: sqlite3.Connection) -> list[IndexedTestFile] | None:
    """Every indexed test file, by path — ``None`` for an index without the table."""
    try:
        rows = conn.execute(
            "SELECT path, ref_id, placement FROM test_files ORDER BY path"
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    return [
        IndexedTestFile(
            path=str(row[0]),
            ref_id=None if row[1] is None else str(row[1]),
            placement=str(row[2]),
        )
        for row in rows
    ]


def read_test_imports(conn: sqlite3.Connection) -> list[TestImport] | None:
    """Every recorded test import, in a stable order — ``None`` without the table.

    The reader that recorded them keeps an aliased ``import a as b``, which the
    code-import extractor drops, so a test's imports are read slightly more
    completely than a source file's (C1).
    """
    try:
        rows = conn.execute(
            "SELECT file_path, line_number, import_path FROM test_imports "
            "ORDER BY file_path, line_number, import_path"
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    return [TestImport(str(row[0]), int(row[1]), str(row[2])) for row in rows]


class NodeSelection:
    """Which nodes a matcher names, and whether a node is one of them or inside one."""

    def __init__(self, conn: sqlite3.Connection, matcher: NodeMatcher) -> None:
        self._matcher = matcher
        tags = node_tags(conn)
        rows = conn.execute("SELECT ref_id, kind FROM nodes ORDER BY ref_id").fetchall()
        self.nodes: list[str] = [
            str(row[0])
            for row in rows
            if matcher.matches(str(row[0]), str(row[1]), tags=tags.of(str(row[0])))
        ]
        self._selected = frozenset(self.nodes)
        self._parents = part_of_parents(conn)

    def holds_or_contains(self, ref_id: str) -> bool:
        """True when *ref_id* is selected or is ``part_of`` a selected node."""
        if ref_id in self._selected:
            return True
        return not self._selected.isdisjoint(part_of_ancestors(ref_id, self._parents))

    def covered_by(self, bound_refs: set[str]) -> set[str]:
        """The selected nodes that are, or contain, one of *bound_refs*."""
        reached: set[str] = set()
        for ref_id in bound_refs:
            reached.add(ref_id)
            reached.update(part_of_ancestors(ref_id, self._parents))
        return reached & self._selected
