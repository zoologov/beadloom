# beadloom:domain=application
# beadloom:component=intent-reader
"""Read the TO-BE space's node declarations into the shape a bundle consumes.

The adapter half of the intent that ``beadloom ctx`` delivers. The join is not
re-implemented here: :func:`~beadloom.application.doc_spaces.read_epic_intents`
already reads an epic's ``Related Files`` declaration, was measured against the
unscoped alternative and rejected it, and stays the one reader of that section.
This module turns its per-epic answer into the per-node one a context bundle
needs, and adds nothing to what it read.

Why it lives in ``application`` and the policy does not
------------------------------------------------------
``context_oracle`` is a domain and ``application`` is the layer above it, so a
domain reaching up for this read would be the wrong direction. The port types
(:class:`~beadloom.context_oracle.intent.IntentReading` and
:class:`~beadloom.context_oracle.intent.DeclaredIntent`) are therefore declared
in the domain and the adapter that fills them lives here, which is the
direction ``architecture-layers`` enforces.

Why the tracker is not read
---------------------------
``read_epic_intents`` accepts bead statuses and this module passes none. Two
reasons, both measured. ``bd close`` writes only the local database, so the
committed ``.beads/issues.jsonl`` export and the live tracker disagree on a
branch — a bead status shown inside ``ctx`` would be confidently wrong exactly
where the work is happening. And the export is 2.7 MB and 15 ms to parse on this
repository, paid on every cold bundle, for a fact that does not change which
epic declared the node. The surface makes no claim about bead status rather than
a cheap wrong one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.doc_spaces import graph_facts, read_epic_intents
from beadloom.context_oracle.intent import (
    REASON_CONFIG_ERROR,
    DeclaredIntent,
    IntentReading,
)
from beadloom.infrastructure.doc_roots import resolve_doc_spaces

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def read_intent(project_root: Path, *, known_refs: frozenset[str]) -> IntentReading:
    """Every node declaration the TO-BE space of *project_root* carries.

    *known_refs* is the graph's own vocabulary: a backticked token that names no
    node is not a declaration, which is what keeps the ``Related Files`` read a
    declaration rather than a guess.
    """
    spaces = resolve_doc_spaces(project_root)
    if spaces.config_errors:
        return IntentReading(unreadable_reason=REASON_CONFIG_ERROR)

    intents = read_epic_intents(
        project_root,
        spaces=spaces,
        known_refs=known_refs,
        beads_by_epic=None,
    )
    declarations = [
        DeclaredIntent(
            epic=intent.key,
            title=intent.title,
            document=intent.path,
            line=line,
            ref_id=ref_id,
        )
        for intent in intents
        for ref_id, line in intent.declared_refs
    ]
    return IntentReading(
        declarations=tuple(declarations),
        epics_read=len(intents),
        epics_declaring_nodes=sum(1 for i in intents if i.declared_refs),
    )


def read_node_intent(conn: sqlite3.Connection, project_root: Path) -> IntentReading:
    """The one call a surface makes: graph vocabulary from the index, intent from disk."""
    known, _documented, _paths = graph_facts(conn)
    return read_intent(project_root, known_refs=known)
