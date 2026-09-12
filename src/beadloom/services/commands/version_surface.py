"""The ``version-surface`` command — every place this project states its version.

Presentation and wiring only. The derivation is
:func:`beadloom.doc_sync.version_surface.read_version_surface`; this module turns
a surface into lines on a stream and one exit code.

The command exists because cutting 4.0.0 met its own defect (BDL-UX #281). The
version was stated in nine places; four instruments judged parts of that
population, no two parts overlapped, and three places were judged by nothing.
Every instrument was individually correct and the union had no name, so the
release bumped the four places its author remembered and met the rest one at a
time -- a ``lint --strict`` error at ``severity: error`` and two assertions
inside the suite, both arriving after the work was believed finished.

**The report groups by file, and that is a decision rather than a layout.** On
this repository the derivation returns forty-odd places of which most are judged
by nothing, and nine of those sit in one issue log. A flat per-line list is a
report nobody finishes, which is the same failure as not printing it. A group is
one file and one reason together, so a file whose lines fall outside for two
different reasons is two groups rather than one averaged sentence.

Codes (the contract a caller may rely on):

* ``0`` -- the surface was derived. Places nothing checks do NOT make it
  non-zero: the gap is what the report exists to state, and a release that has
  to read it is not a release that failed.
* ``2`` -- no version could be derived. The verdict carries the reason, on
  standard output, because an empty answer and an empty answer with a reason are
  different answers.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from collections.abc import Callable

    from beadloom.doc_sync.version_surface import (
        Instrument,
        Population,
        SourceOfTruth,
        VersionPlace,
        VersionSurface,
    )

    #: How a group of places is attributed: its instruments, or why it has none.
    Attribution = Callable[[VersionPlace], str]

_EXIT_DERIVED = 0
_EXIT_UNRESOLVED = 2

#: How much of a stating line is shown. A place is identified by its file, its
#: line and enough of the text to recognise; the rest is in the file, and a row
#: the terminal wraps costs more than the tail it would have carried.
_EXCERPT_WIDTH = 80

#: The width every other line is wrapped to. A reason is the actionable half of
#: an unjudged row, so it is wrapped rather than cut: what a reader loses to a
#: terminal's own wrapping is the alignment that makes a group readable.
_LINE_WIDTH = 100

#: A group's header, the rows under it, and the second line of a header whose
#: reason wraps. The last is indented past the rows on purpose: at a row's
#: indent it reads as a place that has lost its line number.
_HEADER_INDENT = "    "
_ROW_INDENT = "      "
_HEADER_HANGING = "          "


@main.command("version-surface")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON output.")
def version_surface(*, project: Path | None, as_json: bool) -> None:
    """Report every place this project states its version, and what checks each.

    A release edits the places its author remembers. This names the places the
    project has, attributes each to the instrument whose population holds it,
    and states the ones no instrument holds — the list derived rather than
    recalled.
    """
    from beadloom.doc_sync.version_surface import read_version_surface

    surface = read_version_surface(project or Path.cwd())
    click.echo(json.dumps(_payload(surface), indent=2) if as_json else _human(surface))
    sys.exit(_EXIT_DERIVED if surface.source_of_truth is not None else _EXIT_UNRESOLVED)


_TITLE = "Version surface — every place this project states its version, derived, never listed"


def _human(surface: VersionSurface) -> str:
    """The report a person cutting a release reads, top to bottom."""
    source = surface.source_of_truth
    if source is None:
        return "\n".join([_TITLE, "", *_not_derived(surface)])
    blocks = [
        [_TITLE],
        _source_lines(source),
        _checked_lines(surface),
        _gap_lines(surface),
        _instrument_lines(surface.instruments),
        _population_lines(surface.population),
        _limit_lines(source),
    ]
    return "\n\n".join("\n".join(block) for block in blocks)


def _not_derived(surface: VersionSurface) -> list[str]:
    """No version, and why — never an empty list wearing the same shape."""
    return [
        f"  NOT DERIVED: {surface.unresolved}",
        "  Every place below a version this reader cannot follow would be attributed to a",
        "  value nothing builds from, so none is reported.",
    ]


def _source_lines(source: SourceOfTruth) -> list[str]:
    """The literal every other place restates, and how it was arrived at."""
    return [
        f"  Source of truth: {source.value}",
        *_wrapped(
            f"{source.path}:{source.line}    {source.derived_from}",
            indent="    ",
            hanging="      ",
        ),
    ]


def _checked_lines(surface: VersionSurface) -> list[str]:
    """The places some instrument's population holds, grouped by file."""
    checked = tuple(place for place in surface.places if place.checkers)
    if not checked:
        return ["  Checked: none — no instrument's population holds a place stating the version."]
    return [
        f"  Checked ({_count(checked)}):",
        *_groups(checked, lambda place: ", ".join(place.checkers)),
    ]


def _gap_lines(surface: VersionSurface) -> list[str]:
    """The places nothing holds — the line this command exists to print."""
    if not surface.unchecked:
        return ["  Checked by nothing: none — every place is inside some instrument's population."]
    return [
        f"  Checked by nothing ({_count(surface.unchecked)}):",
        *_groups(surface.unchecked, lambda place: f"— {place.reason}"),
    ]


