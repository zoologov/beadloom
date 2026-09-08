"""The markdown bead-status table: its rows, its Status column, one cell write.

The table is a markdown table whose header's first cell is ``Bead`` followed by a
separator row; each data row carries a bead id in its first cell and a status in
its ``Status`` column (3-col ``| Bead | Role | Status |`` or 4-col
``| Bead | Role | Status | Depends |``). Everything here is **tolerant and
fail-safe**: it never raises and never corrupts the file — a missing file, no
table, or an unrecognised status leaves the document untouched.
"""

# beadloom:component=active-table

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.active_table.row_ids import names_bead

if TYPE_CHECKING:
    from pathlib import Path


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


def find_status_column(lines: list[str]) -> tuple[int, int] | None:
    """Locate the bead-status table: return ``(header_index, status_col_index)``.

    The table is identified by a header row whose first cell is ``Bead`` directly
    followed by a separator row, AND carrying a ``Status`` column (located by that
    header cell's index, case-insensitively). Returns ``None`` when absent.

    **The scan does not stop at the first ``Bead``-headed table (BDL-061.84).** A
    ``Bead``-headed table with no Status column is not the bead-status table, and
    treating it as a failed match for the whole document made this repository's own
    ACTIVE.md unreadable: it carries a ``| Bead | What it is | Why it was not done
    here |`` deferral table 480 lines above the status table, and the search
    returned ``None`` at the first of the two.
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


def _sanitize_status(status: str) -> str:
    """Collapse any whitespace run to single spaces and replace ``|`` with ``/``.

    Neither row-splitting (newlines) nor extra cells (pipes) is meaningful in a
    short one-line status label, so this keeps an arbitrary status from
    corrupting the table row.
    """
    return " ".join(status.split()).replace("|", "/")


def render_row(cells: list[str], *, newline: str) -> str:
    """One table row, rendered from its *cells* with the file's own line ending."""
    return "| " + " | ".join(cells) + " |" + newline


def set_active_table_status(active_path: Path, bead_id: str, status: str) -> bool:
    """Best-effort: flip the status cell of *bead_id*'s row in an ACTIVE.md table.

    Parses the markdown table(s) in *active_path*, finds the row whose FIRST cell
    names *bead_id* in either of its two forms — the full id, or the short ``.22``
    the table abbreviates it to — as a WHOLE token (so ``...mukc.1`` never matches
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
        if not names_bead(cells[0], bead_id):
            continue
        cells[-1] = _sanitize_status(status)
        lines[idx] = render_row(cells, newline="\n" if line.endswith("\n") else "")
        try:
            active_path.write_text("".join(lines), encoding="utf-8")
        except OSError:
            return False
        return True
    return False
