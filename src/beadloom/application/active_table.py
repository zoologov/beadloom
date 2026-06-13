"""Shared ACTIVE.md bead-status table parser/updater + reconcile-from-bd core.

Single source of truth for the bead-status markdown table format used by the
packaged agentic flow. The MCP S4 tools (``checkpoint``/``complete_bead``) and
the ``active-sync`` command (BDL-053 BEAD-02) both build on these primitives.

The table is a markdown table whose header's first cell is ``Bead`` followed by
a separator row; each data row carries a bead-id in its first cell and a status
in its ``Status`` column (3-col ``| Bead | Role | Status |`` or 4-col
``| Bead | Role | Status | Depends |``). Everything here is **tolerant and
fail-safe**: it never raises and never corrupts the file — a missing file, no
table, or an unrecognised status leaves the document untouched.
"""

# beadloom:component=active-table

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Table primitives (extracted from mcp_server S4 — behaviour byte-identical)
# ---------------------------------------------------------------------------


def split_table_row(line: str) -> list[str] | None:
    """Split a markdown table *line* into its cells, or None if it is not one.

    A table row is a line whose stripped form starts and ends with ``|``. The
    leading/trailing empty fragments produced by the border pipes are dropped;
    the inner cell texts are returned stripped.
    """
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_separator_cells(cells: list[str]) -> bool:
    """True for a markdown header-separator row (cells are all ``---`` dashes)."""
    return bool(cells) and all(set(c) <= {"-", ":"} and c for c in cells)


def _sanitize_status(status: str) -> str:
    """Collapse any whitespace run to single spaces and replace ``|`` with ``/``.

    Neither row-splitting (newlines) nor extra cells (pipes) is meaningful in a
    short one-line status label, so this keeps an arbitrary status from
    corrupting the table row.
    """
    return " ".join(status.split()).replace("|", "/")


def set_active_table_status(active_path: Path, bead_id: str, status: str) -> bool:
    """Best-effort: flip the status cell of *bead_id*'s row in an ACTIVE.md table.

    Parses the markdown table(s) in *active_path*, finds the row whose FIRST cell
    equals *bead_id* as a whole token (so ``...mukc.1`` never matches
    ``...mukc.10``), replaces its LAST (status) cell with *status*, and writes the
    file back. Tolerant: a missing file, no table, or no matching row leaves the
    file untouched and returns ``False``. Never raises, never corrupts the file.
    """
    try:
        original = active_path.read_text(encoding="utf-8")
    except OSError:
        return False
    lines = original.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        cells = split_table_row(line)
        if cells is None or len(cells) < 2 or is_separator_cells(cells):
            continue
        if cells[0] != bead_id:
            continue
        cells[-1] = _sanitize_status(status)
        newline = "\n" if line.endswith("\n") else ""
        lines[idx] = "| " + " | ".join(cells) + " |" + newline
        try:
            active_path.write_text("".join(lines), encoding="utf-8")
        except OSError:
            return False
        return True
    return False


# ---------------------------------------------------------------------------
# bd status -> Status cell map (single documented source; reused by tests/BEAD-02)
# ---------------------------------------------------------------------------

#: Mapping from a ``bd`` status token to the canonical Status-cell state token.
#: The caller injects ``"blocked"`` for an ``open`` bead with an open blocker.
_BD_STATUS_CELL: dict[str, str] = {
    "closed": "✓ done",
    "in_progress": "in progress",
    "blocked": "blocked",
    "open": "ready",
    "ready": "ready",
}


def bd_status_to_cell(bd_status: str) -> str | None:
    """Map a ``bd`` status token to the canonical Status-cell state token.

    Returns ``None`` for an unrecognised status so the caller leaves the row
    untouched (never corrupt). ``closed -> "✓ done"``, ``in_progress ->
    "in progress"``, ``blocked -> "blocked"``, ``open``/``ready -> "ready"``.
    """
    return _BD_STATUS_CELL.get(bd_status)


# ---------------------------------------------------------------------------
# reconcile_active_tables — pure reconcile-from-bd core
# ---------------------------------------------------------------------------


