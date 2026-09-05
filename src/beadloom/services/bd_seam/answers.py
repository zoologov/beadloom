"""The population a ``bd`` answer covers, which is never the population asked for.

:mod:`.invocations` and :mod:`.assumptions` judge a call FORM before it runs.
This module reads what came BACK, because two of bd's answers cover a population
that is not the one the question named and neither answer has room to say so:

* ``bd list`` returns LESS than the tracker. Two default filters, of which bd
  announces exactly one. Measured on this repository: ``bd list --json`` returns
  50 rows of 843 and prints ``Showing 50 issues; more results matched but were
  hidden by --limit…`` on STDERR, while the status filter that omits every closed
  bead is silent on both streams. ``--all`` lifts both and returns 843 with a
  silent stderr.
* ``bd close --suggest-next`` returns MORE than the question. It names beads for
  which the closed issue was A blocker without checking whether others remain
  (BDL-UX #97). Measured over TWENTY-THREE dependency shapes, each in its own
  ``bd init`` rig: it named a still-blocked bead in sixteen of them, and
  ``bd ready`` was correct in all twenty-three.

**This is not a wrapper, and CONTEXT Q4 is why.** Nothing here re-implements a
decision bd makes or invents a population of its own. It reads the notice bd
prints, the ids bd names and the argv WE wrote, and it states which population
the answer covers. A wrapper would be a second thing to keep in step with
upstream; a reader of bd's own output goes stale loudly instead.

**The vocabulary has no clean-pass value for the unchecked case**, which is the
distinction this epic has now shipped seven times — ``not compared`` rather than
``agrees``, ``NOTHING TO CHECK`` rather than a pass. A subcommand whose
population this derivation has not measured is
:data:`COVERAGE_UNCHECKED`; a suggestion nothing confirmed is
:data:`NOT_COMPARED`; a close that suggested nothing is
:data:`NOTHING_TO_CHECK`. None of the three may be read as "the whole".

**Measured on bd 1.0.4 (``ce242a879``)**, streams separated and exit codes read
without a pipe. Both notice forms were measured rather than quoted:
``Showing 50 issues; more results matched…`` from ``bd list`` on this
repository's tracker, and ``Showing 100 of 120 ready issues.`` from ``bd ready``
on a rig grown past the cap with ``bd create --graph``. If a later bd stops
narrowing either answer, ``tests/test_bd_call_sites.py`` compares
:data:`~beadloom.services.bd_seam.assumptions.BD_MEASURED_VERSION` against the
``bd`` on PATH and fails, so this guards nothing loudly rather than quietly.
"""

# beadloom:component=bd-seam

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from beadloom.services.bd_seam.assumptions import (
    BD_MEASURED_VERSION,
    population_flags,
    subcommand_of,
)
from beadloom.services.bd_seam.invocations import tokens_of

__all__ = [
    "COVERAGE",
    "COVERAGE_AS_ASKED",
    "COVERAGE_FILTERED",
    "COVERAGE_TRUNCATED",
    "COVERAGE_UNCHECKED",
    "NOTHING_TO_CHECK",
    "NOT_COMPARED",
    "READY_COMMAND",
    "AnswerCoverage",
    "ConfirmedSuggestion",
    "confirmed_suggestion",
    "coverage_of",
    "ready_ids",
    "suggested_beads",
]

#: The population the CALL FORM named, with nothing withheld. Deliberately not
#: called "complete": ``bd list --status open`` names a population and bd honours
#: it, and an answer covering every open bead is not an answer covering the
#: tracker. What a consumer may rely on is that it got what it asked for.
COVERAGE_AS_ASKED = "as-asked"
#: Narrower than the question, because the call form named no widening flag.
COVERAGE_FILTERED = "filtered"
#: Narrower than the question, and bd's own notice says by how much.
COVERAGE_TRUNCATED = "truncated"
#: A subcommand whose population this derivation has not measured. Never clean.
COVERAGE_UNCHECKED = "unchecked"

#: Every coverage this module can report, widest first.
COVERAGE: tuple[str, ...] = (
    COVERAGE_AS_ASKED,
    COVERAGE_FILTERED,
    COVERAGE_TRUNCATED,
    COVERAGE_UNCHECKED,
)

