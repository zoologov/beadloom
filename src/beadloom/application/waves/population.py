"""The beads a plan could have been about, and which of them it was not asked about.

Everything else in this package decides the HARD half from the graph: given a set
of beads, which of them may run at the same time. The set itself was the easy
half and it was authored — whatever ids the caller typed on the command line. So
the command derived what a human cannot compute and inherited what a human can
forget, and nothing could report the second, because nothing knew what should
have been present.

**The measured instance is this project's own coordinator** (BDL-UX #274).
``beadloom-0mdo.69`` could not close because three beads of BDL-068's S6 had
never been executed — ``beadloom-0mdo.78``, ``beadloom-ec1a`` and
``beadloom-iur5``. All three sat in ``bd ready --limit 0`` the whole time, and
every plan produced over that slice was internally correct: right waves, right
serialisations, all seven media measured. A plan over a subset is not a wrong
plan. It is a right plan about a smaller world.

**This is a NOTICE and never a finding, and the ratio decided that.** Measured
over BDL-068's own S6 by clustering the ``started_at`` of every bead in the
slice's population: 15 launches, and every one of the 15 was a subset of what
was ready under the slice at the moment it started, from 15 unasked ready beads
at the first launch down to 1 at the last. Two of the 15 recorded why they were
narrowed. A line that goes red on 15 of 15 real runs is a line its reader learns
to discount, which is the rule
:func:`~beadloom.application.waves.derivation.derivation_findings` already
applies to an unreadable derivation and ``docs_audit.ignore`` applies to an
intermittently-red test. Narrowing deliberately stays legitimate; what this
module changes is that the narrowing is now VISIBLE and no longer
indistinguishable from an oversight.

**One thing here can fail, and it is this report's own population rather than
the caller's.** A count of "ready beads you did not ask about" taken from a
truncated ``bd ready`` is a claim about the truncation. bd caps that answer at
100 and announces the cap on stderr only (BDL-UX #187), so an answer that was
capped makes the comparison a claim about part of the tracker, and that is
reported as a finding.

**Membership is derived from the tracker's own edges, and the parent field alone
is not enough.** Two of the three lost beads have no parent at all: they belong
to the slice because they BLOCK it. So a work item's population is its
parent-child closure plus every bead any member of that closure depends on — one
step out of the parent tree, not a transitive walk, because a blocker's own
blockers belong to that blocker's work item and not to this one. Measured on this
repository, the bounded rule over ``beadloom-0mdo.14`` returns 31 beads and holds
all three lost ones; the unbounded walk returns 110 and reaches a different
epic entirely.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

#: Why a plan compared its bead list against nothing. Not silence and not an
#: empty count: a plan whose list was held against no population has verified
#: nothing about it, the same rule that makes an unmeasured medium a finding
#: rather than a lenient pass.
POPULATION_NOT_GATHERED = (
    "this caller gathered no tracker census, so the bead list was held against "
    "no population and a bead ready under the same work item cannot be reported"
)

#: Why a census was read and still decided nothing: the beads asked about do not
#: all sit under one work item. Attributing them to the widest item that holds
#: SOME of them would report a count nobody could act on.
POPULATION_NO_COMMON_ITEM = (
    "no work item in this census contains every bead the plan was asked about, "
    "so there is no one population to hold the list against"
)

#: The one finding this module produces, named so the planner, the renderer and
#: the JSON shape cannot spell one fact three ways.
FINDING_POPULATION_PART = "population_not_whole"

#: How many unasked beads the notice spells out before it counts the rest. The
#: same limit and the same reason as
#: :data:`~beadloom.application.waves.models._NAMED_LIMIT`: the reader needs the
#: shape of the omission, not a transcript of the tracker.
_NAMED_LIMIT = 6


@dataclass(frozen=True)
class TrackerBead:
    """One bead as this derivation needs it: an id, its parent, its blockers.

    Deliberately not a tracker object and deliberately not
    :class:`~beadloom.application.waves.models.BeadRecord`, which carries what a
    bead SAYS. This carries where a bead SITS, and the two are gathered from
    different call forms — ``bd show`` per bead against one ``bd list --all``.

    ``depends_on`` holds the non-parent-child dependencies only: a parent-child
    row is a containment the :attr:`parent` field already states, and reading it
    as a blocker would put every child of an epic one step out of its own tree.
    """

    bead_id: str
    parent: str = ""
    depends_on: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TrackerCensus:
    """What the tracker says about beads this plan was not asked about.

    Both fields are ``None`` by default and ``None`` means *not observed*, the
    same convention as
    :class:`~beadloom.application.waves.models.WaveEnvironment`. A caller that
    gathers nothing gets :data:`POPULATION_NOT_GATHERED` rather than a
    comfortable zero.

    ``ready_whole`` and ``ready_note`` carry what the tracker said about its own
    answer. They are two plain fields rather than the ``bd`` seam's
    ``AnswerCoverage`` because that type lives in ``services`` and this layer
    never reaches up into it; the seam's own sentence arrives as ``ready_note``.
    """

    #: Every bead the tracker holds, however the caller widened that answer.
    beads: tuple[TrackerBead, ...] | None = None

    #: The ids the tracker's ready list named. An empty tuple is a real
    #: observation — nothing is ready — and is not the same fact as ``None``.
    ready: tuple[str, ...] | None = None

    #: Whether the ready answer covered the population the call form asked for.
    ready_whole: bool = True

    #: What the tracker said about that answer, in the seam's own words.
    ready_note: str = ""


@dataclass(frozen=True)
class Population:
    """The work item this plan belongs to, and what it did not ask about.

    ``reason`` is empty exactly when a population was derived. A plan that
    derived none says which of the two ways it failed, because "nobody gathered
    a census" and "the census contains no work item holding these beads" have
    different remedies and only one of them is the caller's.
    """

    work_item: str = ""
    asked: tuple[str, ...] = ()

    #: Every bead under :attr:`work_item`, ready or not. The denominator.
    under: tuple[str, ...] = ()

    #: Those of :attr:`under` the tracker lists as ready.
    ready_under: tuple[str, ...] = ()

    #: Ready under the same work item and absent from this plan.
    unasked: tuple[str, ...] = ()

    reason: str = POPULATION_NOT_GATHERED
    ready_whole: bool = True
    ready_note: str = ""

    @property
    def derived(self) -> bool:
        """Whether there is a population this plan's list was held against."""
        return not self.reason


