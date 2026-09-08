"""Creating beads without ever authoring an id, and in one process rather than N.

**BDL-UX #171 is a defect of this project's convention, not of bd's allocator.**
A bead's number is AUTHORED before creation and ALLOCATED at creation, so the two
diverge the moment anything else creates a bead in between. Measured on bd 1.0.4
(``ce242a879``): four ``bd create --parent`` launched simultaneously took ``.1``
through ``.4`` in an order that was not the launch order. The allocator is sound;
an author who writes the number first is guaranteed nothing.

**The damage is the wiring.** In BDL-061 S2 a ``bd dep add`` built from an
authored id made a different agent's bead depend on the wrong parent — a real,
valid, wrong edge. Nothing can reject it: both ids exist and the graph stays
acyclic. What caught it was that ``bd dep add`` echoes both beads' FULL TITLES,
which a human read.

**So the fix is to stop keeping the number twice**, and this module is the form
that makes an authored id impossible rather than discouraged. A plan names its
beads by KEYS the author chose, its edges name two of those keys, and the tracker
answers with the id it allocated for each. No id is written down anywhere on that
path, so there is nothing to diverge.

**What ``bd create --graph`` does and does not close, measured rather than
assumed.** It closes #171 for the path it covers, for two independent reasons:
its edges name keys, and it allocates a FLAT id (``proj-p05``) rather than a
positional one — a run racing four ``bd create --parent`` calls returned four flat
ids and consumed no number from the ``.N`` sequence those four were fighting over.
The bead that commissioned this module predicted a different reason, that a single
transaction allocates the numbers together; that is not what the measurement
shows. It closes nothing for ``bd create --parent``, which is how every
per-slice bead of this epic is created, and that path is answered by
``--json`` — the id read from bd's own answer — and by the convention this module
refuses to break.

**BDL-UX #165 is the same call form seen from the cost side.** A 60-bead DAG with
59 edges cost 34.25 s over 60 ``bd create`` processes plus 35.20 s over 59
``bd dep add`` processes, against 1.15 s in one ``bd create --graph`` process: 119
processes against one, a factor of 60 in wall clock. Speed is the consequence
here and not the driver. :data:`PLAN_THRESHOLD` is 1 because two beads imply an
edge, an edge implies an id somebody writes down, and the plan is the form where
nobody does.

**And the echo is preserved.** ``bd dep add`` still names both titles on 1.0.4 —
``✓ Added dependency: proj-027 (bead 59) depends on proj-9to (bead 60)`` — and
``bd dep add --file``, the bulk form a reader of #165 reaches for next, prints
``✓ Added 2 dependencies`` and no titles at all. The fast form of the WIRING half
destroys the only check that caught #171; the fast form of the CREATION half
removes the need for it. That is why this module plans the wiring and does not
bulk-wire, and why :mod:`.assumptions` judges ``dep add --file`` rather than
treating it as the faster spelling of the same thing.

**This module deliberately does NOT export the argv.** A helper returning
``["create", "--graph", path, "--json"]`` reads well and is invisible to
:mod:`.invocations`, which resolves a list literal passed to ``run_bd`` and
cannot follow a function call. A creation site that the derivation cannot see is
worse than an unsecured one, because it reports nothing at all — so the seam's
call forms are spelled where they are made, and this module owns the document and
the answer rather than the command line.
"""

# beadloom:component=bd-seam

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

# services -> application is the sanctioned direction. The grammar of a bead
# reference is the wave plan's, read here where a number is WRITTEN and there
# where it is compared, so the tree holds one grammar rather than two.
from beadloom.application.waves import title_references

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "EDGE_BLOCKS",
    "PLAN_SCHEMA_KEYS",
    "PLAN_THRESHOLD",
    "AuthoredNumberError",
    "PlannedBead",
    "allocated_ids",
    "created_id",
    "graph_plan",
    "plan_is_required",
]

#: The dependency type ``bd create --graph`` gives an edge that blocks.
EDGE_BLOCKS = "blocks"

#: The keys bd's graph plan accepts on a node and an edge, measured on 1.0.4. A
#: node key spelled ``parent`` rather than ``parent_id`` is SILENTLY IGNORED —
#: exit 0, no parent set — which is why this module writes the document rather
#: than leaving each caller to spell it.
PLAN_SCHEMA_KEYS = ("key", "title", "type", "priority", "parent_id", "from_key", "to_key")

