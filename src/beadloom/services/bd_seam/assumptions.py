"""What each ``bd`` call form assumes about the answer, measured on one release.

**The bead this module answers had four premises and two of them were false.**
BDL-UX #194 and #237 declared ``bd merge-slot`` no exclusion primitive; it is
one, and every defect the two entries measured is a property of the call form
this project instructed (`beadloom-0mdo.39`). `beadloom-l2f2`'s premise — that the ``bd
import -i`` in the post-merge hook does not exist — is false too: it is a
documented legacy alias and it imported 137 issues at exit 0.

**And one withdrawal in this module was itself wrong, which is the sharper
lesson.** BDL-UX #97 was withdrawn here on a measurement that stayed silent while
the target was still blocked and spoke exactly when it became ready — both
directions of the OUTCOME, and one shape only. Closing `beadloom-0mdo.51`
immediately afterwards named two beads that `bd dep tree` shows blocked by four
and six open beads. Exercising both directions of one axis is not anti-vacuity
when the defect lives on another.

**The mechanism has now been characterised three times and no characterisation
survived the next measurement.** `beadloom-0mdo.51`'s correction concluded
``--suggest-next`` is silent in every shape where exactly one blocker had just
closed; `beadloom-0mdo.52` re-measured twenty-three shapes in twenty-three
SEPARATE ``bd init`` rigs — the axis .51 could not hold constant, because its ten
cells shared one — and that shape names a still-blocked bead. Sixteen of the
twenty-three are false positives, on no shape rule any of the three sessions
found. So this module records the observation and NOT the mechanism: on bd 1.0.4
``--suggest-next`` names beads that are still blocked, and ``bd ready`` was
correct in all twenty-three. A guard can be built on that. Claiming a mechanism
is what got the previous two readings wrong.

So an inherited claim is not a fact, a claim of one's own is not a fact either,
and the module records **the release every verdict was taken against**. A
derived population with no version is a measurement with no room, and an
External defect a later ``bd`` fixes must fail loudly rather than quietly guard
nothing:
``tests/test_bd_call_sites.py`` compares :data:`BD_MEASURED_VERSION` against the
``bd`` on PATH and fails when they differ, naming what has to be re-measured.

**The four verdicts, because two are not enough.** The distinction this epic has
now shipped seven times is that a site whose assumption nobody checks reads
differently from one that is checked and holding:

* :data:`VERDICT_SECURED` — the call form itself makes the assumption true.
* :data:`VERDICT_UNSECURED` — it relies on a default that measurement shows is
  narrower than the question, and a flag would fix it.
* :data:`VERDICT_HOLDS` — no flag can secure it, and it is measured TRUE on
  :data:`BD_MEASURED_VERSION`. Not a clean site: a claim pinned to a release.
* :data:`VERDICT_UNMEASURED` — a subcommand this module has not measured. An
  unjudged site must never read as a clean one.

**Measured on bd 1.0.4 (``ce242a879``), streams read separately, exit codes read
without a pipe** — the discipline itself, because merging the streams is how two
of the four premises above became bug reports against a working tool.

``bd list`` carries TWO default filters and announces exactly one of them. The
status filter omits closed beads and is silent on both streams: ``--limit 0``
alone returned 55 rows against 842 in this repository's tracker. The 50-row cap
does print ``Showing 50 issues; … Use --limit 0 for all`` — on stderr, where a
consumer that merged its streams has already destroyed its own JSON. ``--all``
lifts both, which its own help calls an override of the default filter and which
was measured: ``bd list --all --json`` returned all 842 with a silent stderr.

``bd ready`` carries the same cap at a different number and no entry records it.
Over a rig grown to 120 ready beads with ``bd create --graph`` it returned 100 and
printed ``Showing 100 of 120 ready issues.`` on stderr. This flow's own
``CLAUDE.md`` treats that answer as authoritative and every role is told to
confirm against it, which makes it the most-relied-upon assumption in the flow
and the one nothing checked.

``bd close --suggest-next`` names beads that remain blocked, so nothing on that
LINE can settle it and the flow's own instruction to confirm against ``bd ready``
is the remedy. That instruction is now checked rather than trusted: an artifact
that instructs the suggestion and names ``bd ready`` nowhere is ``unsecured``,
and the artifact is the unit because it is what a reader reads — a role core is
read on its own by the subagent it configures, so a mitigation that lives in
``CLAUDE.md`` never reaches it. Three of the four role cores were in exactly that
state when `beadloom-0mdo.52` derived them.

``bd create`` allocates the id AT creation while our title convention authors it
BEFORE: eight simultaneous ``--parent`` creates took ``.4`` through ``.11`` in an
order that was not the launch order. ``--json`` returns the allocated id, so
BDL-UX #171's second Expected item is already satisfied upstream and the fix is
ours to take. ``bd dep add`` has no ``--expect-title`` on 1.0.4, so nothing at
that call site can check that the ids name the beads intended — which is why it
is ``unsecured`` and not ``holds``.
"""

