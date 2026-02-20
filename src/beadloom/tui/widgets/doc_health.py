# beadloom:service=tui
"""Doc health table widget showing documentation status per node."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual.widgets import DataTable

if TYPE_CHECKING:
    from beadloom.tui.data_providers import GraphDataProvider, SyncDataProvider

logger = logging.getLogger(__name__)

# Status indicators
STATUS_FRESH = "\u25cf"  # ●
STATUS_STALE = "\u25b2"  # ▲
STATUS_MISSING = "\u2716"  # ✖

# Status labels
LABEL_FRESH = "fresh"
LABEL_STALE = "stale"
LABEL_MISSING = "missing"

# Sort order: stale first, then missing, then fresh
_STATUS_SORT_ORDER: dict[str, int] = {
    LABEL_STALE: 0,
    LABEL_MISSING: 1,
    LABEL_FRESH: 2,
}

# Column definitions
_COL_NODE = "Node"
_COL_STATUS = "Status"
_COL_DOC_PATH = "Doc Path"
_COL_REASON = "Reason"


def compute_doc_rows(
    *,
    graph_provider: GraphDataProvider | None,
    sync_provider: SyncDataProvider | None,
) -> list[dict[str, str]]:
    """Compute doc health rows from graph and sync data.

    Each row contains: ref_id, status_label, status_indicator, doc_path, reason.
    Rows are sorted: stale first, then missing, then fresh.
    """
    if graph_provider is None:
        return []

    nodes = graph_provider.get_nodes()
    if not nodes:
        return []

    # Build sync lookup: ref_id -> list of sync results
    sync_lookup: dict[str, list[dict[str, Any]]] = {}
    if sync_provider is not None:
        try:
            for result in sync_provider.get_sync_results():
                ref_id = str(result.get("ref_id", ""))
                if ref_id:
                    sync_lookup.setdefault(ref_id, []).append(result)
        except Exception:
            logger.debug("Failed to load sync results", exc_info=True)

    # Build doc_ref_ids set
    doc_ref_ids = graph_provider.get_doc_ref_ids()

    rows: list[dict[str, str]] = []
    for node in nodes:
        ref_id = node["ref_id"]

        # Determine status
        if ref_id in sync_lookup:
            # Has sync entries — check if any are stale
            sync_entries = sync_lookup[ref_id]
            any_stale = any(e.get("status") == "stale" for e in sync_entries)
            if any_stale:
                status_label = LABEL_STALE
                indicator = STATUS_STALE
                # Get reason from first stale entry
                stale_entry = next(
                    e for e in sync_entries if e.get("status") == "stale"
                )
                reason = str(stale_entry.get("reason", ""))
                doc_path = str(stale_entry.get("doc_path", ""))
            else:
                status_label = LABEL_FRESH
                indicator = STATUS_FRESH
                reason = ""
                doc_path = str(sync_entries[0].get("doc_path", ""))
        elif ref_id in doc_ref_ids:
            # Has docs but no sync entries — treat as fresh
            status_label = LABEL_FRESH
            indicator = STATUS_FRESH
            reason = ""
            doc_path = ""
        else:
            # No docs at all — missing
            status_label = LABEL_MISSING
            indicator = STATUS_MISSING
            reason = ""
            doc_path = ""

        rows.append({
            "ref_id": ref_id,
            "status_label": status_label,
            "status_indicator": indicator,
            "doc_path": doc_path,
            "reason": reason,
        })

    # Sort: stale first, then missing, then fresh; within same status, alphabetical
    rows.sort(
        key=lambda r: (
            _STATUS_SORT_ORDER.get(r["status_label"], 99),
            r["ref_id"],
        )
    )

    return rows


def compute_coverage_stats(
    rows: list[dict[str, str]],
) -> tuple[float, int, int]:
    """Compute coverage percentage, stale count, and total nodes from rows.

    Returns:
        (coverage_percent, stale_count, total_nodes)
    """
    total = len(rows)
    if total == 0:
        return 0.0, 0, 0

    fresh_count = sum(1 for r in rows if r["status_label"] == LABEL_FRESH)
    stale_count = sum(1 for r in rows if r["status_label"] == LABEL_STALE)

    # Coverage = (fresh + stale) / total * 100 — both have docs
    documented = fresh_count + stale_count
    coverage = (documented / total) * 100.0

    return coverage, stale_count, total


class DocHealthTable(DataTable[str]):
    """DataTable showing documentation health per architecture node.

    Columns: Node, Status (indicator + label), Doc Path, Reason.
    Color coding: green for fresh, yellow for stale, red for missing.
    Rows sorted: stale first, then missing, then fresh.
    """

    DEFAULT_CSS: ClassVar[str] = """
    DocHealthTable {
        width: 100%;
        height: 1fr;
    }
    """

    def __init__(self, *, widget_id: str | None = None) -> None:
        super().__init__(id=widget_id)
        self._rows: list[dict[str, str]] = []
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """Set up columns when widget mounts."""
        self.add_columns(_COL_NODE, _COL_STATUS, _COL_DOC_PATH, _COL_REASON)

    def refresh_data(
        self,
        *,
        graph_provider: GraphDataProvider | None = None,
        sync_provider: SyncDataProvider | None = None,
    ) -> None:
        """Reload table data from providers."""
        self._rows = compute_doc_rows(
            graph_provider=graph_provider,
            sync_provider=sync_provider,
        )
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        """Clear and rebuild all table rows from cached data."""
        self.clear()
        for row in self._rows:
            indicator = row["status_indicator"]
            label = row["status_label"]
            status_display = f"{indicator} {label}"
            doc_path = row["doc_path"] or "\u2014"  # em-dash
            reason = row["reason"] or "\u2014"

            self.add_row(
                row["ref_id"],
                status_display,
                doc_path,
                reason,
                key=row["ref_id"],
            )

    def get_selected_ref_id(self) -> str | None:
        """Return the ref_id of the currently selected row, or None."""
        if self.cursor_row is not None and self.cursor_row < len(self._rows):
            return self._rows[self.cursor_row]["ref_id"]
        return None

    def get_rows_data(self) -> list[dict[str, str]]:
        """Return current row data for external inspection."""
        return list(self._rows)
