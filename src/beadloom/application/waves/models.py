"""The wave vocabulary: what a bead declares, what serialises it, what it shares.

Types and named constants only — no decision is taken here. The decisions live in
:mod:`.scope` (what a bead occupies), :mod:`.independence` (whether two beads may
run at once), :mod:`.media` (what a wave shares no matter what the graph says)
and :mod:`.planner` (the shape itself).

Every serialisation reason is a NAMED constant rather than a sentence built at
the point of use, for the reason this epic has met four times: a verdict spelled
at its call site becomes several spellings of one fact, and then a reader cannot
tell whether two reports disagree or merely differ (BDL-UX #171, #179).
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from beadloom.graph.rules import exit_condition_deadline

if TYPE_CHECKING:
    from collections.abc import Sequence

#: The two beads' node scopes intersect — the same node, or one inside the other.
REASON_SHARED_NODE = "shared_node"

#: Distinct nodes, but the index says a source file belongs to both scopes.
REASON_SHARED_FILE = "shared_file"

#: A ``depends_on`` edge runs between the two scopes. Not independent subgraphs:
#: one bead can change what the other compiles against, mid-wave.
REASON_DEPENDENCY_EDGE = "dependency_edge"

#: One of the two beads does not say what it occupies. An unknown scope is not an
#: empty scope, so it cannot be shown independent of anything and serialises
#: against everything — the whole point of the command is that it DECIDES, and a
#: decision taken on an absent declaration would be a guess wearing a verdict.
REASON_UNRESOLVED_SCOPE = "unresolved_scope"

#: The tracker says one bead blocks the other. Ordering the tracker already owns;
#: named here so the wave shape can never contradict it in silence.
REASON_BLOCKED_BY_BEAD = "blocked_by_bead"

#: A declared override put the pair apart on purpose.
REASON_OVERRIDE_SERIAL = "override_serial"

#: Why a bead's scope could not be resolved. Two causes, kept apart because their
#: remedies differ: one bead has to say something, the other has to say something
#: TRUE.
UNRESOLVED_NO_DECLARATION = "no_declared_refs"
UNRESOLVED_UNKNOWN_REF = "ref_not_in_graph"

#: The two directions a human override may push a decision.
DECISION_PARALLEL = "parallel"
DECISION_SERIAL = "serial"
DECISIONS: tuple[str, ...] = (DECISION_PARALLEL, DECISION_SERIAL)


@dataclass(frozen=True)
class BeadRecord:
    """One bead as the planner needs it: an id, its own words, and its blockers.

    Deliberately not a tracker object. ``plan_waves`` takes these as data so the
    application layer never imports the ``bd`` seam (which lives in ``services``),
    and so every scenario runs without a ``bd`` binary on the machine.
    """

    bead_id: str
    declaration: str = ""
    blocked_by: frozenset[str] = field(default_factory=frozenset)

    #: The bead's title, held apart from the rest of its words because ONE check
    #: needs it on its own: the id a title numbers a bead with, against the id the
    #: tracker allocated (BDL-UX #171). Recovering it by slicing the first line
    #: off ``declaration`` would make the composition order of that string a
    #: second source of truth for the same fact. A caller that has no separate
    #: title leaves it empty and the check falls back to the first line, which is
    #: how the CLI composes the declaration.
    title: str = ""


@dataclass(frozen=True)
class BeadScope:
    """What one bead occupies in the graph, and what could not be resolved."""

    bead_id: str
    refs: frozenset[str]
    files: frozenset[str]
    unresolved: str | None = None
    unknown_refs: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        """True when the bead named a scope and every name was in the graph."""
        return self.unresolved is None


@dataclass(frozen=True)
class Conflict:
    """Why two beads may not run at the same time.

    ``left`` and ``right`` are stored in sorted order so a pair has one identity,
    and ``detail`` names the thing that is shared — the node, the file, the edge,
    the missing declaration — because a reason without its subject is a verdict
    nobody can act on.
    """

    left: str
    right: str
    reason: str
    detail: str


@dataclass(frozen=True)
class WaveOverride:
    """A human decision that outranks the computed one, with its exit condition.

    ``until`` may name a date or an event; which of the two it is, is decided by
    :func:`~beadloom.graph.rules.exit_condition_deadline` — the same function the
    guard exclusions and the ``forbid_import`` exemptions use, because all three
    make the identical promise and restating it here is how they would come to
    mean different things.
    """

    beads: tuple[str, ...]
    decision: str
    reason: str
    until: str

    def pairs(self) -> list[tuple[str, str]]:
        """Every unordered pair this override speaks about, in sorted order."""
        ordered = sorted(set(self.beads))
        return [
            (ordered[i], ordered[j])
            for i in range(len(ordered))
            for j in range(i + 1, len(ordered))
        ]

    def expired(self, today: date | None = None) -> bool:
        """True when ``until`` names a day and that day is behind us.

        An event-shaped exit condition is never expired: unparseable is not a
        verdict either way. The deadline names the LAST day the override covers.
        """
        deadline = exit_condition_deadline(self.until)
        return deadline is not None and deadline < (today or date.today())


@dataclass(frozen=True)
class OverrideOutcome:
    """What one override actually did to the shape.

    ``changed`` is the count of pairwise decisions it flipped. It is reported
    whether or not it is zero, because an override that excuses nothing is itself
    a finding — the same rule that makes a guard's suppressed count and a
    documentation space's excused count printable rather than implicit.
    """

    override: WaveOverride
    changed: int
    expired: bool = False

    @property
    def inert(self) -> bool:
        """True when the override changed no decision at all."""
        return self.changed == 0


@dataclass(frozen=True)
class SharedMedium:
    """Something a wave's beads share no matter how independent their code is."""

    name: str
    statement: str
    evidence: str