def beads_under(work_item: str, beads: Sequence[TrackerBead]) -> frozenset[str]:
    """Every bead that belongs to *work_item*, by the tracker's own edges.

    The parent-child closure of *work_item*, plus every bead any member of that
    closure depends on. One step out of the parent tree and no further: a
    blocker's own blockers are that blocker's work, and following them reaches
    whatever else the tracker happens to be connected to. *work_item* itself is
    not in the result — an item is not a member of its own population.
    """
    by_id = {bead.bead_id: bead for bead in beads}
    children: dict[str, list[str]] = {}
    for bead in beads:
        if bead.parent:
            children.setdefault(bead.parent, []).append(bead.bead_id)

    tree = {work_item}
    pending = [work_item]
    while pending:
        for child in children.get(pending.pop(), ()):
            if child not in tree:
                tree.add(child)
                pending.append(child)

    found = set(tree)
    for member in tree:
        found |= by_id[member].depends_on if member in by_id else frozenset()
    found.discard(work_item)
    return frozenset(found)


def _populations(beads: Sequence[TrackerBead]) -> Mapping[str, frozenset[str]]:
    """Each candidate work item's population, computed once per census."""
    return {bead.bead_id: beads_under(bead.bead_id, beads) for bead in beads}


def _narrowest(
    asked: frozenset[str], populations: Mapping[str, frozenset[str]]
) -> str:
    """The smallest work item whose population contains every bead in *asked*.

    Smallest rather than widest, because the count is only actionable at the
    unit a wave is planned in: BDL-068's S6 slice holds 31 beads and the epic
    above it holds 94, and a plan of three beads is a subset of both. Ties are
    broken by id so one census yields one answer.
    """
    candidates = [
        (len(population), item)
        for item, population in populations.items()
        if item not in asked and asked and asked <= population
    ]
    return min(candidates)[1] if candidates else ""


