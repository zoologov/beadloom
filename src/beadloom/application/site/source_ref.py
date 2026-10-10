# beadloom:domain=application
# beadloom:feature=site-generation
"""Which revision the portal's source links name: the built commit, or a branch origin holds.

BDL-080 S4c (``beadloom-e1xo``), BDL-UX #307. A source link is a permalink to the
commit the portal was built from, so a page shows the source it describes. A
portal built locally from a commit no remote branch holds linked every node to a
404, because the forge has never seen that commit.

The links name ``origin``'s address, so only ``origin``'s branches count: a
commit only another remote holds, a fork's, is a 404 there too (the S4 review's
M1, ``beadloom-af99.16``). When no branch of ``origin`` holds the built commit,
the links name a branch ``origin`` does hold, the first of:

1. the upstream of the branch the commit is on, when it is a branch of
   ``origin`` and this clone has fetched it;
2. the branch of ``origin`` with the same name, which a push without ``-u``
   leaves untracked;
3. ``origin``'s default branch, ``origin/HEAD``.

With none of them the links keep the commit, since nothing better is known, and
:func:`unpublished_warning` names the command that records the default branch.
A path that exists only in the unpublished commit is still a 404 on the branch:
nothing on the remote holds it.

Only refs this clone already has are read; the remote is never contacted, so a
remote branch fetched long ago still counts as holding what it held then.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The remote whose branches hold or stand in for the built commit, the one the
#: links are read from when the project declares no address.
_ORIGIN = "origin"
_REMOTES = "refs/remotes/"
_ORIGIN_BRANCHES = f"{_REMOTES}{_ORIGIN}/"
_HEADS = "refs/heads/"
#: How many characters of a commit the warning shows: enough to name one in any repository.
SHORT_COMMIT = 12


@dataclass(frozen=True)
class SourceRef:
    """The commit the portal was built from, the revision its links name, and whether it is pushed.

    ``linked`` is ``commit`` when a branch of ``origin`` holds the commit, and
    when no branch can stand in for it; otherwise it is the name of the branch on
    ``origin``. ``pushed`` is ``False`` only when git says no branch of ``origin``
    holds the commit.
    """

    commit: str
    linked: str
    pushed: bool

    @property
    def on_branch(self) -> bool:
        """Whether the links name a branch rather than the commit."""
        return self.linked != self.commit

    def as_dict(self) -> dict[str, object]:
        """The data file's ``source_ref``: ``{commit, linked, pushed}``."""
        return {"commit": self.commit, "linked": self.linked, "pushed": self.pushed}


def _git(project_root: Path, *args: str) -> str | None:
    """Git's answer to *args* in *project_root*, stripped; ``None`` when git says no."""
    try:
        result = subprocess.run(  # noqa: S603 - fixed git arguments, no shell
            ["git", *args],  # noqa: S607 - the git on PATH, as every git read here
            cwd=project_root,
            capture_output=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )
    except OSError as exc:
        logger.debug("git is not available to read the remote branches: %s", exc)
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _exists(project_root: Path, ref: str) -> bool:
    return _git(project_root, "show-ref", "--verify", "--quiet", ref) is not None


def _upstream(project_root: Path, branch: str) -> str:
    """The name of *branch*'s upstream on ``origin``, when origin holds it here; else ``""``."""
    # A branch tracking another remote, or a local branch ("."), names no branch of origin.
    if _git(project_root, "config", "--get", f"branch.{branch}.remote") != _ORIGIN:
        return ""
    tracking = _git(project_root, "for-each-ref", "--format=%(upstream)", f"{_HEADS}{branch}")
    merge = _git(project_root, "config", "--get", f"branch.{branch}.merge")
    if not tracking or not merge or not _exists(project_root, tracking):
        return ""
    return merge.removeprefix(_HEADS)


def _same_name(project_root: Path, branch: str) -> str:
    """*branch* when ``origin`` has a branch of that name; else ``""``."""
    return branch if _exists(project_root, f"{_ORIGIN_BRANCHES}{branch}") else ""


def _default_branch(project_root: Path) -> str:
    """``origin``'s default branch as this clone records it (``origin/HEAD``); else ``""``."""
    head = _git(project_root, "symbolic-ref", "--quiet", f"{_ORIGIN_BRANCHES}HEAD")
    if not head or not head.startswith(_ORIGIN_BRANCHES):
        return ""
    return head.removeprefix(_ORIGIN_BRANCHES)


def _stand_in(project_root: Path) -> str:
    """The branch ``origin`` holds that stands in for an unpublished commit; ``""`` for none."""
    branch = _git(project_root, "symbolic-ref", "--quiet", "--short", "HEAD") or ""
    if branch:
        found = _upstream(project_root, branch) or _same_name(project_root, branch)
        if found:
            return found
    return _default_branch(project_root)


def source_ref_of(project_root: Path, commit: str) -> SourceRef:
    """The revision the links of a portal built from *commit* name, and why.

    *commit* is the built commit, read at the top of the project's own repository.
    """
    holders = _git(
        project_root, "for-each-ref", "--contains", commit, "--format=%(refname)", _ORIGIN_BRANCHES
    )
    if holders is None or holders:
        # Held by a branch of origin, or git cannot say: the permalink, as it always was.
        return SourceRef(commit=commit, linked=commit, pushed=True)
    stand_in = _stand_in(project_root)
    return SourceRef(commit=commit, linked=stand_in or commit, pushed=False)


def unpublished_warning(source_ref: SourceRef | None) -> str | None:
    """What ``docs site`` says on stderr about a portal built from an unpublished commit."""
    if source_ref is None or source_ref.pushed:
        return None
    short = source_ref.commit[:SHORT_COMMIT]
    said = f"Warning: the portal was built from {short}, which is on no branch of {_ORIGIN}, "
    if source_ref.on_branch:
        return (
            said + f"so its source links point at {source_ref.linked} instead; a path that "
            "exists only in that commit is not there. Push the commit and run "
            "`beadloom docs site` again for links to it."
        )
    return (
        said + f"and no branch of {_ORIGIN} stands in for it, so its source links point at "
        f"{short} and stay dead until it is pushed. Push it, or record {_ORIGIN}'s default "
        f"branch with `git remote set-head {_ORIGIN} --auto`, and run `beadloom docs site` again."
    )
