"""One node per graph file, and the surface where a shared write is still possible.

:mod:`beadloom.onboarding.graph_files` states the one policy every READER of
`.beadloom/_graph/` holds. This module states the one property every WRITER of it
depends on, which is a different question and is why it is a different body: not
*which files may I read* but *can two agents adding two nodes collide*.

**Why it is a property and not a convention** (BDL-UX #265). A graph held in one
file is written by every bead that adds, renames or moves a node, and this
project measured that as 7 of the 8 commits that touched its graph on one
branch. `beadloom-kqsv` shipped the `graph-files` medium so a wave STATES that
sharing. Stating it is as far as a plan can go: the node a bead is about to add
is in no graph the plan could read, so the collision is reported after the fact
or not at all. One file per node removes it instead — two node-adding beads
write two files, and there is nothing left to detect. It is the same primitive
`beadloom-0mdo.66` took for the issue log's numbers, at a different boundary.

**The name carries the workflow.** A node's file is named after the node, so
hand-editing one is `vi .beadloom/_graph/<ref-id>.yml` rather than a search
through a file holding a hundred of them. The two facts are reported apart —
:attr:`GraphLayout.shared` and :attr:`GraphLayout.misnamed` — because a project
can have the property without the name, and only the first removes the shared
write.

**A single-file graph stays valid, and this module reports rather than refuses.**
`beadloom init` writes one `services.yml` an adopter reviews by hand, and one
file is the easier thing to review once. The layout is what a project moves to
when concurrent agents start writing its graph, so what is owed there is the
number — how many of its nodes sit in a file another bead writes — and not a
verdict on a project that has never run a wave.
"""

# beadloom:domain=onboarding
# beadloom:component=graph-layout

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.onboarding.graph_files import each_graph_file

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

#: The suffix every graph file carries, which is the glob every reader of the
#: directory already uses. Stated here so the naming rule below is written once.
GRAPH_FILE_SUFFIX = ".yml"


def node_file_name(ref_id: str) -> str:
    """The file *ref_id* is declared in under the one-node-per-file layout.

    The ref id is used verbatim. It is already the graph's unique identifier, so
    any transformation would put a second spelling of one name into the tree —
    the class of defect this epic removes everywhere else.
    """
    return f"{ref_id}{GRAPH_FILE_SUFFIX}"


@dataclass(frozen=True)
class SharedFile:
    """A graph file declaring more than one node, and the nodes it holds.

    Every one of ``nodes`` is a node no bead can add, rename or move without
    writing a file some other bead writes for the same reason.
    """

    name: str
    nodes: tuple[str, ...]


@dataclass(frozen=True)
class EdgeHome:
    """One edge and the graph file it is declared in.

    An edge is a fact about TWO nodes, so one file per node can give it only one
    home and the property the layout can state is the weaker one: an edge lives
    in a file named after one of its endpoints. That is enough for what the
    layout is for. Under ``src`` it is where a reader looks for what a node
    depends on; under ``dst`` it is where a bead that ADDS a node puts the edges
    pointing at it, which is the placement that leaves every existing node's file
    untouched. A split that left the edges in one shared file would not have
    removed the shared write for a bead that adds an edge.
    """

    file: str
    src: str
    dst: str
    kind: str

    @property
    def under_an_endpoint(self) -> bool:
        """Whether this edge's file is named after one of the nodes it joins."""
        return self.file in (node_file_name(self.src), node_file_name(self.dst))

    def __str__(self) -> str:
        return f"{self.src} -> {self.dst} ({self.kind})"


@dataclass(frozen=True)
class GraphLayout:
    """A graph directory's layout, at the grain the shared write is a property of.

    ``files`` holds every file that declares at least one node, in name order. A
    file declaring none is not part of the layout: it is neither a shared write
    nor a node's home, and counting it would make the answer depend on how a
    project spells "nothing here".
    """

    files: tuple[SharedFile, ...] = ()
    edges: tuple[EdgeHome, ...] = ()

    @property
    def shared(self) -> tuple[SharedFile, ...]:
        """The files two node-writing beads can still collide in."""
        return tuple(file for file in self.files if len(file.nodes) > 1)

    @property
    def shared_nodes(self) -> int:
        """How many nodes sit in a file they share with another node."""
        return sum(len(file.nodes) for file in self.shared)

    @property
    def declared(self) -> int:
        """How many nodes the directory declares."""
        return sum(len(file.nodes) for file in self.files)

    @property
    def holds(self) -> bool:
        """Whether every node has a file of its own.

        A directory declaring nothing holds vacuously: there is no node whose
        write could be shared, and reporting a virgin project as a violation
        would be a finding about an absence.
        """
        return not self.shared

    @property
    def misplaced_edges(self) -> tuple[str, ...]:
        """Edges declared in a file named after neither of their endpoints.

        Every edge of a single-file graph is reported, which is the true and
        unsurprising statement about that layout: a bead adding an edge writes
        the file every other bead writes for the same reason.
        """
        return tuple(str(edge) for edge in self.edges if not edge.under_an_endpoint)

    @property
    def misnamed(self) -> tuple[str, ...]:
        """Nodes declared in a file that is not named after them, in id order.

        Reported separately from :attr:`shared` because it is the findability
        half rather than the collision half. Every node of a single-file graph
        is misnamed, which is a true statement about that layout and not a
        second complaint about it.
        """
        return tuple(
            sorted(
                ref
                for file in self.files
                for ref in file.nodes
                if file.name != node_file_name(ref)
            )
        )


def shared_files(files: Mapping[str, Iterable[str]]) -> tuple[SharedFile, ...]:
    """The files of *files* that declare more than one node, in name order.

    Takes a mapping of file name to declared ref ids rather than a directory, so
    the one computation serves both callers: this module reads it off disk, and
    :mod:`beadloom.application.waves.media_checks` already holds the same mapping
    as the ``GraphInput`` a plan was derived from. A second body would be one
    derivable fact with two homes.
    """
    return tuple(
        SharedFile(name=name, nodes=tuple(sorted(refs)))
        for name, refs in sorted(files.items())
        if len(tuple(refs)) > 1
    )


def layout_of(graph_dir: Path) -> GraphLayout:
    """Read *graph_dir*'s layout through the one policy every reader holds.

    A missing directory, an unreadable file and a file that is not a graph file
    are :func:`~beadloom.onboarding.graph_files.each_graph_file`'s questions and
    are not asked again here.
    """
    declared: dict[str, tuple[str, ...]] = {}
    edges: list[EdgeHome] = []
    for path, data in each_graph_file(graph_dir):
        refs = tuple(
            str(node["ref_id"])
            for node in (data.get("nodes") or [])
            if isinstance(node, dict) and node.get("ref_id")
        )
        if refs:
            declared[path.name] = refs
        edges.extend(
            EdgeHome(
                file=path.name,
                src=str(edge.get("src", "")),
                dst=str(edge.get("dst", "")),
                kind=str(edge.get("kind", "")),
            )
            for edge in (data.get("edges") or [])
            if isinstance(edge, dict)
        )
    return GraphLayout(
        files=tuple(
            SharedFile(name=name, nodes=tuple(sorted(refs)))
            for name, refs in sorted(declared.items())
        ),
        edges=tuple(edges),
    )