# beadloom:component=bd-seam

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

# services -> application is the sanctioned direction. The landing lock's three
# measured failures are judged in `application/waves/landing.py`, where the wave
# plan reads them; they are re-expressed here as one assumption rather than
# re-derived, so the tree holds one judgement of merge-slot and one grammar.
from beadloom.application.waves.landing import (
    DEFECT_UNKNOWN_FORM,
    LockInvocation,
    defect_detail,
    lock_sites,
)
from beadloom.services.bd_seam.invocations import MAX_SUBCOMMAND_WORDS

if TYPE_CHECKING:
    from collections.abc import Iterable

    from beadloom.services.bd_seam.invocations import BdInvocation

__all__ = [
    "ASSUMPTIONS",
    "ASSUMPTION_ALLOCATED_ID",
    "ASSUMPTION_COMPLETE_POPULATION",
    "ASSUMPTION_EXCLUSIVE_HOLD",
    "ASSUMPTION_INTENDED_ID",
    "ASSUMPTION_LEGACY_ALIAS",
    "ASSUMPTION_UNBLOCKED_IS_READY",
    "ASSUMPTION_UNMEASURED_SUBCOMMAND",
    "ASSUMPTION_UNTRUNCATED_POPULATION",
    "BD_MEASURED_VERSION",
    "LOCK_COMMAND_WORD",
    "VERDICTS",
    "VERDICT_HOLDS",
    "VERDICT_SECURED",
    "VERDICT_UNMEASURED",
    "VERDICT_UNSECURED",
    "Assumption",
    "BdCallSite",
    "CallSiteReport",
    "call_sites",
    "lock_invocations",
    "population_flags",
    "report_of",
    "subcommand_of",
]

#: The release every verdict below was measured against. Not a pin on what may
#: be installed — a statement of the room the measurement was taken in.
BD_MEASURED_VERSION = "1.0.4"

VERDICT_SECURED = "secured"
VERDICT_UNSECURED = "unsecured"
VERDICT_HOLDS = "holds"
VERDICT_UNMEASURED = "unmeasured"

#: Every verdict this module can return, worst last, so a report can sort by it.
VERDICTS: tuple[str, ...] = (
    VERDICT_SECURED,
    VERDICT_HOLDS,
    VERDICT_UNSECURED,
    VERDICT_UNMEASURED,
)

ASSUMPTION_COMPLETE_POPULATION = "complete-population"
ASSUMPTION_UNTRUNCATED_POPULATION = "untruncated-population"
ASSUMPTION_ALLOCATED_ID = "allocated-id"
ASSUMPTION_INTENDED_ID = "intended-id"
ASSUMPTION_EXCLUSIVE_HOLD = "exclusive-hold"
ASSUMPTION_UNBLOCKED_IS_READY = "unblocked-is-ready"
ASSUMPTION_LEGACY_ALIAS = "legacy-alias"
ASSUMPTION_UNMEASURED_SUBCOMMAND = "unmeasured-subcommand"

