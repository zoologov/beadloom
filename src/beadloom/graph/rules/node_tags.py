# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Every node's own tags, read once for one evaluation run.

Five evaluators — deny, require, forbid-edge, layer, cardinality — each kept a
private closure of exactly this shape::

    tags_cache: dict[str, set[str]] = {}

    def _cached_tags(ref_id: str) -> set[str]:
        if ref_id not in tags_cache:
            tags_cache[ref_id] = get_node_tags(conn, ref_id)
        return tags_cache[ref_id]

Five copies of one idea is five places for it to drift, and this epic exists
because three copies of a different idea — what layer a node is in — did drift
into three answers. The copies are replaced by one object rather than left as a
duplication nobody was going to notice.

**One query instead of one per node.** The closures read a node at a time; this
reads the tag column once and answers from memory afterwards, which is the same
answer with a different number of round trips. The read is deferred until the
first question, because four of the five call sites skip tags entirely when no
rule in their set matches on one, and that saving is theirs to keep.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Mapping


def _read_all_tags(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """Every node's ``extra["tags"]``, in one pass over the nodes table.

    A node whose ``extra`` is absent, null, not an object, or carries no
    ``tags`` key is simply not in the result, so :meth:`NodeTags.of` answers the
    empty set for it — which is what :func:`~beadloom.graph.loader.get_node_tags`
    answers for the same node, one node at a time. The ``isinstance`` guard is
    the one deliberate difference: reading every row at once means one malformed
    ``extra`` would otherwise break an evaluation that never asked about that
    node.
    """
    tags: dict[str, set[str]] = {}
    for row in conn.execute("SELECT ref_id, extra FROM nodes"):
        raw = row[1]
        if raw is None:
            continue
        extra = json.loads(str(raw))
        if not isinstance(extra, dict):
            continue
        declared = extra.get("tags", [])
        if declared:
            tags[str(row[0])] = set(declared)
    return tags


class NodeTags:
    """The tags each node carries, read on first use and answered from memory.

    The returned sets are the cached ones, not copies — as they were in the
    closures this replaces. Read them; do not mutate them.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._tags: dict[str, set[str]] | None = None

    def _loaded(self) -> dict[str, set[str]]:
        if self._tags is None:
            self._tags = _read_all_tags(self._conn)
        return self._tags

    def of(self, ref_id: str) -> set[str]:
        """The tags *ref_id* carries — empty for a node the graph does not hold."""
        return self._loaded().get(ref_id, set())

    def as_mapping(self) -> Mapping[str, set[str]]:
        """Every tagged node's tags, for a caller that wants the whole map.

        :func:`~beadloom.graph.rules.layers.layer_of` takes the map rather than a
        callback, because it is pure and a callback would hand it a connection.
        """
        return self._loaded()


def node_tags(conn: sqlite3.Connection) -> NodeTags:
    """The tag lookup for one evaluation run over *conn*."""
    return NodeTags(conn)