#: What a suggestion reads when nothing confirmed it. Not "all of them are ready".
NOT_COMPARED = "not compared"

#: What a close reads when it suggested nothing at all. Not "all confirmed".
NOTHING_TO_CHECK = "NOTHING TO CHECK"

#: The subcommand that answers "which beads are actually workable". It was correct
#: in all twenty-three measured shapes, which is why it is the confirmation.
#:
#: The argv that asks it is deliberately NOT spelled here. A caller owns its own
#: call form, and a shared constant imported from this module would be invisible
#: to :func:`~beadloom.services.bd_seam.invocations.python_invocations`, which
#: resolves a name bound in the module it is reading. A caller's own
#: ``["ready", "--json", "--limit", "0"]`` is judged by the derivation; an import
#: of ours would be judged by nothing, which is the phantom gate this epic exists
#: to remove.
READY_COMMAND = "ready"

#: bd's own truncation notice, in both the forms measured on 1.0.4: ``Showing 50
#: issues; …`` from ``bd list`` and ``Showing 100 of 120 ready issues.`` from
#: ``bd ready``. The second number is optional because only one form carries it.
_NOTICE = re.compile(r"\bShowing\s+(?P<shown>\d+)(?:\s+of\s+(?P<total>\d+))?\b")

#: The block ``--suggest-next`` writes on STDOUT, measured: a header line, then
#: one bullet per candidate as ``  • <id> — <title> (<priority>)``.
_SUGGESTED_HEADER = "Newly unblocked:"
_SUGGESTED_ROW = re.compile(r"^\s*[•*-]\s*(?P<bead>\S+)\s")


@dataclass(frozen=True)
class AnswerCoverage:
    """Which population one ``bd`` answer covers, and how a reader can tell.

    ``shown`` and ``total`` come from bd's own notice and are ``None`` when it
    printed none: an absent notice is not a count of zero, and reporting it as
    one would be the false confidence this epic exists to remove.
    """

    subcommand: str
    coverage: str
    shown: int | None = None
    total: int | None = None
    widening_flags: tuple[str, ...] = ()

    @property
    def as_asked(self) -> bool:
        """Whether the answer covers the population the call form named."""
        return self.coverage == COVERAGE_AS_ASKED

    @property
    def stated(self) -> str:
        """The sentence a consumer reports instead of an unqualified answer."""
        pinned = f"(measured on bd {BD_MEASURED_VERSION})"
        if self.coverage == COVERAGE_UNCHECKED:
            return (
                f"the population a `bd {self.subcommand}` answer covers is not one this "
                f"derivation has measured, so it is UNCHECKED and not complete {pinned}"
            )
        if self.coverage == COVERAGE_TRUNCATED:
            withheld = f" of {self.total}" if self.total is not None else ""
            return (
                f"`bd {self.subcommand}` returned {self.shown}{withheld} row(s) and said so "
                f"on stderr, so this answer is PART of the population and not the whole. "
                f"Widen it with {_flag_list(self.widening_flags)} {pinned}"
            )
        if self.coverage == COVERAGE_FILTERED:
            return (
                f"`bd {self.subcommand}` was asked with no flag naming its population, so "
                f"the answer is FILTERED by a default and bd need not say so. Widen it "
                f"with {_flag_list(self.widening_flags)} {pinned}"
            )
        return (
            f"`bd {self.subcommand}` named the population it wanted with "
            f"{_flag_list(self.widening_flags)} and bd announced no truncation, so this "
            f"answer covers what the call form ASKED FOR — which is not the same claim "
            f"as covering the tracker {pinned}"
        )


