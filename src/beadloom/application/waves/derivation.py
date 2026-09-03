"""Hold each bead's declaration against the derivation its work item recorded.

One responsibility, and the reason it is not in :mod:`.scope`: *what a bead
occupies* is a fact about the graph, while *whether the bead's own words agree
with what a human approved* is a fact about a document. Keeping them apart is
what lets the second answer be reported without the first changing — the
declaration still decides the shape, and this module says what the shape rests
on.

**Why the comparison exists at all.** Everything BDL-068 built is derived and
names the population it could not resolve; the wave planner's scope input was a
line the bead's AUTHOR wrote. So two beads that edit one document read as
independent whenever neither declaration happens to name the node that owns it,
which is not a hypothesis: ``beadloom-0mdo.21`` (``refs: review-brief``) and
``beadloom-0mdo.26`` (``refs: mutation-scope, ci-gate``) both edited
``docs/services/cli.md``, and ``beadloom waves`` reported 1 wave, 2 beads, 0
serialisations, 0 findings. In ``.21``'s words, both sets of edits survived by
luck rather than by design (BDL-UX #232).

CONTEXT Q1 decides the direction and it is not "stop reading the declaration":
the axes are DERIVED by ``beadloom impact``, the document records the derivation
and the human's scope decision, the bead's ``refs:`` is GENERATED from the
document, **and a disagreement between the three is a finding**.

**CONTEXT Q2 decides the unit — the WORK ITEM's axes, never the bead's.** A bead
may narrow freely inside them. ``beadloom-0mdo.27`` edited
``services/commands/setup.py``, node ``cli-commands``, which its own ``refs:``
does not name, and that is CORRECT because ``cli-commands`` is a kept row of this
epic's table. A check that read it as a finding would be noise on its first day.

**Three verdicts are not findings, deliberately.** A ref the table never names is
the DERIVATION not reaching, which this project has measured on itself: seeded
under ``tests/``, ``beadloom impact`` attributed a node to none of the 148 caller
sites it found (BDL-UX #225, open). An axis row attributing no node is compared
against nothing, the same shape as the 41 of 52 changed paths ``beadloom-0mdo.32``
measured with no owning node. And a row nobody has ruled on is
``axis-without-a-scope-decision``'s fault, not this module's.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.waves.models import (
    AXIS_AGREES,
    AXIS_NOT_ATTRIBUTED,
    AXIS_NOT_DERIVED,
    AXIS_RULED_OUT,
    AXIS_UNDECIDED,
    FINDING_DECLARED_OUTSIDE,
    FINDING_NOT_COMPARED,
    FINDING_UNGUARDED_AXIS,
    ScopeAgreement,
    UnguardedAxis,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from beadloom.application.waves.models import BeadScope, Wave, WorkItemAxes

#: Below this, a wave makes no pair, so nothing here has anything to say about
#: it. Named rather than written as a bare ``2`` at three call sites, because the
#: number IS the argument: every finding this module produces is a sentence about
#: what a PAIRWISE verdict did not compare.
_PAIR = 2


def compare_declarations(
    scopes: Sequence[BeadScope], axes: WorkItemAxes
) -> tuple[ScopeAgreement, ...]:
    """Every declared ref, and every unattributed axis row, with its verdict.

    Returns nothing at all when there is no derivation to compare against: an
    empty list of agreements beside a stated reason is the honest pair, and a
    list of ``agrees`` taken against an absent table would be the false green
    this epic exists to remove.
    """
    if not axes.readable:
        return ()
    found: list[ScopeAgreement] = [
        _agreement(scope.bead_id, ref, axes)
        for scope in scopes
        for ref in scope.declared
    ]
    found.extend(
        ScopeAgreement(
            ref=axis,
            verdict=AXIS_NOT_ATTRIBUTED,
            detail=(
                f"the row for `{axis}` attributes no node, so no declaration can "
                "name it and no bead's scope was compared against it"
            ),
        )
        for axis in axes.unattributed
    )
    return tuple(found)


def _agreement(bead_id: str, ref: str, axes: WorkItemAxes) -> ScopeAgreement:
    """Where one declared ref stands against the work item's recorded table."""
    if ref in axes.approved:
        return ScopeAgreement(
            ref=ref,
            verdict=AXIS_AGREES,
            detail=f"{axes.work_item} keeps `{ref}` in scope",
            bead_id=bead_id,
        )
    if ref in axes.ruled_out:
        return ScopeAgreement(
            ref=ref,
            verdict=AXIS_RULED_OUT,
            detail=f"{axes.work_item} rules `{ref}` OUT of scope",
            bead_id=bead_id,
        )
    if ref in axes.undecided:
        return ScopeAgreement(
            ref=ref,
            verdict=AXIS_UNDECIDED,
            detail=(
                f"the row for `{ref}` records no scope decision, so it neither "
                "authorises this declaration nor condemns it"
            ),
            bead_id=bead_id,
        )
    return ScopeAgreement(
        ref=ref,
        verdict=AXIS_NOT_DERIVED,
        detail=(
            f"no row of {axes.document} names `{ref}` — the derivation did not "
            "reach it, which is not the same as the declaration being wrong"
        ),
        bead_id=bead_id,
    )


