"""Reconcile ACTIVE.md bead-status tables from the statuses the tracker reported.

Pure with respect to ``bd``: the caller injects the statuses, so what is tested
here is the reading of a document and not the answer of a tool. The MCP S4 tools
(``checkpoint``/``complete_bead``) and the ``active-sync`` command both build on
this package's primitives.

**An empty finding list had two meanings that read identically**, which is why a
run states its denominator: every row agreed with the tracker, or no row was ever
compared (BDL-061.84). This module now names four populations rather than one —
the rows it resolved, the rows it could not and what each of them was
(BDL-UX #210), the beads the tracker holds under this table's epic that the table
carries no row for at all, and the beads a row NAMES and this run could not read.

**The last two were one, and the run contradicted itself over them.** ``seen``
was filled only from rows that resolved, so every unresolved row handed its bead
to "no row in their epic's table" while the same run printed the row under
``bead-and-text`` or ``more-than-one-bead``. Measured on this repository at
27db92b: 79 beads reported as carried by no row, 38 of which had a row whose
first cell's head is exactly that bead's id. A reader acting on the message adds
a row that is already there (BDL-068 S5, review Major 1).

**It never writes a row it did not find.** A bead missing from a table is real
drift and it is reported, not inserted: adding a row to somebody's document is
the same fault as adding a path to somebody's commit, which is the other half of
this bead (:mod:`~beadloom.application.active_table.staging`).
"""

