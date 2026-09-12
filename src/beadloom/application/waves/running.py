"""The work already running under a plan's work item, and which planned beads wait for it.

A wave plan decides which of the beads it was given may run at once. The beads it
is given are READY ones — ``--parent`` takes them from ``bd ready`` — and a bead in
progress is not ready, so until BDL-UX #283 a bead already running under the same
work item was never compared against the plan at all. The plan then printed
``0 serialisation(s)``, which a coordinator deciding whether to launch reads as
"nothing conflicts".

**The measured instance is this project's own epic.** In BDL-069, on 2026-09-11,
``beadloom waves --parent beadloom-rqma`` answered one clean wave for
``beadloom-8lmj`` while ``beadloom-h7b3`` was running, and naming the pair
explicitly serialised them over ``cli-commands -> agent-prime``. Both answers were
correct about the population they were given. Only one of them named its
population.

**A conflict with running work is kept apart from a serialisation within the
plan**, because the two are acted on differently. A serialisation within the plan
orders the plan's own waves; a conflict with running work means a bead the plan
places in a wave cannot start until a bead nobody is launching lands. Folding the
second into the first would put a bead the plan does not contain into its waves.

**Neither is a finding.** A serialisation is a decision the shape makes, not a
defect of it. What IS a finding is a bead known to be running that could not be
compared — its record could not be read — because then the count beside it is a
claim about part of the running work, the shape
:func:`~beadloom.application.waves.population.population_findings` reports for a
capped ready list.

**A bead that is running and has no declared scope serialises every planned bead
behind it**, for the reason :mod:`.independence` gives: an unknown scope is not an
empty one. Measured on this repository on 2026-09-11, 3 of 51 beads that have
children were ever started, so a running container is rare and is left to that
rule rather than exempted by a second one.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beadloom.application.waves.population import Population, TrackerCensus

#: The tracker's own word for a bead somebody has claimed and not yet closed.
TRACKER_IN_PROGRESS = "in_progress"

#: The one finding this module produces, named so the planner, the renderer and
#: the JSON shape cannot spell one fact three ways.
FINDING_RUNNING_NOT_COMPARED = "running_not_compared"

#: Why no running work was compared: there is no work item to look under.
RUNNING_NO_WORK_ITEM = (
    "no work item was derived for this plan, so no bead already in progress beside "
    "it could be found or compared"
)

#: Why no running work was compared although a work item was derived: the
#: tracker's rows did not say which beads are in progress. A bead whose status
#: was never observed is not a bead known to be idle.
RUNNING_STATUS_UNOBSERVED = (
    "the tracker's answer carried no status for a bead under this work item, so "
    "which of its beads are in progress was not observed"
)

#: How many ids a line spells out before it counts the rest, for the reason
#: :data:`~beadloom.application.waves.population._NAMED_LIMIT` gives.
_NAMED_LIMIT = 6


@dataclass(frozen=True)
class RunningConflict:
    """Why a planned bead cannot start while a running bead is still open.

    Oriented rather than sorted, unlike
    :class:`~beadloom.application.waves.models.Conflict`: the two sides are not
    interchangeable, and which one is running is the fact a reader acts on.
    """

    planned: str
    running: str
    reason: str
    detail: str


@dataclass(frozen=True)
class RunningWork:
    """The beads in progress under a plan's work item, and what they were compared to.

    ``reason`` is empty exactly when the running beads could be derived. A plan
    that derived none says why, so ``0 against 0 running bead(s)`` can only ever
    mean that nothing was running.
    """

    work_item: str = ""

    #: In progress under :attr:`work_item`, and not in the plan.
    in_progress: tuple[str, ...] = ()

    #: Those of :attr:`in_progress` whose record was read and held against the plan.
    compared: tuple[str, ...] = ()

    conflicts: tuple[RunningConflict, ...] = ()
    reason: str = RUNNING_NO_WORK_ITEM

    @property
    def derived(self) -> bool:
        """Whether the running beads under the work item could be derived."""
        return not self.reason

    @property
    def not_compared(self) -> tuple[str, ...]:
        """Running beads known to the tracker that no planned bead was held against."""
        return tuple(sorted(set(self.in_progress) - set(self.compared)))

    def waits_for(self, bead: str) -> tuple[str, ...]:
        """The running beads *bead* conflicts with, sorted."""
        return tuple(sorted({c.running for c in self.conflicts if c.planned == bead}))


def running_population(
    population: Population, census: TrackerCensus | None
) -> RunningWork:
    """The beads in progress under *population*'s work item that the plan does not hold.

    Derived from the same membership rule as the ready beads, so the running work
    and the ready work of one plan are two cuts of one population. ``compared``
    and ``conflicts`` are left empty: which records could be read is the caller's
    to say.
    """
    if not population.derived or census is None or census.beads is None:
        return RunningWork(reason=RUNNING_NO_WORK_ITEM)
    under = frozenset(population.under)
    statuses = {bead.bead_id: bead.status for bead in census.beads if bead.bead_id in under}
    if any(status is None for status in statuses.values()):
        return RunningWork(work_item=population.work_item, reason=RUNNING_STATUS_UNOBSERVED)
    asked = frozenset(population.asked)
    return RunningWork(
        work_item=population.work_item,
        in_progress=tuple(
            sorted(
                bead
                for bead, status in statuses.items()
                if status == TRACKER_IN_PROGRESS and bead not in asked
            )
        ),
        reason="",
    )


def running_summary(work: RunningWork) -> str:
    """The clause the plan's first line carries beside its own serialisation count."""
    if not work.derived:
        return "running work not compared"
    summary = f"{len(work.conflicts)} against {len(work.compared)} running bead(s)"
    if work.not_compared:
        summary += f" ({len(work.not_compared)} not compared)"
    return summary