def derive_population(
    asked: Sequence[str], census: TrackerCensus | None, *, work_item: str = ""
) -> Population:
    """What *census* says this plan could have been about, beside what it was.

    Never raises and never guesses: an absent census, an absent ready list and a
    bead set spanning no single work item each produce a stated reason rather
    than a count of zero.

    *work_item* is the item a caller NAMED. Passing it stops the search, because
    a caller that said ``--parent`` asked about that item and a narrower one the
    census happens to hold would answer a question nobody put.
    """
    ids = tuple(sorted(set(asked)))
    if census is None or census.beads is None or census.ready is None:
        return Population(asked=ids, reason=POPULATION_NOT_GATHERED)
    work_item = work_item or _narrowest(frozenset(ids), _populations(census.beads))
    if not work_item:
        return Population(
            asked=ids,
            reason=POPULATION_NO_COMMON_ITEM,
            ready_whole=census.ready_whole,
            ready_note=census.ready_note,
        )
    under = beads_under(work_item, census.beads)
    ready_under = under & frozenset(census.ready)
    return Population(
        work_item=work_item,
        asked=ids,
        under=tuple(sorted(under)),
        ready_under=tuple(sorted(ready_under)),
        unasked=tuple(sorted(ready_under - frozenset(ids))),
        reason="",
        ready_whole=census.ready_whole,
        ready_note=census.ready_note,
    )


def ready_under(work_item: str, census: TrackerCensus) -> tuple[str, ...] | None:
    """The ready beads under *work_item*, for a caller that states the item.

    ``None`` when the census could not answer, which is not the same fact as a
    work item with nothing ready under it — the caller decides what to do about
    each, and only one of the two is a plan of no beads.
    """
    if census.beads is None or census.ready is None:
        return None
    return tuple(sorted(beads_under(work_item, census.beads) & frozenset(census.ready)))


def population_lines(population: Population) -> list[str]:
    """The notice block: what was ready under the same work item and left out.

    Lives beside the model rather than in a renderer because the human shape and
    ``--json`` both quote it, and a second wording is how two surfaces of one
    plan come to disagree — the same reason
    :func:`~beadloom.application.gate_coverage.gate_coverage_lines` sits beside
    its own model.
    """
    lines = ["Ready under this plan's work item and not in it:"]
    if not population.derived:
        lines.append(f"  {population.reason}")
        return lines
    counted = (
        f"{len(population.ready_under)} of {len(population.under)} bead(s) under "
        f"{population.work_item} are ready"
    )
    if not population.unasked:
        lines.append(
            f"  every ready bead under {population.work_item} is in this "
            f"plan ({counted})"
        )
        return lines
    named = ", ".join(population.unasked[:_NAMED_LIMIT])
    remaining = len(population.unasked) - _NAMED_LIMIT
    tail = f" and {remaining} more" if remaining > 0 else ""
    lines.append(
        f"  {len(population.unasked)} ready bead(s) this plan was not asked "
        f"about: {named}{tail} ({counted})"
    )
    lines.append(
        "  a subset is legitimate; this line says the narrowing happened, not "
        "that it was wrong"
    )
    return lines


def population_findings(population: Population) -> tuple[str, ...]:
    """What a reader must be told about the population this count rests on.

    The count itself is never here. What can fail is the ANSWER it was taken
    from: a ready list the tracker capped makes every number above a claim about
    part of the tracker, and bd announces that cap on stderr only.
    """
    if population.ready_whole:
        return ()
    return (
        f"{FINDING_POPULATION_PART}: the ready list this plan's bead set was "
        f"held against is PART of the population — {population.ready_note}. "
        f"Every count of beads not asked about is a claim about that part and "
        f"not about the tracker",
    )
