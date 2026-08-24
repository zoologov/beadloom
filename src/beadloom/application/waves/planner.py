"""Assign beads to waves, apply the declared overrides, and report the findings.

The shape is decided, not suggested. Given the pairwise conflicts, beads are laid
out greedily in sorted id order: each bead goes into the first wave that holds no
bead it conflicts with, and never earlier than the wave after its tracker
blockers. Greedy colouring is not optimal, and optimal is not what is wanted —
the shape has to be the SAME shape every time it is computed, so that two agents
reading the same plan act on the same decision.

A human may outrank the computation, and does so the way every other stand-down
in this codebase is recorded: as an entry carrying a reason and an exit
condition, reported with the number of decisions it actually changed. An override
that changes nothing is a finding, because an override nobody can see doing
anything is how a check gets switched off without anybody saying so.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.waves.independence import conflicts_among
from beadloom.application.waves.media import media_for
from beadloom.application.waves.media_checks import check_media, finding_for
from beadloom.application.waves.models import (
    DECISION_PARALLEL,
    DECISION_SERIAL,
    REASON_OVERRIDE_SERIAL,
    UNRESOLVED_REMEDIES,
    BeadScope,
    Conflict,
    OverrideOutcome,
    Wave,
    WavePlan,
    sorted_pair,
)
from beadloom.application.waves.scope import resolve_scopes

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Mapping, Sequence
    from datetime import date

    from beadloom.application.waves.models import (
        BeadRecord,
        MediumCheck,
        WaveEnvironment,
        WaveOverride,
    )


def _conflict_set(
    conflicts: Sequence[Conflict],
    overrides: Sequence[WaveOverride],
    present: frozenset[str],
) -> tuple[Conflict, ...]:
    """The conflict set *overrides* asks for, over the beads the plan contains.

    A ``serial`` override about a bead the plan does not contain used to CREATE a
    conflict for the absent pair, which was then printed under "Serialised
    because:" beside the real serialisations, where a reader cannot tell the two
    apart (BDL-061.22-2). A stale override left behind after its beads closed is
    the ordinary way that happens, so the pairs are restricted to beads that are
    actually here.
    """
    by_pair: dict[tuple[str, str], Conflict] = {
        sorted_pair(c.left, c.right): c for c in conflicts
    }
    for override in overrides:
        for pair in override.pairs():
            if not present.issuperset(pair):
                continue
            if override.decision == DECISION_PARALLEL:
                by_pair.pop(pair, None)
            elif override.decision == DECISION_SERIAL and pair not in by_pair:
                by_pair[pair] = Conflict(
                    pair[0], pair[1], REASON_OVERRIDE_SERIAL, override.reason
                )
    return tuple(by_pair[key] for key in sorted(by_pair))


def _together(waves: Sequence[Wave], pair: tuple[str, str]) -> bool | None:
    """Whether *pair* shares a wave; ``None`` when either bead was not placed."""
    placement = {bead: wave.index for wave in waves for bead in wave.beads}
    left, right = pair
    if left not in placement or right not in placement:
        return None
    return placement[left] == placement[right]


def _decisions_changed(
    override: WaveOverride,
    planned: Sequence[Wave],
    counterfactual: Sequence[Wave],
) -> int:
    """How many of *override*'s pairs the shape decides differently without it.

    ``changed`` used to count edits to the conflict SET, which is not the same
    question: deleting a ``blocked_by_bead`` conflict counted as a change while
    ``_earliest_wave`` put the blocked bead behind its blocker anyway, so an
    override the tracker overrules reported "changed 1 decision(s)" over a shape
    it had not moved (BDL-061.22-1). The counterfactual is leave-one-out — this
    override removed, every other one still applied — because that is the
    question a reader is asking: what would be different if this entry were gone?
    """
    return sum(
        1
        for pair in override.pairs()
        if _together(planned, pair) != _together(counterfactual, pair)
    )


def _earliest_wave(
    bead: str,
    placement: Mapping[str, int],
    blockers: Mapping[str, frozenset[str]],
) -> int:
    """The first wave index *bead* may occupy given the tracker's own ordering."""
    placed = [placement[b] for b in blockers.get(bead, frozenset()) if b in placement]
    return max(placed, default=0) + 1


def _tracker_order(
    beads: Sequence[str], blockers: Mapping[str, frozenset[str]]
) -> list[str]:
    """*beads* in an order no bead precedes one that blocks it.

    Kahn's algorithm over the blocker relation restricted to the beads actually
    asked about, with the ready set taken in sorted order so the result is one
    order rather than any valid one. A cycle cannot be laid out at all, so its
    members are appended in sorted order and the pairwise conflict between them
    keeps them in separate waves — a wrong order is still better than a silent
    drop, and the tracker is where a cycle has to be fixed.
    """
    present = set(beads)
    waiting = {
        bead: {b for b in blockers.get(bead, frozenset()) if b in present}
        for bead in beads
    }
    ordered: list[str] = []
    while True:
        ready = sorted(bead for bead, deps in waiting.items() if not deps)
        if not ready:
            break
        for bead in ready:
            ordered.append(bead)
            del waiting[bead]
        for deps in waiting.values():
            deps.difference_update(ready)
    ordered.extend(sorted(waiting))
    return ordered


