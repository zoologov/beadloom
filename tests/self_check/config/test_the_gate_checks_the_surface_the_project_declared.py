"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_the_gate_checks_the_surface_the_project_declared.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.application.typed_surface import declared_typed_surface

if TYPE_CHECKING:
    from pathlib import Path

#: The commits of `features/BDL-068` that staged Python at all, with the two
#: counts the warn/block decision was taken over: paths matching the filter the
#: hook carried AT THE TIME, `^(src|tests)/.*\.py$`, and how many of those are
#: inside the surface `pyproject` declares. MEASURED at `b7c9476..49c2ebe`, each
#: commit against its own tree in a linked worktree. `beadloom-0mdo.42` has since
#: replaced that filter, and the counts below are deliberately still taken with
#: it: they record the population a past decision was taken over, and rewriting
#: them to today's filter would restate the decision as one nobody made.
#:
#: The mypy half of that measurement is NOT re-run here and is deliberately not:
#: it takes 24 checkouts and 31 type-check runs. It is recorded instead --
#: the old block warned on 4 of these 7 and all 4 warnings were false; a
#: surface-scoped check is clean on all 7. What the test holds is the
#: POPULATION, so a decision taken over these seven commits cannot quietly come
#: to be about a different seven.
_MEASURED_COMMITS = {
    "9d73c995f343e49f82005c863602b632ffe447e2": (6, 3),
    "5fd96360d91026e495a44465012d90a66087da6c": (16, 8),
    "a1988326be8ced470090472641644ccc0f72e35d": (6, 4),
    "a5bf5aeda823b9247c384e1b10adfb5927099dfb": (12, 5),
    "4fce7d29d00912fdc5ed3008aa7b9497b39eef72": (7, 2),
    "204fc95846f08b6f7f70ff9919a6c495c2c88507": (2, 1),
    "ded748d18a83fc9305edc30d29147622ce179825": (14, 8),
}


class TestThisRepositorysOwnSurface:
    """The regression `beadloom-mr2l.82` shipped: a list that stopped agreeing."""

    def test_the_derived_surface_is_the_one_ci_type_checks(
        self, self_check_snapshot: Path
    ) -> None:
        surface = declared_typed_surface(self_check_snapshot)
        assert [r.path for r in surface.roots] == ["src/beadloom"]
        workflow = (self_check_snapshot / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        checked = [
            line.split("uv run mypy", 1)[1].strip()
            for line in workflow.splitlines()
            if "uv run mypy" in line
        ]
        assert checked, "ci.yml no longer runs mypy; this surface has no CI leg"
        for target in checked:
            assert surface.roots[0].path.startswith(target.rstrip("/")), (
                f"pyproject declares {surface.roots[0].path} typed and ci.yml "
                f"checks {target}; one of the two moved without the other"
            )

    def test_the_tests_tree_is_outside_the_declared_surface(
        self, self_check_snapshot: Path
    ) -> None:
        """970 errors in 90 files, and not one a violation of a declared standard."""
        surface = declared_typed_surface(self_check_snapshot)
        assert not surface.contains("tests/conftest.py")
        assert surface.contains("src/beadloom/application/typed_surface.py")


class TestThePopulationTheDecisionWasTakenOver:
    """Seven real commits, and how much of each the old block judged.

    Read from the self-check snapshot, which carries this repository's history
    (BDL-074 A3). Skipped where the history is not reachable -- a clean room
    built with ``git archive`` has no ``.git``, and a measurement that cannot be
    made is reported as not made rather than as passing.
    """

    @staticmethod
    def _staged(root: Path, commit: str) -> list[str] | None:
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "git",
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "--diff-filter=ACMR",
                commit,
            ],
            cwd=root,
            capture_output=True,
            # git writes path names as bytes; UTF-8 is what it produces for a
            # non-ASCII one, and leaving the codec to the image is the same
            # defect `_run_hook` above carries a comment about.
            encoding="utf-8",
            errors="strict",
            check=False,
        )
        if result.returncode != 0:
            return None
        pattern = re.compile(r"^(src|tests)/.*\.py$")
        return [p for p in result.stdout.splitlines() if pattern.match(p)]

    @pytest.mark.parametrize("commit", sorted(_MEASURED_COMMITS))
    def test_each_commits_two_counts_are_the_ones_measured(
        self, commit: str, self_check_snapshot: Path
    ) -> None:
        staged = self._staged(self_check_snapshot, commit)
        if staged is None:
            pytest.skip(f"{commit[:8]} is not reachable from here")
        surface = declared_typed_surface(self_check_snapshot)
        inside = [p for p in staged if surface.contains(p)]
        assert (len(staged), len(inside)) == _MEASURED_COMMITS[commit]

    def test_the_old_block_judged_more_than_half_of_what_it_was_handed_wrongly(
        self, self_check_snapshot: Path
    ) -> None:
        """Across the seven: 63 paths handed to mypy, 31 of them declared typed."""
        totals = [self._staged(self_check_snapshot, c) for c in _MEASURED_COMMITS]
        if any(t is None for t in totals):
            pytest.skip("the branch history is not reachable from here")
        surface = declared_typed_surface(self_check_snapshot)
        staged = [p for t in totals if t is not None for p in t]
        inside = [p for p in staged if surface.contains(p)]
        assert (len(staged), len(inside)) == (63, 31)
