"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_the_commit_gate_states_what_it_compared.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.doc_sync.scope_check import ScopeVerdict


#: The eleven commits of `features/BDL-068` that preceded this bead, oldest
#: first. Named rather than derived: the population a decision was taken over
#: must not change under the decision after the fact.
_THE_MEASURED_POPULATION = (
    "b7c9476",
    "adce04f",
    "edc20cd",
    "2b8bf9c",
    "8b29918",
    "9d73c99",
    "5fd9636",
    "a6f2272",
    "f7e5419",
    "b444c30",
    "8b40417",
)


class TestTheExemptSetOnThisRepositorysOwnCommits:
    """The measurement the warn/block decision was taken on, kept executable.

    Skipped where the history is absent — CI's tests job checks out at depth 1 —
    and the skip is declared rather than discovered.
    """

    @pytest.fixture
    def project(self, self_check_snapshot: Path) -> Path:
        # The self-check snapshot (BDL-074 A2): its index answers ownership, and
        # it carries the git history, so `git diff-tree` below runs in the copy.
        return self_check_snapshot

    @staticmethod
    def _verdict(project: Path, commit: str) -> ScopeVerdict:
        from beadloom.application.declared_scope import scope_of_branch
        from beadloom.application.impact.boundary import open_boundary
        from beadloom.doc_sync.scope_check import check_commit_scope

        result = subprocess.run(  # noqa: S603
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],  # noqa: S607
            cwd=project,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            pytest.skip(f"commit {commit} is not in this checkout")
        scope, reason = scope_of_branch(project, branch="features/BDL-068")
        if scope is None:
            pytest.skip(f"BDL-068 declares no axes in this checkout: {reason}")
        boundary = open_boundary(project)
        paths = result.stdout.split()
        ownership = {
            path: (owner.node, owner.domain)
            for path in paths
            for owner in (boundary.owner_of(path),)
        }
        return check_commit_scope(paths, scope, ownership=ownership)

    @pytest.mark.parametrize("commit", _THE_MEASURED_POPULATION)
    def test_no_commit_of_this_branch_is_a_false_positive(
        self, project: Path, commit: str
    ) -> None:
        verdict = self._verdict(project, commit)
        assert verdict.findings == (), [f.path for f in verdict.findings]

    def test_the_population_is_mostly_paths_no_node_owns(self, project: Path) -> None:
        """The number that made warn the honest default, not the zero above."""
        judged = sum(self._verdict(project, c).judged for c in _THE_MEASURED_POPULATION)
        unowned = sum(self._verdict(project, c).unowned for c in _THE_MEASURED_POPULATION)
        assert judged == 11, judged
        assert unowned == 41, unowned