def _assign(
    beads: Sequence[str],
    conflicts: Sequence[Conflict],
    blockers: Mapping[str, frozenset[str]],
) -> tuple[Wave, ...]:
    """Lay *beads* out into waves; deterministic, given the same inputs."""
    conflicting: dict[str, set[str]] = {bead: set() for bead in beads}
    for conflict in conflicts:
        conflicting.setdefault(conflict.left, set()).add(conflict.right)
        conflicting.setdefault(conflict.right, set()).add(conflict.left)

    members: dict[int, list[str]] = {}
    placement: dict[str, int] = {}
    for bead in _tracker_order(beads, blockers):
        index = _earliest_wave(bead, placement, blockers)
        while any(other in conflicting[bead] for other in members.get(index, ())):
            index += 1
        members.setdefault(index, []).append(bead)
        placement[bead] = index

    return tuple(
        Wave(
            index=position,
            beads=tuple(sorted(members[key])),
            gate_owner=sorted(members[key])[-1],
        )
        for position, key in enumerate(sorted(members), start=1)
    )


def _findings(
    scopes: Sequence[BeadScope],
    outcomes: Sequence[OverrideOutcome],
    checks: Sequence[MediumCheck],
) -> tuple[str, ...]:
    """Everything the plan rests on that a reader has to be told about."""
    found: list[str] = []
    for scope in scopes:
        if scope.resolved:
            continue
        named = scope.unknown_refs or scope.dropped_refs
        detail = f" ({', '.join(named)})" if named else ""
        remedy = UNRESOLVED_REMEDIES.get(scope.unresolved or "", "declare `refs: <ref_id>`")
        # What the finding may claim is what HAPPENED — no pairwise comparison was
        # made for this bead — not where the bead ended up. A `parallel` override
        # can legitimately place an unresolved bead beside another, and the older
        # wording ("it is serialised against every bead") was then contradicted by
        # the wave list printed beside it (BDL-061.23 M10).
        found.append(
            f"unresolved_scope: {scope.bead_id} — {scope.unresolved}{detail}; "
            f"its scope was compared with no bead's — {remedy}"
        )
    for outcome in outcomes:
        beads = ", ".join(outcome.override.beads)
        if outcome.expired:
            found.append(
                f"expired_override: [{beads}] passed its exit condition "
                f"({outcome.override.until}) and still applies"
            )
        if outcome.inert:
            found.append(
                f"inert_override: [{beads}] changed no decision — the shape is "
                "the same with it and without it"
            )
    found.extend(
        line for line in (finding_for(check) for check in checks) if line is not None
    )
    return tuple(found)


def _outcomes(
    overrides: Sequence[WaveOverride],
    *,
    computed: Sequence[Conflict],
    present: frozenset[str],
    blockers: Mapping[str, frozenset[str]],
    planned: Sequence[Wave],
    today: date | None,
) -> tuple[OverrideOutcome, ...]:
    """What each override did to the shape, measured against the shape without it."""
    ids = tuple(sorted(present))
    outcomes: list[OverrideOutcome] = []
    for index, override in enumerate(overrides):
        others = [other for position, other in enumerate(overrides) if position != index]
        without = _assign(ids, _conflict_set(computed, others, present), blockers)
        outcomes.append(
            OverrideOutcome(
                override=override,
                changed=_decisions_changed(override, planned, without),
                expired=override.expired(today),
            )
        )
    return tuple(outcomes)


def plan_waves(
    records: Sequence[BeadRecord],
    *,
    conn: sqlite3.Connection,
    overrides: Sequence[WaveOverride] = (),
    today: date | None = None,
    environment: WaveEnvironment | None = None,
) -> WavePlan:
    """Decide the wave shape for *records* against the indexed graph in *conn*.

    *environment* carries what the machine says about the media the graph cannot
    see. Leaving it out is allowed and is not silent: the media checks then come
    back ``unmeasured``, which is a finding, so a concurrent plan nobody measured
    reaches exit 1 rather than exit 0.
    """
    scopes = resolve_scopes(conn, records)
    computed = conflicts_among(conn, scopes, records)
    present = frozenset(scope.bead_id for scope in scopes)
    blockers = {record.bead_id: frozenset(record.blocked_by) for record in records}
    conflicts = _conflict_set(computed, overrides, present)
    waves = _assign(tuple(sorted(present)), conflicts, blockers)
    outcomes = _outcomes(
        overrides,
        computed=computed,
        present=present,
        blockers=blockers,
        planned=waves,
        today=today,
    )
    widest = max((len(wave.beads) for wave in waves), default=0)
    checks = check_media(
        records,
        concurrent=widest > 1,
        owned_paths=frozenset(path for scope in scopes for path in scope.files),
        environment=environment,
    )
    return WavePlan(
        waves=waves,
        scopes=scopes,
        conflicts=conflicts,
        overrides=outcomes,
        shared_media=media_for(widest),
        findings=_findings(scopes, outcomes, checks),
        media_checks=checks,
    )
