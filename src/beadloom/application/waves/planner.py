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
from beadloom.application.waves.models import (
    DECISION_PARALLEL,
    DECISION_SERIAL,
    REASON_OVERRIDE_SERIAL,
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

    from beadloom.application.waves.models import BeadRecord, WaveOverride


def _apply_overrides(
    conflicts: Sequence[Conflict],
    overrides: Sequence[WaveOverride],
    *,
    today: date | None,
) -> tuple[tuple[Conflict, ...], tuple[OverrideOutcome, ...]]:
    """The conflict set a human asked for, plus what each override did."""
    by_pair: dict[tuple[str, str], Conflict] = {
        sorted_pair(c.left, c.right): c for c in conflicts
    }
    outcomes: list[OverrideOutcome] = []
    for override in overrides:
        changed = 0
        for pair in override.pairs():
            if override.decision == DECISION_PARALLEL and pair in by_pair:
                del by_pair[pair]
                changed += 1
            elif override.decision == DECISION_SERIAL and pair not in by_pair:
                by_pair[pair] = Conflict(
                    pair[0], pair[1], REASON_OVERRIDE_SERIAL, override.reason
                )
                changed += 1
        outcomes.append(
            OverrideOutcome(
                override=override, changed=changed, expired=override.expired(today)
            )
        )
    ordered = tuple(by_pair[key] for key in sorted(by_pair))
    return ordered, tuple(outcomes)


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
    scopes: Sequence[BeadScope], outcomes: Sequence[OverrideOutcome]
) -> tuple[str, ...]:
    """Everything the plan rests on that a reader has to be told about."""
    found: list[str] = []
    for scope in scopes:
        if scope.resolved:
            continue
        detail = (
            f" ({', '.join(scope.unknown_refs)})" if scope.unknown_refs else ""
        )
        found.append(
            f"unresolved_scope: {scope.bead_id} — {scope.unresolved}{detail}; "
            "it is serialised against every bead until it declares "
            "`refs: <ref_id>`"
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
    return tuple(found)


def plan_waves(
    records: Sequence[BeadRecord],
    *,
    conn: sqlite3.Connection,
    overrides: Sequence[WaveOverride] = (),
    today: date | None = None,
) -> WavePlan:
    """Decide the wave shape for *records* against the indexed graph in *conn*."""
    scopes = resolve_scopes(conn, records)
    computed = conflicts_among(conn, scopes, records)
    conflicts, outcomes = _apply_overrides(computed, overrides, today=today)
    blockers = {
        record.bead_id: frozenset(record.blocked_by) for record in records
    }
    waves = _assign(tuple(scope.bead_id for scope in scopes), conflicts, blockers)
    widest = max((len(wave.beads) for wave in waves), default=0)
    return WavePlan(
        waves=waves,
        scopes=scopes,
        conflicts=conflicts,
        overrides=outcomes,
        shared_media=media_for(widest),
        findings=_findings(scopes, outcomes),
    )
