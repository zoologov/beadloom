"""Decide whether two beads may run at the same time, and say why not.

Independence is asked of a PAIR, and it is asked in four ways, because this
session measured that one way is not enough. Two beads are independent when
their node scopes are disjoint, when no source file belongs to both, when no
``depends_on`` edge runs between the scopes, and when both scopes could be
resolved at all. The last of those is the one an advisory tool gets wrong: a
bead that says nothing about what it touches is not independent, it is unknown,
and unknown must serialise.

What this module deliberately does NOT judge is everything a wave shares that is
not code — the tree, the commit gate, the doc baseline, the tracker's ids. Those
are not properties of a pair and cannot be made true by choosing a shape; they
are stated by :mod:`.media` instead.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.waves.models import (
    REASON_BLOCKED_BY_BEAD,
    REASON_DEPENDENCY_EDGE,
    REASON_SHARED_FILE,
    REASON_SHARED_NODE,
    REASON_UNRESOLVED_SCOPE,
    Conflict,
    sorted_pair,
)
from beadloom.infrastructure.repository import get_outgoing_edges

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Mapping, Sequence

    from beadloom.application.waves.models import BeadRecord, BeadScope

#: The edge kind that makes two subgraphs non-independent. ``part_of`` is already
#: absorbed into the scope itself (see :mod:`.scope`), and the remaining kinds
#: (``touches_code``, contracts) do not say one node's change reaches the other.
_DEPENDS_ON = "depends_on"


def _dependency_detail(
    conn: sqlite3.Connection, left: BeadScope, right: BeadScope
) -> str | None:
    """``a -> b`` for the first ``depends_on`` edge crossing the two scopes."""
    for src_scope, dst_scope in ((left, right), (right, left)):
        for ref in sorted(src_scope.refs):
            for edge in get_outgoing_edges(conn, ref):
                if edge.kind == _DEPENDS_ON and edge.dst_ref_id in dst_scope.refs:
                    return f"{ref} -> {edge.dst_ref_id}"
    return None


def conflict_between(
    conn: sqlite3.Connection,
    left: BeadScope,
    right: BeadScope,
    *,
    blockers: Mapping[str, frozenset[str]] | None = None,
) -> Conflict | None:
    """Why *left* and *right* may not run together, or ``None`` if they may.

    The reasons are tried in the order a reader would want them reported: the
    tracker's own ordering first (it outranks any judgement made here), then the
    absence of a declaration, then the three code-level overlaps from coarsest to
    finest. Only one reason is returned — the pair is already serialised, and a
    second reason would not change the shape.
    """
    first, second = sorted_pair(left.bead_id, right.bead_id)
    by_id = {left.bead_id: left, right.bead_id: right}

    if blockers:
        for blocked, blocker in ((first, second), (second, first)):
            if blocker in blockers.get(blocked, frozenset()):
                return Conflict(first, second, REASON_BLOCKED_BY_BEAD, blocker)

    unresolved = [scope for scope in (by_id[first], by_id[second]) if not scope.resolved]
    if unresolved:
        detail = ", ".join(f"{s.bead_id}: {s.unresolved}" for s in unresolved)
        return Conflict(first, second, REASON_UNRESOLVED_SCOPE, detail)

    shared_nodes = left.refs & right.refs
    if shared_nodes:
        return Conflict(first, second, REASON_SHARED_NODE, min(shared_nodes))

    shared_files = left.files & right.files
    if shared_files:
        return Conflict(first, second, REASON_SHARED_FILE, min(shared_files))

    edge = _dependency_detail(conn, left, right)
    if edge is not None:
        return Conflict(first, second, REASON_DEPENDENCY_EDGE, edge)

    return None


def conflicts_among(
    conn: sqlite3.Connection,
    scopes: Sequence[BeadScope],
    records: Sequence[BeadRecord],
) -> tuple[Conflict, ...]:
    """Every pairwise conflict among *scopes*, in a stable order."""
    blockers = {
        record.bead_id: frozenset(record.blocked_by) for record in records
    }
    present = {scope.bead_id for scope in scopes}
    blockers = {
        bead: frozenset(b for b in blocked if b in present)
        for bead, blocked in blockers.items()
    }
    ordered = sorted(scopes, key=lambda s: s.bead_id)
    found: list[Conflict] = []
    for i, left in enumerate(ordered):
        for right in ordered[i + 1 :]:
            conflict = conflict_between(conn, left, right, blockers=blockers)
            if conflict is not None:
                found.append(conflict)
    return tuple(found)
