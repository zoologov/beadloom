# beadloom:domain=doc-sync
# beadloom:feature=work-item-type
"""The route a work item took, checked against the axes it was decided from.

The unit here is the WORK ITEM — a folder of planning documents — and not a
document, because a type is a property of the work item and every other
planning check reads one file at a time. Two questions, both about the route:

* a work item on the simplified route carrying no ``## Axes`` section at all
  decided its type from nothing;
* a work item on the simplified route whose kept axes name more than one graph
  node took a route with no document in it that records the crossing.

**Why this is not ``missing-section`` again.** Measured on this repository at
``2a5c0d1``: ``beadloom docs quality`` reported "BRIEF documents do not carry
Axes (0/12)" and "RFC documents do not carry Axes (0/48)". BDL-068 S1.4's
``missing-section`` is PEER-RELATIVE by design, so a section no peer keeps
produces one kind-level statement and zero document-level findings — ``##
Axes`` was required by the template and reported by nothing. That policy is
right for a convention an archive never adopted and wrong for the input to a
decision, so this check is absolute and the simplified route's ``Axes``
requirement is withdrawn from the peer-gated corpus. One fault, one reporter.

**Why only the simplified route.** The full route writes a PRD and an RFC and
each passes an approval gate, so a mis-route meets a person. The simplified
route writes one BRIEF and passes one gate on the work already scoped. It is
the route BDL-067 took: routed ``bug``, one BRIEF, 28 beads, and ``beadloom
impact src/beadloom/onboarding/scanner/bootstrap.py --section`` on its own
target keeps rows naming four nodes.

Which document kinds mark which route is NOT declared here. It arrives as an
argument, derived from the composed ``/task-init`` command by
:mod:`beadloom.application.work_item_routing`, because ``doc_sync`` is a peer
domain of ``onboarding`` and may not import a template.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.doc_sync.axes_section import AXES_HEADING, read_axes_section
from beadloom.doc_sync.doc_quality import QualityFinding, document_kind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from beadloom.doc_sync.axes_section import AxesSection

#: A work item on a route that passes no approval gate on its scope, carrying no
#: axes to have decided that route from.
ROUTED_WITHOUT_AXES = "routed-without-axes"

#: A work item whose kept axes name more graph nodes than its route can hold.
ROUTE_NOT_SUPPORTED_BY_THE_AXES = "route-not-supported-by-the-axes"

#: Every check this module runs, in report order.
CHECK_NAMES: tuple[str, ...] = (ROUTED_WITHOUT_AXES, ROUTE_NOT_SUPPORTED_BY_THE_AXES)

#: How many distinct nodes the simplified route can hold. One: the route writes
#: a single BRIEF and no RFC, so a change ranging wider has no document in it
#: that records the crossing. This is a property of the route's documents, not a
#: number chosen for how many findings it produces.
NODES_THE_SIMPLIFIED_ROUTE_HOLDS = 1


@dataclass(frozen=True)
class WorkItem:
    """One folder of planning documents, and what its documents say about it."""

    key: str
    #: The document whose kind identifies the route, and which a finding names.
    routed_by: str
    kinds: tuple[str, ...]
    #: The first ``## Axes`` section found in the folder, with the document it
    #: came from. A work item states its axes once; two documents stating
    #: different axes is a disagreement the axes checks report per document.
    axes: AxesSection | None = None
    axes_document: str = ""

    @property
    def nodes(self) -> tuple[str, ...]:
        """The distinct graph nodes the kept axes name, in the table's order."""
        if self.axes is None:
            return ()
        return tuple(
            dict.fromkeys(axis.node for axis in self.axes.kept if axis.node)
        )


@dataclass(frozen=True)
class WorkItemTypeReport:
    """What the route checks found, and how many work items they entered.

    ``work_items`` is the honest half: these checks read a FOLDER, so the
    document count every other planning check reports would overstate the
    population by a factor of however many documents a work item carries.
    """

    findings: tuple[QualityFinding, ...] = ()
    work_items: int = 0