def _count(places: tuple[VersionPlace, ...]) -> str:
    """Places and files counted separately: two lines in one file are two edits."""
    return f"{len(places)} place(s) in {len({place.path for place in places})} file(s)"


def _groups(places: tuple[VersionPlace, ...], attribute: Attribution) -> list[str]:
    """One header per file-and-attribution, then the lines under it.

    Grouping on the pair rather than on the file keeps a file whose lines fall
    outside for two reasons reading as two facts.
    """
    grouped: dict[tuple[str, str], list[VersionPlace]] = defaultdict(list)
    for place in places:
        grouped[(str(place.path), attribute(place))].append(place)
    lines: list[str] = []
    for (path, attribution), group in sorted(grouped.items(), key=_group_order):
        lines.extend(
            _wrapped(
                f"{path} ({len(group)})    {attribution}",
                indent=_HEADER_INDENT,
                hanging=_HEADER_HANGING,
            )
        )
        lines.extend(
            f"{_ROW_INDENT}{place.line}    {_excerpt(place.excerpt)}"
            for place in sorted(group, key=lambda place: place.line)
        )
    return lines


def _group_order(item: tuple[tuple[str, str], list[VersionPlace]]) -> tuple[str, int]:
    (path, _), group = item
    return (path, min(place.line for place in group))


def _wrapped(text: str, *, indent: str, hanging: str) -> list[str]:
    """*text* over as many lines as a 100-column terminal needs, paths intact."""
    return textwrap.wrap(
        text,
        width=_LINE_WIDTH,
        initial_indent=indent,
        subsequent_indent=hanging,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [f"{indent}{text}"]


def _excerpt(text: str) -> str:
    stripped = text.strip()
    if len(stripped) <= _EXCERPT_WIDTH:
        return stripped
    return stripped[: _EXCERPT_WIDTH - 1] + "…"


def _instrument_lines(instruments: tuple[Instrument, ...]) -> list[str]:
    """What each named instrument turned out to hold on THIS project."""
    lines = [f"  Instruments ({len(instruments)}):"]
    for instrument in instruments:
        held = (
            instrument.population if instrument.resolved else f"NOT RESOLVED — {instrument.reason}"
        )
        lines.extend(_wrapped(f"{instrument.name}    {held}", indent="    ", hanging="      "))
    return lines


def _population_lines(population: Population) -> list[str]:
    """What the sweep read, pruned, skipped by suffix, and could not decode."""
    lines = [
        f"  Population: {population.files_read} file(s) read",
        *_wrapped(
            f"Suffixes read: {', '.join(population.suffixes_read)}",
            indent="    ",
            hanging="      ",
        ),
        *_wrapped(
            f"Directories skipped: {', '.join(population.directories_skipped)}",
            indent="    ",
            hanging="      ",
        ),
        *_wrapped(f"Not read: {_not_read(population)}", indent="    ", hanging="      "),
    ]
    if not population.unreadable:
        lines.append("    Unreadable: none")
        return lines
    lines.append(f"    Unreadable ({len(population.unreadable)}):")
    for path, why in population.unreadable:
        lines.extend(_wrapped(f"{path} — {why}", indent="      ", hanging="        "))
    return lines


def _not_read(population: Population) -> str:
    if not population.not_read:
        return "none — every file under the sweep carried a suffix it reads"
    return ", ".join(f"{suffix} ({count})" for suffix, count in population.not_read)


def _limit_lines(source: SourceOfTruth) -> list[str]:
    """The limit to read first, stated beside the answer it qualifies."""
    return _wrapped(
        f"The sweep is by the current literal ({source.value}): a place that already states an "
        "older version is invisible to it, so run this before the bump and not after. Catching "
        "a place that has gone stale is what the instruments above are for, and which places "
        "have one is what this report names.",
        indent="  ",
        hanging="  ",
    )


def _payload(surface: VersionSurface) -> dict[str, object]:
    """The same facts as the human report, in the shape a release script reads."""
    return {
        "source_of_truth": _source_payload(surface),
        "unresolved": surface.unresolved,
        "places": [_place_payload(place) for place in surface.places],
        "unchecked": [_place_payload(place) for place in surface.unchecked],
        "instruments": [
            {
                "name": instrument.name,
                "population": instrument.population,
                "resolved": instrument.resolved,
                "reason": instrument.reason,
            }
            for instrument in surface.instruments
        ],
        "population": {
            "files_read": surface.population.files_read,
            "suffixes_read": list(surface.population.suffixes_read),
            "directories_skipped": list(surface.population.directories_skipped),
            "not_read": [
                {"suffix": suffix, "files": count} for suffix, count in surface.population.not_read
            ],
            "unreadable": [
                {"path": str(path), "why": why} for path, why in surface.population.unreadable
            ],
        },
    }


def _source_payload(surface: VersionSurface) -> dict[str, object] | None:
    source = surface.source_of_truth
    if source is None:
        return None
    return {
        "path": str(source.path),
        "line": source.line,
        "value": source.value,
        "derived_from": source.derived_from,
    }


def _place_payload(place: VersionPlace) -> dict[str, object]:
    return {
        "path": str(place.path),
        "line": place.line,
        "excerpt": place.excerpt.strip(),
        "checkers": list(place.checkers),
        "reason": place.reason,
    }
