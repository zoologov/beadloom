# beadloom:domain=application
# beadloom:feature=impact
"""The answer rendered as the ``## Axes`` section a work item's document carries.

A third rendering of the SAME computation the text and the JSON come from, not a
third answer. It writes the derivation's half — the seed, the rule, the axes and
the population the derivation could not read — and leaves the person's half
undecided, because a renderer that filled the scope column in would be deciding
the thing the section exists to record.

The grammar is :mod:`beadloom.doc_sync.axes_section`'s, imported rather than
restated, so the writer and the reader of this section cannot drift apart. What
the reader would report about a section this renderer just produced is exactly
what is true of it: every row is undecided until a person rules on it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.impact.axes import THE_TARGET_SEAT
from beadloom.doc_sync.axes_section import (
    AXES_HEADING,
    COLUMNS,
    DERIVED_BY_FIELD,
    NO_SEED,
    OWNS_NOTHING_UNREAD,
    SEED_FIELD,
    UNRESOLVED_FIELD,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from beadloom.application.impact.answer import ImpactAnswer, Population
    from beadloom.application.impact.axes import Command

#: The cell a rendered row carries where a person's decision goes. Not blank:
#: an empty cell reads as an oversight, and this one is a question waiting for
#: an answer — the check reports it either way.
UNDECIDED = "?"

#: What a node cell says when the derivation named no node for the row.
_NO_NODE = "—"

#: How a branch row taken over a caller of the target is spelled.
_FROM_A_CALLERS_SEAT = ", from a caller's seat"

#: What the ``Owns unread`` cell says for a named node when the answer had no
#: index to read ownership from. Not ``none``: nothing was measured, and a
#: stated absence would be a claim this run cannot make.
_OWNERSHIP_UNKNOWN = "unknown — no index"


def render_axes_section(answer: ImpactAnswer) -> str:
    """The ``## Axes`` section for *answer*, ready to paste into a document."""
    lines = [f"## {AXES_HEADING}", ""]
    lines.extend(_fields(answer))
    lines.append("")
    lines.append("| " + " | ".join(COLUMNS) + " |")
    lines.append("|" + "|".join("---" for _ in COLUMNS) + "|")
    lines.extend(_rows(answer))
    lines.append("")
    return "\n".join(lines)


def _fields(answer: ImpactAnswer) -> list[str]:
    return [
        f"> **{DERIVED_BY_FIELD}:** `beadloom impact {answer.target}` over `{answer.root}`",
        f"> **{SEED_FIELD}:** {_seed(answer)}",
        f"> **{UNRESOLVED_FIELD}:** {_unresolved(answer)}",
    ]


def _seed(answer: ImpactAnswer) -> str:
    """The seed field: the names, the rule that derived them, or a stated absence.

    An absent seed is rendered as the word, never as an empty list. The answer
    itself keeps the two apart — ``resolved=False`` is not ``sites=()`` — and a
    section that flattened them would report a derivation that knew nothing as
    one that found nothing.
    """
    if not answer.seeds:
        return (
            f"{NO_SEED} — no name the target reaches performs a declared effect "
            f"under rule `{answer.seed_rule}`, so every axis below is unresolved "
            f"and not empty"
        )
    named = ", ".join(
        f"`{seed.name}` (effect `{seed.effect}`)" for seed in answer.seeds
    )
    return f"{named}, under rule `{answer.seed_rule}`"


def _unresolved(answer: ImpactAnswer) -> str:
    if not answer.unresolved:
        return f"{NO_SEED} — every call read under `{answer.root}` resolved"
    counts: dict[str, int] = {}
    for gap in answer.unresolved:
        counts[gap.kind] = counts.get(gap.kind, 0) + 1
    return ", ".join(f"{counts[kind]} {kind}" for kind in sorted(counts))


def _rows(answer: ImpactAnswer) -> list[str]:
    owns = _ownership_cells(answer)
    rows = [
        *_population_rows("co-writers", answer.co_writers, owns),
        *_population_rows("callers", answer.callers, owns),
        *(_command_row(command, owns) for command in answer.commands),
    ]
    return rows or [_row("co-writers", _NO_NODE, "no site found", owns)]


def _ownership_cells(answer: ImpactAnswer) -> Callable[[str], str]:
    """The ``Owns unread`` cell for a row, from the node it names (BDL-UX #284).

    Written on the row because the row is where a person rules. The unresolved
    field counts the same population, and a count in a blockquote above a table
    of forty rows is what one epic's ruling read past: a ``callers`` row was
    ruled "not changed" while the fix lived in that node's templates.
    """
    owned = {entry.node: entry.files for entry in answer.unread_ownership}

    def cell(node: str) -> str:
        if node == _NO_NODE:
            return _NO_NODE
        if not answer.boundary.resolved:
            return _OWNERSHIP_UNKNOWN
        files = owned.get(node)
        return f"{len(files)} — `{files[0]}`" if files else OWNS_NOTHING_UNREAD

    return cell


def _population_rows(
    axis: str, population: Population, owns: Callable[[str], str]
) -> list[str]:
    """The rows for one axis: the caveat, if there is one, and then the sites.

    An unresolved axis keeps the sites it did find. A section that dropped them
    would be a narrower artifact than the answer it renders, and the reader of
    the section is the one deciding scope.
    """
    by_node: dict[str, list[str]] = {}
    for site in population.sites:
        by_node.setdefault(site.node or _NO_NODE, []).append(
            f"{site.path}:{site.lineno}"
        )
    found = [
        _row(axis, node, f"{len(sites)} — `{sites[0]}`", owns)
        for node, sites in sorted(by_node.items())
    ]
    if not population.resolved:
        return [_row(axis, _NO_NODE, f"unresolved — {population.reason}", owns), *found]
    return found or [_row(axis, _NO_NODE, "no site found", owns)]


def _command_row(command: Command, owns: Callable[[str], str]) -> str:
    narrowing = "" if command.narrowed_to_the_seeds else ", over every call"
    seat = "" if command.seat == THE_TARGET_SEAT else _FROM_A_CALLERS_SEAT
    return _row(
        "branches",
        command.node or _NO_NODE,
        f"`{command.name}`: {len(command.branches)} branch(es), "
        f"{len(command.exits)} exit form(s){narrowing}{seat}",
        owns,
    )


def _row(axis: str, node: str, sites: str, owns: Callable[[str], str]) -> str:
    return f"| {axis} | {node} | {sites} | {owns(node)} | {UNDECIDED} |  |"
