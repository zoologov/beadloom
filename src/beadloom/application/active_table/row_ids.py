"""The bead id a table row names, and what the row names when it names none.

**A bead id is written in two forms, and both are read here (BDL-061.84).** The
tracker allocates ``beadloom-mr2l.22``; an ACTIVE table abbreviates it to ``.22``
because the prefix is the same for every row in the file and repeating it buys
nothing. Comparing the two as whole strings matches nothing, which is what the
reconcile did for the whole of BDL-053's life: ``active-sync --check`` reported
``already coherent`` over a table it had compared zero rows of.

**And an id is written inside whatever a Markdown document wraps it in
(BDL-UX #210).** A cell is text in a document before it is a key in a lookup, so
an author writes ``` `.10` ``` or ``**.10**`` the way they write every other
identifier in the same file. Neither is a different bead. Measured on this
repository at ``5846b20``, before this module existed: 329 rows read, 211
resolved, 118 unresolved, and 27 of the 118 were BDL-067's own table, every row
of which writes its id as a code span. A reconcile that is inert on the commonest
way to write an id in Markdown does not prevent hand-drift; it certifies it.

**A row that did not resolve says WHICH of four things it was.** All 118 carried
one sentence — "is not a bead id in either form" — over four different facts with
four different remedies: an id under decoration (ours to read), an id followed by
a title (the table's shape), a range of ids (one row, several beads), and a label
that is not an id at all. One message for four populations is the same defect as
one message for two, and this epic has shipped the distinction eight times.
"""

# beadloom:component=active-table

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

#: The short form an ACTIVE table abbreviates a bead id to: a dot, the number the
#: tracker allocated, and an optional letter suffix (``.22``, ``.22a``). Bounded
#: at both ends so ``.1 Contract model`` — a first cell carrying a title, which
#: this repository's older epics really contain — is NOT read as the bead ``.1``.
_SHORT_ID = re.compile(r"^\.\d+[a-z]?$")

#: The id-shaped head of a cell: an optional tracker prefix, a dot, a number.
#: Used only to CLASSIFY a cell that did not resolve, never to resolve one.
_ID_HEAD = r"[A-Za-z0-9_-]*\.\d+[a-z]?"

#: Two ids with a range separator between them (``.73`` to ``.76``, ``proj-x.3..8``).
#: One row, several beads: there is no single status cell to write. The separator
#: class is spelled in escapes because an en dash and an em dash are what a writer
#: actually types, and a literal one here is a character ruff cannot tell from a
#: hyphen.
_RANGE = re.compile(
    rf"^(?P<first>{_ID_HEAD})\s*(?:\.\.|[-\u2013\u2014])\s*\.?\d+[a-z]?$"
)

#: An id followed by a title in the same cell (``.7 review``).
_ID_THEN_TEXT = re.compile(rf"^(?P<id>{_ID_HEAD})\s+(?P<text>\S.*)$")

#: A Markdown link, reduced to the text it displays.
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")

#: The decoration a Markdown document puts around an identifier. Deliberately
#: only the two characters a bead id can never contain: an underscore CAN appear
#: in a tracker id, so stripping ``_`` to catch ``_.22_`` would corrupt one.
_DECORATION = re.compile(r"[`*]")


# --- What a cell was, when it named no bead. ------------------------------- #

#: The cell holds nothing id-shaped (``BEAD-01``, ``01``, ``b0xl``).
SHAPE_NO_ID = "no-bead-id"

#: The cell names one bead and then adds text (``.7 review``).
SHAPE_WITH_TEXT = "bead-and-text"

#: The cell names a range (``.73`` to ``.76``): several beads, one status cell.
SHAPE_RANGE = "more-than-one-bead"

#: The cell names a bead the tracker's answer did not contain.
SHAPE_UNKNOWN_TO_TRACKER = "unknown-to-tracker"

#: The short number the cell carries belongs to more than one bead, and this
#: table's epic is not known to the tracker.
SHAPE_AMBIGUOUS = "ambiguous-number"

#: Every shape, in report order: ours to read first, then the table's shape,
#: then the tracker's answer.
SHAPES: tuple[str, ...] = (
    SHAPE_WITH_TEXT,
    SHAPE_RANGE,
    SHAPE_NO_ID,
    SHAPE_UNKNOWN_TO_TRACKER,
    SHAPE_AMBIGUOUS,
)


