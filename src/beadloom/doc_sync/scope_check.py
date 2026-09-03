# beadloom:domain=doc-sync
# beadloom:feature=scope-check
"""The paths a commit stages, judged against the axes its work item declared.

CONTEXT Q2 decides the unit: the WORK ITEM's axes, never the claimed bead's. The
work item's axes are what a human approved and a bead may narrow freely inside
them, so a commit leaving the work item's axes means the approval no longer
covers the change — which is the re-plan trigger. Comparing against the bead
would fire on every legitimate cross-bead commit inside one approved scope.

**The rule was measured before it was chosen, because an always-red check is an
ignored check.** ``docs_audit.ignore`` exists in this repository because a check
that fired on everything was suppressed instead of repaired. Two candidate rules
were run against BDL-068's own ``## Axes`` table:

* *the staged path's owning NODE must be a node a kept row names* — red on all
  three of this branch's code commits (``c7591a8`` 11 paths, ``3f68442`` 5,
  ``2f9e343`` 6). Not because those commits left the approval, but because the
  table records what a change RANGES OVER and the surfaces it CHANGES are named
  in the ``Derived by`` field instead;
* *the bounded context the declared axes reach* — silent on all three, and
  outside for 115 of the 155 commits before this branch that touch an owned path
  (74 per cent). Specific to the work item's own work, and still a signal.

So the rule has two clauses, each with its own reason:

1. a node a kept row names, or a node the derivation ran over, is INSIDE — the
   surfaces the answer was derived from are the surfaces the work item changes;
2. otherwise the path is inside when its bounded context is one the declared
   axes reach, and outside when it is not. A sibling module in a context the
   work item already works in is inside the approval; a context it never named
   is not.

A node a row names and RULES OUT of scope is outside whatever its context says,
and that is the sharpest half: the person wrote "not this one".

**What this deliberately does not report.** A path no node owns — a document, a
test, a graph YAML — is not a call site and has no axis to be outside of. It is
counted and stated beside the verdict, never reported, the way
:class:`~beadloom.doc_sync.commit_scope.CommitScope` already states the pairs it
left to the push gate. A count that reads as a checked count is the false green
this epic exists to remove.

**An undecided row neither widens the scope nor narrows it.** It is not kept, so
it cannot authorise a commit; and it is not a ruling, so it does not condemn one
either. The count travels with the verdict, because
``axis-without-a-scope-decision`` already owns that fault and a second reporter
of one fault is a second thing to keep in step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.doc_sync.axes_section import AXES_HEADING
from beadloom.doc_sync.doc_quality import QualityFinding

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from beadloom.doc_sync.axes_section import AxesSection

#: A staged path the work item's declared axes do not cover.
OUTSIDE_THE_DECLARED_AXES = "outside-the-declared-axes"

#: Every check this module runs, in report order.
CHECK_NAMES: tuple[str, ...] = (OUTSIDE_THE_DECLARED_AXES,)

#: What a finding says where the graph places the owning node in no bounded
#: context at all. Not an empty string: a blank reads as an oversight.
NO_CONTEXT = "no bounded context"

#: How many declared axes a finding spells out before it counts the rest. The
#: reader needs the shape of the approval, not a transcript of the table.
_NAMED_LIMIT = 6


@dataclass(frozen=True)
class DeclaredScope:
    """What a work item's ``## Axes`` section puts inside the approval."""

    #: Where the section was read from, so a finding can send a reader to it.
    document: str
    #: Nodes a row keeps in scope.
    kept: frozenset[str] = frozenset()
    #: Nodes the derivation ran over, named in the ``Derived by`` field. Inside
    #: by construction: a work item changes the surfaces it derived its answer
    #: from, and the table below them records what those surfaces reach.
    targets: frozenset[str] = frozenset()
    #: Node -> the axes whose rows name it and rule it OUT of scope.
    ruled_out: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    #: Bounded contexts the kept nodes and the targets sit in.
    contexts: frozenset[str] = frozenset()
    #: Axis name -> the contexts its kept rows reach, for the finding to name.
    axis_contexts: Mapping[str, frozenset[str]] = field(default_factory=dict)
    #: Rows carrying the derivation's half and no decision.
    undecided: int = 0

    @property
    def inside(self) -> frozenset[str]:
        """Every node inside the approval by name rather than by context."""
        return self.kept | self.targets

    def declared(self) -> str:
        """The axes this work item declared, as a finding spells them out."""
        if not self.axis_contexts:
            return "no axis keeps a node in scope"
        named = [
            f"`{axis}` ({', '.join(sorted(contexts)) or NO_CONTEXT})"
            for axis, contexts in sorted(self.axis_contexts.items())
        ]
        if len(named) > _NAMED_LIMIT:
            rest = len(named) - _NAMED_LIMIT
            return ", ".join(named[:_NAMED_LIMIT]) + f" and {rest} more"
        return ", ".join(named)


