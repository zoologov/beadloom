"""This repository's portal is the output of ``docs site``, and git keeps none of it.

BDL-076 slice 2. The PRD's goal for adopters ends with "this repository builds its
own portal through the same path; no private copy remains". Before B2
(``beadloom-qki6``) the theme, the viewer and the VitePress config were tracked
under ``site/``, and they were the copy an adopter could not get. Now ``site/`` is
what ``beadloom docs site --out site`` writes from the installed package, and the
CI jobs that build and deploy the portal run that command first.

Two claims, because they fail differently. The ``.gitignore`` line keeps a
generated ``site/`` out of ``git add``; the snapshot shows that no file under
``site/`` is tracked, which an ignore line cannot undo once a file was forced in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path


def test_this_repositorys_gitignore_ignores_the_portal_output_whole() -> None:
    lines = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/site/" in lines


def test_no_file_of_the_portal_is_tracked_or_left_unignored(self_check_snapshot: Path) -> None:
    """The snapshot holds every tracked file and every untracked one git would not ignore."""
    if not (self_check_snapshot / ".git").is_dir():
        pytest.skip(
            "the snapshot was walked, not listed by git, so it holds a generated site/ "
            "whether git keeps it or not; this claim needs a git work tree"
        )

    kept = sorted(
        path.relative_to(self_check_snapshot).as_posix()
        for path in (self_check_snapshot / "site").rglob("*")
        if path.is_file()
    )

    assert kept == []
