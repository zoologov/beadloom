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
        self.clear_options()

        # Get all domains
        rows = conn.execute(
            "SELECT ref_id, summary FROM nodes WHERE kind = 'domain' ORDER BY ref_id"
        ).fetchall()

        for row in rows:
            ref_id: str = row["ref_id"]

            # Count edges involving this domain
            child_count: int = conn.execute(
                "SELECT count(*) FROM edges WHERE src_ref_id = ? OR dst_ref_id = ?",
                (ref_id, ref_id),
            ).fetchone()[0]

            # Check doc coverage
            has_docs: bool = (
                conn.execute(
                    "SELECT count(*) FROM docs WHERE ref_id = ?",
                    (ref_id,),
                ).fetchone()[0]
                > 0
            )

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
