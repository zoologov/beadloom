"""The ACTIVE.md bead-status table: reading it, reconciling it, staging it.

Four responsibilities, one per module, and this file is the import path they are
all reached through — the package replaced a single ``active_table.py`` whose own
docstring already needed an "and" to describe itself.

* :mod:`~beadloom.application.active_table.row_ids` — the bead id a row names,
  and what the row names when it names none (BDL-061.84, BDL-UX #210).
* :mod:`~beadloom.application.active_table.table` — the markdown table: its rows,
  its Status column, one cell write.
* :mod:`~beadloom.application.active_table.statuses` — the state a Status cell
  states, and the ``bd`` status it comes from.
* :mod:`~beadloom.application.active_table.reconcile` — the reconcile core, pure
  with respect to ``bd``.
* :mod:`~beadloom.application.active_table.staging` — what a reconcile may stage,
  which is never more than the commit already carries (BDL-UX #207).
"""

# beadloom:component=active-table

from __future__ import annotations

from beadloom.application.active_table.reconcile import (
    ReconcileResult,
    UnresolvedRow,
    discover_active_files,
    reconcile_active_tables,
)
from beadloom.application.active_table.row_ids import (
    SHAPE_AMBIGUOUS,
    SHAPE_NO_ID,
    SHAPE_RANGE,
    SHAPE_UNKNOWN_TO_TRACKER,
    SHAPE_WITH_TEXT,
    SHAPES,
    RowId,
    names_bead,
    resolve_row_bead_id,
    short_form,
    undecorate,
)
from beadloom.application.active_table.staging import (
    StagingDecision,
    decide_staging,
    paths_the_index_has_not_taken,
    paths_this_commit_stages,
    stage_paths,
    stageable,
)
from beadloom.application.active_table.statuses import (
    bd_status_to_cell,
    state_of,
    states_agree,
)
from beadloom.application.active_table.table import (
    find_status_column,
    is_separator_cells,
    render_row,
    set_active_table_status,
    split_table_row,
)

__all__ = [
    "SHAPES",
    "SHAPE_AMBIGUOUS",
    "SHAPE_NO_ID",
    "SHAPE_RANGE",
    "SHAPE_UNKNOWN_TO_TRACKER",
    "SHAPE_WITH_TEXT",
    "ReconcileResult",
    "RowId",
    "StagingDecision",
    "UnresolvedRow",
    "bd_status_to_cell",
    "decide_staging",
    "discover_active_files",
    "find_status_column",
    "is_separator_cells",
    "names_bead",
    "paths_the_index_has_not_taken",
    "paths_this_commit_stages",
    "reconcile_active_tables",
    "render_row",
    "resolve_row_bead_id",
    "set_active_table_status",
    "short_form",
    "split_table_row",
    "stage_paths",
    "stageable",
    "state_of",
    "states_agree",
    "undecorate",
]
