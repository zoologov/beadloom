# beadloom:domain=doc-sync
# beadloom:component=markdown-tables
"""What a markdown table row is, and where one table ends and the next begins.

**One responsibility, because two readers of it disagreed twice in one slice.**
BDL-UX #213 and BDL-UX #244 are one sentence found in two places: a section
holding two tables was read as one, so the second table's rows were judged
against the FIRST table's column index and the second table's header row came
back as data. In ``doc-quality`` that reported a measurement table's header as a
decision row with a missing reason; in ``axes-section`` it produced an approved
node literally named ``Node``, in the list ``scope-check`` compares every commit
against. ``beadloom-0mdo.68`` fixed the first with a local ``_tables()``; this
module is that answer lifted to the one place both readers spend, so a third
reader cannot be wrong about it a third time.

**Both second tables exist because this project's own document rules ask for
them.** The RFC says each slice appends its axis rows under its own ``Derived
by`` line, and the ``/coordinator`` playbook asks for a verification table beside
the decision table it verifies. Neither reader was wrong about one table; both
were wrong that there is one.

**A separator row belongs to its table and does not end it.** Everything that is
not a table row does. That is the whole boundary rule, and it reads no header
vocabulary at all — the residual class that vocabulary cannot decide is
``doc-quality``'s and is answered there, by asking what the DOCUMENT declares.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

#: A markdown table row: a line whose content sits between two pipes.
_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")

#: One cell of the alignment row under a header (``---``, ``:---:``).
_SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")

#: One contiguous table, as its rows: the line number and the cells of each,
#: the first being the header the rest are judged against.
Table = list[tuple[int, list[str]]]


def cells_of(line: str) -> list[str] | None:
    """The cells of *line*, separator row included, or ``None`` when it is no row.

    The raw reading. A caller that wants to know whether a line is a table row at
    all spends this; a caller that wants DATA spends :func:`table_cells`, which
    tells the alignment row apart from a row that says something.
    """
    match = _ROW_RE.match(line)
    if match is None:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def is_separator(cells: Iterable[str]) -> bool:
    """Whether *cells* are an alignment row rather than a row of content."""
    return all(_SEPARATOR_CELL_RE.match(cell) for cell in cells if cell)


def table_cells(line: str) -> list[str] | None:
    """The cells of a markdown table row, or ``None`` when *line* is not one.

    The one table reader in the project (BDL-068 S1.5). The ``## Axes`` grammar
    and the ``/task-init`` routing table are two different tables read for two
    different facts, and reading them with two parsers would make "what a row
    is" a thing that can disagree with itself — the class this epic removes.
    An alignment row is not a row of data and returns ``None``, so a caller
    never has to know it exists.
    """
    cells = cells_of(line)
    if cells is None or is_separator(cells):
        return None
    return cells


def table_blocks(lines: Iterable[tuple[int, str]]) -> list[Table]:
    """The tables in *lines*, each as its own ``(line number, cells)`` rows.

    *lines* are numbered lines — usually one section's body — and each returned
    table leads with its own header row. A table ends where its rows stop; a
    separator row is dropped and does NOT end one, because it is part of one.

    The reader this replaced collected every row under a heading into ONE list,
    took the first as the header and judged the rest against its column index, so
    a second table below the first was read as continuation rows of it and that
    table's own header row was read as data. That is BDL-UX #213 in
    ``doc-quality`` and BDL-UX #244 in ``axes-section``.
    """
    tables: list[Table] = []
    current: Table = []
    for number, line in lines:
        cells = cells_of(line)
        if cells is None:
            if current:
                tables.append(current)
                current = []
            continue
        if is_separator(cells):
            continue
        current.append((number, cells))
    if current:
        tables.append(current)
    return tables