#: Every assumption this module knows how to judge.
ASSUMPTIONS: tuple[str, ...] = (
    ASSUMPTION_COMPLETE_POPULATION,
    ASSUMPTION_UNTRUNCATED_POPULATION,
    ASSUMPTION_ALLOCATED_ID,
    ASSUMPTION_INTENDED_ID,
    ASSUMPTION_EXCLUSIVE_HOLD,
    ASSUMPTION_UNBLOCKED_IS_READY,
    ASSUMPTION_LEGACY_ALIAS,
    ASSUMPTION_UNMEASURED_SUBCOMMAND,
)

#: The subcommand whose judgement lives in the application layer.
LOCK_COMMAND_WORD = "merge-slot"

#: The two assumptions that are about HOW MUCH of the tracker an answer covers,
#: as opposed to what it says about the rows it returned. :func:`population_flags`
#: is the run-time half of these, read by :mod:`.answers`.
_POPULATION_ASSUMPTIONS = frozenset(
    {ASSUMPTION_COMPLETE_POPULATION, ASSUMPTION_UNTRUNCATED_POPULATION}
)


@dataclass(frozen=True)
class _Rule:
    """One assumption a subcommand makes, and what would settle it.

    ``securing_flags`` empty means no call form can secure it, and ``measured``
    then decides between :data:`VERDICT_HOLDS` and :data:`VERDICT_UNSECURED`.
    """

    assumption: str
    securing_flags: tuple[str, ...]
    measured: bool
    detail: str
    #: The flags that make the rule APPLY at all. Empty means every invocation of
    #: the subcommand makes the assumption; ``("-i",)`` means only the call form
    #: that uses the legacy alias does.
    applies_when: tuple[str, ...] = ()
    #: A subcommand whose presence in the SAME ARTIFACT settles the assumption,
    #: for the assumptions no flag can reach. The artifact is the unit because it
    #: is what a reader reads: a role core is read on its own by the subagent it
    #: configures, so a mitigation living in ``CLAUDE.md`` does not reach it.
    confirmed_by: str = ""


def _pinned(text: str) -> str:
    """A measurement sentence, with the release it was taken on attached."""
    return f"{text} (measured on bd {BD_MEASURED_VERSION})"


_COMPLETE = _Rule(
    assumption=ASSUMPTION_COMPLETE_POPULATION,
    securing_flags=("--all", "--status", "-s"),
    measured=False,
    detail=_pinned(
        "the default omits every closed bead and says so on neither stream — "
        "`--limit 0` alone returned 55 rows against 842 in the tracker. Name the "
        "population with `--status <s>`, or take all of it with `--all`"
    ),
)

_UNTRUNCATED_LIST = _Rule(
    assumption=ASSUMPTION_UNTRUNCATED_POPULATION,
    securing_flags=("--all", "--limit", "-n"),
    measured=False,
    detail=_pinned(
        "`bd list` caps at 50 rows and announces it on STDERR, which a consumer "
        "that merged its streams has already destroyed its own JSON with. Pass "
        "`--limit 0`, or `--all`, which lifts the cap as well as the filter"
    ),
)

_UNTRUNCATED_READY = _Rule(
    assumption=ASSUMPTION_UNTRUNCATED_POPULATION,
    securing_flags=("--limit", "-n"),
    measured=False,
    detail=_pinned(
        "`bd ready` caps at 100 rows and announces it on STDERR — 100 of 135 over "
        "a rig grown past the cap. This flow calls `bd ready` authoritative and "
        "tells every role to confirm against it, so this is the assumption it "
        "relies on most. Pass `--limit 0`"
    ),
)

