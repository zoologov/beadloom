# beadloom:domain=application
# beadloom:component=declared-scope
"""Which work item a commit belongs to, and the scope its ``## Axes`` declare.

The join :mod:`beadloom.doc_sync.scope_check` cannot make for itself. The check
is a domain question — do these paths fall outside these axes — and answering it
needs three things from outside that domain: the graph index that says which
node owns a path, git for the paths themselves and for the branch, and the
planning corpus that says which folders are work items. This module composes
them and hands the check pure data, the way
:mod:`beadloom.application.work_item_routing` does for ``work-item-type``.

**The work item is found by the branch, and it has to be.** The pre-commit hook
runs BEFORE the commit message is finalised, so the ``[BDL-068]`` prefix is not
readable at the moment the commit is judged. The branch is, and this project's
own convention (``git switch -c features/<ISSUE-KEY>``) puts the key in it.
Rather than parsing a prefix, the key is matched against the work items that
actually exist: a folder is the work item when its name is one of the branch's
``/``-separated segments. A branch naming none is NOT CHECKED with a reason,
never a pass — the class of false green this epic exists to remove.

**Nothing is guessed.** No index, no branch, no work item, no ``## Axes``
section and no answer from git are five different reasons to have checked
nothing, and each is reported as itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.application.doc_shape import planning_documents
from beadloom.application.guards.config import GuardConfigError
from beadloom.application.impact.answer import source_root_of
from beadloom.application.impact.boundary import open_boundary
from beadloom.doc_sync.axes_section import (
    AXES_HEADING,
    AxesSection,
    derived_targets,
    read_axes_section,
)
from beadloom.doc_sync.git_baseline import (
    current_branch,
    paths_changed_since,
    ref_exists,
    staged_paths,
)
from beadloom.doc_sync.scope_check import (
    DeclaredScope,
    ScopeVerdict,
    check_commit_scope,
    declared_scope,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.impact.boundary import GraphBoundary

#: No branch is checked out, so nothing names the work item to judge against.
NO_BRANCH = "no branch is checked out, so no work item names the scope to judge against"

#: The project has no index, so no path can be resolved to the node that owns it.
NO_INDEX = (
    "the project has no index, so no staged path can be resolved to the node "
    "that owns it — run `beadloom reindex`"
)

#: git could not say which paths to judge.
GIT_SILENT = "git could not say which paths this commit changes, so nothing was judged"

#: The guard whose ``options.trunk`` names this project's trunk branch. Read
#: from there rather than declared again: ``working-branch`` already asks the
#: project for the name, and two declarations of one branch are two things that
#: can disagree about which ref an approval was given against.
_TRUNK_OPTION_OWNER = "working-branch"
_TRUNK_OPTION = "trunk"

#: Trunk assumed when the project declares none — the same default
#: ``working-branch`` carries, imported rather than repeated.


@dataclass(frozen=True)
class ScopeRun:
    """One run of the commit-scope check, and what it was able to judge.

    ``reason`` is present exactly when nothing was checked. A run that reports
    no findings and states no reason really did compare the paths; a run that
    states one compared nothing, and the two must never read alike.
    """

    verdict: ScopeVerdict = field(default_factory=ScopeVerdict)
    #: The work item whose axes were used, as its folder name.
    work_item: str = ""
    #: The document the ``## Axes`` section was read from, project-relative.
    document: str = ""
    #: What was compared: the staged index, or the branch against a ref.
    scope: str = ""
    reason: str | None = None

    @property
    def checked(self) -> bool:
        """Whether this run compared anything at all."""
        return self.reason is None

    def describe(self) -> str:
        """The one line a commit gate prints."""
        if self.reason is not None:
            return f"Declared axes: NOT CHECKED — {self.reason}"
        return (
            f"Declared axes ({self.work_item}, {self.scope}): "
            f"{self.verdict.describe()}"
        )


def trunk_ref(project_root: Path) -> str:
    """The ref a branch's whole work is compared against for the push gate.

    ``origin/<trunk>`` when that remote-tracking ref exists, and the local
    ``<trunk>`` otherwise. Not a preference: measured on this repository with a
    local ``main`` two commits behind the remote, ``--since main`` reported
    another work item's LANDED change as this branch's, and ``--since
    origin/main`` did not. The remote branch is also what the pull request is
    compared against, which is where the approval is actually spent.
    """
    from beadloom.application.guards.checks.working_branch import DEFAULT_TRUNK
    from beadloom.application.guards.config import load_guards_config

    try:
        options = load_guards_config(project_root).spec_for(_TRUNK_OPTION_OWNER).options
        trunk = options.get(_TRUNK_OPTION, DEFAULT_TRUNK)
    except GuardConfigError:
        # A malformed flow.yml is `config-check`'s finding, not this one's. The
        # shipped default keeps the comparison running rather than adding a
        # second reporter of one fault.
        trunk = DEFAULT_TRUNK
    remote = f"origin/{trunk}"
    return remote if ref_exists(project_root, remote) else trunk


def work_item_of_branch(project_root: Path, branch: str) -> Path | None:
    """The work-item folder *branch* names, or ``None`` when it names none.

    The population is DERIVED from the planning documents the quality checks
    already read, so a project that configures its own ``doc_quality.paths`` is
    judged over its own corpus and not over this repository's convention.

    A segment match rather than a substring one: ``features/BDL-068`` names
    ``BDL-068``, and a branch whose segment merely CONTAINS a key names nothing.
    Two folders cannot match one segment, because a folder name is its key.
    """
    segments = {segment for segment in branch.split("/") if segment}
    folders = {document.parent for document in planning_documents(project_root)}
    for folder in sorted(folders):
        if folder.name in segments:
            return folder
    return None


def scope_of_branch(
    project_root: Path, *, branch: str | None
) -> tuple[DeclaredScope | None, str | None]:
    """The scope the branch's work item declares, or the reason there is none."""
    if not branch:
        return None, NO_BRANCH
    folder = work_item_of_branch(project_root, branch)
    if folder is None:
        return None, (
            f"the branch {branch!r} names no work item among the planning "
            "documents, so there are no declared axes to judge against"
        )
    found: tuple[str, AxesSection] | None = None
    for document in sorted(folder.glob("*.md")):
        section = read_axes_section(document.read_text(encoding="utf-8"))
        if section is not None:
            found = (document.relative_to(project_root).as_posix(), section)
            break
    if found is None:
        # Asked BEFORE the index, and the order is the answer: reading a section
        # needs no index, so a work item that declares no scope gets the reason
        # that names its own fault rather than one about this machine's cache.
        return None, (
            f"{folder.name} carries no `## {AXES_HEADING}` section, so the work "
            "item declares no scope — `routed-without-axes` and "
            "`missing-section` own that fault"
        )
    boundary = open_boundary(project_root)
    if not boundary.readable:
        return None, NO_INDEX
    relative, section = found
    return (
        declared_scope(
            section,
            document=relative,
            target_nodes=_target_nodes(project_root, boundary, section),
            node_contexts=_node_contexts(boundary, section),
        ),
        None,
    )