#: The number of beads above which a creation goes through a plan. One, because
#: two beads imply an edge between them, an edge wired by hand implies an id
#: somebody wrote down, and a plan is the form where nobody does. The 60x wall
#: clock is the consequence of that choice and not its reason.
PLAN_THRESHOLD = 1


class AuthoredNumberError(ValueError):
    """A plan whose title states a number the tracker has not allocated yet.

    Raised rather than reported because this is a creation path and the plan has
    not run: refusing costs nothing, while a bead created with the wrong number
    in its title is a fact somebody has to notice afterwards. `beadloom waves`
    makes the same comparison after the fact, where refusing is no longer
    available.
    """


@dataclass(frozen=True)
class PlannedBead:
    """One bead of a creation plan, named by a key rather than by an id.

    ``depends_on`` holds PLAN-LOCAL KEYS and never ids, which is the whole point:
    an edge the author writes names two things the author chose, so there is no
    id to get wrong. ``parent_id`` is an id the tracker already allocated and
    answered with, which is a different fact from a number authored ahead of it.
    """

    key: str
    title: str
    bead_type: str = "task"
    priority: int | None = None
    parent_id: str = ""
    depends_on: tuple[str, ...] = field(default_factory=tuple)


def plan_is_required(bead_count: int) -> bool:
    """Whether a creation of *bead_count* beads must go through a plan."""
    return bead_count > PLAN_THRESHOLD


def _refuse_authored_numbers(beads: Sequence[PlannedBead]) -> None:
    """Raise when any planned title states a bead number, naming every one."""
    found = [
        (bead.key, reference)
        for bead in beads
        for reference in title_references(bead.title)
    ]
    if not found:
        return
    named = "; ".join(f"`{key}` is titled {reference}" for key, reference in found)
    msg = (
        f"{len(found)} planned title(s) state a bead number the tracker has not "
        f"allocated — {named}. At creation there is no id to agree with, so the "
        "number is a promise nothing can check: name the bead without it, or "
        "write the title from the id `bd create` answers with (BDL-UX #171)"
    )
    raise AuthoredNumberError(msg)


def graph_plan(beads: Sequence[PlannedBead]) -> dict[str, Any]:
    """The JSON document ``bd create --graph`` accepts for *beads*.

    Every edge names two plan keys, so the document carries no id at all unless a
    bead declares a ``parent_id`` the tracker already answered with. Empty
    optional fields are omitted rather than written as blanks, because bd reads
    the document by key presence.

    Raises :class:`AuthoredNumberError` when a title states a bead number.
    """
    _refuse_authored_numbers(beads)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for bead in beads:
        node: dict[str, Any] = {"key": bead.key, "title": bead.title, "type": bead.bead_type}
        if bead.priority is not None:
            node["priority"] = bead.priority
        if bead.parent_id:
            node["parent_id"] = bead.parent_id
        nodes.append(node)
        edges.extend(
            {"from_key": bead.key, "to_key": blocker, "type": EDGE_BLOCKS}
            for blocker in bead.depends_on
        )
    return {"nodes": nodes, "edges": edges}


def allocated_ids(stdout: str) -> dict[str, str] | None:
    """The ``key -> allocated id`` mapping bd answered a plan with.

    ``None`` when the answer could not be read, and that is not the same fact as
    a plan that created nothing: returning an empty mapping for both would turn a
    failed read into "the tracker allocated nothing", which is the collapse
    :func:`~beadloom.services.bd_seam.answers.ready_ids` refuses for the same
    reason. A caller that scrapes the human form — ``Created 4 issues`` and a
    ``dev -> proj-fac`` line per bead — reads a layout, so this reads the JSON.
    """
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    ids = parsed.get("ids")
    if not isinstance(ids, dict):
        return None
    return {str(key): str(value) for key, value in ids.items()}


def created_id(stdout: str) -> str | None:
    """The id ``bd create --json`` allocated, or ``None`` when it cannot be read.

    ``--silent`` prints the id too, and reading it means taking the last line of
    a stream whose shape is not a contract. The JSON answer names the field, so
    an upstream that adds a line above it does not silently rename this bead.
    """
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    bead_id = parsed.get("id")
    return str(bead_id) if isinstance(bead_id, str) and bead_id else None