_ALLOCATED_ID = _Rule(
    assumption=ASSUMPTION_ALLOCATED_ID,
    securing_flags=("--json",),
    measured=False,
    detail=_pinned(
        "the id is allocated AT creation while a title convention authors it "
        "before — eight simultaneous `--parent` creates took `.4` through `.11` "
        "out of launch order. `bd create --json` returns the allocated id, which "
        "is BDL-UX #171's own Expected item and exists today"
    ),
)

_INTENDED_ID = _Rule(
    assumption=ASSUMPTION_INTENDED_ID,
    securing_flags=(),
    measured=False,
    detail=_pinned(
        "`bd dep add` accepts any two ids that exist and keeps the graph acyclic, "
        "so a mis-wired edge is well-formed. There is no `--expect-title`, so "
        "NOTHING at this call site can check it — verify the titles bd echoes, or "
        "verify with `bd dep tree` afterwards (BDL-UX #171)"
    ),
)

_UNBLOCKED_IS_READY = _Rule(
    assumption=ASSUMPTION_UNBLOCKED_IS_READY,
    securing_flags=(),
    confirmed_by="ready",
    measured=False,
    detail=_pinned(
        "BDL-UX #97 stands: `--suggest-next` names beads that are still blocked. "
        "Measured over twenty-three dependency shapes in twenty-three separate "
        "rigs, it named a still-blocked bead in sixteen, and on this repository "
        "closing `beadloom-0mdo.51` named `.55` and `.13`, which `bd dep tree` "
        "shows blocked by four and six open beads. No flag settles it, so nothing "
        "on this line can — name `bd ready` in the same artifact, which was "
        "correct in all twenty-three shapes"
    ),
)

_LEGACY_ALIAS = _Rule(
    assumption=ASSUMPTION_LEGACY_ALIAS,
    securing_flags=(),
    measured=True,
    applies_when=("-i",),
    detail=_pinned(
        "`beadloom-l2f2` records `bd import -i` as a flag that does not exist; it "
        "does. Upstream's own help calls it a legacy alias for a named file, and it "
        "imported 137 issues at exit 0. Nothing at this call site can secure an "
        "alias upstream may retire, so the verdict is pinned to the release"
    ),
)

#: Every subcommand whose behaviour has been measured. A key present with an
#: empty tuple is a subcommand measured to carry no assumption this module knows
#: how to break — a read by id, an export, a version — and that is a different
#: fact from a subcommand nobody looked at, which is why absence is not silence.
_MEASURED: dict[str, tuple[_Rule, ...]] = {
    "list": (_COMPLETE, _UNTRUNCATED_LIST),
    "ready": (_UNTRUNCATED_READY,),
    "create": (_ALLOCATED_ID,),
    "dep add": (_INTENDED_ID,),
    "close": (_UNBLOCKED_IS_READY,),
    "dep tree": (),
    "show": (),
    "comments": (),
    "comments add": (),
    "comment": (),
    "update": (),
    "export": (),
    "import": (_LEGACY_ALIAS,),
    "graph": (),
    "version": (),
}


@dataclass(frozen=True)
class Assumption:
    """One thing a call site takes for granted about bd's answer, and its verdict."""

    name: str
    verdict: str
    detail: str


@dataclass(frozen=True)
class BdCallSite:
    """One invocation, named, with what it assumes and whether anything settles it.

    ``assumptions`` is never empty: a subcommand measured to carry none is
    reported with no entries only when it is IN the measured table, and a
    subcommand outside it carries
    :data:`ASSUMPTION_UNMEASURED_SUBCOMMAND`. That is the whole point — an
    unjudged site must not read like a clean one.
    """

    source: str
    line: int
    channel: str
    text: str
    subcommand: str
    flags: tuple[str, ...]
    unresolved_arguments: int
    assumptions: tuple[Assumption, ...]

    @property
    def unsettled(self) -> tuple[Assumption, ...]:
        """The assumptions nothing at this site settles."""
        return tuple(
            a for a in self.assumptions if a.verdict in (VERDICT_UNSECURED, VERDICT_UNMEASURED)
        )


