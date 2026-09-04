# beadloom:domain=application
# beadloom:feature=flow-guards
"""The guard firing record — evidence that a gate actually ran (BDL-061 S1).

A gate that cannot demonstrate it ran is treated as not having run, so every
evaluation the CLI performs appends one JSON line to
``.beadloom/guard-firings.jsonl``. That file is the only thing guards write, and
it is deliberately **not** the index: a check that writes to the artifact it
inspects cannot be trusted about it.

**What a line HOLDS, which is a separate question from how often one is written
(``beadloom-0mdo.43``).** A firing carries the verdict and the evaluation
context: for a file edit, the path the harness named; for a shell edit, the
program the line ran and the write targets a declared shape named — never the
command line itself (:mod:`~beadloom.application.guards.hook_payload` builds it
and states the decision in full). Until this bead it carried the line verbatim, because
widening the binding to the shell tool (BDL-UX #170) changed the record's
contents while every sentence about it still described a record of paths.
Measured on this repository the day it was found: 1 897 of 1 941 firings held a
command line, 895 481 characters of one session's shell history in a plaintext
file inside the project directory. The reduction happens at that door rather
than here, so this module writes whatever the context holds and owes the
decision no second implementation — but a reader deciding whether to commit this
file is reading here, which is why the decision is stated here too.

**What that does NOT reach: a record already written.** Lines appended before
this change keep their command lines until the cap rotates them out of the
active file and a second rollover replaces the archive. Nothing rewrites them —
a check that edits its own evidence is the shape this module exists not to be —
so a project that wants them gone deletes ``guard-firings.jsonl`` and
``guard-firings.1.jsonl``, at the cost of the carried counts they hold.

Append-only JSONL rather than a table: an append is atomic enough for parallel
agents (``O_APPEND`` on one line), needs no schema migration, and a corrupt line
costs exactly that line — :func:`read_firings` skips what it cannot parse rather
than failing the report that depends on it.

**Bounded by RECORDS, and no count is lost (BDL-061.56).** The record used to
grow without limit and ``--liveness`` parsed it whole on every run, so the cost
of the report grew with every guarded edit; bead ``.35`` only added the
``.gitignore`` entry, which made that growth invisible rather than absent.

What is bounded is the number of records, not bytes and not age, because the
three questions the report asks decide it. A byte cap truncates mid-record. An
age cap loses "how often" on a long-lived project and makes a quiet month read
like a dead guard. A record cap bounds exactly what was measured — the parse.

What rotation may lose is nothing the report reads. ``--liveness`` treats a gate
that cannot demonstrate it ran as not having run, so dropping firings silently
could turn a healthy guard into a false ``never-fired``. Instead the firings
that leave the active record are folded into a CARRIED SUMMARY
(:func:`read_carried`) that keeps, per guard, the count, how many of those
reached a verdict, and the first and last moment and outcome — every input
:mod:`~beadloom.application.guards.liveness` has. Their full detail stays on
disk for one more generation in ``guard-firings.1.jsonl``, so a human can still
read the ``why`` of a rotated firing until the next rollover replaces it.

Rotation renames rather than rewrites, and the summary is APPENDED to the fresh
record rather than written over it, so a concurrent appender loses nothing: a
process holding the old handle writes into the archive, which is read for the
summary AFTER the rename. The one uncovered window is a write into the archive
after that read; such a firing keeps its line on disk and is missing only from
the carried counts, which is why the rename comes first.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from beadloom.application.guards.models import GuardVerdict

#: Where firings are recorded, relative to the project root.
FIRINGS_RELPATH = Path(".beadloom") / "guard-firings.jsonl"

#: Where the previous generation is kept after a rollover. One generation only:
#: the counts survive forever in the carried summary, the detail for one more
#: rollover, and the disk cost stays bounded at twice the cap.
ARCHIVE_RELPATH = Path(".beadloom") / "guard-firings.1.jsonl"

#: How many firings the ACTIVE record holds before it rolls over.
#:
#: A count rather than a size, for the reason above; what one record costs has
#: been measured twice on this repository and moved both times, which is why the
#: figure is dated rather than stated as a property. At BDL-061.56, before the
#: binding saw the shell tool: ~200 bytes a record. On the generation that
#: rotated during ``beadloom-0mdo.43``, with every command line stored: 1 007
#: bytes over 1 999 records, so the cap held 2.0 MB rather than the 400 KB the
#: first measurement implied. The same 1 999 replayed through the reduction this
#: bead added: 557 bytes a record, 1.1 MB at the cap. It is a threshold, not a
#: target: a project that wants a longer tail keeps the archive.
ACTIVE_FIRINGS_CAP = 2000

#: Marks the carried-summary line, which is NOT a firing. :func:`read_firings`
#: already skips it (it carries no ``guard``/``outcome`` of its own), so a reader
#: that predates rotation is unaffected.
CARRIED_KIND = "rotation-summary"


@dataclass(frozen=True)
class FiringRecord:
    """One recorded guard evaluation."""

    guard: str
    outcome: str
    at: str = ""
    why: str = ""


@dataclass(frozen=True)
class CarriedGuard:
    """What survives rotation for one guard: every input the report reads."""

    count: int
    answered: int
    first_at: str
    last_at: str
    last_outcome: str


@dataclass(frozen=True)
class Carried:
    """The firings folded out of the active record, summarised by guard."""

    rotated: int = 0
    guards: Mapping[str, CarriedGuard] = field(default_factory=dict)

    def for_guard(self, name: str) -> CarriedGuard | None:
        """The carried summary for *name*, or ``None`` when nothing was rotated."""
        return self.guards.get(name)


def record_firing(
    project_root: Path, verdict: GuardVerdict, *, at: datetime | None = None
) -> Path:
    """Append *verdict* to the firing record; return the file written.

    Rolls the record over once it reaches :data:`ACTIVE_FIRINGS_CAP`. The count
    is exact rather than inferred from the file size: the file is bounded, so
    counting it is bounded too, and a size proxy would make the documented cap a
    guess about the average record.
    """
    path = project_root / FIRINGS_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    moment = at or datetime.now(timezone.utc)
    payload = {"at": moment.isoformat(), **verdict.to_dict()}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    if _line_count(path) >= ACTIVE_FIRINGS_CAP:
        _roll_over(project_root, path)
    return path


def _line_count(path: Path) -> int:
    try:
        return path.read_bytes().count(b"\n")
    except OSError:  # unreadable record: rotation is not the place to fail
        return 0


def _roll_over(project_root: Path, path: Path) -> None:
    """Move the active record aside and append its summary to a fresh one."""
    archive = project_root / ARCHIVE_RELPATH
    try:
        path.replace(archive)
    except OSError:  # cannot rotate (read-only tree, racing rotation): keep appending
        return
    # The OUTGOING summary travelled with the file, so it is read from the
    # archive: reading the fresh active file here would find nothing and reset
    # the total at every cap.
    carried = _fold(_carried_from(archive), _parse(archive))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(carried, sort_keys=True) + "\n")


def _fold(previous: Carried, records: tuple[FiringRecord, ...]) -> dict[str, object]:
    """The carried payload after *records* leave the active file.

    *previous* is the summary the outgoing generation itself carried, so a
    firing rotated twice is still counted once — the alternative is a count that
    silently resets every cap.
    """
    from beadloom.application.guards.models import GuardOutcome

    guards: dict[str, CarriedGuard] = dict(previous.guards)
    for record in records:
        held = guards.get(record.guard)
        answered = int(record.outcome != GuardOutcome.ERROR.value)
        first_at = record.at if held is None or not held.first_at else held.first_at
        if held is not None and record.at and record.at < first_at:
            first_at = record.at
        guards[record.guard] = CarriedGuard(
            count=(held.count if held else 0) + 1,
            answered=(held.answered if held else 0) + answered,
            first_at=first_at,
            last_at=record.at,
            last_outcome=record.outcome,
        )
    return {
        "kind": CARRIED_KIND,
        "rotated": sum(summary.count for summary in guards.values()),
        "guards": {
            name: {
                "count": summary.count,
                "answered": summary.answered,
                "first_at": summary.first_at,
                "last_at": summary.last_at,
                "last_outcome": summary.last_outcome,
            }
            for name, summary in guards.items()
        },
    }


def read_carried(project_root: Path) -> Carried:
    """The summary of the firings that have left the active record.

    Empty when nothing has rotated, which is the state of every project that has
    not yet reached the cap.
    """
    return _carried_from(project_root / FIRINGS_RELPATH)


def _carried_from(path: Path) -> Carried:
    """The carried summary held by one JSONL file."""
    if not path.is_file():
        return Carried()
    guards: dict[str, CarriedGuard] = {}
    rotated = 0
    for payload in _payloads(path):
        if payload.get("kind") != CARRIED_KIND:
            continue
        raw = payload.get("guards")
        if not isinstance(raw, dict):
            continue
        rotated += int(payload.get("rotated") or 0)
        for name, entry in raw.items():
            if not isinstance(name, str) or not isinstance(entry, dict):
                continue
            guards[name] = CarriedGuard(
                count=int(entry.get("count") or 0),
                answered=int(entry.get("answered") or 0),
                first_at=str(entry.get("first_at") or ""),
                last_at=str(entry.get("last_at") or ""),
                last_outcome=str(entry.get("last_outcome") or ""),
            )
    return Carried(rotated=rotated, guards=guards)


def _payloads(path: Path) -> list[dict[str, Any]]:
    """Every parseable JSON object in *path*, in file order."""
    found: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return found
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            found.append(payload)
    return found


def read_firings(project_root: Path) -> tuple[FiringRecord, ...]:
    """Every parseable firing in the ACTIVE record, oldest first.

    Bounded by :data:`ACTIVE_FIRINGS_CAP`. Firings that have rotated out are
    summarised by :func:`read_carried` and are deliberately not re-parsed here:
    reading both files would put the unbounded parse back, and the archive holds
    detail for a human rather than input for the report.

    An absent file reads as no firings. The carried-summary line is skipped like
    any other object that names no guard, so this function needed no change to
    stay right after rotation.
    """
    return _parse(project_root / FIRINGS_RELPATH)


def _parse(path: Path) -> tuple[FiringRecord, ...]:
    """Firing records from one JSONL file, oldest first."""
    if not path.is_file():
        return ()
    records: list[FiringRecord] = []
    for payload in _payloads(path):
        guard = payload.get("guard")
        outcome = payload.get("outcome")
        if not isinstance(guard, str) or not isinstance(outcome, str):
            continue
        records.append(
            FiringRecord(
                guard=guard,
                outcome=outcome,
                at=str(payload.get("at") or ""),
                why=str(payload.get("why") or ""),
            )
        )
    return tuple(records)
