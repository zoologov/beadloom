"""No check prints a remediation that cannot clear the reason it was printed for.

BDL-069 S1, bead `beadloom-h7b3`, the worse half of BDL-UX #282. Measured before
this bead on a repository whose package document did not name one of its modules:
the gate printed "run `beadloom sync-update <ref>` to review and re-attest",
`sync-update --yes --all` exited 0 and reported the pairs re-attested, and the
verdict did not move. `sync-update` rewrites recorded hashes, and
`missing_modules` is a claim about what the document says.

**Whether attesting clears a reason is measured here, not declared.** Each case
produces its reason through the real pipeline, re-attests exactly what
`sync-update --yes` claims, and reads the check again. The engine's flag has to
agree with that measurement for every reason, which is what keeps the flag from
becoming a second opinion about the pipeline.

The flag is an ALLOW-LIST. A reason added later is not clearable until somebody
measures that it is, so it cannot inherit a re-attest instruction by default —
the failure this bead exists to remove.
"""

from __future__ import annotations

import re
import shutil
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner

from beadloom.application.gate import _sync_finding, _sync_unverified_finding
from beadloom.application.reindex import reindex
from beadloom.doc_sync.engine import (
    REASONS_ATTESTATION_CLEARS,
    attestation_clears,
    content_remedy,
)
from beadloom.services.cli import main
from beadloom.services.commands.docsync import (
    _HOOK_TEMPLATE_BLOCK,
    _HOOK_TEMPLATE_WARN,
    _build_sync_report,
)
from tests import stale_pair_project as project

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: Each mutation, and the one reason it produces. The case list is the population
#: the flag is measured over; a reason missing from it is not measured.
_MUTATIONS: dict[str, Callable[[Path], None]] = {
    "hash_changed": project.change_a_body,
    "hash_changed_since_head": project.change_a_body_on_a_rebuilt_index,
    "symbols_changed": project.add_an_annotated_module,
    "untracked_files": project.add_an_unannotated_module,
    "missing_modules": project.unname_a_module,
}


def _row(reason: str, **extra: str) -> dict[str, Any]:
    return {
        "status": "stale",
        "ref_id": project.REF_ID,
        "doc_path": project.DOC_PATH,
        "code_path": "src/widgets/alpha.py",
        "reason": reason,
        **extra,
    }


