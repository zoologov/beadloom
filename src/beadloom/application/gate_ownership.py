# beadloom:domain=application
# beadloom:component=gate-ownership
"""Who owns what a gate run found, so a red nobody owns stops training a discount.

**The defect this closes.** This project's own branch carried a red Gate across
two waves — two stale docs owned by no bead in the running plan — and every gate
owner in those waves had to be told by the coordinator, by hand, that the red was
not theirs, so their reports would attribute the finding rather than discount it.
A known red trains its reader to discount the next one; the cost is never the red
itself but the work of proving a SECOND finding is real against a background that
already holds one, and this project has now paid it three times (BDL-UX #233,
#258, and here on the instrument rather than in the suite).

**The move is :mod:`beadloom.application.gate_coverage`'s, one layer over.** That
one derives what a run did NOT do from the run's own step list. This one derives
who owns what it DID find, from the index and from the tracker — and like it, it
is not a step: it has no status, and the exit code is the one the steps produced.

**Where the claim is read from, and why the other two lose.** The owner is a
BEAD the tracker reports ``in_progress`` right now, and the nodes its own
``refs:`` declare — the same population ``bead-claimed`` reads, through the same
port, resolved by the same parser the wave planner uses.

* *The work item's declared axes* answer a different question — is this change
  inside the approval — and ``scope-check`` already asks it, as a step of this
  same run. Every finding on one branch is inside one approval, so an owner
  derived from the axes names the work item, which every agent on that branch
  shares. That is not the sentence the coordinator had to write.
* *A wave's plan* names beads that have not started and beads whose wave is
  over, and it exists only where a plan was made. A plan states what SHOULD run;
  a claim states what IS running, and "is this red mine" is about the second.

**Three verdicts, because they are three different facts.** ``owned`` names the
beads. ``unowned`` says a node was derived and no claim covers it — the
interesting case, and precisely what had to be said by hand. ``unattributed``
says no node could be derived from the finding at all, which is not the same
absence and must not be read as one. A tracker that cannot answer, or a project
with no index, is a :attr:`GateOwnership.reason` on the whole report rather than
a page of ``unowned``: telling every gate owner "not yours" when nobody was asked
would be the false green this epic exists to remove, wearing the new vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.impact.boundary import GraphBoundary
from beadloom.application.waves.models import BeadRecord
from beadloom.application.waves.scope import resolve_scope
from beadloom.infrastructure.db import open_db_readonly
from beadloom.infrastructure.doc_roots import resolve_docs_dir

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence
    from pathlib import Path

    from beadloom.application.guards.contract import ClaimedBead, WorkTracker
    from beadloom.application.waves.models import BeadScope

#: A finding in the gate's shared shape. Spelled here rather than imported from
#: :mod:`beadloom.application.gate`, which imports this module.
Finding = dict[str, object]

#: A claimed bead declares the node this finding is about.
OWNED = "owned"

#: A node was derived and no bead claimed now declares it. A VERDICT, not a
#: blank: it is the answer the coordinator had to supply by hand twice.
UNOWNED = "unowned"

#: No node could be derived from the finding — it names none and its locations
#: (if any) belong to no node this index knows. A different fact from
#: :data:`UNOWNED`, and reporting the two as one would hide which of "nobody
#: claims it" and "there was nothing to claim" actually happened.
UNATTRIBUTED = "unattributed"

#: The tracker did not answer, so no claim was read at all.
NO_TRACKER = (
    "the work tracker could not be reached, so no finding of this run was held "
    "against a claim"
)

#: There is no index, so no finding could be resolved to the node it is about.
NO_INDEX = (
    "the project has no index, so no finding could be resolved to the node it is "
    "about — run `beadloom reindex`"
)

#: How many beads or paths a line spells out before it counts the rest. The
#: reader needs the shape of the attribution, not a transcript of it.
_NAMED_LIMIT = 5

#: How the node was reached, when the finding named it itself.
_NAMED_BY_FINDING = "named by the finding"


@dataclass(frozen=True)
class FindingOwner:
    """One finding, the node it is about, and the beads that claim that node."""

    rule: str
    verdict: str
    node: str | None = None
    beads: tuple[str, ...] = ()
    where: str = ""
    """How the node was reached — named by the finding, or owner of a path."""


@dataclass(frozen=True)
class UnreadClaim:
    """A claimed bead whose own declaration this run could not read as a scope.

    Carried because it qualifies every :data:`UNOWNED` verdict in the same
    report: a bead whose scope could not be read might own any of them, so
    "nobody claims this" is a statement about the claims that WERE readable.
    """

    bead_id: str
    why: str


@dataclass(frozen=True)
class GateOwnership:
    """What a gate run found, held against the beads claimed while it ran."""

    owners: tuple[FindingOwner, ...] = ()
    """One entry per finding, in the run's finding order."""

    claimed: tuple[str, ...] = ()
    """The bead ids the tracker reported claimed, in sorted order."""

    unread: tuple[UnreadClaim, ...] = ()
    """Claimed beads whose declaration could not be read as a scope."""

    reason: str | None = None
    """Present exactly when nothing was attributed, and never with owners."""

    @property
    def owned(self) -> tuple[FindingOwner, ...]:
        """Findings a claimed bead declares the node of."""
        return tuple(o for o in self.owners if o.verdict == OWNED)

    @property
    def unowned(self) -> tuple[FindingOwner, ...]:
        """Findings whose node no bead claimed now declares."""
        return tuple(o for o in self.owners if o.verdict == UNOWNED)

    @property
    def unattributed(self) -> tuple[FindingOwner, ...]:
        """Findings no node could be derived from."""
        return tuple(o for o in self.owners if o.verdict == UNATTRIBUTED)

    @property
    def none_owned(self) -> bool:
        """True when findings were attributed and not one of them is owned.

        The sentence a gate owner needs, and the one a coordinator wrote by hand:
        the run is red and none of it belongs to a bead running now. False when
        there was nothing to attribute or nobody was asked, because neither of
        those is that sentence.
        """
        return bool(self.owners) and not self.owned

    def by_bead(self) -> tuple[tuple[str, int], ...]:
        """Each owning bead and how many findings it owns, most first."""
        counts: dict[str, int] = {}
        for owner in self.owned:
            for bead in owner.beads:
                counts[bead] = counts.get(bead, 0) + 1
        return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def derive_gate_ownership(
    project_root: Path, *, findings: Sequence[Finding], tracker: WorkTracker
) -> GateOwnership:
    """Attribute every finding of a run to the beads claimed while it ran.

    The tracker is asked only when there is something to attribute: a green run
    has no finding to own, and a report that shells out to ``bd`` on every push
    to say nothing is a cost with no reader.
    """
    if not findings:
        return GateOwnership()
    beads = tracker.claimed_beads()
    if beads is None:
        return GateOwnership(reason=NO_TRACKER)
    database = project_root / ".beadloom" / "beadloom.db"
    try:
        connection = open_db_readonly(database)
    except FileNotFoundError:
        return GateOwnership(
            claimed=tuple(sorted(bead.id for bead in beads)), reason=NO_INDEX
        )
    try:
        return _attribute(project_root, connection, findings=findings, beads=beads)
    finally:
        connection.close()


