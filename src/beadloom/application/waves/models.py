"""The wave vocabulary: what a bead declares, what serialises it, what it shares.

Types, named constants, and the words each of them prints in — no decision about
the SHAPE is taken here. Those live in :mod:`.scope` (what a bead occupies),
:mod:`.independence` (whether two beads may run at once), :mod:`.derivation`
(whether a declaration agrees with what the work item approved), :mod:`.media`
(what a wave shares no matter what the graph says) and :mod:`.planner` (the shape
itself). Choosing which sentence a named reason prints is part of naming it, and
:func:`remedy_for` is here for the same reason the reasons are: a remedy spelled
at its call site becomes several spellings of one instruction.

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

    from beadloom.application.waves.landing import LockSite

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

#: Why a bead's scope could not be resolved. Four causes, kept apart because their
#: remedies differ: one bead has to say something, one has to say something TRUE,
#: one has to say it where a parser can see it, and one has to say it in a list.
#:
#: Every one of them SERIALISES the bead, which is the whole direction of this
#: parser: a declaration nobody can read with confidence must not widen a wave.
#: The two added by `beadloom-mr2l.83` were both silent narrowings before it — a
#: `refs:` written inside a sentence handed the bead the next word as a scope, and
#: a second ref written without a comma was dropped — and a narrower scope
#: compares INDEPENDENT of more beads than the true one does.
UNRESOLVED_NO_DECLARATION = "no_declared_refs"
UNRESOLVED_UNKNOWN_REF = "ref_not_in_graph"
UNRESOLVED_UNANCHORED = "declaration_not_at_a_line_start"
UNRESOLVED_DROPPED_NODE = "declaration_dropped_a_node"

#: How a bead's declared ref stands against the derivation its work item
#: recorded. Four answers rather than two, because "the declaration is wrong"
#: and "the derivation did not reach here" are not the same fact and only one of
#: them is anybody's fault. BDL-UX #225 is the measured case: `beadloom impact`
#: attributed a node to none of the 148 caller sites it found under ``tests/``,
#: so a ref that table never names says nothing at all about the declaration.
AXIS_AGREES = "agrees"
AXIS_RULED_OUT = "ruled_out_of_scope"
AXIS_UNDECIDED = "no_scope_decision"
AXIS_NOT_DERIVED = "not_derived"

#: An axis row the derivation found and attributed to NO node. No declaration
#: can name it and no comparison can reach it, so it is stated as compared
#: against nothing — the same shape `beadloom-0mdo.32` measured over this
#: branch's own commits, where 41 of 52 changed paths had no owning node and
#: were counted rather than passed.
AXIS_NOT_ATTRIBUTED = "not_attributed"

#: The three findings the comparison produces, named here so the planner, the
#: renderer and the JSON shape cannot spell one fact three ways.
FINDING_UNGUARDED_AXIS = "unguarded_axis"
FINDING_DECLARED_OUTSIDE = "declared_outside_the_axes"
FINDING_NOT_COMPARED = "declarations_not_compared"

#: Why a plan compared nothing when its caller gathered nothing. Not an empty
#: string and not silence: a wave whose declarations were held against no
#: derivation has verified nothing, which is the same rule that makes an
#: unmeasured medium a finding rather than a lenient pass.
AXES_NOT_GATHERED = (
    "this caller gathered no `## Axes` section, so no declaration was held "
    "against the derivation it should have been generated from"
)


@dataclass(frozen=True)
class WorkItemAxes:
    """The derivation a work item recorded, as the wave plan compares against it.

    CONTEXT Q2 decides the unit: the WORK ITEM's axes, never the claimed bead's.
    A bead may narrow freely inside them — ``beadloom-0mdo.27`` edited
    ``cli-commands`` without declaring it and that was correct, because
    ``cli-commands`` is a kept row of this epic's own table — so what is compared
    is never "did this bead leave its own refs".

    Composed at the services edge from the SAME read
    :func:`beadloom.application.declared_scope.scope_of_branch` makes for the
    commit gate, so the gate and the plan cannot come to disagree about what one
    work item approved.

    ``reason`` is present exactly when there is nothing to compare against, and
    a plan that compared nothing says so rather than reporting agreement.
    """

    work_item: str = ""
    document: str = ""
    #: What the axes were derived from, carried so a reader can re-run it.
    seed: str = ""
    #: What the derivation itself says it could not reach, verbatim. Carried
    #: because this project has measured its own derivation under-reporting
    #: (BDL-UX #225), so the report needs the derivation's own account of its
    #: limits beside the verdicts taken under them.
    unresolved: str = ""
    #: Nodes a row keeps in scope.
    kept: frozenset[str] = frozenset()
    #: Nodes the ``Derived by`` field ran over. Inside the approval by
    #: construction, exactly as :attr:`DeclaredScope.inside` has it — a work
    #: item changes the surfaces it derived its answer from.
    targets: frozenset[str] = frozenset()
    #: Nodes a row names and rules OUT of scope. The sharpest half: somebody
    #: wrote "not this one".
    ruled_out: frozenset[str] = frozenset()
    #: Nodes a row names and decides nothing about. Neither authorises nor
    #: condemns; ``axis-without-a-scope-decision`` already owns that fault and a
    #: second reporter of one fault is a second thing to keep in step.
    undecided: frozenset[str] = frozenset()
    #: Axis names whose row attributes no node.
    unattributed: tuple[str, ...] = ()
    reason: str | None = None

    @property
    def readable(self) -> bool:
        """Whether there is a recorded derivation to compare anything against."""
        return self.reason is None

    @property
    def approved(self) -> frozenset[str]:
        """Every node inside the approval by name — kept rows and targets."""
        return self.kept | self.targets

    def spell_approved(self) -> str:
        """The approved nodes as a finding spells them out."""
        names = sorted(self.approved)
        if not names:
            return "no row keeps a node in scope"
        if len(names) > _NAMED_LIMIT:
            return ", ".join(names[:_NAMED_LIMIT]) + f" and {len(names) - _NAMED_LIMIT} more"
        return ", ".join(names)


@dataclass(frozen=True)
class ScopeAgreement:
    """One thing the declaration and the derivation were held against each other.

    Two populations, one record, because both answer the same question and a
    reader comparing two lists would have to join them. ``ref`` is a declared
    ref id for the four :data:`AXIS_AGREES`-family verdicts, and an AXIS NAME
    for :data:`AXIS_NOT_ATTRIBUTED`, where there is no node to name and that is
    the whole finding. ``bead_id`` is empty for the latter for the same reason:
    the row belongs to the work item, not to any bead.
    """

    ref: str
    verdict: str
    detail: str
    bead_id: str = ""


@dataclass(frozen=True)
class UnguardedAxis:
    """Approved nodes a wave's beads may all reach and none of them declares.

    The measured shape of BDL-UX #232: ``beadloom-0mdo.21`` declared
    ``review-brief``, ``beadloom-0mdo.26`` declared ``mutation-scope, ci-gate``,
    both edited ``docs/services/cli.md`` — owned by a node neither named and
    kept in scope by the work item — and the pairwise verdict placed them in one
    wave with 0 findings.

    Per WAVE and not per plan, because that is the extent of what it may claim:
    the sentence is *the pairwise verdict for these beads did not compare these
    nodes*, and a wave of one bead makes no pair. Reporting the same gap over a
    plan of one bead would have printed 7 findings for every bead of this epic,
    every time — and an always-red check is an ignored check.
    """

    wave: int
    beads: tuple[str, ...]
    nodes: tuple[str, ...]


#: How many approved nodes a finding spells out before it counts the rest. The
#: reader needs the shape of the approval, not a transcript of the table — the
#: same limit and the same reason as
#: :meth:`beadloom.doc_sync.scope_check.DeclaredScope.declared`.
_NAMED_LIMIT = 6


#: What to do about each unresolved reason, in the words the finding prints. A
#: reason without a remedy is a verdict a reader cannot act on, and the four
#: remedies genuinely differ, so one sentence for all four would be wrong three
#: times.
#:
#: **Two of them are not decided by the cause alone, so they are not here.** See
#: :func:`remedy_for`, which is what every caller spends: this dict is the base
#: text for the two causes whose remedy really is one sentence, and the function
#: owns the two that depend on what else is known.
UNRESOLVED_REMEDIES: dict[str, str] = {
    UNRESOLVED_NO_DECLARATION: (
        "declare `refs: <ref_id>` on a line of its own"
    ),
    UNRESOLVED_UNKNOWN_REF: (
        "name a ref the graph has, or add the node — `refs: <ref_id>`"
    ),
    UNRESOLVED_UNANCHORED: (
        "a `refs:` token appears in the text but never at the start of a line, "
        "and this check cannot tell a declaration written mid-sentence from "
        "prose ABOUT declarations. If it is a declaration, move it to the start "
        "of its own line. If it is prose — which is how a bead that declares no "
        "scope on purpose says so — nothing needs moving, and promoting the "
        "sentence would author the scope this check exists to derive"
    ),
    UNRESOLVED_DROPPED_NODE: (
        "separate the names with a comma — `refs: <ref_id>, <ref_id>`; only the "
        "first word of a list item is read, so the rest was thrown away"
    ),
}

#: What is said when the reason is not one this module knows.
UNKNOWN_REMEDY = "declare `refs: <ref_id>`"


def remedy_for(unresolved: str | None, *, axes: WorkItemAxes | None = None) -> str:
    """What to do about *unresolved*, given everything else that is known.

    A dict lookup was the whole of this until BDL-UX #234, and it printed one
    sentence per cause while the cause itself has sub-cases. ``beadloom-nn4c``
    declares no scope deliberately and explains why in prose; the parser matched
    the ``refs:`` inside that explanation, reported
    :data:`UNRESOLVED_UNANCHORED` correctly, and then told its reader to promote
    the sentence to a real declaration — which would have manufactured exactly
    the authored scope BDL-UX #232 is filed against. Where the two sub-cases
    cannot be told apart, both are stated and the ambiguity is stated with them;
    where the answer depends on something outside the cause, that something is
    read here rather than guessed at the call site.
    """
    if unresolved == UNRESOLVED_NO_DECLARATION and axes is not None and axes.readable:
        # The remedy is not "write a line" but "generate it from the document",
        # which is CONTEXT Q1's direction: the axes are derived, the document
        # records them, and the bead's `refs:` comes from the document.
        return (
            f"generate `refs:` from the `## Axes` section of {axes.document} — "
            f"{axes.work_item} approves {len(axes.approved)} node(s) "
            f"({axes.spell_approved()})"
        )
    return UNRESOLVED_REMEDIES.get(unresolved or "", UNKNOWN_REMEDY)


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

    #: The ref ids the bead's own words named, before ``part_of`` expanded them.
    #: Held apart from :attr:`refs` because the two answer different questions:
    #: the expansion decides what the bead OCCUPIES, and the declaration is what
    #: CONTEXT Q1 says is generated from the work item's document — so it is the
    #: declaration, not its closure, that the recorded derivation is compared
    #: against. Comparing the closure would report every component of a domain a
    #: bead named as a ref its author never wrote.
    declared: tuple[str, ...] = ()

    #: Words the declaration named that the parser did not read as refs AND that
    #: the graph does have as nodes. Held rather than discarded because that is
    #: the difference between a scope that was narrowed in silence and one that
    #: says so: a word the graph cannot confirm is prose, a word it can confirm
    #: is a ref the bead declared and this parser threw away.
    dropped_refs: tuple[str, ...] = ()

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
    """What the machine says about the four media the graph cannot see.

    Every field is ``None`` by default and ``None`` means *not observed*. A caller
    that gathers nothing therefore gets four ``unmeasured`` checks and an exit
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

    #: Every place this project's flow artifacts instruct the landing lock, as
    #: :func:`beadloom.application.waves.landing.lock_sites` derives them. An
    #: empty tuple is a real observation — somebody read the artifacts and the
    #: lock is instructed nowhere — and is not the same fact as ``None``.
    landing_lock_sites: tuple[LockSite, ...] | None = None


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

    #: The derivation every declaration above was held against, or the reason
    #: there was none. Never absent: a plan that compared nothing says so.
    axes: WorkItemAxes = field(default_factory=lambda: WorkItemAxes(reason=AXES_NOT_GATHERED))

    #: One verdict per declared ref, plus one per axis row naming no node.
    agreements: tuple[ScopeAgreement, ...] = ()

    #: Per wave, the approved nodes none of its beads declares. Empty for a wave
    #: of one, which makes no pair and therefore claims nothing about one.
    unguarded_axes: tuple[UnguardedAxis, ...] = ()

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
