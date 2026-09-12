"""`sync-update --yes` names the pairs it left stale, and why attesting did not move them.

BDL-069 S1, bead `beadloom-h7b3`, the RFC's Q1. The evidence is first-hand:
during this epic's scoping `sync-update --yes --all` returned rc 0 and
`Marked 2 ref(s) synced (4 pair(s) total)`, and the operator believed the defect
fixed. The command reported over the population it attested and said nothing
about the population it left.

Output only. What the command attests is BDL-UX #279 and is untouched, and so is
its exit code: every case below asserts rc 0 alongside the new lines, so a change
of verdict cannot ride in on a change of wording.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from click.testing import CliRunner

from beadloom.services.cli import main
from tests import stale_pair_project as project

if TYPE_CHECKING:
    from pathlib import Path

_SECOND_DOC = "widgets-guide.md"


def _sync_update(root: Path, *args: str) -> Any:
    return CliRunner().invoke(main, ["sync-update", *args, "--project", str(root)])


def _pair(row: dict[str, Any]) -> str:
    return f"{row['doc_path']} <-> {row['code_path']}"


class TestAContentReasonIsNamedAfterTheRun:
    """The measured defect: rc 0, pairs attested, verdict unmoved, nothing said."""

    def test_all_names_every_pair_the_check_still_reports_stale(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.unname_a_module(root)

        result = _sync_update(root, "--yes", "--all")

        assert result.exit_code == 0, result.output
        left = project.stale(root)
        # Anti-vacuity: the verdict really did not move, so there is something to name.
        assert len(left) == len(project.MODULES), left
        for row in left:
            assert _pair(row) in result.output, result.output
        assert "re-attesting cannot clear missing_modules" in result.output

    def test_one_ref_names_them_too(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.add_an_unannotated_module(root)

        result = _sync_update(root, project.REF_ID, "--yes")

        assert result.exit_code == 0, result.output
        left = project.stale(root)
        assert left, "the reason was expected to survive the attestation"
        for row in left:
            assert _pair(row) in result.output, result.output
        assert "re-attesting cannot clear untracked_files" in result.output

    def test_the_line_says_how_many_were_left(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.unname_a_module(root)

        result = _sync_update(root, "--yes", "--all")

        assert f"Still stale after this run: {len(project.MODULES)} pair(s)" in result.output


class TestARunThatClearedEverythingSaysSo:
    """The control: a hash reason is cleared, and the run says it checked."""

    def test_a_cleared_reason_is_reported_as_cleared(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.change_a_body(root)

        result = _sync_update(root, project.REF_ID, "--yes")

        assert result.exit_code == 0, result.output
        assert project.stale(root) == []
        assert "Still stale" not in result.output
        assert "no pair of widgets is still stale" in result.output

    def test_nothing_to_attest_prints_no_recheck(self, tmp_path: Path) -> None:
        """No attestation happened, so there is no 'after' to report on."""
        root = project.build(tmp_path / "proj")

        result = _sync_update(root, "--yes", "--all")

        assert result.exit_code == 0, result.output
        assert "No stale refs to re-baseline." in result.output
        assert "Re-checked" not in result.output


class TestAPairOutsideTheRunsScopeIsNotBlamedOnTheReason:
    """A clearable pair the operator did not name was left by choice, not by the rule."""

    def test_an_unclaimed_stale_pair_says_it_was_not_claimed(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj", documents=(project.DOC_PATH, _SECOND_DOC))
        project.change_a_body(root)
        stale = project.stale(root)
        assert {row["doc_path"] for row in stale} == {project.DOC_PATH, _SECOND_DOC}, stale

        result = _sync_update(root, project.REF_ID, "--yes", "--pair", project.DOC_PATH)

        assert result.exit_code == 0, result.output
        left = project.stale(root)
        assert [row["doc_path"] for row in left] == [_SECOND_DOC], left
        line = next(ln for ln in result.output.splitlines() if _pair(left[0]) in ln)
        assert "not claimed by this run" in line
        assert "re-attesting cannot clear" not in line
