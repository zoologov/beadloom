"""Status bar widget showing health metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Static

if TYPE_CHECKING:
    import sqlite3


class StatusBar(Static):
    """Bottom bar showing index health metrics."""

    def load_stats(self, conn: sqlite3.Connection) -> None:
        """Load and display health statistics."""
        nodes_count: int = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        edges_count: int = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        docs_count: int = conn.execute("SELECT count(*) FROM docs").fetchone()[0]

        covered: int = conn.execute(
            "SELECT count(DISTINCT n.ref_id) FROM nodes n "
            "JOIN docs d ON d.ref_id = n.ref_id"
        ).fetchone()[0]

        coverage_pct = (covered / nodes_count * 100) if nodes_count > 0 else 0.0

        stale_count: int = conn.execute(
            "SELECT count(*) FROM sync_state WHERE status = 'stale'"
        ).fetchone()[0]

        text = (
            f" {nodes_count} nodes, {edges_count} edges, {docs_count} docs | "
            f"Coverage: {coverage_pct:.0f}% | "
            f"Stale: {stale_count}"
        )
        self.update(text)