def _attribute(
    project_root: Path,
    connection: sqlite3.Connection,
    *,
    findings: Sequence[Finding],
    beads: Sequence[ClaimedBead],
) -> GateOwnership:
    """The attribution itself, once the index and the claims are both in hand."""
    boundary = GraphBoundary(connection)
    documented = _documented_nodes(project_root, connection)
    scopes = {
        bead.id: resolve_scope(
            connection, BeadRecord(bead_id=bead.id, declaration=bead.declaration)
        )
        for bead in beads
    }
    owners = tuple(
        _owner_of(finding, boundary=boundary, documented=documented, scopes=scopes)
        for finding in findings
    )
    unread = tuple(
        UnreadClaim(bead_id=bead_id, why=scope.unresolved)
        for bead_id, scope in sorted(scopes.items())
        if scope.unresolved is not None
    )
    return GateOwnership(
        owners=owners, claimed=tuple(sorted(scopes)), unread=unread
    )


def _owner_of(
    finding: Finding,
    *,
    boundary: GraphBoundary,
    documented: dict[str, str],
    scopes: dict[str, BeadScope],
) -> FindingOwner:
    """One finding's node, and the claims that cover it."""
    rule = str(finding.get("rule", ""))
    node, where = _node_of(finding, boundary=boundary, documented=documented)
    if node is None:
        return FindingOwner(rule=rule, verdict=UNATTRIBUTED)
    claiming = tuple(
        bead_id
        for bead_id, scope in sorted(scopes.items())
        if node in scope.refs
    )
    verdict = OWNED if claiming else UNOWNED
    return FindingOwner(
        rule=rule, verdict=verdict, node=node, beads=claiming, where=where
    )