@dataclass(frozen=True)
class RowId:
    """What a row's first cell resolved to, or why it did not.

    ``bead_id`` is set and ``shape``/``reason`` are ``None`` on a resolution;
    on a failure it is the other way round. A reason is always given rather than
    a bare ``None``: a row that could not be resolved is a finding about the
    table or about the tracker's answer, and a reconcile that dropped it
    silently is the defect this module exists to close.
    """

    bead_id: str | None = None
    shape: str | None = None
    reason: str | None = None


def undecorate(cell: str) -> str:
    """The identifier text a table *cell* names, with its Markdown removed.

    A link is reduced to the text it displays, and every code-span and emphasis
    character is deleted wherever it stands rather than only at the ends: a cell
    reads ``` `.7` review ``` as often as ``` `.7 review` ``` and the id is the
    same bead in both.
    """
    return _DECORATION.sub("", _LINK.sub(r"\1", cell)).strip()


def short_form(bead_id: str) -> str:
    """The short form of *bead_id* (``proj-x.22`` -> ``.22``), or ``""``.

    Only the trailing number is the short form, and it is compared as a WHOLE
    token: ``.2`` is not ``.22``. A comparison by text suffix would resolve one
    row onto a different bead, which is a worse failure than not resolving it.
    """
    _, dot, tail = bead_id.rpartition(".")
    return f".{tail}" if dot else ""


def names_bead(cell: str, bead_id: str) -> bool:
    """True when a row's first *cell* names *bead_id* in either of its forms."""
    text = undecorate(cell)
    return text == bead_id or (bool(short_form(bead_id)) and text == short_form(bead_id))


def resolve_row_bead_id(
    cell: str, bd_statuses: Mapping[str, str], *, prefix: str | None = None
) -> RowId:
    """Resolve a table row's first *cell* to a bead id ``bd`` reported.

    A full id resolves to itself. A short id is read against *prefix* — the
    tracker id of the epic this table belongs to — because the number alone is
    not unique across a tracker: this repository holds eight beads numbered
    ``.17`` in eight epics, and resolving BDL-061's ``.17`` row without its epic
    would write another epic's status into it. When no prefix is known the short
    id must be unique in the WHOLE tracker to resolve, and an ambiguity is
    reported rather than guessed.
    """
    text = undecorate(cell)
    if text in bd_statuses:
        return RowId(bead_id=text)
    if _SHORT_ID.match(text) is not None:
        return _resolve_short(text, bd_statuses, prefix)
    return _unresolvable_shape(text)


def _resolve_short(
    text: str, bd_statuses: Mapping[str, str], prefix: str | None
) -> RowId:
    """Resolve a short id (``.22``) against its epic, or against the whole tracker."""
    if prefix is not None:
        full = f"{prefix}{text}"
        if full in bd_statuses:
            return RowId(bead_id=full)
        return RowId(
            shape=SHAPE_UNKNOWN_TO_TRACKER,
            reason=(
                f"this table's epic is tracked as `{prefix}` and the tracker "
                f"reported no `{full}`"
            ),
        )
    candidates = sorted(key for key in bd_statuses if short_form(key) == text)
    if not candidates:
        return RowId(
            shape=SHAPE_UNKNOWN_TO_TRACKER,
            reason=f"no bead the tracker reported is numbered `{text}`",
        )
    if len(candidates) > 1:
        named = ", ".join(f"`{c}`" for c in candidates)
        return RowId(
            shape=SHAPE_AMBIGUOUS,
            reason=(
                f"`{text}` is ambiguous — {named} are all numbered `{text}` and "
                f"this table's epic is not known to the tracker, so the row names "
                f"no single bead"
            ),
        )
    return RowId(bead_id=candidates[0])


def _unresolvable_shape(text: str) -> RowId:
    """Name which of the three table-side shapes *text* is, and what to do about it.

    Ranges are tested before the id-and-text shape because ``proj-x.3..8`` has an
    id-shaped head and is not a row about one bead.
    """
    ranged = _RANGE.match(text)
    if ranged is not None:
        return RowId(
            shape=SHAPE_RANGE,
            reason=(
                f"`{text}` names more than one bead, and a row carries one status "
                f"cell — give each bead its own row to have it reconciled"
            ),
        )
    with_text = _ID_THEN_TEXT.match(text)
    if with_text is not None:
        return RowId(
            shape=SHAPE_WITH_TEXT,
            reason=(
                f"`{text}` names a bead and then adds text: the whole cell is read "
                f"as the id, so `{with_text.group('id')}` is not reconciled — move "
                f"the title into a column of its own"
            ),
        )
    return RowId(
        shape=SHAPE_NO_ID,
        reason=(
            f"`{text}` carries no bead id in either form — a full id the tracker "
            f"allocated, or the short form a table abbreviates it to (`.7`)"
        ),
    )