def _key_of(path: str) -> str:
    """The work item a planning document belongs to — its folder."""
    parent = PurePosixPath(path.replace("\\", "/")).parent
    return str(parent)


@dataclass
class _Folder:
    """One work item under construction, while its documents are being read."""

    kinds: list[str] = field(default_factory=list)
    routed_by: str = ""
    axes: AxesSection | None = None
    axes_document: str = ""


def _collect(
    documents: Iterable[tuple[str, str]], simplified_kinds: frozenset[str]
) -> list[WorkItem]:
    """Group the documents by folder, keeping only the items on the judged route."""
    folders: dict[str, _Folder] = {}
    for path, text in sorted(documents):
        kind = document_kind(path)
        folder = folders.setdefault(_key_of(path), _Folder())
        folder.kinds.append(kind)
        if kind in simplified_kinds and not folder.routed_by:
            folder.routed_by = path
        if folder.axes is None:
            section = read_axes_section(text)
            if section is not None:
                folder.axes = section
                folder.axes_document = path
    return [
        WorkItem(
            key=key,
            routed_by=folder.routed_by,
            kinds=tuple(folder.kinds),
            axes=folder.axes,
            axes_document=folder.axes_document,
        )
        for key, folder in sorted(folders.items())
        if folder.routed_by
    ]


def check_work_item_types(
    documents: Iterable[tuple[str, str]],
    *,
    simplified_kinds: frozenset[str],
) -> WorkItemTypeReport:
    """Report a work item whose route its axes do not support.

    *documents* are ``(path, text)`` pairs; *simplified_kinds* are the document
    kinds written only by the simplified route, derived from the composed
    ``/task-init`` command. An empty set means the routing could not be derived,
    and nothing is judged: :func:`_collect` keeps a folder only when one of its
    documents identifies the route, so an empty set leaves an empty population
    and the report states zero rather than a clean run over one. There is no
    early return for it, because a mutant showed one could not be made to fail.
    """
    items = _collect(documents, simplified_kinds)
    findings: list[QualityFinding] = []
    for item in items:
        if item.axes is None:
            findings.append(_no_axes(item, simplified_kinds))
            continue
        nodes = item.nodes
        if len(nodes) > NODES_THE_SIMPLIFIED_ROUTE_HOLDS:
            findings.append(_too_wide(item, nodes))
    findings.sort(key=lambda finding: (finding.path, finding.line, finding.check))
    return WorkItemTypeReport(findings=tuple(findings), work_items=len(items))


def _no_axes(item: WorkItem, simplified_kinds: frozenset[str]) -> QualityFinding:
    routes = ", ".join(sorted(simplified_kinds))
    return QualityFinding(
        check=ROUTED_WITHOUT_AXES,
        path=item.routed_by,
        line=1,
        excerpt=f"{routes} and no `## {AXES_HEADING}` section",
        why=(
            "the work item took the route that passes no approval gate on its "
            "scope, and carries nothing the type was decided from — the axis "
            "count is what says whether a work item is a bug, and this one "
            "states none"
        ),
        remediation=(
            "run the explore step: `beadloom impact <path|symbol> --section`, "
            "paste the section into the document and rule each row in or out "
            "of scope"
        ),
    )


def _too_wide(item: WorkItem, nodes: tuple[str, ...]) -> QualityFinding:
    return QualityFinding(
        check=ROUTE_NOT_SUPPORTED_BY_THE_AXES,
        path=item.axes_document,
        line=item.axes.line if item.axes is not None else 1,
        excerpt=f"{len(nodes)} nodes kept in scope: {', '.join(nodes)}",
        why=(
            f"the route writes one document and holds "
            f"{NODES_THE_SIMPLIFIED_ROUTE_HOLDS} node, and the axes kept in "
            "scope name more — so the crossing between them is recorded nowhere"
        ),
        remediation=(
            "take the full route, which records the crossing in an RFC, or "
            "narrow the scope decision until the kept axes name one node"
        ),
    )