def _node_of(
    finding: Finding, *, boundary: GraphBoundary, documented: dict[str, str]
) -> tuple[str | None, str]:
    """The node a finding is about, and how it was reached.

    The finding's own ``node`` field first, because a step that already knows
    which node it is reporting on is a better source than any re-derivation —
    the linter has carried it since BDL-067 `.14` and the sync steps carry it for
    this report. Failing that, each location's path is resolved through the
    INDEX: source ownership as ``scope-check`` resolves it, then the documented
    node, since a doc is owned by no source prefix and half of this gate's
    findings are about documents.
    """
    named = finding.get("node")
    if isinstance(named, str) and named:
        return named, _NAMED_BY_FINDING
    for path in _located_paths(finding):
        owner = boundary.owner_of(path).node
        if owner is not None:
            return owner, f"owner of {path}"
        documents = documented.get(path)
        if documents is not None:
            return documents, f"documented node of {path}"
    return None, ""


def _located_paths(finding: Finding) -> list[str]:
    """Every project-relative path the finding's locations name."""
    locations = finding.get("locations")
    if not isinstance(locations, list):
        return []
    paths: list[str] = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        file = location.get("file")
        if isinstance(file, str) and file and file not in paths:
            paths.append(file)
    return paths


def _documented_nodes(
    project_root: Path, connection: sqlite3.Connection
) -> dict[str, str]:
    """Project-relative doc path -> the node that document is declared for.

    The ``docs`` table stores a path relative to the documentation root, while a
    finding carries one relative to the project. The root is read from the
    project's own configuration rather than assumed, so a project that renames
    ``docs/`` is still joined correctly.
    """
    prefix = resolve_docs_dir(project_root).strip("/")
    rows = connection.execute(
        "SELECT path, ref_id FROM docs WHERE ref_id IS NOT NULL"
    ).fetchall()
    return {
        f"{prefix}/{row['path']}" if prefix else str(row["path"]): str(row["ref_id"])
        for row in rows
    }


def gate_ownership_lines(ownership: GateOwnership) -> list[str]:
    """The human report's block: who owns what this run found.

    Beside the model rather than in a renderer, for the same reason
    :func:`beadloom.application.gate_coverage.gate_coverage_lines` is: three
    formats and one MCP tool quote it, and a second wording is how two surfaces
    of one run come to disagree.
    """
    if ownership.reason is not None:
        return ["Findings by owner:", f"  {ownership.reason}"]
    if not ownership.owners:
        return []
    lines = ["Findings by owner:"]
    for bead, count in ownership.by_bead():
        lines.append(f"  {bead} — {count} finding(s)")
    lines.extend(_unowned_lines(ownership))
    if ownership.unattributed:
        lines.append(
            f"  {UNATTRIBUTED} — {len(ownership.unattributed)} finding(s): no node "
            "could be derived from them, so no claim could cover them"
        )
    lines.extend(_unread_lines(ownership))
    return lines


def _unowned_lines(ownership: GateOwnership) -> list[str]:
    """The unowned count, and the headline when nothing at all is owned."""
    if not ownership.unowned:
        return []
    nodes = sorted({owner.node for owner in ownership.unowned if owner.node})
    named = ", ".join(nodes[:_NAMED_LIMIT])
    if len(nodes) > _NAMED_LIMIT:
        named += f" and {len(nodes) - _NAMED_LIMIT} more"
    lines = [
        f"  {UNOWNED} — {len(ownership.unowned)} finding(s): no bead claimed now "
        f"declares the node that owns them ({named})"
    ]
    if ownership.none_owned:
        lines.append(
            "  no finding of this run is owned by a bead claimed now"
            f" ({_claimed_clause(ownership)})"
        )
    return lines


def _claimed_clause(ownership: GateOwnership) -> str:
    """Which claims the report was actually held against."""
    if not ownership.claimed:
        return "no bead is claimed"
    named = ", ".join(ownership.claimed[:_NAMED_LIMIT])
    if len(ownership.claimed) > _NAMED_LIMIT:
        named += f" and {len(ownership.claimed) - _NAMED_LIMIT} more"
    return f"claimed: {named}"


def _unread_lines(ownership: GateOwnership) -> list[str]:
    """The claims whose own words could not be read, and what that costs."""
    if not ownership.unread:
        return []
    named = ", ".join(
        f"{claim.bead_id} ({claim.why})" for claim in ownership.unread[:_NAMED_LIMIT]
    )
    if len(ownership.unread) > _NAMED_LIMIT:
        named += f" and {len(ownership.unread) - _NAMED_LIMIT} more"
    return [
        f"  {len(ownership.unread)} of {len(ownership.claimed)} claimed bead(s) "
        f"declare a scope this run could not read, so `{UNOWNED}` is not a proof "
        f"that nobody owns it: {named}"
    ]
