"""Where the git root stands against the project root, read from git.

BDL-083 S2e (``beadloom-7pd6``), BDL-UX #325, the owner's ruling of 2026-10-12. Beadloom takes
its project root from the current directory or ``--project`` and never searches upward, while
git answers every question in paths relative to the root of its working tree. When
``.beadloom/`` sits in a subfolder of a repository, the two frames disagree: ``sync-check
--since`` reads ``git show <ref>:<path>`` with a path git does not hold at that place, both
sides come back empty, and every pair is called fresh whatever changed. Nested roots are a
transition-period layout, so the answer is a refusal by name rather than support, and this
module is the one reader every refusing surface asks.

The question is put to git (``rev-parse --show-cdup``) rather than answered by looking for a
``.git`` above the directory, because git's answer is the one the other commands will act
on: a linked worktree, a submodule and ``GIT_CEILING_DIRECTORIES`` are all git's to decide.
The answer is a run of ``../`` and nothing else, so no path git prints is decoded here.

``None`` means "not nested": the project root is the git root, or it is in no repository,
or git could not answer. None of those is a layout this module refuses, and a missing git
fails the commands that need it on their own terms.
"""

# beadloom:domain=infrastructure
# beadloom:component=git-root

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class NestedRoot:
    """A project root that lies below the root of the git working tree holding it."""

    project_root: Path
    git_root: Path

    def sentence(self) -> str:
        """The refusal every surface prints: both roots, and the rule that refuses them."""
        inside = self.project_root.relative_to(self.git_root).as_posix()
        return (
            f"the git root is above the project root: the project root is {self.project_root}, "
            f"the git root {self.git_root}. Git answers in paths relative to its own root, so "
            "the project root must be the git root — put .beadloom/ at the git root, or give "
            f"{inside}/ a repository of its own."
        )


def nested_root(project_root: Path) -> NestedRoot | None:
    """The git root when it lies above *project_root*, or ``None`` when it does not."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-cdup"],  # noqa: S607 - the git on PATH, as every reader
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        # git missing or not executable, or an unusable cwd: no answer, which is not a nesting.
        return None
    if result.returncode != 0:
        return None
    up = result.stdout.decode("ascii", errors="replace").strip()
    if not up:
        return None
    resolved = project_root.resolve()
    return NestedRoot(project_root=resolved, git_root=(resolved / up).resolve())