@dataclass(frozen=True)
class CallSiteReport:
    """The derived population, and the regions the derivation did not reach.

    ``unreached`` is part of the answer rather than an appendix. `beadloom-0mdo.58`
    measured the reach before this bead began: a sweep of Python source sees
    about a twentieth of the subject. A derivation that returned only what it
    found would hand a reader a clean list, and a clean list is trusted and
    stopped at.
    """

    sites: tuple[BdCallSite, ...]
    unreached: tuple[tuple[str, str], ...]
    measured_against: str

    @property
    def unsettled(self) -> tuple[BdCallSite, ...]:
        """Every site with at least one assumption nothing settles."""
        return tuple(site for site in self.sites if site.unsettled)


def subcommand_of(words: tuple[str, ...]) -> str:
    """The subcommand *words* names, longest measured form first.

    bd nests one level deep, so a two-word form is preferred when the table
    declares it — ``dep add`` is a different question from ``dep tree``. When
    neither form is measured the first word is reported, because a reader needs
    to see which command was unjudged.
    """
    if len(words) >= MAX_SUBCOMMAND_WORDS:
        pair = " ".join(words[:MAX_SUBCOMMAND_WORDS])
        if pair in _MEASURED or words[0] == LOCK_COMMAND_WORD:
            return pair
    return words[0] if words else ""


def lock_invocations(invocations: Iterable[BdInvocation]) -> tuple[LockInvocation, ...]:
    """The landing-lock invocations among *invocations*, ready for judgement.

    The bridge between the one grammar here and the one judgement in the
    application layer. Nothing else converts between them, so a merge-slot form
    is parsed once and judged once.
    """
    return tuple(
        LockInvocation(
            source=invocation.source,
            line=invocation.line,
            text=invocation.text,
            subcommand=invocation.words[1] if len(invocation.words) > 1 else "",
            flags=invocation.flags,
        )
        for invocation in invocations
        if _names_the_lock(invocation.words)
    )


def _names_the_lock(words: tuple[str, ...]) -> bool:
    """Whether *words* names a landing-lock CALL rather than the group.

    ``bd merge-slot`` with no subcommand names the command group and takes no
    slot, so it is a mention. Judging it as a lock site would report the sentence
    that DESCRIBES the primitive as a defective use of it.
    """
    return len(words) > 1 and words[0] == LOCK_COMMAND_WORD


def _lock_assumption(invocation: BdInvocation) -> Assumption:
    """The landing lock's three measured failures, as one assumption."""
    site = lock_sites(lock_invocations((invocation,)))[0]
    if not site.defects:
        return Assumption(
            name=ASSUMPTION_EXCLUSIVE_HOLD,
            verdict=VERDICT_SECURED,
            detail=_pinned(
                "the call form names its holder, so a hold names a bead and a "
                "release cannot free a neighbour's (BDL-UX #194, #237)"
            ),
        )
    verdict = (
        VERDICT_UNMEASURED if site.defects == (DEFECT_UNKNOWN_FORM,) else VERDICT_UNSECURED
    )
    return Assumption(
        name=ASSUMPTION_EXCLUSIVE_HOLD,
        verdict=verdict,
        detail=_pinned("; ".join(defect_detail(defect) for defect in site.defects)),
    )


def population_flags(subcommand: str) -> tuple[str, ...] | None:
    """The flags that widen *subcommand*'s answer to the whole population.

    ``None`` when this derivation has not measured what population the
    subcommand's answer covers — which includes every subcommand outside the
    table AND the ones in it that carry no population question, such as a read
    by id. :mod:`.answers` turns that ``None`` into
    :data:`~beadloom.services.bd_seam.answers.COVERAGE_UNCHECKED` rather than
    into a clean pass, so the two facts stay apart at run time exactly as
    :data:`VERDICT_UNMEASURED` keeps them apart at derivation time.
    """
    rules = _MEASURED.get(subcommand)
    if rules is None:
        return None
    widening: list[str] = []
    for rule in rules:
        if rule.assumption not in _POPULATION_ASSUMPTIONS:
            continue
        widening.extend(flag for flag in rule.securing_flags if flag not in widening)
    return tuple(widening) or None


