"""Doctor: validation checks for graph and data integrity."""

# beadloom:domain=doctor

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


class Severity(enum.Enum):
    """Severity level for a check result."""

    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Check:
    """Result of a single validation check."""

    name: str
    severity: Severity
    description: str


def _check_empty_summaries(conn: sqlite3.Connection) -> list[Check]:
    """Nodes with empty summary."""
    rows = conn.execute(
        "SELECT ref_id FROM nodes WHERE summary = '' OR summary IS NULL"
    ).fetchall()
    if not rows:
        return [Check("empty_summaries", Severity.OK, "All nodes have summaries.")]
    return [
        Check(
            "empty_summaries",
            Severity.WARNING,
            f"Node '{r['ref_id']}' has empty summary.",
        )
        for r in rows
    ]


def _check_unlinked_docs(conn: sqlite3.Connection) -> list[Check]:
    """Docs without a ref_id link to a graph node."""
    rows = conn.execute("SELECT path FROM docs WHERE ref_id IS NULL").fetchall()
    if not rows:
        return [Check("unlinked_docs", Severity.OK, "All docs are linked to nodes.")]
    return [
        Check(
            "unlinked_docs",
            Severity.WARNING,
            f"Doc '{r['path']}' has no ref_id — unlinked from graph.",
        )
        for r in rows
    ]


def _check_nodes_without_docs(conn: sqlite3.Connection) -> list[Check]:
    """Nodes that have no associated documentation."""
    rows = conn.execute(
        "SELECT n.ref_id FROM nodes n LEFT JOIN docs d ON d.ref_id = n.ref_id WHERE d.id IS NULL"
    ).fetchall()
    if not rows:
        return [Check("nodes_without_docs", Severity.OK, "All nodes have documentation.")]
    return [
        Check(
            "nodes_without_docs",
            Severity.INFO,
            f"Node '{r['ref_id']}' has no doc linked.",
        )
        for r in rows
    ]


def _check_isolated_nodes(conn: sqlite3.Connection) -> list[Check]:
    """Nodes with no incoming or outgoing edges."""
    rows = conn.execute(
        "SELECT n.ref_id FROM nodes n "
        "LEFT JOIN edges e1 ON e1.src_ref_id = n.ref_id "
        "LEFT JOIN edges e2 ON e2.dst_ref_id = n.ref_id "
        "WHERE e1.src_ref_id IS NULL AND e2.dst_ref_id IS NULL"
    ).fetchall()
    if not rows:
        return [Check("isolated_nodes", Severity.OK, "No isolated nodes.")]
    return [
        Check(
            "isolated_nodes",
            Severity.INFO,
            f"Node '{r['ref_id']}' has no edges (isolated).",
        )
        for r in rows
    ]


def run_checks(conn: sqlite3.Connection) -> list[Check]:
    """Run all validation checks and return results."""
    results: list[Check] = []
    results.extend(_check_empty_summaries(conn))
    results.extend(_check_unlinked_docs(conn))
    results.extend(_check_nodes_without_docs(conn))
    results.extend(_check_isolated_nodes(conn))
    return results
