"""What the commit gate says about the paths INSIDE the commit (`beadloom-0mdo.32`).

The residue of `beadloom-mr2l.81`. `.22` measured the half about paths outside a
commit and the hook has stated it since: ``N modified or untracked file(s)
outside this commit were not judged here``. This module pins the other half.

S1 shipped ``beadloom scope-check`` and the hook already called it, so the
wiring existed. What the hook did with the answer did not work: it read the
command as ``2>/dev/null`` and printed only when stdout came back non-empty,
while the ``NOT CHECKED`` reason went to stderr. Measured at ``8b40417`` on this
repository, both of these produce the empty string on that stream:

* a run that compared the staged paths and found none outside;
* a run that could attribute no work item at all — the consequence of BDL-UX
  #230 / ``beadloom-bdnv``, where a branch named ``features/BDL-068-S4`` matches
  no work-item folder and a whole slice reads unjudged.

So the gate printed the same nothing for both, and a commit nobody could
attribute read as clean. That is the false green BDL-068 exists to remove.

**The exempt set, measured before the reader was written**, over the eleven
commits of ``features/BDL-068`` at ``b7c9476..8b40417``: 52 paths, 11 a node
owns, 41 no node owns, 0 findings. The zero is the false-positive rate and it is
the smaller number. The larger one is that four paths in five were never
compared, because they are the tracker export, the planning documents, the
tests, the docs and the graph YAML — none of which a node owns. The exempt set
therefore needs no authored path list: it is already *the paths no node owns*,
derived from graph ownership, and an authored list would be a second thing to
keep in step with the graph. What it lacked was somewhere to be read.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.declared_scope import VERDICT_MARKER
from beadloom.services.cli import main

if TYPE_CHECKING:
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


def _hook(tmp_path: Path, mode: str) -> str:
    project = tmp_path / "proj"
    project.mkdir()
    subprocess.run(  # noqa: S603
        ["git", "init", "-q", "-b", "main", str(project)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    result = CliRunner().invoke(
        main, ["install-hooks", "--mode", mode, "--project", str(project)]
    )
    assert result.exit_code == 0, result.output
    return (project / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")


@pytest.mark.parametrize("mode", ["warn", "block"])
class TestTheGateStatesTheVerdictWhateverItIs:
    def test_the_hook_prints_the_verdict_outside_the_findings_branch(
        self, tmp_path: Path, mode: str
    ) -> None:
        """The line is unconditional, so a silent run and a clean run differ."""
        content = _hook(tmp_path, mode)
        assert "axes_verdict=" in content
        # The verdict echo is not nested inside the findings branch: that branch
        # closes between the two, so the line prints whether or not anything
        # fell outside.
        between = content.split('if [ -n "$axes_outside" ]')[1]
        between = between.split('echo "$axes_verdict"')[0]
        assert "\nfi\n" in between, between

    def test_the_hook_reads_the_verdict_off_stdout_rather_than_discarding_it(
        self, tmp_path: Path, mode: str
    ) -> None:
        """The marker is the one the command emits, not a second spelling."""
        content = _hook(tmp_path, mode)
        assert f"sed -n 's/^{VERDICT_MARKER}//p'" in content

    def test_the_hook_separates_the_verdict_line_from_the_finding_lines(
        self, tmp_path: Path, mode: str
    ) -> None:
        content = _hook(tmp_path, mode)
        assert "axes_outside=" in content
        assert "grep -v" in content.split("axes_outside=")[1].split("\n")[0]

    def test_a_command_that_returned_no_verdict_at_all_is_unjudged_not_clean(
        self, tmp_path: Path, mode: str
    ) -> None:
        """`beadloom` absent from PATH must not read as a comparison that passed."""
        content = _hook(tmp_path, mode)
        assert "NOT CHECKED" in content

    def test_the_axes_check_still_only_warns_in_both_modes(
        self, tmp_path: Path, mode: str
    ) -> None:
        """Warn, not block — see the module docstring for the population.

        Zero false positives over eleven commits is not enough to block on: only
        two of those commits touched a path a node owns at all, and one work
        item in this repository's sixty-four carries an `## Axes` section. A
        check that blocked would meet a repository that cannot satisfy it and be
        answered with `--no-verify`, which is the failure BDL-UX #118 was.
        """
        content = _hook(tmp_path, mode)
        block = content.split("Declared axes, over the paths this commit stages")[1]
        block = block.split("What this commit did NOT judge")[0]
        assert "failed=1" not in block
        assert "Warning:" in block


class TestThePorcelainProtocolTheHookReads:
    def test_the_verdict_leads_standard_output(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(
            main,
            ["scope-check", "--porcelain", "--project", str(tmp_path), "--branch", "main"],
        )
        assert result.stdout.startswith(VERDICT_MARKER)

    def test_an_unattributable_run_says_so_on_the_stream_the_gate_reads(
        self, tmp_path: Path
    ) -> None:
        result = CliRunner().invoke(
            main,
            ["scope-check", "--porcelain", "--project", str(tmp_path), "--branch", "main"],
        )
        assert "NOT CHECKED" in result.stdout

    def test_the_reason_is_stated_once_rather_than_on_two_streams(
        self, tmp_path: Path
    ) -> None:
        """It used to be stderr only, which `2>/dev/null` threw away."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["scope-check", "--porcelain", "--project", str(tmp_path), "--branch", "main"],
        )
        assert result.stdout.count("NOT CHECKED") == 1


class TestTheExemptSetOnThisRepositorysOwnCommits:
    """The measurement the warn/block decision was taken on, kept executable.

    Skipped where the history is absent — CI's tests job checks out at depth 1 —
    and the skip is declared rather than discovered.
    """

    @pytest.fixture
    def project(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        if not (root / ".beadloom" / "beadloom.db").is_file():
            pytest.skip("no index in this checkout, so no path can be resolved to a node")
        return root

    @staticmethod
    def _verdict(project: Path, commit: str) -> ScopeVerdict:
        from beadloom.application.declared_scope import scope_of_branch
        from beadloom.application.impact.boundary import open_boundary
        from beadloom.doc_sync.scope_check import check_commit_scope

        result = subprocess.run(  # noqa: S603
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],  # noqa: S607
            cwd=project,
            capture_output=True,
            text=True,
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
