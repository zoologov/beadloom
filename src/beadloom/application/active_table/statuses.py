"""The state a Status cell states, and the ``bd`` status it comes from."""

# beadloom:component=active-table

from __future__ import annotations

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


def state_of(cell: str) -> str:
    """The state token a Status cell carries, with its decoration removed.

    ``✓ done``, ``Done`` and ``**DONE** (a1b2c3d)`` are one state written three
    ways, and the contract is already that a richer cell is preserved when the
    STATE agrees. Comparing the cells verbatim made that contract hold only for
    the exact spelling this package happens to write: BDL-061.84 measured 78 rows
    of one ACTIVE.md that a first working reconcile would have rewritten solely to
    add a checkmark. Leading non-alphanumerics are stripped and the rest is
    case-folded, so the comparison is about the word and not about the ornament.
    """
    text = cell.strip().casefold()
    while text and not text[0].isalnum():
        text = text[1:]
    return text.lstrip()


def states_agree(old_cell: str, wanted: str) -> bool:
    """True when *old_cell* already states *wanted*, whatever it adds after it."""
    return state_of(old_cell).startswith(state_of(wanted))
