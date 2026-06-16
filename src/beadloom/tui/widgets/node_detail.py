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
        from beadloom.application import graph_reads

        node = graph_reads.get_node(conn, ref_id)
        if node is None:
            self.update(f"Node '{ref_id}' not found.")
            return

        lines = [
            f"[bold]{node.ref_id}[/bold] ({node.kind})",
            f"{node.summary}",
            "",
            "[bold]Child nodes:[/bold]",
        ]

        # Get child nodes via part_of edges
        children = graph_reads.get_part_of_children(conn, ref_id)
        for child in children:
            lines.append(
                f"  \u251c\u2500\u2500 {child.ref_id} ({child.kind}): {child.summary}"
            )

        if not children:
            lines.append("  (no child nodes)")

        self.update("\n".join(lines))

    def show_node(self, conn: sqlite3.Connection, ref_id: str) -> None:
        """Show detailed node info with edges, docs, symbols."""
        from beadloom.application import graph_reads

        node = graph_reads.get_node(conn, ref_id)
        if node is None:
            self.update(f"Node '{ref_id}' not found.")
            return

        lines = [
            f"[bold]{node.ref_id}[/bold] ({node.kind})",
            f"{node.summary}",
            "",
        ]

        # Outgoing edges
        out_edges = graph_reads.get_outgoing_edges(conn, ref_id)
        if out_edges:
            lines.append("[bold]Outgoing edges:[/bold]")
            for edge in out_edges:
                lines.append(f"  \u2192 {edge.dst_ref_id} [{edge.kind}]")
            lines.append("")

        # Incoming edges
        in_edges = graph_reads.get_incoming_edges(conn, ref_id)
        if in_edges:
            lines.append("[bold]Incoming edges:[/bold]")
            for edge in in_edges:
                lines.append(f"  \u2190 {edge.src_ref_id} [{edge.kind}]")
            lines.append("")

        # Docs
        docs = graph_reads.get_docs_for_ref(conn, ref_id)
        if docs:
            lines.append(f"[bold]Docs ({len(docs)}):[/bold]")
            for path, kind in docs:
                lines.append(f"  {path} ({kind})")
            lines.append("")

        # Sync status
        stale = graph_reads.get_stale_pairs_for_ref(conn, ref_id)
        if stale:
            lines.append(f"[bold red]Stale docs ({len(stale)}):[/bold red]")
            for doc_path, code_path in stale:
                lines.append(f"  {doc_path} <-> {code_path}")

        self.update("\n".join(lines))
