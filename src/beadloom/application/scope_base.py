# beadloom:domain=application
# beadloom:component=declared-scope
"""The branch a run judges, and the ref that branch's work is judged against.

**The defect this closes (BDL-UX #330).** The scope check compared a branch with the
trunk, always. Measured on 9.0.0 on an outside monorepo: a work item cut from a
feature branch not yet merged got the parent's whole diff, 304
``outside-the-declared-axes`` warnings about files it never touched, and the one
true finding about its own work was invisible among them. The base it had judged
against was printed nowhere, so nothing on the screen said why.

**The rule (RFC D4, agreed with the owner as PRD ruling 4).** ``--base`` when the
caller names one; else the merge-base with the branch this one was cut from; else
the trunk. The parent is read from three sources, in this order, and the first that
names a branch git still resolves decides:

1. the reflog of this machine, which recorded the start point when the branch was
   created (``git switch -c`` records ``HEAD``, and the HEAD reflog then names the
   branch that was checked out);
2. the pull or merge request's target branch (``GITHUB_BASE_REF``,
   ``CI_MERGE_REQUEST_TARGET_BRANCH_NAME``), because a CI checkout has no reflog;
3. the nearest branch the working copy knows whose merge-base with ``HEAD`` is
   newer than the trunk's, from ``git for-each-ref`` and ``git merge-base``.

A parent counts only when its merge-base is strictly newer than the trunk's: a
parent already merged into the trunk leaves the trunk as the base. The third source
is a heuristic and has one blind spot, stated rather than hidden: a branch cut FROM
this one at an older commit looks exactly like a parent to git. A branch that holds
this branch's whole history is skipped, and the base and the branch it came from are
printed on every surface, so a wrong pick is visible where it is used.

**The header says which base, in every case** — the ref, the rule that chose it, and
how many files of the trunk's diff it attributed to the parent branch — so a reader
can tell a finding about this work from a finding about its parent's (#330, #344).

**The branch comes from the pull request first (BDL-UX #300).** A CI job checks a
pull request out on a detached HEAD, so the scope check skipped on every pull
request. ``GITHUB_HEAD_REF`` and GitLab's ``CI_MERGE_REQUEST_SOURCE_BRANCH_NAME``
name the branch before the checkout's own name is read.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.guards.config import GuardConfigError
from beadloom.doc_sync.git_baseline import (
    branch_names,
    branch_start_point,
    commit_distance,
    current_branch,
    is_ancestor,
    merge_base,
    paths_changed_since,
    ref_exists,
    short_commit,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

#: The base was named by the caller (``scope-check --base``, ``review-brief --since``).
BASE_EXPLICIT = "explicit"

#: The base is the merge-base with the branch this one was cut from.
BASE_PARENT = "parent"

#: The base is the trunk, because no unmerged branch was found to have been cut from.
BASE_TRUNK = "trunk"

#: The CI variables naming the branch a pull or merge request carries, GitHub first.
HEAD_BRANCH_VARIABLES = ("GITHUB_HEAD_REF", "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME")

#: The CI variables naming the branch a pull or merge request is to be merged into.
TARGET_BRANCH_VARIABLES = ("GITHUB_BASE_REF", "CI_MERGE_REQUEST_TARGET_BRANCH_NAME")

#: The guard whose ``options.trunk`` names this project's trunk branch. Read from
#: there rather than declared again: ``working-branch`` already asks the project
#: for the name, and two declarations of one branch are two things that can
#: disagree about which ref an approval was given against.
_TRUNK_OPTION_OWNER = "working-branch"
_TRUNK_OPTION = "trunk"

#: The remote whose tracking branches stand for the shared ones.
_REMOTE = "origin"

#: Prefixes a reflog may spell a start point with, removed to compare names.
_REF_PREFIXES = ("refs/heads/", "refs/remotes/")


@dataclass(frozen=True)
class ScopeBase:
    """The ref a branch's work is compared against, and how it was chosen."""

    ref: str
    """What git compares against: a ref name, or the merge-base's short hash."""

    kind: str
    """:data:`BASE_EXPLICIT`, :data:`BASE_PARENT` or :data:`BASE_TRUNK`."""

    trunk: str
    """The trunk ref the attribution is counted against."""

    parent: str | None = None
    """The branch this one was cut from, when the base is its merge-base."""

    parent_files: int | None = None
    """Files the trunk's diff holds and this base's does not; ``None`` when uncounted."""

    def describe(self) -> str:
        """The base, the rule that chose it and the attribution, as one clause."""
        if self.kind == BASE_EXPLICIT:
            rule = "named by the caller"
        elif self.kind == BASE_PARENT:
            rule = f"the merge-base with {self.parent}, the branch this one was cut from"
        else:
            rule = "the trunk: this branch was cut from no unmerged branch"
        if self.parent_files is None:
            counted = "git could not compare it with the trunk, so no file was counted"
            return f"{self.ref} ({rule}; {counted})"
        if self.kind == BASE_TRUNK:
            return f"{self.ref} ({rule})"
        counted = f"{self.parent_files} file(s) attributed to the parent branch"
        return f"{self.ref} ({rule}; {counted})"

    def payload(self) -> dict[str, object]:
        """The base as structured data, for every JSON surface that prints it."""
        return {
            "ref": self.ref,
            "kind": self.kind,
            "parent": self.parent,
            "parent_files": self.parent_files,
            "trunk": self.trunk,
        }