#: The four verdicts a medium's plan-time check can return. ``unmeasured`` is a
#: verdict of its own rather than a lenient ``passed``, because "not checked" and
#: "checked and fine" are the two answers this codebase refuses to print with one
#: word — and printing them with one word is how clause two stayed prose.
STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_UNMEASURED = "unmeasured"
STATUS_NOT_APPLICABLE = "not_applicable"

#: What the installed pre-commit hook judges, as the commit-gate check reads it.
GATE_COMMIT_SCOPED = "commit-scoped"
GATE_WHOLE_TREE = "whole-tree"
GATE_ABSENT = "absent"


@dataclass(frozen=True)
class WaveEnvironment:
    """What the machine says about the three media the graph cannot see.

    Every field is ``None`` by default and ``None`` means *not observed*. A caller
    that gathers nothing therefore gets three ``unmeasured`` checks and an exit
    code of 1, which is the intended outcome: a concurrent wave whose shared media
    nobody measured is not a clean plan, it is an unmeasured one.
    """

    #: Paths that differ from ``HEAD``, as
    #: :func:`beadloom.doc_sync.git_baseline.changed_paths` reports them.
    tree_changed_paths: tuple[str, ...] | None = None

    #: What the installed pre-commit hook judges — one of the ``GATE_*`` constants.
    commit_gate: str | None = None

    #: How many doc pairs are stale before the wave starts.
    doc_baseline_stale_pairs: int | None = None


@dataclass(frozen=True)
class MediumCheck:
    """One medium's plan-time verdict, and the measurement behind it."""

    medium: str
    status: str
    detail: str

    @property
    def is_finding(self) -> bool:
        """A failed check and an unmeasured one are both findings."""
        return self.status in (STATUS_FAILED, STATUS_UNMEASURED)


@dataclass(frozen=True)
class Wave:
    """One wave: the beads that run at once, and who measures the tree after.

    ``gate_owner`` exists because of a measured signalling failure: four agents
    each verified in a clean room, each honestly reported green, and the combined
    tree was red — nothing ran the combined tree until the coordinator did it
    last, and that step was in nobody's bead (BDL-UX #181). It is assigned
    deterministically rather than wisely; the point is that it belongs to a named
    bead instead of to a habit.
    """

    index: int
    beads: tuple[str, ...]
    gate_owner: str


@dataclass(frozen=True)
class WavePlan:
    """The decided shape, everything it rests on, and everything it did not decide."""

    waves: tuple[Wave, ...]
    scopes: tuple[BeadScope, ...]
    conflicts: tuple[Conflict, ...]
    overrides: tuple[OverrideOutcome, ...]
    shared_media: tuple[SharedMedium, ...]
    findings: tuple[str, ...]

    #: One verdict per shared medium — what turns the second half of the guarantee
    #: from a printed tuple into something that can fail. See
    #: :mod:`beadloom.application.waves.media_checks`.
    media_checks: tuple[MediumCheck, ...] = ()

    @property
    def exit_code(self) -> int:
        """0 — decided and clean; 1 — decided, with findings.

        2 is never produced here: it means the shape could not be decided at all
        (no index, no tracker answer, a ``waves:`` block that would not parse),
        and that is raised, not returned.
        """
        return 1 if self.findings else 0

    def wave_of(self, bead_id: str) -> int | None:
        """The 1-based wave a bead was placed in, or ``None`` if it was not."""
        for wave in self.waves:
            if bead_id in wave.beads:
                return wave.index
        return None


def sorted_pair(left: str, right: str) -> tuple[str, str]:
    """A pair's single identity: the two ids in sorted order."""
    return (left, right) if left <= right else (right, left)


def bead_ids(records: Sequence[BeadRecord]) -> tuple[str, ...]:
    """Every id in *records*, de-duplicated and sorted."""
    return tuple(sorted({record.bead_id for record in records}))
