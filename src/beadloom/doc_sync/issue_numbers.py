# beadloom:domain=doc-sync
# beadloom:feature=issue-numbers
"""The issue log's numbers: the population in use, and the next one ALLOCATED.

A numbered issue log is a single markdown file that every writer appends to,
and the number a writer takes is the one they read off the end of it. On this
repository that has collided five times — BDL-UX #187, #211, #253, and twice
within one hour on 2026-09-09, when one agent took #259 (already taken hours
earlier by another bead in the same slice) and #260, which never reached the
file at all. The last pair is both failure modes in one act: a number two
writers hold, and a number that lives only in a bead title.

**Why an allocator rather than a check**, since the bead framed it as a choice.
The coordinator's whole-log duplicate check ran on the morning of 2026-09-09 and
found exactly one duplicate; four hours later the fifth collision happened
anyway. A check reports after the fact and two writers filing concurrently
cannot grep each other. So the number is allocated.

**What "atomically" means over a markdown file in git**, since that needed a
definition. It is not git's and it is not the log's: allocation is
``os.open(O_CREAT | O_EXCL)`` of one claim file per number in a ledger
DIRECTORY. POSIX makes that create-or-fail indivisible, so of two writers
computing the same next number exactly one creates the name and the other
retries at the next one. Git never enters it — two writers commit two different
files, which is a merge that has nothing to resolve.

**The claim file is one file per incident, deliberately.** ``beadloom-l9ee``
reached the same shape from the other direction: the property that makes the
collision impossible is one writer per file, not generation, and a shared
append-only log is the same defect under another filename. This module takes
that layout at the boundary rather than migrating the entries already written —
the claim file is where the incident's body grows when the log becomes a
composed view of the ledger, and nothing built here is discarded by that move.

**The check ships beside the allocator, not instead of it.** ``O_EXCL`` spans
one filesystem. Two agents in two clones can still take one number and only the
merge shows it, so the population the allocator cannot span is exactly what
:func:`check_issue_numbers` covers.

**Three legs, and each one is a class this repository has met:**

``duplicate-number``
    One number defined by two entries. #187 and #253.
``unwritten-claim``
    A number claimed and never written into the log. #260 — a number in a bead
    title with nothing in the file.
``unclaimed-number``
    An entry numbered at or above the ledger's floor whose number no claim
    holds: the allocator was bypassed and the log was hand-appended.

**The floor is derived, never authored.** It is the lowest number the ledger
holds, so a project that adopts the allocator is judged from its first
allocation onwards and its history is not retro-required to have been allocated.
A hand-written floor would be the literal ``beadloom-mr2l.72`` was filed about.

**And the floor's cost is stated, which ``beadloom-l9ee`` found it was not.**
``unclaimed-number`` passes over every entry below the floor by design, and the
verdict said nothing about how many that was. Measured on this repository on
2026-09-09: 240 entries, floor 262, so the leg entered five of them and the
report read ``No duplicate, unwritten or unclaimed number`` — a clean list over
a population 2% the size of the one its header named. CONTEXT's constraint for
this epic is that the unresolved population is part of every answer, and a
clean list is trusted and stopped at. :attr:`IssueNumberReport.entries_below_floor`
is that population, and both verdicts state it.

The same reading decides what protects an entry's BODY, which is what
``beadloom-l9ee`` was weighing. A body lost from an entry is detectable only
where a claim holds its number, because the claim is a separate file that the
loss cannot take with it — so ``unwritten-claim`` covers exactly the entries at
or above the floor, and nothing covers the 235 below it.

**What the entry grammar can and cannot decide.** An entry is a line-start
ordered-list number outside a fenced code block, which is how this log's 236
entries are written. A number stated only in a consolidated closed-entry heading
(``### Import extraction depth — #159``) is NOT an entry and does not enter the
duplicate leg — but it does enter :attr:`LogNumbers.mentioned`, so the allocator
never hands it out again. The two populations are separate because they answer
different questions, and a number below the highest that neither population
holds is reported as :attr:`LogNumbers.unaccounted` rather than as free.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The ``.beadloom/config.yml`` block that declares the log. A project that
#: declares none is not judged: the shipped flow tells an adopter to keep a UX
#: log but names no path this code could assume, and a check that guesses a path
#: turns a green project red on the upgrade that ships it.
CONFIG_KEY = "issue_log"
LOG_PATH_KEY = "path"
LEDGER_PATH_KEY = "ledger"

DUPLICATE_NUMBER = "duplicate-number"
UNWRITTEN_CLAIM = "unwritten-claim"
UNCLAIMED_NUMBER = "unclaimed-number"

#: Every leg, in report order. One list, so a summary counting findings per leg
#: cannot silently omit one.
CHECK_NAMES: tuple[str, ...] = (DUPLICATE_NUMBER, UNWRITTEN_CLAIM, UNCLAIMED_NUMBER)

#: An entry heading: a line-start ordered-list number. Deliberately not a
#: heading level or a bold span — this is the grammar the log is written in, and
#: a second accepted spelling is a second thing that can disagree.
_ENTRY_RE = re.compile(r"^(\d{1,6})\.\s+(.*)$")

#: A number REFERRED to, and only where it is THIS log's number. Wider than an
#: entry on purpose — the allocator's floor must never be lowered by a spelling
#: it failed to recognise — but not so wide that it crosses a tracker boundary.
#: A ``#`` glued to the end of a name refers to somebody else's tracker
#: (``anthropics/claude-code#32163``), and reading that as a number in use here
#: is BDL-UX #253's class in a second place: a token attributed to a named
#: subject, read as a claim about ours. Measured by dogfooding: the first
#: allocation this module ever performed on this repository returned #32164.
#:
#: A bare ``#59`` after a foreign noun (``PR #59``) is NOT excluded, because
#: nothing in the token attributes it. That imprecision costs a number and never
#: causes a collision, which is the direction to err in.
_MENTION_RE = re.compile(r"(?<![\w/-])#(\d{1,6})\b")

_FENCE_RE = re.compile(r"^\s*(```|~~~)")

#: The claim file's name. Zero-padded so the directory lists in numeric order,
#: which is the order a reader of the composed view expects.
_CLAIM_NAME = "{number:04d}.md"
_CLAIM_STEM_RE = re.compile(r"^(\d{1,6})$")

#: An allocation retries at the next number when the name is taken. Bounded, so
#: a filesystem that refuses every create reports instead of spinning.
_ALLOCATION_ATTEMPTS = 1000


@dataclass(frozen=True)
class Entry:
    """One numbered entry the log DEFINES, at the line that defines it."""

    number: int
    line: int
    title: str


@dataclass(frozen=True)
class LogNumbers:
    """Every number a log states, in the two populations that mean different things."""

    entries: tuple[Entry, ...]
    mentioned: frozenset[int]

    @property
    def defined(self) -> frozenset[int]:
        """The numbers an entry defines — the population the duplicate leg judges."""
        return frozenset(entry.number for entry in self.entries)

    @property
    def duplicates(self) -> tuple[int, ...]:
        """Numbers more than one entry defines, ascending."""
        seen: dict[int, int] = {}
        for entry in self.entries:
            seen[entry.number] = seen.get(entry.number, 0) + 1
        return tuple(sorted(number for number, count in seen.items() if count > 1))

    @property
    def highest(self) -> int:
        """The highest number the log states in EITHER population, or 0."""
        return max([*self.defined, *self.mentioned], default=0)

    @property
    def unaccounted(self) -> tuple[int, ...]:
        """Numbers below the highest that neither population holds.

        Reported rather than treated as free: a gap is a number this derivation
        could not see, and handing one out is how a collision is created by the
        very mechanism that exists to prevent them.
        """
        held = self.defined | self.mentioned
        return tuple(n for n in range(1, self.highest) if n not in held)


@dataclass(frozen=True)
class Claim:
    """One allocated number, held by the file whose creation allocated it."""

    number: int
    path: Path
    holder: str


@dataclass(frozen=True)
class IssueLog:
    """The declared log and the ledger that allocates its numbers."""

    log: Path
    ledger: Path


@dataclass(frozen=True)
class NumberFinding:
    """One number this check has something to say about."""

    check: str
    number: int
    where: str
    why: str
    remediation: str


@dataclass(frozen=True)
class IssueNumberReport:
    """What the three legs found, and which of them could run at all."""

    declared: bool
    findings: tuple[NumberFinding, ...] = ()
    entries: int = 0
    claims: int = 0
    floor: int | None = None
    log_missing: bool = False
    unaccounted: tuple[int, ...] = ()

    #: Entries strictly below the ledger's floor — the population
    #: ``unclaimed-number`` passes over, stated because the verdict otherwise
    #: reads as a clean bill over every entry the log holds. Kept 0 when there
    #: is no floor at all: :attr:`not_verified` is that case's one home, and two
    #: statements of one fact are two things that can disagree.
    entries_below_floor: int = 0

    @property
    def passed(self) -> bool:
        """No finding. A leg that could not run does not make this ``False``."""
        return not self.findings

    @property
    def not_verified(self) -> bool:
        """A leg read nothing, so a clean result would describe its ignorance.

        Two legs need a ledger with at least one claim to have a floor. Before a
        project's first allocation they enter no number at all, and reporting
        that as a pass is the shape BDL-UX #173 names.
        """
        return self.log_missing or self.floor is None


# ---------------------------------------------------------------------------
# Reading the log
# ---------------------------------------------------------------------------


def read_log_numbers(text: str) -> LogNumbers:
    """Both populations of numbers a log's text states."""
    entries: list[Entry] = []
    mentioned: set[int] = set()
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        mentioned.update(int(token) for token in _MENTION_RE.findall(line))
        if in_fence:
            continue
        match = _ENTRY_RE.match(line)
        if match is not None:
            entries.append(
                Entry(number=int(match.group(1)), line=lineno, title=match.group(2).strip())
            )
    return LogNumbers(entries=tuple(entries), mentioned=frozenset(mentioned))


