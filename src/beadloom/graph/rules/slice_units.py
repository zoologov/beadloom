# beadloom:domain=graph
# beadloom:feature=rule-engine
"""What the two slice rules judge, read off the graph and the folders: slices, segments, groups.

BDL-082 S1b split this out of :mod:`.slices` when the units stopped being one kind. A rule's
*carriers* are the nodes carrying one of its ``tags`` whose ``source`` is a folder on disk,
and among them the graph says which is which:

- a **container** is a carrier that another carrier sharing one of its tags is ``part_of``:
  the ``shared`` or ``app`` layer node ``init`` writes. FSD gives an unsliced layer no public
  API of its own, so a container is not judged as a slice;
- a **segment** is a carrier ``part_of`` a container: a segment of ``shared`` or ``app``,
  entered through its index, and free to import the other segments of its layer;
- every other carrier is a **slice**.

A **group** has no node (RFC D2): it is a folder between a sliced layer's folder and the
slices in it that no node's source claims, as ``features/auth`` holds ``login`` and
``register``. The layer folder is recognised by FSD's own layer names, which the
specification fixes; slices under no folder of those names are read as in no group,
because nothing else tells a group apart from a layer.
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.graph.js_specifiers import MODULE_EXTENSIONS
from beadloom.graph.rules.node_tags import node_tags

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Mapping, Sequence
    from pathlib import Path

#: The stem of a public API file: ``index.ts``, ``index.vue``, ``index.ios.tsx``.
INDEX = "index"

#: The folders of FSD's sliced layers, by the specification's names: a folder between one
#: of these and a slice is a group.
SLICED_LAYER_FOLDERS: frozenset[str] = frozenset({"pages", "widgets", "features", "entities"})


def stem(file_name: str) -> str:
    """The name before its first dot: ``index`` for ``index.ios.tsx``."""
    return file_name.split(".", 1)[0]


def inside(path: str, folder: str) -> bool:
    """Whether the project-relative *path* is *folder* or lies below it."""
    return path == folder or path.startswith(f"{folder}/")


def is_index_file(path: Path) -> bool:
    """Whether *path* is a public API file: a code file named ``index``.

    The one reader of what an ``index`` is, for the slice rules and for ``init``, which
    reads a folder holding one as a slice (BDL-082 S2 fix): two readers over two extension
    sets disagreed on ``index.py`` one way and on ``index.mjs`` the other.
    """
    return path.is_file() and stem(path.name) == INDEX and path.suffix in MODULE_EXTENSIONS


def has_index(folder: str, project_root: Path) -> bool:
    """Whether *folder* holds a code file named ``index`` at its top."""
    return any(is_index_file(path) for path in (project_root / folder).iterdir())


def node_sources(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """``(ref_id, source)`` of every node that declares a source."""
    rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source != '' "
        "ORDER BY ref_id"
    ).fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


def carriers(conn: sqlite3.Connection, tags: Sequence[str]) -> dict[str, frozenset[str]]:
    """Each node carrying one of *tags*, mapped to the ones of *tags* it carries."""
    wanted = set(tags)
    return {
        ref: frozenset(carried & wanted)
        for ref, carried in sorted(node_tags(conn).as_mapping().items())
        if carried & wanted
    }


@dataclass(frozen=True)
class SliceUnits:
    """One rule's carriers that have a folder on disk, and how the graph relates them."""

    #: Each carrier's project-relative folder, without a trailing slash.
    folders: Mapping[str, str]
    #: The rule's tags each carrier carries.
    tags: Mapping[str, frozenset[str]]
    #: Each segment, mapped to the container it is ``part_of``.
    container_of: Mapping[str, str]
    #: Every node's folder, carrier or not: a folder one of them claims is no group.
    claimed: frozenset[str]

    def is_container(self, ref: str) -> bool:
        return ref in self.container_of.values()

    def is_segment(self, ref: str) -> bool:
        return ref in self.container_of

    def noun(self, ref: str) -> str:
        """``segment`` or ``slice``: what a finding calls the unit *ref*."""
        return "segment" if self.is_segment(ref) else "slice"

    def holding(self, path: str) -> str | None:
        """The unit whose folder holds *path* (a file or a folder), deepest first."""
        path = path.rstrip("/")
        held = [ref for ref, folder in self.folders.items() if path and inside(path, folder)]
        return max(held, key=lambda ref: len(self.folders[ref])) if held else None

    def same_layer(self, first: str, second: str) -> bool:
        """Whether the two units carry one of the rule's tags in common."""
        return bool(self.tags.get(first, frozenset()) & self.tags.get(second, frozenset()))

    def slices(self) -> list[str]:
        """The units judged as slices: every carrier but the segments and the containers."""
        return sorted(
            ref for ref in self.folders if not self.is_segment(ref) and not self.is_container(ref)
        )

    def groups(self) -> dict[str, list[str]]:
        """Each group folder, mapped to the slices below it."""
        found: dict[str, list[str]] = {}
        for ref in self.slices():
            for group in self._groups_above(self.folders[ref]):
                found.setdefault(group, []).append(ref)
        return dict(sorted(found.items()))

    def _groups_above(self, folder: str) -> list[str]:
        """The unclaimed folders between *folder* and the sliced layer's folder above it."""
        between: list[str] = []
        parent = posixpath.dirname(folder)
        while parent:
            if posixpath.basename(parent) in SLICED_LAYER_FOLDERS:
                return between
            if parent in self.claimed:
                return []
            between.append(parent)
            parent = posixpath.dirname(parent)
        return []


def read_units(conn: sqlite3.Connection, tags: Sequence[str], project_root: Path) -> SliceUnits:
    """The units a rule over *tags* judges, read from the graph and the disk."""
    carried = carriers(conn, tags)
    sources = node_sources(conn)
    folders = {
        ref: source.rstrip("/")
        for ref, source in sources
        if ref in carried and (project_root / source).is_dir()
    }
    rows = conn.execute("SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'")
    container_of = {
        str(src): str(dst)
        for src, dst in rows.fetchall()
        if src in folders and dst in folders and carried[str(src)] & carried[str(dst)]
    }
    return SliceUnits(
        folders=folders,
        tags={ref: carried[ref] for ref in folders},
        container_of=container_of,
        claimed=frozenset(source.rstrip("/") for _, source in sources),
    )
