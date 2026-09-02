# beadloom:domain=application
# beadloom:feature=impact
"""Where a found site sits in the architecture, and whether the change leaves it.

The graph supplies the boundary and NOTHING ELSE, and that is the constraint the
whole command is built to. `impact` is not `why` at a new name: not one axis
BDL-067 needed is a fact of the graph — the writers of a directory, the branches
of a command, its exit forms, the readers and their policies all live INSIDE one
node. A graph walk would answer confidently and miss every one of them, which is
a green describing the checker's ignorance shipped as a feature.

So the source supplies the sites and this module says which node owns each of
them, using the same most-specific-wins ownership the linter and `sync-check`
already use rather than a second copy of it.

An index that is not there is reported, not skipped. A boundary the run could not
read is a boundary the reader must not take for "the change stays inside".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.infrastructure.db import open_db_readonly
from beadloom.infrastructure.repository import get_owning_ref_id

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

#: The node kinds a site's boundary is stated in. A site's own node may be a
#: component or a feature; the question "did the change leave a bounded context"
#: is answered at the domain (or the service that owns one).
_THE_BOUNDING_KINDS = frozenset({"domain", "service"})


@dataclass(frozen=True)
class Ownership:
    """The node that owns a path, and the bounded context that node sits in."""

    node: str | None
    domain: str | None


class GraphBoundary:
    """Path ownership read from a project's index, or the absence of one."""

    def __init__(self, connection: sqlite3.Connection | None) -> None:
        self._connection = connection
        self._parents: dict[str, str] = {}
        self._kinds: dict[str, str] = {}
        if connection is not None:
            self._kinds = {
                str(row[0]): str(row[1])
                for row in connection.execute("SELECT ref_id, kind FROM nodes").fetchall()
            }
            self._parents = {
                str(row[0]): str(row[1])
                for row in connection.execute(
                    "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = ?", ("part_of",)
                ).fetchall()
            }

    @property
    def readable(self) -> bool:
        """Whether there was an index to read at all."""
        return self._connection is not None

    def owner_of(self, relative_path: str) -> Ownership:
        """The node owning *relative_path*, and the bounded context above it."""
        if self._connection is None:
            return Ownership(None, None)
        node = get_owning_ref_id(self._connection, relative_path)
        return Ownership(node, self._bounding_context(node))

    def context_of(self, node: str | None) -> str | None:
        """The bounded context *node* sits in, by name rather than by path.

        The same walk :meth:`owner_of` performs, exposed because a caller that
        starts from a DECLARED node — a row of a work item's ``## Axes`` table —
        has no path to look it up by. Re-deriving the walk beside this class
        would make "which context owns this node" a thing that can disagree with
        itself.
        """
        return self._bounding_context(node)

    def _bounding_context(self, node: str | None) -> str | None:
        """Walk ``part_of`` upward until a domain or service, guarding against a cycle."""
        seen: set[str] = set()
        current = node
        while current is not None and current not in seen:
            if self._kinds.get(current) in _THE_BOUNDING_KINDS:
                return current
            seen.add(current)
            current = self._parents.get(current)
        return None


def open_boundary(project_root: Path) -> GraphBoundary:
    """The project's boundary, or an unreadable one when it has no index yet.

    A missing index is not an error here. `impact` answers from the source, so
    every axis but this one still has an answer, and refusing to run would make
    the graph a precondition of a command that deliberately does not walk it.
    """
    database = project_root / ".beadloom" / "beadloom.db"
    try:
        return GraphBoundary(open_db_readonly(database))
    except FileNotFoundError:
        return GraphBoundary(None)
