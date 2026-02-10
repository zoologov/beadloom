"""Node detail panel widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Static

if TYPE_CHECKING:
    import sqlite3


class NodeDetail(Static):
    """Panel showing detailed node information."""

    def show_domain(self, conn: sqlite3.Connection, ref_id: str) -> None:
        """Show domain overview with child nodes."""
        row = conn.execute(
            "SELECT ref_id, kind, summary FROM nodes WHERE ref_id = ?",
            (ref_id,),
        ).fetchone()

        if row is None:
            self.update(f"Node '{ref_id}' not found.")
            return

        lines = [
            f"[bold]{row['ref_id']}[/bold] ({row['kind']})",
            f"{row['summary']}",
            "",
            "[bold]Child nodes:[/bold]",
        ]

        # Get child nodes via part_of edges
        children = conn.execute(
            "SELECT n.ref_id, n.kind, n.summary "
            "FROM edges e JOIN nodes n ON e.src_ref_id = n.ref_id "
            "WHERE e.dst_ref_id = ? AND e.kind = 'part_of' "
            "ORDER BY n.ref_id",
            (ref_id,),
        ).fetchall()

        for child in children:
            lines.append(
                f"  \u251c\u2500\u2500 {child['ref_id']} ({child['kind']}): "
                f"{child['summary']}"
            )

        if not children:
            lines.append("  (no child nodes)")

        self.update("\n".join(lines))

    def show_node(self, conn: sqlite3.Connection, ref_id: str) -> None:
        """Show detailed node info with edges, docs, symbols."""
        row = conn.execute(
            "SELECT ref_id, kind, summary FROM nodes WHERE ref_id = ?",
            (ref_id,),
        ).fetchone()

        if row is None:
            self.update(f"Node '{ref_id}' not found.")
            return

        lines = [
            f"[bold]{row['ref_id']}[/bold] ({row['kind']})",
            f"{row['summary']}",
            "",
        ]

        # Outgoing edges
        out_edges = conn.execute(
            "SELECT dst_ref_id, kind FROM edges "
            "WHERE src_ref_id = ? ORDER BY kind, dst_ref_id",
            (ref_id,),
        ).fetchall()

        if out_edges:
            lines.append("[bold]Outgoing edges:[/bold]")
            for edge in out_edges:
                lines.append(f"  \u2192 {edge['dst_ref_id']} [{edge['kind']}]")
            lines.append("")

        # Incoming edges
        in_edges = conn.execute(
            "SELECT src_ref_id, kind FROM edges "
            "WHERE dst_ref_id = ? ORDER BY kind, src_ref_id",
            (ref_id,),
        ).fetchall()

        if in_edges:
            lines.append("[bold]Incoming edges:[/bold]")
            for edge in in_edges:
                lines.append(f"  \u2190 {edge['src_ref_id']} [{edge['kind']}]")
            lines.append("")

        # Docs
        docs = conn.execute(
            "SELECT path, kind FROM docs WHERE ref_id = ? ORDER BY path",
            (ref_id,),
        ).fetchall()

        if docs:
            lines.append(f"[bold]Docs ({len(docs)}):[/bold]")
            for doc in docs:
                lines.append(f"  {doc['path']} ({doc['kind']})")
            lines.append("")

        # Sync status
        stale = conn.execute(
            "SELECT doc_path, code_path FROM sync_state "
            "WHERE ref_id = ? AND status = 'stale'",
            (ref_id,),
        ).fetchall()

        if stale:
            lines.append(f"[bold red]Stale docs ({len(stale)}):[/bold red]")
            for s in stale:
                lines.append(f"  {s['doc_path']} <-> {s['code_path']}")

        self.update("\n".join(lines))