# beadloom:component=active-table

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.application.active_table.row_ids import (
    resolve_row_bead_id,
    short_form,
)
from beadloom.application.active_table.statuses import bd_status_to_cell, states_agree
from beadloom.application.active_table.table import (
    find_status_column,
    is_separator_cells,
    render_row,
    split_table_row,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UnresolvedRow:
    """A row the reconcile read and could not map onto a bead.

    ``shape`` is one of :data:`~beadloom.application.active_table.row_ids.SHAPES`
    and is what makes a count actionable: "118 unresolved" is a number nobody
    acts on, and "27 of them are a decoration we cannot read" is one somebody
    fixes in an hour.
    """

    path: Path
    cell: str
    shape: str
    reason: str


@dataclass
class ReconcileResult:
    """Outcome of a reconcile pass.

    ``changed_files`` lists the ACTIVE.md paths that were rewritten;
    ``drifted_rows`` records every corrected cell as
    ``(path, bead_id, old_status_cell, new_status_cell)`` so a ``--check`` mode
    can exit non-zero on drift.

    ``rows_read`` and ``rows_resolved`` are the denominator and the numerator of
    the run. ``unresolved_rows`` names the difference, by CELL.

    The two bead-keyed lists are the same difference seen from the tracker's side,
    and they are two because their remedies are two. ``unlisted_beads`` is
    ``(path, bead_id)`` for a bead no row of the table names — add a row.
    ``beads_named_by_an_unresolved_row`` is ``(path, bead_id, cell)`` for a bead a
    row does name and this run could not read — fix that cell, and the shape in
    ``unresolved_rows`` says how. No bead is in both.
    """

    changed_files: list[Path] = field(default_factory=list)
    drifted_rows: list[tuple[Path, str, str, str]] = field(default_factory=list)
    rows_read: int = 0
    rows_resolved: int = 0
    unresolved_rows: list[UnresolvedRow] = field(default_factory=list)
    unlisted_beads: list[tuple[Path, str]] = field(default_factory=list)
    beads_named_by_an_unresolved_row: list[tuple[Path, str, str]] = field(
        default_factory=list
    )

    @property
    def is_inert(self) -> bool:
        """True when rows were read and NONE of them resolved to a bead.

        The state the mechanism sat in for its whole life. Kept as a predicate
        rather than recomputed at each call site so the command, the JSON payload
        and the tests cannot disagree about what "inert" means.
        """
        return self.rows_read > 0 and self.rows_resolved == 0

    @property
    def unresolved_by_shape(self) -> dict[str, int]:
        """How many unresolved rows each shape accounts for."""
        return dict(Counter(row.shape for row in self.unresolved_rows))


_FEATURES_GLOB = ".claude/development/docs/features/*/ACTIVE.md"


def discover_active_files(project_root: Path, epic: str | None) -> list[Path]:
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


def _beads_of_epic(bd_statuses: Mapping[str, str], prefix: str) -> list[str]:
    """The tracker's children of *prefix*, in the order their numbers run.

    The epic bead itself is not a row of its own table, so it is not expected in
    one. Sorted by number rather than by text so ``.9`` precedes ``.10``.
    """

    def _number(bead_id: str) -> tuple[int, str]:
        tail = short_form(bead_id).lstrip(".")
        digits = "".join(ch for ch in tail if ch.isdigit())
        return (int(digits) if digits else 0, bead_id)

    return sorted(
        (bead_id for bead_id in bd_statuses if bead_id.startswith(f"{prefix}.")),
        key=_number,
    )


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
    located = find_status_column(lines)
    if located is None:
        return
    header_idx, status_col = located
    seen: set[str] = set()
    named: dict[str, str] = {}
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
        row = resolve_row_bead_id(cells[0], bd_statuses, prefix=prefix)
        if row.bead_id is None:
            result.unresolved_rows.append(
                UnresolvedRow(active_path, cells[0], row.shape or "", row.reason or "")
            )
            if row.names is not None:
                named.setdefault(row.names, cells[0])
            continue
        result.rows_resolved += 1
        seen.add(row.bead_id)
        wanted = bd_status_to_cell(bd_statuses[row.bead_id])
        if wanted is None:
            continue
        old_cell = cells[status_col]
        if states_agree(old_cell, wanted):
            continue
        cells[status_col] = wanted
        lines[idx] = render_row(cells, newline="\n" if lines[idx].endswith("\n") else "")
        result.drifted_rows.append((active_path, row.bead_id, old_cell, wanted))
        changed = True
    _record_beads_without_a_reconciled_row(
        active_path, bd_statuses, result, prefix=prefix, seen=seen, named=named
    )
    if not changed:
        return
    try:
        active_path.write_text("".join(lines), encoding="utf-8")
    except OSError:
        return
    result.changed_files.append(active_path)


def _record_beads_without_a_reconciled_row(
    active_path: Path,
    bd_statuses: Mapping[str, str],
    result: ReconcileResult,
    *,
    prefix: str | None,
    seen: set[str],
    named: Mapping[str, str],
) -> None:
    """Name the epic's beads no row of this table reconciled, and say which kind.

    *seen* is the beads a row RESOLVED to and *named* the beads a row NAMED and
    this run could not read, mapped to the cell that names them. A bead in
    neither has no row at all. The order of the three tests is the order of the
    remedies: a bead this run compared needs nothing, a bead whose row is
    unreadable needs that cell fixed, and only what is left needs a row written.

    Only when the table's epic is known: without a prefix there is no population
    to subtract from, and reporting every bead in the tracker would be a wall
    nobody reads.
    """
    if prefix is None:
        return
    for bead_id in _beads_of_epic(bd_statuses, prefix):
        if bead_id in seen:
            continue
        cell = named.get(bead_id)
        if cell is not None:
            result.beads_named_by_an_unresolved_row.append((active_path, bead_id, cell))
            continue
        result.unlisted_beads.append((active_path, bead_id))


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

    Discovers the target ACTIVE.md files (just *epic*'s when given, else every
    ``features/*/ACTIVE.md``), and for each: finds the bead-status table, and for
    every data row that resolves to a bead in *bd_statuses* rewrites the Status
    cell to the mapped state — unless the existing cell already STATES that state
    (a coordinator's richer note like ``✓ done (PASS-WITH-FIXES)`` is preserved
    when the state agrees). Rows whose bead is absent, or whose ``bd`` status is
    unrecognised, are left untouched; rows that resolve to no bead at all are
    recorded in :attr:`ReconcileResult.unresolved_rows` with the shape and the
    reason, so a run that compared nothing cannot report the same as a run that
    found nothing wrong. A bead of the epic that no row reconciled is reported in
    one of two lists — :attr:`ReconcileResult.unlisted_beads` when no row names it
    and :attr:`ReconcileResult.beads_named_by_an_unresolved_row` when one does —
    and never written into the table. Only files with a changed cell are rewritten
    (everything else byte-preserved). Best-effort: never raises.
    """
    result = ReconcileResult()
    prefixes = epic_prefixes or {}
    for active_path in discover_active_files(project_root, epic):
        _reconcile_one(
            active_path,
            bd_statuses,
            result,
            prefix=prefixes.get(active_path.parent.name),
        )
    return result
