"""The ``rooms`` command — which rooms this project declares, and which you are in.

Presentation and wiring only. The derivation is
:func:`beadloom.application.rooms.take_census`; this module turns a census into
lines on a stream and one exit code.

The command exists so a completion checklist can name ROOMS without listing
them. `uv run mypy src/` is not a claim until it says which interpreter, and a
checklist that spells the interpreters out goes stale the first time a leg
changes — which happened three times to this repository's own required status
checks. What it prints follows the declaration: the supported interpreters from
the packaging metadata, the legs from the CI workflows.

Codes (the contract a caller may rely on):

* ``0`` — the census was taken. A project declaring no leg also exits 0: not
  declaring CI is not a violation, and this command grades nothing.
* ``2`` — the invocation cannot be answered: ``--dimension`` names an axis no
  declared room carries. An empty answer would read as "this project has no such
  axis", which is the clean list an agent trusts and stops at.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.application.rooms import RoomCensus

_EXIT_CLEAN = 0
_EXIT_UNANSWERABLE = 2

#: How many not-entered rooms the human report names before it counts the rest.
_NAMED_LIMIT = 12


@main.command("rooms")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--dimension",
    "dimension",
    default=None,
    help=(
        "Print the distinct values of one axis of the declared rooms, one per "
        "line — the form a checklist loops over instead of a literal list."
    ),
)
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON output.")
def rooms(*, project: Path | None, dimension: str | None, as_json: bool) -> None:
    """Report the room this run is in and the rooms this project declares.

    A measurement is true of the room it was taken in. Naming the room does not
    make a verdict stronger — it makes it answerable, because a reader can see
    which declared rooms the run entered and which it did not.
    """
    from beadloom.application.rooms import take_census

    census = take_census(project or Path.cwd())
    if dimension is not None:
        _print_dimension(census, dimension)
        return
    click.echo(json.dumps(_payload(census), indent=2) if as_json else _human(census))
    sys.exit(_EXIT_CLEAN)


def _print_dimension(census: RoomCensus, dimension: str) -> None:
    """One axis of the declared rooms, or a refusal naming the axes there are."""
    if not census.comparisons:
        click.echo(
            "this project declares no room a verdict could be held against, so "
            f"it carries no `{dimension}` axis",
            err=True,
        )
        sys.exit(_EXIT_UNANSWERABLE)
    axes = sorted({key for c in census.comparisons for key in c.room.dimensions})
    if dimension not in axes:
        click.echo(
            f"no declared room carries a `{dimension}` axis; the axes declared "
            f"are: {', '.join(axes)}",
            err=True,
        )
        sys.exit(_EXIT_UNANSWERABLE)
    values = {
        c.room.dimensions[dimension]
        for c in census.comparisons
        if dimension in c.room.dimensions
    }
    for value in sorted(values, key=_version_key):
        click.echo(value)
    sys.exit(_EXIT_CLEAN)


def _version_key(value: str) -> tuple[int, ...] | tuple[()]:
    """Order ``3.9`` before ``3.10``, and leave anything else to its own order."""
    parts = value.split(".")
    if all(p.isdigit() for p in parts):
        return tuple(int(p) for p in parts)
    return ()


def _human(census: RoomCensus) -> str:
    """The report a person reads: where this run is, and what it does not cover."""
    from beadloom.application.rooms import room_line

    lines = [
        "Rooms — derived from this project's declaration, never from a list",
        "",
        f"  This run is in: {room_line(census.current)}",
        "",
    ]
    lines.extend(_declared_lines(census))
    lines.extend(_supported_lines(census))
    lines.extend(_unresolved_lines(census))
    return "\n".join(lines)


def _declared_lines(census: RoomCensus) -> list[str]:
    if not census.comparisons:
        return [
            "  This project declares no room a verdict could be held against: "
            "no CI workflow declares a leg.",
            "",
        ]
    entered = len(census.entered)
    total = len(census.comparisons)
    lines = [f"  Declared rooms: {total}, entered by this run: {entered}"]
    for comparison in census.comparisons[:_NAMED_LIMIT]:
        mark = "in" if comparison.entered else "  "
        lines.append(
            f"    [{mark}] {comparison.room.label}    {comparison.room.source}"
        )
        if comparison.why:
            lines.append(f"         {comparison.why}")
    if total > _NAMED_LIMIT:
        lines.append(f"    ... and {total - _NAMED_LIMIT} more")
    lines.append("")
    return lines


def _supported_lines(census: RoomCensus) -> list[str]:
    lines: list[str] = []
    if census.supported:
        floor = f" (floor {census.floor})" if census.floor else ""
        lines.append(
            f"  Interpreters this project supports: "
            f"{', '.join(census.supported)}{floor}"
        )
    if census.supported_without_a_leg:
        lines.append(
            "  Supported with no leg entering it: "
            f"{', '.join(census.supported_without_a_leg)}"
        )
    if lines:
        lines.append("")
    return lines


def _unresolved_lines(census: RoomCensus) -> list[str]:
    """What the derivation could not turn into a room, named rather than dropped."""
    if not census.unresolved:
        return []
    lines = [f"  Unresolved ({len(census.unresolved)}):"]
    lines.extend(f"    {u.source} — {u.why}" for u in census.unresolved)
    return lines


def _payload(census: RoomCensus) -> dict[str, object]:
    """The same facts as the human report, in the shape a monitor reads."""
    return {
        "current": dict(census.current.dimensions),
        "declared": [
            {
                "room": c.room.label,
                "dimensions": dict(c.room.dimensions),
                "source": c.room.source,
                "entered": c.entered,
                "why": c.why,
            }
            for c in census.comparisons
        ],
        "supported": list(census.supported),
        "floor": census.floor,
        "supported_without_a_leg": list(census.supported_without_a_leg),
        "unresolved": [{"source": u.source, "why": u.why} for u in census.unresolved],
    }