# ---------------------------------------------------------------------------
# The declaration
# ---------------------------------------------------------------------------


def resolve_issue_log(project_root: Path) -> IssueLog | None:
    """The declared log and ledger, or ``None`` when the project declares none."""
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.is_file():
        return None
    import yaml

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        logger.warning("Failed to read .beadloom/config.yml for %s", CONFIG_KEY)
        return None
    if not isinstance(data, dict):
        return None
    block = data.get(CONFIG_KEY)
    if not isinstance(block, dict):
        return None
    log = block.get(LOG_PATH_KEY)
    ledger = block.get(LEDGER_PATH_KEY)
    if not isinstance(log, str) or not isinstance(ledger, str):
        logger.warning("%s needs both %r and %r", CONFIG_KEY, LOG_PATH_KEY, LEDGER_PATH_KEY)
        return None
    return IssueLog(log=project_root / log, ledger=project_root / ledger)


def _read_log(declared: IssueLog) -> LogNumbers | None:
    try:
        text = declared.log.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return read_log_numbers(text)


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------


def read_claims(ledger: Path) -> tuple[Claim, ...]:
    """Every number the ledger holds, ascending.

    The claim is the FILE NAME, so a claim whose body is unreadable still holds
    its number. Losing a number because its body was mangled is how a mangled
    file becomes a collision.
    """
    if not ledger.is_dir():
        return ()
    claims: list[Claim] = []
    for path in sorted(ledger.glob("*.md")):
        match = _CLAIM_STEM_RE.match(path.stem)
        if match is None:
            continue
        claims.append(Claim(number=int(match.group(1)), path=path, holder=_holder_of(path)))
    return tuple(sorted(claims, key=lambda claim: claim.number))