def _assumptions_of(
    invocation: BdInvocation, subcommand: str, alongside: frozenset[str]
) -> tuple[Assumption, ...]:
    """Every assumption this invocation makes, with the verdict its form earns.

    *alongside* is the set of subcommands the SAME ARTIFACT invokes, which is
    what settles an assumption no flag can reach. It is the artifact and not the
    line because the artifact is the unit a reader reads.
    """
    if _names_the_lock(invocation.words):
        return (_lock_assumption(invocation),)
    rules = _MEASURED.get(subcommand)
    if rules is None:
        return (
            Assumption(
                name=ASSUMPTION_UNMEASURED_SUBCOMMAND,
                verdict=VERDICT_UNMEASURED,
                detail=_pinned(
                    f"`bd {subcommand}` is outside the subcommands this derivation "
                    "has measured, so the site is unjudged rather than clean"
                ),
            ),
        )
    found: list[Assumption] = []
    for rule in rules:
        if rule.applies_when and not any(f in invocation.flags for f in rule.applies_when):
            continue
        if any(flag in invocation.flags for flag in rule.securing_flags):
            found.append(
                Assumption(
                    name=rule.assumption,
                    verdict=VERDICT_SECURED,
                    detail=_pinned("the call form names it"),
                )
            )
            continue
        if rule.confirmed_by and rule.confirmed_by in alongside:
            found.append(
                Assumption(
                    name=rule.assumption,
                    verdict=VERDICT_SECURED,
                    detail=_pinned(
                        f"the artifact also invokes `bd {rule.confirmed_by}`, which is "
                        "the confirmation this flow's own instruction names and which "
                        "was correct in all twenty-three shapes measured. That the two "
                        "answers are actually COMPARED is not something a derivation "
                        "of call forms can see — it reads which commands an artifact "
                        "names, not what it does with them"
                    ),
                )
            )
            continue
        found.append(
            Assumption(
                name=rule.assumption,
                verdict=VERDICT_HOLDS if rule.measured else VERDICT_UNSECURED,
                detail=rule.detail,
            )
        )
    return tuple(found)


def call_sites(invocations: Iterable[BdInvocation]) -> tuple[BdCallSite, ...]:
    """Judge every invocation in *invocations* against the measured table.

    Two passes, because one assumption is a property of the ARTIFACT rather than
    of the line: the first collects which subcommands each source names, the
    second judges. A single pass could only ever secure a confirmation written
    ABOVE the call it confirms, which is a fact about ordering and not about
    what the artifact tells its reader.
    """
    read = tuple(invocations)
    alongside: dict[str, set[str]] = {}
    for invocation in read:
        alongside.setdefault(invocation.source, set()).add(subcommand_of(invocation.words))
    judged: list[BdCallSite] = []
    for invocation in read:
        subcommand = subcommand_of(invocation.words)
        judged.append(
            BdCallSite(
                source=invocation.source,
                line=invocation.line,
                channel=invocation.channel,
                text=invocation.text,
                subcommand=subcommand,
                flags=invocation.flags,
                unresolved_arguments=invocation.unresolved_arguments,
                assumptions=_assumptions_of(
                    invocation,
                    subcommand,
                    frozenset(alongside.get(invocation.source, ())),
                ),
            )
        )
    return tuple(judged)


def report_of(
    sites: Iterable[BdCallSite],
    *,
    unreached: Iterable[tuple[str, str]] = (),
) -> CallSiteReport:
    """The population and what it could not reach, in one answer."""
    return CallSiteReport(
        sites=tuple(sites),
        unreached=tuple(unreached),
        measured_against=BD_MEASURED_VERSION,
    )
