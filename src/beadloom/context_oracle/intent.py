# beadloom:domain=context-oracle
# beadloom:component=node-intent
"""Decide which recorded intent a node's context bundle carries.

``beadloom ctx <ref-id>`` is step 4 of BEFORE ANY WORK, so it is the one moment
an agent is guaranteed to ask about a node. Until this module existed it was
answered with reality alone — the node's AS-IS documentation, its symbols, its
edges — and never with the reason the code is there. That is precisely the
knowledge that stops a "fix" from deleting a deliberate behaviour.

Three decisions live here, and each is a decision rather than an implementation
detail.

Which intent belongs to a node
------------------------------
The epics that **declared** it, and nothing else. ``beadloom-mr2l.17`` measured
the alternative before building this one: scanning an epic's documents for
backticked tokens that happen to be ref ids attributed the node ``status`` to
nine epics whose prose merely used the English word. The ``Related Files``
section is a declaration, so it is what is read. Only the **focus** refs are
looked up, not the whole traversed subgraph: the subgraph reaches twenty nodes
and the question was asked about one or two of them.

The three answers, and why two of them are not one
--------------------------------------------------
:data:`INTENT_DECLARED` names the epics. :data:`INTENT_NONE_DECLARED` says the
TO-BE space was read and nothing in it declares this node — the common case, and
it carries ``epics_read`` and ``epics_declaring_nodes`` so it is a *measurement*
rather than a claim. :data:`INTENT_NOT_CHECKED` says nobody looked, with the
reason. Collapsing the last two would re-earn what this epic spent two slices on
(BDL-UX #174, #175): an absence with a stated reason is a decision, an absence
without one is a gap, and neither is evidence that no intent exists.

The cap, and why nothing is dropped by it
-----------------------------------------
A node can be named by many epics over years, and ``ctx`` has a budget it exists
to respect. At most :data:`MAX_DECLARATIONS` declarations carry their document
and line; the rest are still **named** in ``also_declared_by``, because a cap
that silently truncated would be the same defect at a smaller scale. Order is
descending natural key — a tracker allocates numbers in time order, so the
highest-numbered epic is usually the most recent statement of intent. It is a
heuristic and it is stated as one, which is the other reason the truncated
epics keep their names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

#: At least one epic's declaration names this node.
INTENT_DECLARED = "declared"

#: The TO-BE space was read and no epic in it declares this node.
INTENT_NONE_DECLARED = "none_declared"

#: Nobody read the TO-BE space, or there was nothing in it to read.
INTENT_NOT_CHECKED = "not_checked"

#: The caller built this bundle without reading the intent space.
REASON_NOT_READ = "intent_space_not_read"

#: The TO-BE space holds no document, so there was no intent to relate to.
REASON_NO_INTENT_DOCUMENTS = "no_intent_documents"

#: Documents were read and not one of them declares any node at all.
REASON_NO_EPIC_DECLARES_ANY_NODE = "no_epic_declares_any_node"

#: ``doc_roots`` could not be resolved, so the space read is not trustworthy.
REASON_CONFIG_ERROR = "doc_roots_config_error"

#: Declarations rendered in full before the rest are named without detail.
MAX_DECLARATIONS = 5

_REASON_PROSE: dict[str, str] = {
    REASON_NOT_READ: "this bundle was built without reading the intent space",
    REASON_NO_INTENT_DOCUMENTS: "the TO-BE space holds no document",
    REASON_NO_EPIC_DECLARES_ANY_NODE: "no epic declares any node, so nothing could be related",
    REASON_CONFIG_ERROR: "the doc_roots configuration could not be read",
}

_DIGITS_RE = re.compile(r"(\d+)")

#: Digit-run padding width for :func:`_natural_key`; wider than any issue number.
_PAD_WIDTH = 20


def describe_intent_reason(reason: str) -> str:
    """*reason* as prose, or the raw token when it is one this module never emits."""
    return _REASON_PROSE.get(reason, reason)


@dataclass(frozen=True)
class DeclaredIntent:
    """One epic's declaration that its intent concerns one node.

    ``document`` and ``line`` are the whole point of the record: the bundle
    **points** at the intent rather than pasting it, because a 157 KB bundle is
    not the place to inline a PRD and the reader that wants the reason can open
    the file the record names.
    """

    epic: str
    title: str | None
    document: str
    line: int
    ref_id: str


@dataclass(frozen=True)
class IntentReading:
    """What a read of the TO-BE space found, before any node is looked up.

    The counts travel with the declarations on purpose. "No epic declares this
    node" is only worth reading beside the size of the population that was
    searched — an empty answer over 61 epics and an empty answer over none are
    the same sentence about two different worlds.
    """

    declarations: tuple[DeclaredIntent, ...] = ()
    epics_read: int = 0
    epics_declaring_nodes: int = 0
    unreadable_reason: str | None = None
    """Why the space could not be read at all, or ``None`` when it was read.

    Set by the adapter for a failure it can see and the policy cannot — a
    ``doc_roots`` block that does not parse reads as an empty tree otherwise,
    and an empty tree would be reported as the honest answer to a question that
    was never actually asked.
    """


def _natural_key(text: str) -> str:
    """Sort key that orders ``ORD-31`` above ``ORD-4`` instead of below it.

    Every digit run is zero-padded to a fixed width, so the key stays a plain
    string and ordinary string comparison becomes numeric where the text is
    numeric. ``ORD-4`` beating ``ORD-31`` is what plain ordering does, and it is
    backwards for every tracker that allocates numbers in sequence.
    """
    return "".join(
        part.rjust(_PAD_WIDTH, "0") if part.isdigit() else part
        for part in _DIGITS_RE.split(text)
    )


def _sorted(declarations: list[DeclaredIntent]) -> list[DeclaredIntent]:
    """Highest natural epic key first, then by node and by declaring line.

    Two passes rather than one reversed key: reversing a compound key would
    reverse the tie-breakers too, and there is no reason to read a node's
    declarations backwards inside one epic.
    """
    by_detail = sorted(declarations, key=lambda d: (d.ref_id, d.line))
    return sorted(by_detail, key=lambda d: _natural_key(d.epic), reverse=True)


def _unchecked(reason: str, reading: IntentReading | None) -> dict[str, Any]:
    return {
        "status": INTENT_NOT_CHECKED,
        "reason": reason,
        "epics_read": reading.epics_read if reading is not None else 0,
        "epics_declaring_nodes": reading.epics_declaring_nodes if reading is not None else 0,
        "declared_by": [],
        "also_declared_by": [],
    }


def select_intent(
    reading: IntentReading | None,
    ref_ids: Sequence[str],
    *,
    limit: int = MAX_DECLARATIONS,
) -> dict[str, Any]:
    """The ``intent`` section of a context bundle for *ref_ids*.

    *reading* is ``None`` when the caller did not read the intent space, which
    is reported as :data:`INTENT_NOT_CHECKED` rather than as an absence of
    intent. Every other outcome is decided from the reading's own counts, so
    this function needs no filesystem and no index.
    """
    if reading is None:
        return _unchecked(REASON_NOT_READ, None)
    if reading.unreadable_reason is not None:
        return _unchecked(reading.unreadable_reason, reading)
    if reading.epics_read == 0:
        return _unchecked(REASON_NO_INTENT_DOCUMENTS, reading)
    if reading.epics_declaring_nodes == 0:
        return _unchecked(REASON_NO_EPIC_DECLARES_ANY_NODE, reading)

    wanted = set(ref_ids)
    matches = _sorted([d for d in reading.declarations if d.ref_id in wanted])
    shown = matches[:limit]
    omitted = matches[limit:]
    return {
        "status": INTENT_DECLARED if matches else INTENT_NONE_DECLARED,
        "reason": None,
        "epics_read": reading.epics_read,
        "epics_declaring_nodes": reading.epics_declaring_nodes,
        "declared_by": [
            {
                "epic": d.epic,
                "title": d.title,
                "document": d.document,
                "line": d.line,
                "ref_id": d.ref_id,
            }
            for d in shown
        ],
        "also_declared_by": sorted({d.epic for d in omitted}),
    }