@dataclass(frozen=True)
class ScopeVerdict:
    """What the comparison found, and what it could not judge.

    ``judged`` and ``unowned`` are stated apart because a run that reported
    nothing over paths no node owns has verified nothing, and a green count that
    reads as a checked count is the false green this check exists to remove.
    """

    findings: tuple[QualityFinding, ...] = ()
    judged: int = 0
    unowned: int = 0
    undecided: int = 0

    def describe(self) -> str:
        """The one line a commit gate prints about what it judged."""
        undecided = (
            f", {self.undecided} declared row(s) nobody decided"
            if self.undecided
            else ""
        )
        return (
            f"Judged against the declared axes: {self.judged} staged path(s) a "
            f"node owns, {self.unowned} no node owns{undecided}."
        )


def declared_scope(
    section: AxesSection,
    *,
    document: str,
    target_nodes: Iterable[str] = (),
    node_contexts: Mapping[str, str],
) -> DeclaredScope:
    """The scope *section* declares, resolved through *node_contexts*.

    *target_nodes* are the nodes owning the paths the ``Derived by`` field names,
    resolved by the caller: this domain has no index to ask, and
    :mod:`beadloom.application.declared_scope` owns that half.
    """
    kept = frozenset(axis.node for axis in section.kept if axis.node)
    targets = frozenset(target_nodes)
    ruled_out: dict[str, list[str]] = {}
    axis_contexts: dict[str, set[str]] = {}
    for axis in section.axes:
        if axis.in_scope:
            reached = axis_contexts.setdefault(axis.axis, set())
            context = node_contexts.get(axis.node) if axis.node else None
            if context:
                reached.add(context)
        elif axis.in_scope is False and axis.node and axis.node not in kept:
            # A node kept by one row and ruled out by another is KEPT: the person
            # took it somewhere, and a ruling elsewhere is a narrowing of that
            # row's axis rather than a refusal of the node.
            ruled_out.setdefault(axis.node, []).append(axis.axis)
    contexts = frozenset(
        context
        for node in kept | targets
        if (context := node_contexts.get(node)) is not None
    )
    return DeclaredScope(
        document=document,
        kept=kept,
        targets=targets,
        ruled_out={node: tuple(axes) for node, axes in sorted(ruled_out.items())},
        contexts=contexts,
        axis_contexts={
            axis: frozenset(reached) for axis, reached in axis_contexts.items()
        },
        undecided=sum(1 for axis in section.axes if axis.in_scope is None),
    )


def check_commit_scope(
    paths: Sequence[str],
    scope: DeclaredScope,
    *,
    ownership: Mapping[str, tuple[str | None, str | None]],
) -> ScopeVerdict:
    """Report the staged paths *scope* does not cover.

    *ownership* maps a project-relative path to the node that owns it and the
    bounded context above that node, resolved by the caller from the index.
    """
    findings: list[QualityFinding] = []
    judged = 0
    unowned = 0
    for path in sorted(set(paths)):
        node, context = ownership.get(path, (None, None))
        if node is None:
            unowned += 1
            continue
        judged += 1
        if node in scope.inside:
            continue
        ruling = scope.ruled_out.get(node)
        if ruling:
            findings.append(_ruled_out(path, node, ruling, scope))
            continue
        if context is not None and context in scope.contexts:
            continue
        findings.append(_outside(path, node, context, scope))
    return ScopeVerdict(
        findings=tuple(findings),
        judged=judged,
        unowned=unowned,
        undecided=scope.undecided,
    )


def _ruled_out(
    path: str, node: str, axes: tuple[str, ...], scope: DeclaredScope
) -> QualityFinding:
    named = ", ".join(f"`{axis}`" for axis in axes)
    return QualityFinding(
        check=OUTSIDE_THE_DECLARED_AXES,
        path=path,
        line=1,
        excerpt=f"`{node}`, which the axis {named} names and rules out of scope",
        why=(
            f"the work item's `## {AXES_HEADING}` in {scope.document} rules this "
            "node out, so the approval covers everything the section declares "
            "except this path — a commit on it is a change the human said no to"
        ),
        remediation=(
            f"rule the {named} row for `{node}` into scope with its reason and "
            "have the wider scope approved, or leave the change out of this "
            "work item"
        ),
    )


def _outside(
    path: str, node: str, context: str | None, scope: DeclaredScope
) -> QualityFinding:
    where = f"bounded context `{context}`" if context else NO_CONTEXT
    return QualityFinding(
        check=OUTSIDE_THE_DECLARED_AXES,
        path=path,
        line=1,
        excerpt=f"`{node}`, in {where}",
        why=(
            f"outside every axis the work item declared — {scope.declared()} — "
            f"and outside the {len(scope.contexts)} bounded context(s) they "
            "reach, so what the human approved no longer covers this change"
        ),
        remediation=(
            f"re-derive the axes (`beadloom impact {path} --section`), record "
            f"the new rows in {scope.document} and have the wider scope "
            "approved, or leave the change out of this work item"
        ),
    )