_HOLDER_RE = re.compile(r"^\*\*Holder:\*\*\s*(.+)$", re.MULTILINE)


def _holder_of(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    match = _HOLDER_RE.search(text)
    return match.group(1).strip() if match else ""


def claim_body(number: int, holder: str, *, allocated: str) -> str:
    """The claim file's body: the number, who took it, and when."""
    return (
        f"# {number}\n\n"
        f"**Allocated:** {allocated}\n"
        f"**Holder:** {holder}\n\n"
        f"> Allocated by `beadloom issue-number allocate`. The entry's text lives in the\n"
        f"> issue log until the log becomes a composed view of this directory; until then\n"
        f"> this file is the claim on the number and nothing else.\n"
    )


class AllocationExhaustedError(RuntimeError):
    """No free number after the bounded retry — the filesystem, not the numbers."""


def allocate_number(
    project_root: Path,
    *,
    holder: str,
    today: date | None = None,
) -> Claim:
    """Allocate the next issue number, atomically.

    The next candidate is one above the highest number the log states in either
    population and the highest the ledger holds, so no number already in use is
    handed out. ``os.open(O_CREAT | O_EXCL)`` decides who gets it: the loser of a
    race sees ``FileExistsError`` and retries at the next candidate.

    **The guarantee is the local filesystem's.** POSIX makes an exclusive create
    indivisible, and so does NTFS; over NFSv2 it is emulated and not guaranteed.
    It also does not span CLONES — two writers in two checkouts each allocate
    against their own ledger, and only the merge shows it. That population is
    :func:`check_issue_numbers`'s.
    """
    declared = resolve_issue_log(project_root)
    if declared is None:
        message = (
            "no issue log is declared; add an `issue_log:` block with `path:` and "
            "`ledger:` to .beadloom/config.yml"
        )
        raise ValueError(message)
    numbers = _read_log(declared)
    highest_in_log = numbers.highest if numbers is not None else 0
    claims = read_claims(declared.ledger)
    highest_claimed = max((claim.number for claim in claims), default=0)
    declared.ledger.mkdir(parents=True, exist_ok=True)
    stamp = (today or date.today()).isoformat()
    candidate = max(highest_in_log, highest_claimed) + 1
    for _ in range(_ALLOCATION_ATTEMPTS):
        path = declared.ledger / _CLAIM_NAME.format(number=candidate)
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            candidate += 1
            continue
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(claim_body(candidate, holder, allocated=stamp))
        return Claim(number=candidate, path=path, holder=holder)
    message = (
        f"no free issue number after {_ALLOCATION_ATTEMPTS} attempts from {candidate}; "
        f"the ledger at {declared.ledger} refused every exclusive create"
    )
    raise AllocationExhaustedError(message)


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------


def check_issue_numbers(project_root: Path) -> IssueNumberReport:
    """Run the three legs over the declared log and its ledger."""
    declared = resolve_issue_log(project_root)
    if declared is None:
        return IssueNumberReport(declared=False)
    numbers = _read_log(declared)
    if numbers is None:
        return IssueNumberReport(declared=True, log_missing=True)
    claims = read_claims(declared.ledger)
    log_where = declared.log.name
    findings = list(_duplicate_findings(numbers, log_where))
    floor = min((claim.number for claim in claims), default=None)
    if floor is not None:
        findings.extend(_ledger_findings(numbers, claims, floor, log_where))
    below = 0 if floor is None else sum(1 for e in numbers.entries if e.number < floor)
    return IssueNumberReport(
        declared=True,
        findings=tuple(findings),
        entries=len(numbers.entries),
        claims=len(claims),
        floor=floor,
        unaccounted=numbers.unaccounted,
        entries_below_floor=below,
    )


def _duplicate_findings(numbers: LogNumbers, log_where: str) -> list[NumberFinding]:
    findings: list[NumberFinding] = []
    for number in numbers.duplicates:
        lines = [entry.line for entry in numbers.entries if entry.number == number]
        where = ", ".join(f"{log_where}:{line}" for line in lines)
        findings.append(
            NumberFinding(
                check=DUPLICATE_NUMBER,
                number=number,
                where=where,
                why=(
                    f"{len(lines)} entries are numbered {number}, so a reference to "
                    f"#{number} names both of them and resolves to neither"
                ),
                remediation=(
                    "renumber one of them with `beadloom issue-number allocate` and "
                    "leave a forwarding line where it stood, so references already "
                    "written still land somewhere"
                ),
            )
        )
    return findings


def _ledger_findings(
    numbers: LogNumbers,
    claims: tuple[Claim, ...],
    floor: int,
    log_where: str,
) -> list[NumberFinding]:
    findings: list[NumberFinding] = []
    held = {claim.number: claim for claim in claims}
    defined = numbers.defined
    for number, claim in sorted(held.items()):
        if number in defined:
            continue
        holder = claim.holder or "nobody named"
        findings.append(
            NumberFinding(
                check=UNWRITTEN_CLAIM,
                number=number,
                where=str(claim.path.name),
                why=(
                    f"#{number} is claimed by {holder} and no entry in {log_where} "
                    f"defines it, so the number exists only where it was quoted"
                ),
                remediation=(
                    f"write the entry for #{number} into {log_where}, or delete the "
                    f"claim if the number was taken and not needed"
                ),
            )
        )
    for entry in numbers.entries:
        if entry.number < floor or entry.number in held:
            continue
        findings.append(
            NumberFinding(
                check=UNCLAIMED_NUMBER,
                number=entry.number,
                where=f"{log_where}:{entry.line}",
                why=(
                    f"#{entry.number} is at or above the ledger's floor of {floor} and "
                    f"no claim holds it, so it was read off the end of the log rather "
                    f"than allocated"
                ),
                remediation=(
                    "allocate with `beadloom issue-number allocate --holder <bead-id>` "
                    "and renumber the entry to the number it returns"
                ),
            )
        )
    return findings