def trunk_name(project_root: Path) -> str:
    """The trunk branch's name, as the ``working-branch`` guard declares it."""
    from beadloom.application.guards.checks.working_branch import DEFAULT_TRUNK
    from beadloom.application.guards.config import load_guards_config

    try:
        options = load_guards_config(project_root).spec_for(_TRUNK_OPTION_OWNER).options
    except GuardConfigError:
        # A malformed flow.yml is `config-check`'s finding, not this one's. The
        # shipped default keeps the comparison running rather than adding a
        # second reporter of one fault.
        return DEFAULT_TRUNK
    return str(options.get(_TRUNK_OPTION, DEFAULT_TRUNK))


def trunk_ref(project_root: Path) -> str:
    """The trunk as git should compare against it: ``origin/<trunk>``, else ``<trunk>``.

    Not a preference: measured on this repository with a local ``main`` two commits
    behind the remote, ``--since main`` reported another work item's LANDED change
    as this branch's, and ``--since origin/main`` did not. The remote branch is also
    what the pull request is compared against, which is where the approval is spent.
    """
    trunk = trunk_name(project_root)
    remote = f"{_REMOTE}/{trunk}"
    return remote if ref_exists(project_root, remote) else trunk


def working_branch(project_root: Path, *, environ: Mapping[str, str] | None = None) -> str | None:
    """The branch this run judges: the pull or merge request's, else the checkout's.

    ``None`` on a detached HEAD outside a pull or merge request, which is a reason
    to have judged nothing, never a branch named ``HEAD``.
    """
    env = os.environ if environ is None else environ
    for variable in HEAD_BRANCH_VARIABLES:
        value = env.get(variable, "").strip()
        if value:
            return value
    return current_branch(project_root)