class TestTheFlagIsTheMeasurement:
    """``attestation_clears`` says what re-attesting did, reason by reason."""

    @pytest.mark.parametrize("reason", sorted(_MUTATIONS))
    def test_the_flag_agrees_with_what_attesting_did(self, reason: str, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        _MUTATIONS[reason](root)
        before = {row["reason"] for row in project.stale(root)}
        # Anti-vacuity: the mutation produced the reason under test and no other,
        # so the reading after the attestation is a reading about this reason.
        assert before == {reason}, project.verdicts(root)

        project.attest_stale(root)

        still = {row["reason"] for row in project.stale(root)}
        assert (reason not in still) is attestation_clears(reason), still

    def test_every_reason_the_flag_clears_was_measured(self) -> None:
        """The allow-list cannot grow past the population measured above."""
        assert set(REASONS_ATTESTATION_CLEARS) <= set(_MUTATIONS)

    def test_a_reason_nobody_has_measured_is_not_clearable(self) -> None:
        assert attestation_clears("a_reason_added_next_year") is False


class TestTheContentRemedyClearsWhatItNames:
    """The instruction printed instead of a re-attestation, followed literally."""

    def test_naming_the_modules_it_names_clears_missing_modules(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.unname_a_module(root)
        row = project.stale(root)[0]
        remedy = content_remedy(row)
        assert row["details"] in remedy
        assert project.DOC_PATH in remedy

        document = root / "docs" / project.DOC_PATH
        text = document.read_text(encoding="utf-8")
        document.write_text(text + f"- `{row['details']}.py`\n", encoding="utf-8")
        reindex(root)

        assert project.stale(root) == []

    def test_the_track_marker_it_names_clears_untracked_files(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.add_an_unannotated_module(root)
        row = project.stale(root)[0]
        remedy = content_remedy(row)
        assert row["details"] in remedy
        marker = re.search(r"`(<!-- beadloom:track=<path> -->)`", remedy)
        assert marker is not None, remedy

        document = root / "docs" / project.DOC_PATH
        path = f"{project.SOURCE}{row['details']}"
        line = marker.group(1).replace("<path>", path)
        text = document.read_text(encoding="utf-8")
        # The module is named too: pairing the file makes the document answer for
        # it, and a document that does not name it is stale for THAT reason.
        document.write_text(f"{text}{line}\n- `{row['details']}`\n", encoding="utf-8")
        reindex(root)

        assert [r for r in project.stale(root) if r["reason"] == "untracked_files"] == []

    @pytest.mark.parametrize(
        ("reason", "claim"),
        [
            ("untracked_files", "re-attesting cannot clear untracked_files"),
            ("missing_modules", "re-attesting cannot clear missing_modules"),
            # Not measured, so not claimed either way: the remedy says what is known.
            ("a_future_reason", "re-attesting is not known to clear a_future_reason"),
        ],
    )
    def test_a_content_remedy_never_tells_the_reader_to_re_attest(
        self, reason: str, claim: str
    ) -> None:
        remedy = content_remedy(_row(reason, details="gamma"))
        assert "sync-update" not in remedy
        assert claim in remedy


class TestTheGateChoosesItsRemediationFromTheFlag:
    """``_sync_finding`` for a stale pair: one instruction per kind of reason."""

    @pytest.mark.parametrize("reason", sorted(REASONS_ATTESTATION_CLEARS))
    def test_a_reason_attesting_clears_keeps_the_re_attest_instruction(self, reason: str) -> None:
        finding = _sync_finding(_row(reason))
        assert f"beadloom sync-update {project.REF_ID}" in str(finding["remediation"])

    @pytest.mark.parametrize("reason", ["untracked_files", "missing_modules", "a_future_reason"])
    def test_a_reason_attesting_cannot_clear_is_not_told_to_re_attest(self, reason: str) -> None:
        finding = _sync_finding(_row(reason, details="gamma"))
        remediation = str(finding["remediation"])
        assert "sync-update" not in remediation
        assert remediation == content_remedy(_row(reason, details="gamma"))

    def test_the_why_names_the_pair_and_what_the_check_found(self) -> None:
        finding = _sync_finding(_row("missing_modules", details="beta"))
        why = str(finding["why"])
        assert f"{project.DOC_PATH} <-> src/widgets/alpha.py" in why
        assert "missing_modules: beta" in why

    def test_a_row_with_no_code_file_names_no_pair(self) -> None:
        """A document-level row has no code file, and inventing an arrow would lie."""
        row = _row("missing_modules", details="beta")
        row["code_path"] = ""
        assert "<->" not in str(_sync_finding(row)["why"])


class TestTheUnverifiedRemediationCanBeFollowed:
    """A pair that was not verified is not cleared by the bare command either."""

    def test_the_no_baseline_remediation_names_the_form_that_attests(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        # No git and a rebuilt index: nothing to compare against.
        shutil.rmtree(root / ".git")
        (root / ".beadloom" / "beadloom.db").unlink()
        reindex(root)
        rows = [r for r in project.verdicts(root) if r["status"] == "unverified"]
        assert {r["reason"] for r in rows} == {"no_baseline"}, rows

        remediation = str(_sync_unverified_finding(rows[0])["remediation"])
        command = re.search(r"`beadloom (sync-update [^`]+)`", remediation)
        assert command is not None, remediation
        result = CliRunner().invoke(main, [*command.group(1).split(), "--project", str(root)])
        assert result.exit_code == 0, result.output

        assert [r for r in project.verdicts(root) if r["status"] != "ok"] == []

    def test_a_sibling_row_is_not_told_to_re_attest_itself(self) -> None:
        """Bead `.78`: a pair nobody can revise is not handed `sync-update`."""
        row = _row("sibling_symbols_changed", details="gamma.py")
        row["status"] = "unverified"
        finding = _sync_unverified_finding(row)
        assert "sync-update" not in str(finding["remediation"])
        assert "gamma.py" in str(finding["remediation"])
        assert "index was rebuilt" not in str(finding["why"])


class TestTheOtherPrintedInstructionsFollowTheFlag:
    """The hook and the markdown report print an instruction too."""

    @pytest.mark.parametrize(
        "template", [_HOOK_TEMPLATE_WARN, _HOOK_TEMPLATE_BLOCK], ids=["warn", "block"]
    )
    def test_the_hook_scopes_its_re_attest_instruction(self, template: str) -> None:
        lines = [ln for ln in template.splitlines() if "sync-update" in ln]
        assert lines, template
        for line in lines:
            for reason in REASONS_ATTESTATION_CLEARS:
                assert reason in line, line
            assert "which re-attesting cannot do" in line, line

    def test_a_report_over_content_reasons_does_not_recommend_sync_update(self) -> None:
        rows = [_row("missing_modules", details="beta")]
        report = _build_sync_report(rows)
        assert "sync-update" not in report
        assert content_remedy(rows[0]) in report

    def test_a_report_over_a_hash_reason_still_recommends_it(self) -> None:
        report = _build_sync_report([_row("hash_changed")])
        assert "sync-update" in report

    def test_a_report_against_a_git_ref_does_not_recommend_sync_update(
        self, tmp_path: Path
    ) -> None:
        """`--since` spells its verdict `hash_changed` and reads git, not the baseline.

        Measured: attesting every pair left `sync-check --since HEAD` exactly as
        stale as before, so the token alone cannot choose the instruction.
        """
        root = project.build(tmp_path / "proj")
        project.write(
            root, f"{project.SOURCE}alpha.py", project.annotated_module("alpha", "return 1")
        )

        def run(*args: str) -> Any:
            return CliRunner().invoke(main, [*args, "--project", str(root)])

        attested = run("sync-update", project.REF_ID, "--yes", "--all-pairs")
        assert attested.exit_code == 0, attested.output
        still = run("sync-check", "--since", "HEAD", "--porcelain")
        assert still.exit_code == 2, still.output  # the measurement the test rests on

        report = run("sync-check", "--since", "HEAD", "--report").output
        assert "sync-update" not in report, report
        assert f"revise {project.DOC_PATH}" in report, report