def scope_check(
    project_root: Path, *, branch: str | None = None, since: str | None = None
) -> ScopeRun:
    """Judge this commit — or this branch — against its work item's declared axes.

    *since* names a ref to compare the branch against, for the push gate; its
    absence judges the staged index, for the commit gate. One comparison, two
    scopes, because a commit gate and a push gate disagreeing about what left
    the approval would be the second home this epic removes.
    """
    name = branch if branch is not None else current_branch(project_root)
    scope, reason = scope_of_branch(project_root, branch=name)
    if scope is None:
        return ScopeRun(reason=reason)
    paths = (
        paths_changed_since(project_root, since)
        if since is not None
        else staged_paths(project_root)
    )
    if paths is None:
        return ScopeRun(work_item=_key(scope), document=scope.document, reason=GIT_SILENT)
    boundary = open_boundary(project_root)
    ownership = {
        path: (owner.node, owner.domain)
        for path in sorted(paths)
        for owner in (boundary.owner_of(path),)
    }
    return ScopeRun(
        verdict=check_commit_scope(sorted(paths), scope, ownership=ownership),
        work_item=_key(scope),
        document=scope.document,
        scope=f"against {since}" if since is not None else "staged",
    )


def _key(scope: DeclaredScope) -> str:
    """The work item's folder name, read back off the document it declared in."""
    return PurePosixPath(scope.document).parent.name


def _node_contexts(boundary: GraphBoundary, section: AxesSection) -> dict[str, str]:
    """Every node the section names, mapped to the bounded context above it."""
    contexts: dict[str, str] = {}
    for axis in section.axes:
        if not axis.node or axis.node in contexts:
            continue
        context = boundary.context_of(axis.node)
        if context is not None:
            contexts[axis.node] = context
    return contexts


def _target_nodes(
    project_root: Path, boundary: GraphBoundary, section: AxesSection
) -> tuple[str, ...]:
    """The nodes owning the paths the ``Derived by`` field names.

    A word is resolved against the project root and, failing that, against the
    single source package — the ``Derived by`` field is written by a human as
    often as it is rendered, and a human writes ``doc_sync/axes_section.py``.
    Only an existing FILE is resolved: the rendered field names the sweep root
    beside the target, and resolving a directory would put its whole domain
    inside the approval by accident.
    """
    source_root = source_root_of(project_root)
    nodes: list[str] = []
    for token in derived_targets(section):
        for candidate in (project_root / token, source_root / token):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(project_root).as_posix()
            node = boundary.owner_of(relative).node
            if node is not None and node not in nodes:
                nodes.append(node)
            break
    return tuple(nodes)
