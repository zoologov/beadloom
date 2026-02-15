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


def _check_symbol_drift(conn: sqlite3.Connection) -> list[Check]:
    """Check for nodes with code symbol changes since last doc sync.

    Uses symbols_hash stored in sync_state (from BEAD-08) to detect
    when code symbols have changed but documentation hasn't been updated.
    """
    from beadloom.doc_sync.engine import _compute_symbols_hash

    # Gracefully handle old DBs without symbols_hash column.
    try:
        rows = conn.execute(
            "SELECT ref_id, doc_path, symbols_hash FROM sync_state "
            "WHERE symbols_hash != '' AND status = 'ok'"
        ).fetchall()
    except Exception:  # OperationalError on missing column
        return [
            Check(
                "symbol_drift",
                Severity.OK,
                "symbols_hash column not present — skipping drift check.",
            )
        ]

    if not rows:
        return [
            Check(
                "symbol_drift",
                Severity.OK,
                "No sync entries with symbols_hash to check.",
            )
        ]

    drifted: list[Check] = []
    for row in rows:
        ref_id: str = row["ref_id"]
        doc_path: str = row["doc_path"]
        stored_hash: str = row["symbols_hash"]
        current_hash = _compute_symbols_hash(conn, ref_id)
        if current_hash and current_hash != stored_hash:
            drifted.append(
                Check(
                    "symbol_drift",
                    Severity.WARNING,
                    f"Node '{ref_id}' has code changes since last doc update ({doc_path})",
                )
            )

    if not drifted:
        return [Check("symbol_drift", Severity.OK, "No symbol drift detected.")]
    return drifted


def _check_stale_sync(conn: sqlite3.Connection) -> list[Check]:
    """Report sync_state entries already marked as stale."""
    try:
        rows = conn.execute(
            "SELECT ref_id, doc_path, code_path FROM sync_state WHERE status = 'stale'"
        ).fetchall()
    except Exception:  # OperationalError on missing table
        return [Check("stale_sync", Severity.OK, "sync_state not available — skipping.")]

    if not rows:
        return [Check("stale_sync", Severity.OK, "No stale sync entries.")]

    return [
        Check(
            "stale_sync",
            Severity.WARNING,
            f"Sync stale for '{r['ref_id']}': doc={r['doc_path']}, code={r['code_path']}",
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
    results.extend(_check_symbol_drift(conn))
    results.extend(_check_stale_sync(conn))
    return results
