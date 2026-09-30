"""A project directory made a git repository with one commit, for tests of links at a commit.

BDL-076 B4 (``beadloom-ujzb.8``). ``docs site`` links a repository path at the
commit the site was generated from, and a project that is not the top of its own
git repository has no such commit, so its paths get no link. A test of a link
therefore needs the project committed; this is that step, written once.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

#: A committer identity for the one commit, so the step does not depend on the
#: machine's git configuration.
_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


def git(cwd: Path, *args: str) -> str:
    """Run git in *cwd* and return its standard output, stripped; raise on failure."""
    result = subprocess.run(  # noqa: S603 - fixed git arguments written by the calling test
        ["git", *args],  # noqa: S607 - the git on PATH, as the generator uses
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def commit_project(root: Path, *, origin: str | None = None) -> str:
    """Make *root* a git repository holding everything in it, and return the commit.

    *origin*, when given, is added as the ``origin`` remote before the commit.
    """
    git(root, "init", "-q")
    if origin is not None:
        git(root, "remote", "add", "origin", origin)
    git(root, "add", "-A")
    git(root, *_IDENTITY, "commit", "-q", "-m", "the project")
    return git(root, "rev-parse", "HEAD")
