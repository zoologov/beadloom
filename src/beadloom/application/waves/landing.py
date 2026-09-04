"""The lock a wave's landings are told to take, and what that call form grants.

**The measurement this module is built on, taken on bd 1.0.4 (``ce242a879``) in
an isolated ``bd init`` rig, every exit code read without a pipe.** BDL-UX #194
and #237 are one defect filed twice, nine days apart, by two agents that had
never met, and both entries name ``bd merge-slot`` as the broken thing. It is
not the broken thing:

* ``acquire`` on a free slot exits 0; on a held slot it exits **1** and names the
  holder. Four rounds of eight simultaneous ``acquire`` calls produced exactly
  one winner in every round, so the acquire IS mutually exclusive under
  contention on one machine.
* ``release --holder <name>`` is owner-checked — it exits 1 with ``slot held by
  alice, not bob``. A bare ``release`` is not, and frees whoever holds it.
* ``--holder`` accepts any string, so a BEAD id can hold the slot today, and
  ``check --json`` reports it back.

What grants nothing is the CALL FORM this project instructs, and each of its
three defects is ours:

* an ``acquire`` with no ``--holder`` takes the tracker actor
  (``$BEADS_ACTOR`` → ``git user.name`` → ``$USER``), which is ONE identity for
  every role in a repository, so the holder cannot be told from the claimant and
  an agent re-reading its own hold is refused as if a neighbour held it;
* a bare ``release`` is the one form bd does not check, so an agent frees a
  neighbour's hold and is told it succeeded (#194's second defect, reproduced);
* ``--wait`` appends the caller to a queue that nothing drains and returns
  without blocking. Upstream's own help says so — *"Add to waiters list if slot
  is held"* — while this project's prose said it *"blocks/queues until the slot
  is free"*, and an agent that believes our sentence never looks at the exit
  code. The queue on this repository's own slot holds five identities from
  sessions that ended.

**So the derivation here is over what a wave is TOLD, not over what bd does.**
It reads the flow artifacts an agent is handed and reports, per call site,
which of those three the site walks into. That is CONTEXT Q4 applied literally:
an external finding is answered by deriving our own call sites and asserting
each one's behaviour, never by a wrapper.

**Over a shape, not a spelling.** A site is any invocation of the lock, whatever
surrounds it, and the verdict comes from the FLAGS of that invocation rather
than from the prose around it. Reading the prose for a promise ("blocks until
free") would be the keyword-proximity class this project has already filed three
times against the docs audit. The cost of that choice is stated rather than
hidden: a subcommand this module has not measured is reported as
:data:`DEFECT_UNKNOWN_FORM`, because an unjudged site that reads as a clean one
is the defect the whole epic exists to remove.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = [
    "DEFECTS",
    "DEFECT_ANONYMOUS_HOLDER",
    "DEFECT_QUEUE_ONLY_WAIT",
    "DEFECT_UNGUARDED_RELEASE",
    "DEFECT_UNKNOWN_FORM",
    "HOLDER_FLAG",
    "LOCK_COMMAND",
    "WAIT_FLAG",
    "LockSite",
    "defect_detail",
    "lock_sites",
]

#: The command this module is about, spelled once so a rename reddens one place.
LOCK_COMMAND = "bd merge-slot"

#: The flag that decides both answerable questions: who holds the slot, and
#: whether bd will refuse a release from anyone else.
HOLDER_FLAG = "--holder"

#: The flag whose name promises the one thing it does not do.
WAIT_FLAG = "--wait"

DEFECT_ANONYMOUS_HOLDER = "anonymous-holder"
DEFECT_UNGUARDED_RELEASE = "unguarded-release"
DEFECT_QUEUE_ONLY_WAIT = "queue-only-wait"
DEFECT_UNKNOWN_FORM = "unknown-form"

#: Every defect this derivation can report, in the order a call site meets them.
DEFECTS: tuple[str, ...] = (
    DEFECT_ANONYMOUS_HOLDER,
    DEFECT_QUEUE_ONLY_WAIT,
    DEFECT_UNGUARDED_RELEASE,
    DEFECT_UNKNOWN_FORM,
)

_DETAIL: dict[str, str] = {
    DEFECT_ANONYMOUS_HOLDER: (
        f"`{LOCK_COMMAND} acquire` with no `{HOLDER_FLAG}` takes the tracker "
        "actor, which is one identity for every role in a repository — the "
        f"holder cannot be told from the claimant. Pass `{HOLDER_FLAG} "
        "<bead-id>` so the holder names a bead whose claim can be checked"
    ),
    DEFECT_QUEUE_ONLY_WAIT: (
        f"`{WAIT_FLAG}` appends the caller to a queue nothing drains and returns "
        "at once with exit 1 — it does not block, and prose that says it does is "
        "what stops an agent reading the exit code. Drop it and treat a non-zero "
        "exit as *you do not hold the slot*"
    ),
    DEFECT_UNGUARDED_RELEASE: (
        f"`{LOCK_COMMAND} release` with no `{HOLDER_FLAG}` frees whoever holds "
        "the slot, including a live neighbour, and reports success. bd checks "
        f"the holder only when asked: pass `{HOLDER_FLAG} <bead-id>`"
    ),
    DEFECT_UNKNOWN_FORM: (
        f"this check has measured what `{LOCK_COMMAND} acquire`, `release`, "
        "`check` and `create` guarantee, and not this subcommand — the site is "
        "unjudged rather than clean"
    ),
}

#: One invocation of the lock: the command, its subcommand, and the flags up to
#: whatever ends the command line. The terminators are the ones a Markdown
#: instruction actually uses — a closing backtick, a comment, a pipe, a
#: separator — so a sentence continuing after the command does not become flags.
_INVOCATION = re.compile(
    r"\bbd\s+merge-slot\s+(?P<sub>[a-z][a-z-]*)(?P<flags>[^\n`|;&#]*)"
)

#: The subcommands whose behaviour was measured, and the defect each call form
#: walks into when a flag is missing. ``check`` and ``create`` read and create;
#: neither claims exclusion, so neither can be called wrongly here.
_MEASURED: dict[str, str | None] = {
    "acquire": DEFECT_ANONYMOUS_HOLDER,
    "release": DEFECT_UNGUARDED_RELEASE,
    "check": None,
    "create": None,
}


@dataclass(frozen=True)
class LockSite:
    """One place a flow artifact tells an agent to take or free the landing lock.

    ``source`` is the artifact a reader opens and ``line`` the line inside it,
    because a finding that cannot be navigated to is a finding somebody argues
    with. ``defects`` is empty for a call form that grants what it is relied on
    for, and that is the whole verdict: this type says nothing about whether the
    site is in prose, in a code fence or in a checklist.
    """

    source: str
    line: int
    invocation: str
    subcommand: str
    defects: tuple[str, ...]


def defect_detail(defect: str) -> str:
    """What *defect* costs and the move that fixes it, in one sentence."""
    return _DETAIL.get(defect, f"unrecognised defect {defect!r}")


def _defects_of(subcommand: str, flags: str) -> tuple[str, ...]:
    """Which of the measured failures this invocation walks into."""
    if subcommand not in _MEASURED:
        return (DEFECT_UNKNOWN_FORM,)
    found: list[str] = []
    missing_holder = _MEASURED[subcommand]
    if missing_holder is not None and HOLDER_FLAG not in flags:
        found.append(missing_holder)
    if WAIT_FLAG in flags:
        found.append(DEFECT_QUEUE_ONLY_WAIT)
    return tuple(found)


def lock_sites(sources: Iterable[tuple[str, str]]) -> tuple[LockSite, ...]:
    """Every landing-lock invocation in *sources*, with what its form grants.

    *sources* is ``(label, text)`` per artifact — taken as data, like every other
    observation this package's checks read, so the derivation runs without a
    repository, without a scaffolded flow and without ``bd``.

    Order is the order the artifacts were handed over and then by line, so two
    runs over one project produce the same list and a diff of two runs is a diff
    of the instructions.
    """
    found: list[LockSite] = []
    for label, text in sources:
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in _INVOCATION.finditer(line):
                subcommand = match.group("sub")
                flags = match.group("flags")
                found.append(
                    LockSite(
                        source=label,
                        line=line_number,
                        invocation=match.group(0).strip(),
                        subcommand=subcommand,
                        defects=_defects_of(subcommand, flags),
                    )
                )
    return tuple(found)