def scope_base(
    project_root: Path,
    *,
    explicit: str | None = None,
    branch: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ScopeBase:
    """The base a branch's work is judged against: ``explicit``, the parent's, the trunk.

    *branch* names the working branch instead of resolving it with
    :func:`working_branch`; *environ* replaces ``os.environ`` for the CI variables.
    """
    env = os.environ if environ is None else environ
    trunk = trunk_ref(project_root)
    if explicit:
        return _counted(project_root, ScopeBase(ref=explicit, kind=BASE_EXPLICIT, trunk=trunk))
    working = branch if branch is not None else working_branch(project_root, environ=env)
    found = _parent_fork(project_root, working=working, trunk=trunk, environ=env)
    if found is None:
        answered = paths_changed_since(project_root, trunk) is not None
        return ScopeBase(
            ref=trunk, kind=BASE_TRUNK, trunk=trunk, parent_files=0 if answered else None
        )
    parent, fork = found
    return _counted(
        project_root, ScopeBase(ref=fork, kind=BASE_PARENT, trunk=trunk, parent=parent)
    )


def _counted(project_root: Path, base: ScopeBase) -> ScopeBase:
    """*base* with the files of the trunk's diff it leaves out counted."""
    on_trunk = paths_changed_since(project_root, base.trunk)
    on_base = paths_changed_since(project_root, base.ref)
    if on_trunk is None or on_base is None:
        return base
    return ScopeBase(
        ref=base.ref,
        kind=base.kind,
        trunk=base.trunk,
        parent=base.parent,
        parent_files=len(on_trunk - on_base),
    )


def _parent_fork(
    project_root: Path, *, working: str | None, trunk: str, environ: Mapping[str, str]
) -> tuple[str, str] | None:
    """The branch this one was cut from and the merge-base with it, or ``None``.

    The first source that names a branch git resolves decides, and a named branch
    that is the trunk, or whose merge-base is no newer than the trunk's, decides
    for the trunk: the nearest-branch search runs only when nothing was named.
    """
    trunk_fork = merge_base(project_root, "HEAD", trunk)
    name = trunk_name(project_root)
    names = {name, f"{_REMOTE}/{name}", trunk}
    for parent in _named_parents(project_root, working=working, environ=environ):
        if _without_prefix(parent) in names:
            return None
        fork = _newer_fork(project_root, parent, trunk_fork)
        return (parent, fork) if fork is not None else None
    return _nearest_branch(project_root, working=working, names=names, trunk_fork=trunk_fork)


def _named_parents(
    project_root: Path, *, working: str | None, environ: Mapping[str, str]
) -> Iterator[str]:
    """Branches a source NAMES as this one's parent, reflog first, each one git resolves."""
    if working:
        start = branch_start_point(project_root, working)
        if (
            start is not None
            and not _is_itself(_without_prefix(start), working)
            and ref_exists(project_root, start)
        ):
            yield _without_prefix(start)
    for variable in TARGET_BRANCH_VARIABLES:
        target = environ.get(variable, "").strip()
        if not target:
            continue
        for candidate in (f"{_REMOTE}/{target}", target):
            if ref_exists(project_root, candidate):
                yield candidate
                break


def _nearest_branch(
    project_root: Path, *, working: str | None, names: set[str], trunk_fork: str | None
) -> tuple[str, str] | None:
    """The branch whose merge-base with ``HEAD`` is nearest and newer than the trunk's."""
    found: list[tuple[int, str, str]] = []
    for name in branch_names(project_root) or ():
        if name in names or (working and _is_itself(name, working)):
            continue
        if is_ancestor(project_root, "HEAD", name):
            # It holds this branch's whole history: a copy or a branch cut from it.
            continue
        fork = merge_base(project_root, "HEAD", name)
        if fork is None or not _is_newer(project_root, fork, trunk_fork):
            continue
        distance = commit_distance(project_root, fork, "HEAD")
        if distance is not None:
            found.append((distance, name, fork))
    if not found:
        return None
    _distance, name, fork = min(found)
    short = short_commit(project_root, fork)
    return (name, short) if short is not None else None


def _newer_fork(project_root: Path, parent: str, trunk_fork: str | None) -> str | None:
    """The merge-base with *parent* as a short hash, when it is newer than the trunk's."""
    fork = merge_base(project_root, "HEAD", parent)
    if fork is None or not _is_newer(project_root, fork, trunk_fork):
        return None
    return short_commit(project_root, fork)


def _is_newer(project_root: Path, fork: str, trunk_fork: str | None) -> bool:
    """Whether *fork* is strictly newer than the trunk's merge-base with ``HEAD``.

    No trunk to compare with is no reason to refuse a parent the working copy names.
    """
    if trunk_fork is None:
        return True
    return fork != trunk_fork and is_ancestor(project_root, trunk_fork, fork)


def _without_prefix(name: str) -> str:
    """*name* without the ``refs/heads/`` or ``refs/remotes/`` a reflog may spell."""
    for prefix in _REF_PREFIXES:
        if name.startswith(prefix):
            return name.removeprefix(prefix)
    return name


def _is_itself(name: str, working: str) -> bool:
    """Whether *name* is the working branch or a remote's tracking copy of it."""
    _remote, _, rest = name.partition("/")
    return working in (name, rest)
