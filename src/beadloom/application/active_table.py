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

**A bead id is written in two forms, and both are read here (BDL-061.84).** The
tracker allocates ``beadloom-mr2l.22``; an ACTIVE table abbreviates it to ``.22``
because the prefix is the same for every row in the file and repeating it buys
nothing. Comparing the two as whole strings matches nothing, which is what this
module did for the whole of BDL-053's life: ``active-sync --check`` reported
``already coherent`` over a table it had compared zero rows of.
:func:`resolve_row_bead_id` is the single place that maps one form onto the
other, and it is used by BOTH lookups in this module — ``set_active_table_status``
had the same blind spot.
"""

# beadloom:component=active-table

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# The two forms one bead id is written in
# ---------------------------------------------------------------------------

#: The short form an ACTIVE table abbreviates a bead id to: a dot, the number the
#: tracker allocated, and an optional letter suffix (``.22``, ``.22a``). Bounded
#: at both ends so ``.1 Contract model`` — a first cell carrying a title, which
#: this repository's older epics really contain — is NOT read as the bead ``.1``.
_SHORT_ID = re.compile(r"^\.\d+[a-z]?$")


def short_form(bead_id: str) -> str:
    """The short form of *bead_id* (``proj-x.22`` -> ``.22``), or ``""``.

    Only the trailing number is the short form, and it is compared as a WHOLE
    token: ``.2`` is not ``.22``. A comparison by text suffix would resolve one
    row onto a different bead, which is a worse failure than not resolving it.
    """
    _, dot, tail = bead_id.rpartition(".")
    return f".{tail}" if dot else ""


def resolve_row_bead_id(
    cell: str, bd_statuses: Mapping[str, str], *, prefix: str | None = None
) -> tuple[str | None, str | None]:
    """Resolve a table row's first *cell* to a bead id ``bd`` reported.

    Returns ``(bead_id, None)`` when the cell names exactly one known bead, and
    ``(None, reason)`` when it does not. A reason is always given rather than a
    bare ``None``: a row that could not be resolved is a finding about the table
    or about the tracker scope, and a reconcile that dropped it silently is the
    defect this function exists to close.

    A full id resolves to itself. A short id is read against *prefix* — the
    tracker id of the epic this table belongs to — because the number alone is
    not unique across a tracker: this repository holds eight beads numbered
    ``.17`` in eight epics, and resolving BDL-061's ``.17`` row without its epic
    would write another epic's status into it. When no prefix is known the short
    id must be unique in the WHOLE tracker to resolve, and an ambiguity is
    reported rather than guessed.
    """
    if cell in bd_statuses:
        return cell, None
    if _SHORT_ID.match(cell) is None:
        return None, (
            f"`{cell}` is not a bead id in either form — a full id the tracker "
            f"allocated, or the short form a table abbreviates it to (`.7`)"
        )
    if prefix is not None:
        full = f"{prefix}{cell}"
        if full in bd_statuses:
            return full, None
        return None, (
            f"this table's epic is tracked as `{prefix}` and the tracker reported "
            f"no `{full}`"
        )
    candidates = sorted(key for key in bd_statuses if short_form(key) == cell)
    if not candidates:
        return None, f"no bead the tracker reported is numbered `{cell}`"
    if len(candidates) > 1:
        named = ", ".join(f"`{c}`" for c in candidates)
        return None, (
            f"`{cell}` is ambiguous — {named} are all numbered `{cell}` and this "
            f"table's epic is not known to the tracker, so the row names no single bead"
        )
    return candidates[0], None


def _names_bead(cell: str, bead_id: str) -> bool:
    """True when a row's first *cell* names *bead_id* in either of its two forms."""
    return cell == bead_id or (bool(short_form(bead_id)) and cell == short_form(bead_id))


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
        if not _names_bead(cells[0], bead_id):
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

    ``rows_read`` and ``rows_resolved`` are the denominator and the numerator of
    the run, and they exist because an empty ``drifted_rows`` had two meanings
    that read identically: every row agreed with the tracker, or no row was ever
    compared (BDL-061.84). ``unresolved_rows`` names the difference as
    ``(path, cell, reason)``.
    """

    changed_files: list[Path] = field(default_factory=list)
    drifted_rows: list[tuple[Path, str, str, str]] = field(default_factory=list)
    rows_read: int = 0
    rows_resolved: int = 0
    unresolved_rows: list[tuple[Path, str, str]] = field(default_factory=list)

    @property
    def is_inert(self) -> bool:
        """True when rows were read and NONE of them resolved to a bead.

        The state the mechanism sat in for its whole life. Kept as a predicate
        rather than recomputed at each call site so the command, the JSON payload
        and the tests cannot disagree about what "inert" means.
        """
        return self.rows_read > 0 and self.rows_resolved == 0


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


def _state_of(cell: str) -> str:
    """The state token a Status cell carries, with its decoration removed.

    ``✓ done``, ``Done`` and ``**DONE** (a1b2c3d)`` are one state written three
    ways, and the module's contract is already that a richer cell is preserved
    when the STATE agrees. Comparing the cells verbatim made that contract hold
    only for the exact spelling this module happens to write: BDL-061.84 measured
    78 rows of one ACTIVE.md that a first working reconcile would have rewritten
    solely to add a checkmark. Leading non-alphanumerics are stripped and the rest
    is case-folded, so the comparison is about the word and not about the ornament.
    """
    text = cell.strip().casefold()
    while text and not text[0].isalnum():
        text = text[1:]
    return text.lstrip()


def _states_agree(old_cell: str, wanted: str) -> bool:
    """True when *old_cell* already states *wanted*, whatever it adds after it."""
    return _state_of(old_cell).startswith(_state_of(wanted))


def _reconcile_one(
    active_path: Path,
    bd_statuses: dict[str, str],
    result: ReconcileResult,
    *,
    prefix: str | None = None,
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
        if cells is None:
            # The table ended. Everything after it is prose or another table, and
            # counting those lines would make `rows_read` a denominator of the
            # document rather than of the bead-status table.
            break
        if is_separator_cells(cells) or status_col >= len(cells):
            continue
        result.rows_read += 1
        bead_id, reason = resolve_row_bead_id(cells[0], bd_statuses, prefix=prefix)
        if bead_id is None:
            result.unresolved_rows.append((active_path, cells[0], reason or ""))
            continue
        result.rows_resolved += 1
        wanted = bd_status_to_cell(bd_statuses[bead_id])
        if wanted is None:
            continue
        old_cell = cells[status_col]
        if _states_agree(old_cell, wanted):
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
    epic_prefixes: Mapping[str, str] | None = None,
) -> ReconcileResult:
    """Rewrite ACTIVE.md bead-status tables to match injected ``bd`` statuses.

    Pure with respect to ``bd``: the caller injects ``bd_statuses`` (bead-id ->
    ``bd`` status, e.g. ``{"beadloom-x.1": "closed"}``; ``"blocked"`` when an open
    bead has an open blocker). *epic_prefixes* maps an epic DIRECTORY name onto
    the tracker id of its epic bead (``{"BDL-061": "beadloom-mr2l"}``); that is
    what lets a table written in short ids be read against the right epic, and a
    directory absent from it falls back to whole-tracker uniqueness.

    Discovers the target ACTIVE.md files (just *epic*'s
    when given, else every ``features/*/ACTIVE.md``), and for each: finds the
    bead-status table, and for every data row that resolves to a bead in
    *bd_statuses*
    rewrites the Status cell to the mapped state — unless the existing cell
    already STATES that state (a coordinator's richer note like
    ``✓ done (PASS-WITH-FIXES)`` is preserved when the state agrees). Rows whose
    bead is absent, or whose ``bd`` status is unrecognised, are left untouched;
    rows that resolve to no bead at all are recorded in
    :attr:`ReconcileResult.unresolved_rows` with the reason, so a run that
    compared nothing cannot report the same as a run that found nothing wrong.
    Only files with a changed cell are rewritten (everything else byte-preserved).
    Best-effort: never raises.
    """
    result = ReconcileResult()
    prefixes = epic_prefixes or {}
    for active_path in _discover_active_files(project_root, epic):
        _reconcile_one(
            active_path,
            bd_statuses,
            result,
            prefix=prefixes.get(active_path.parent.name),
        )
    return result