@dataclass(frozen=True)
class ConfirmedSuggestion:
    """``--suggest-next``'s candidates, against the answer that is authoritative.

    ``compared`` is the field that stops this being readable as a clean pass: a
    suggestion nobody could confirm has an empty ``confirmed`` for the same
    reason a fully-blocked one does, and only ``compared`` tells the two apart.
    """

    candidates: tuple[str, ...]
    confirmed: tuple[str, ...]
    still_blocked: tuple[str, ...]
    compared: bool

    @property
    def stated(self) -> str:
        """The sentence a consumer returns instead of bd's raw suggestion."""
        pinned = f"(BDL-UX #97, measured on bd {BD_MEASURED_VERSION})"
        if not self.candidates:
            return (
                f"`bd close --suggest-next` named no bead, so there is {NOTHING_TO_CHECK} "
                f"— which is not the same fact as a confirmed empty queue {pinned}"
            )
        if not self.compared:
            return (
                f"{len(self.candidates)} candidate(s) from `bd close --suggest-next`, "
                f"{NOT_COMPARED} against `bd ready` because that answer could not be "
                f"read. `--suggest-next` names beads that are still blocked, so these "
                f"are candidates and nothing here confirms any of them {pinned}"
            )
        return (
            f"{len(self.candidates)} candidate(s) from `bd close --suggest-next`, "
            f"confirmed against `bd ready`: {len(self.confirmed)} ready, "
            f"{len(self.still_blocked)} still blocked {pinned}"
        )


def _flag_list(flags: tuple[str, ...]) -> str:
    """The widening flags, spelled for a sentence rather than for a parser."""
    return ", ".join(f"`{flag}`" for flag in flags) if flags else "no flag bd offers"


def coverage_of(argv: tuple[str, ...], stderr: str) -> AnswerCoverage:
    """Which population the answer to *argv* covers, given bd's *stderr*.

    Both halves are needed and neither is sufficient. The call form decides
    whether a SILENT bd may be believed — ``bd list --json`` is filtered by a
    default that announces nothing — and bd's notice decides whether a widened
    call form was honoured, which is what turns "we passed ``--all``" into a
    measurement rather than an intention.
    """
    words, flags = tokens_of(argv)
    subcommand = subcommand_of(words)
    widening = population_flags(subcommand)
    if widening is None:
        return AnswerCoverage(subcommand=subcommand, coverage=COVERAGE_UNCHECKED)
    notice = _NOTICE.search(stderr)
    if notice is not None:
        total = notice.group("total")
        return AnswerCoverage(
            subcommand=subcommand,
            coverage=COVERAGE_TRUNCATED,
            shown=int(notice.group("shown")),
            total=int(total) if total is not None else None,
            widening_flags=widening,
        )
    if any(flag in flags for flag in widening):
        return AnswerCoverage(
            subcommand=subcommand,
            coverage=COVERAGE_AS_ASKED,
            widening_flags=widening,
        )
    return AnswerCoverage(
        subcommand=subcommand,
        coverage=COVERAGE_FILTERED,
        widening_flags=widening,
    )


def ready_ids(stdout: str) -> tuple[str, ...] | None:
    """The bead ids in a ``bd ready --json`` answer, or ``None`` if unreadable.

    ``None`` and ``()`` are different answers and the caller must keep them
    apart: an empty ready queue is a measurement, and an answer nobody could
    parse is not. Returning ``()`` for both is how a failed confirmation becomes
    "every candidate is still blocked".
    """
    try:
        rows = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(rows, list):
        return None
    found = [row["id"] for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)]
    return tuple(found) if len(found) == len(rows) else None


def suggested_beads(stdout: str) -> tuple[str, ...]:
    """The bead ids ``--suggest-next`` named, read from bd's own stdout block.

    Everything before the header is the close confirmation and everything the
    header introduces is a candidate, so a close that suggested nothing yields
    an empty tuple rather than a parse failure.
    """
    lines = stdout.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if _SUGGESTED_HEADER in line)
    except StopIteration:
        return ()
    found: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            continue
        row = _SUGGESTED_ROW.match(line)
        if row is None:
            break
        found.append(row.group("bead"))
    return tuple(found)


def confirmed_suggestion(close_stdout: str, ready: tuple[str, ...] | None) -> ConfirmedSuggestion:
    """``--suggest-next``'s candidates, split by what ``bd ready`` actually lists.

    *ready* is ``None`` when that answer could not be read, which produces
    :data:`NOT_COMPARED` rather than an empty confirmation — the two look
    identical in the ids and are opposite facts.
    """
    candidates = suggested_beads(close_stdout)
    if ready is None:
        return ConfirmedSuggestion(
            candidates=candidates, confirmed=(), still_blocked=(), compared=False
        )
    listed = set(ready)
    return ConfirmedSuggestion(
        candidates=candidates,
        confirmed=tuple(bead for bead in candidates if bead in listed),
        still_blocked=tuple(bead for bead in candidates if bead not in listed),
        compared=True,
    )