def _spelled(ids: tuple[str, ...]) -> str:
    """*ids* joined, with the ones past the named limit counted rather than listed."""
    remaining = len(ids) - _NAMED_LIMIT
    tail = f" and {remaining} more" if remaining > 0 else ""
    return ", ".join(ids[:_NAMED_LIMIT]) + tail


def running_lines(work: RunningWork) -> list[str]:
    """The block naming the running work and every planned bead that waits for it.

    Beside the model for the reason
    :func:`~beadloom.application.waves.population.population_lines` is: the human
    shape quotes it, and a second wording is how two surfaces of one plan come to
    disagree.
    """
    lines = ["In progress under this plan's work item, and compared against it:"]
    if not work.derived:
        lines.append(f"  NOT COMPARED — {work.reason}")
        return lines
    if not work.in_progress:
        lines.append(f"  no bead under {work.work_item} is in progress outside this plan")
        return lines
    lines.append(
        f"  {len(work.in_progress)} in-progress bead(s) under {work.work_item} and "
        f"not in this plan: {_spelled(work.in_progress)}"
    )
    if work.not_compared:
        lines.append(
            f"  {len(work.not_compared)} could not be compared, because the tracker "
            f"gave no record of them: {_spelled(work.not_compared)}"
        )
    if work.conflicts:
        lines.append("  Serialised against running work:")
        lines.extend(
            f"    {c.planned} waits for {c.running} — {c.reason}: {c.detail}"
            for c in work.conflicts
        )
    elif work.compared:
        lines.append("  no bead of this plan conflicts with them")
    return lines


def running_findings(work: RunningWork) -> tuple[str, ...]:
    """What a reader must be told about the running work this count rests on."""
    if not work.not_compared:
        return ()
    return (
        f"{FINDING_RUNNING_NOT_COMPARED}: {len(work.not_compared)} bead(s) in "
        f"progress under {work.work_item} could not be read from the tracker "
        f"({_spelled(work.not_compared)}), so no bead of this plan was compared "
        f"against them and a bead it places in a wave may conflict with work "
        f"already running",
    )
