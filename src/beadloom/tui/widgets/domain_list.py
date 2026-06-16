"""Domain list sidebar widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    import sqlite3


class DomainList(OptionList):
    """Sidebar listing all domains with indicators."""

    class DomainSelected(Message):
        """Emitted when a domain is selected."""

        def __init__(self, ref_id: str) -> None:
            super().__init__()
            self.ref_id = ref_id

    class NodeSelected(Message):
        """Emitted when a node is selected."""

        def __init__(self, ref_id: str) -> None:
            super().__init__()
            self.ref_id = ref_id

    def load_domains(self, conn: sqlite3.Connection) -> None:
        """Load domains from database."""
        from beadloom.application import graph_reads

        self.clear_options()

        for node in graph_reads.get_nodes_by_kind(conn, "domain"):
            ref_id = node.ref_id
            child_count = graph_reads.count_edges_touching(conn, ref_id)
            has_docs = graph_reads.count_docs_for_ref(conn, ref_id) > 0

            indicator = "\u25cf" if has_docs else "\u25cb"
            label = f"{indicator} {ref_id} [{child_count}]"
            self.add_option(Option(label, id=ref_id))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection (click / Enter)."""
        if event.option.id is not None:
            self.post_message(self.DomainSelected(str(event.option.id)))

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Handle highlight change (arrow keys)."""
        if event.option.id is not None:
            self.post_message(self.DomainSelected(str(event.option.id)))