@dataclass
class ReconcileResult:
    """Outcome of a reconcile pass.

    ``changed_files`` lists the ACTIVE.md paths that were rewritten;
    ``drifted_rows`` records every corrected cell as
    ``(path, bead_id, old_status_cell, new_status_cell)`` so BEAD-02 can drive a
    ``--check`` mode (nonzero exit when non-empty) vs the fix mode.
    """

    changed_files: list[Path] = field(default_factory=list)
    drifted_rows: list[tuple[Path, str, str, str]] = field(default_factory=list)


_FEATURES_GLOB = ".claude/development/docs/features/*/ACTIVE.md"


def _discover_active_files(project_root: Path, epic: str | None) -> list[Path]:
    """Return the ACTIVE.md files to reconcile (one epic, or scan the flow dir)."""
    if epic is not None:
        candidate = (
            project_root
            / ".claude"
            / "development"
            / "docs"
            / "features"
            / epic
            / "ACTIVE.md"
        )
        return [candidate] if candidate.is_file() else []
    return sorted(project_root.glob(_FEATURES_GLOB))


def _find_status_column(lines: list[str]) -> tuple[int, int] | None:
    """Locate the bead-status table: return ``(header_index, status_col_index)``.

    The table is identified by a header row whose first cell is ``Bead`` directly
    followed by a separator row. The Status column is located by the ``Status``
    header cell's index (case-insensitive). Returns ``None`` when absent.
    """
    for idx in range(len(lines) - 1):
        header = split_table_row(lines[idx])
        if header is None or not header or header[0].strip().lower() != "bead":
            continue
        sep = split_table_row(lines[idx + 1])
        if sep is None or not is_separator_cells(sep):
            continue
        for col, cell in enumerate(header):
            if cell.strip().lower() == "status":
                return idx, col
        return None
    return None


def _reconcile_one(
    active_path: Path, bd_statuses: dict[str, str], result: ReconcileResult
) -> None:
    """Reconcile a single ACTIVE.md file in place (best-effort, never raises)."""
    try:
        original = active_path.read_text(encoding="utf-8")
    except OSError:
        return
    lines = original.splitlines(keepends=True)
    located = _find_status_column(lines)
    if located is None:
        return
    header_idx, status_col = located
    changed = False
    for idx in range(header_idx + 2, len(lines)):
        cells = split_table_row(lines[idx])
        if cells is None or is_separator_cells(cells) or status_col >= len(cells):
            continue
        bead_id = cells[0]
        bd_status = bd_statuses.get(bead_id)
        if bd_status is None:
            continue
        wanted = bd_status_to_cell(bd_status)
        if wanted is None:
            continue
        old_cell = cells[status_col]
        if old_cell == wanted or old_cell.startswith(wanted):
            continue
        cells[status_col] = wanted
        newline = "\n" if lines[idx].endswith("\n") else ""
        lines[idx] = "| " + " | ".join(cells) + " |" + newline
        result.drifted_rows.append((active_path, bead_id, old_cell, wanted))
        changed = True
    if not changed:
        return
    try:
        active_path.write_text("".join(lines), encoding="utf-8")
    except OSError:
        return
    result.changed_files.append(active_path)


def reconcile_active_tables(
    project_root: Path,
    bd_statuses: dict[str, str],
    *,
    epic: str | None = None,
) -> ReconcileResult:
    """Rewrite ACTIVE.md bead-status tables to match injected ``bd`` statuses.

    Pure with respect to ``bd``: the caller injects ``bd_statuses`` (bead-id ->
    ``bd`` status, e.g. ``{"beadloom-x.1": "closed"}``; ``"blocked"`` when an open
    bead has an open blocker). Discovers the target ACTIVE.md files (just *epic*'s
    when given, else every ``features/*/ACTIVE.md``), and for each: finds the
    bead-status table, and for every data row whose bead-id is in *bd_statuses*
    rewrites the Status cell to the mapped state — unless the existing cell
    already STARTS WITH that state token (a coordinator's richer note like
    ``✓ done (PASS-WITH-FIXES)`` is preserved when the state agrees). Rows whose
    bead-id is absent, or whose ``bd`` status is unrecognised, are left untouched.
    Only files with a changed cell are rewritten (everything else byte-preserved).
    Best-effort: never raises.
    """
    result = ReconcileResult()
    for active_path in _discover_active_files(project_root, epic):
        _reconcile_one(active_path, bd_statuses, result)
    return result