def unguarded_axes(
    waves: Sequence[Wave], scopes: Sequence[BeadScope], axes: WorkItemAxes
) -> tuple[UnguardedAxis, ...]:
    """Per concurrent wave, the approved nodes none of its beads declares.

    Measured against the ``part_of`` EXPANSION rather than the declaration, and
    the two directions are deliberate: a bead declaring a domain does cover its
    components, so the containment is real coverage, while
    :func:`compare_declarations` compares the declaration itself because that is
    what CONTEXT Q1 says is generated from the document.
    """
    if not axes.readable or not axes.approved:
        return ()
    covered = {scope.bead_id: scope.refs for scope in scopes}
    gaps: list[UnguardedAxis] = []
    for wave in waves:
        if len(wave.beads) < _PAIR:
            continue
        declared = set[str]().union(
            *(covered.get(bead, frozenset()) for bead in wave.beads)
        )
        missing = tuple(sorted(axes.approved - declared))
        if missing:
            gaps.append(
                UnguardedAxis(wave=wave.index, beads=wave.beads, nodes=missing)
            )
    return tuple(gaps)


def derivation_findings(
    waves: Sequence[Wave],
    agreements: Sequence[ScopeAgreement],
    gaps: Sequence[UnguardedAxis],
    axes: WorkItemAxes,
) -> tuple[str, ...]:
    """What a reader has to be told about the declarations the shape rests on.

    Every line here speaks about a PAIR, which is why an unreadable derivation
    is reported only where the plan actually put two beads together. A plan run
    off a work-item branch legitimately has no axes, and a command that exits 1
    on every such run teaches its reader to discount it — the rule this project
    already applies to ``docs_audit.ignore`` and to an intermittently-red test.
    """
    concurrent = [wave for wave in waves if len(wave.beads) >= _PAIR]
    found = [
        f"{FINDING_DECLARED_OUTSIDE}: {agreement.bead_id} declares "
        f"`{agreement.ref}` and {agreement.detail} — the approval does not cover "
        "it, so widening the declaration is not the fix; re-derive the axes or "
        "record the decision"
        for agreement in agreements
        if agreement.verdict == AXIS_RULED_OUT
    ]
    if not axes.readable and concurrent:
        found.append(
            f"{FINDING_NOT_COMPARED}: {len(concurrent)} wave(s) place two or more "
            f"beads together and their declarations were held against no "
            f"derivation — {axes.reason}"
        )
    found.extend(
        f"{FINDING_UNGUARDED_AXIS}: wave {gap.wave} runs {', '.join(gap.beads)} "
        f"together and {axes.work_item} approves {len(gap.nodes)} node(s) none of "
        f"them declares ({', '.join(gap.nodes)}) — their pairwise verdict did not "
        f"compare those nodes, so a collision in one of them is invisible to this "
        f"plan; generate each bead's `refs:` from the `## Axes` section of "
        f"{axes.document}"
        for gap in gaps
    )
    return tuple(found)
