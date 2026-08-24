"""The five section-quality checks (BDL-061 S4b).

CONTEXT's reason for them: *these planning documents read well because of
conventions written down nowhere, and a practice that is not a mechanism does
not survive the session.* Each check is proved here on a document that violates
it AND on one that does not — a check that reports everything is as useless as
one that reports nothing, and this epic has shipped both shapes.

The last class fires the checks at THIS repository's own planning documents. The
counts are asserted as "more than zero", not pinned: pinning them would make
every future document edit a test failure, while zero would mean the checks read
nothing here and nobody would notice.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.doc_quality import (
    CHECK_NAMES,
    DECISION_REASON,
    MEASURABLE_GOAL,
    PENDING_IN_APPROVED,
    RISK_MITIGATION,
    UNFILLED_PLACEHOLDER,
    check_document,
    check_documents,
    is_approved,
)

if TYPE_CHECKING:
    from pathlib import Path

_APPROVED = "> **Status:** Approved\n\n"


def _checks(text: str, *, placeholders: tuple[str, ...] = ()) -> list[str]:
    report = check_document(text, path="D.md", placeholders=placeholders)
    return [f.check for f in report.findings]


# ---------------------------------------------------------------------------
# 1. A goal carries a measurable clause
# ---------------------------------------------------------------------------


class TestMeasurableGoal:
    def test_a_goal_with_no_number_is_reported(self) -> None:
        text = "## Goals\n\n- Make the tool better and faster.\n"
        assert _checks(text) == [MEASURABLE_GOAL]

    def test_a_goal_with_a_measured_quantity_passes(self) -> None:
        text = "## Goals\n\n- The core shrinks from 440 to 376 lines.\n"
        assert _checks(text) == []

    def test_a_bead_identifier_is_not_a_measurable_clause(self) -> None:
        """``BDL-061`` and ``v2.2`` are names with digits in them, not quantities."""
        text = "## Goals\n\n- Finish BDL-061 before v2.2 ships.\n"
        assert _checks(text) == [MEASURABLE_GOAL]

    def test_a_goal_continued_on_the_next_line_is_read_whole(self) -> None:
        text = (
            "## Goals\n\n"
            "- [ ] **G1 — Rules become mechanisms.** Every rule is classified,\n"
            "      and the shipped core shrinks by 64 lines.\n"
        )
        assert _checks(text) == []

    def test_prose_outside_a_goal_section_is_not_a_goal(self) -> None:
        text = "## Problem\n\n- Everything is bad and nothing works.\n"
        assert _checks(text) == []

    def test_a_prose_goal_is_read_when_the_section_has_no_bullets(self) -> None:
        text = "## Goal\n\nTurn prose into mechanisms so the flow survives.\n"
        assert _checks(text) == [MEASURABLE_GOAL]


# ---------------------------------------------------------------------------
# 2. A decision carries its reason
# ---------------------------------------------------------------------------


_DECISIONS = """\
## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-08-22 | Guards are data | {reason} |
"""


class TestDecisionReason:
    def test_a_decision_with_an_empty_reason_is_reported(self) -> None:
        assert _checks(_DECISIONS.format(reason="")) == [DECISION_REASON]

    def test_a_decision_with_a_dash_for_a_reason_is_reported(self) -> None:
        assert _checks(_DECISIONS.format(reason="—")) == [DECISION_REASON]

    def test_a_decision_with_a_reason_passes(self) -> None:
        text = _DECISIONS.format(reason="a shell script is not portable")
        assert _checks(text) == []

    def test_a_table_with_no_reason_column_is_not_a_decision_table(self) -> None:
        text = (
            "## Beads\n\n"
            "| ID | Name | Status |\n|----|------|--------|\n"
            "| .13 | scenario binding | Done |\n"
        )
        assert _checks(text) == []


# ---------------------------------------------------------------------------
# 3. A risk carries a mitigation
# ---------------------------------------------------------------------------


_RISKS = """\
## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| The index goes stale | Med | High | {mitigation} |
"""


class TestRiskMitigation:
    def test_a_risk_with_no_mitigation_is_reported(self) -> None:
        assert _checks(_RISKS.format(mitigation="")) == [RISK_MITIGATION]

    @pytest.mark.parametrize("weak", ["Monitor it", "monitor", "TBD", "watch closely"])
    def test_a_mitigation_that_names_no_action_is_reported(self, weak: str) -> None:
        """CONTEXT states it outright: "monitor it" is not a mitigation."""
        assert _checks(_RISKS.format(mitigation=weak)) == [RISK_MITIGATION]

    def test_a_mitigation_that_names_an_action_passes(self) -> None:
        text = _RISKS.format(
            mitigation="monitor the pair count and fail the gate below 300"
        )
        assert _checks(text) == []


# ---------------------------------------------------------------------------
# 4. No Pending question in an Approved document
# ---------------------------------------------------------------------------


_QUESTIONS = """\
{status}
## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Where does the overlay live? | {decision} |
"""


class TestPendingInApproved:
    def test_a_pending_question_in_an_approved_document_is_reported(self) -> None:
        text = _QUESTIONS.format(status=_APPROVED, decision="Pending")
        assert _checks(text) == [PENDING_IN_APPROVED]

    def test_a_pending_with_a_leaning_is_still_pending(self) -> None:
        text = _QUESTIONS.format(status=_APPROVED, decision="Pending — likely .beadloom/")
        assert _checks(text) == [PENDING_IN_APPROVED]

    def test_a_decided_question_passes(self) -> None:
        text = _QUESTIONS.format(status=_APPROVED, decision="Decided: `.beadloom/flow/`")
        assert _checks(text) == []

    def test_a_draft_may_have_pending_questions(self) -> None:
        """A Draft is supposed to have open questions; reporting them teaches
        the author to ignore the check."""
        text = _QUESTIONS.format(status="> **Status:** Draft\n\n", decision="Pending")
        assert _checks(text) == []

    def test_an_undeclared_status_is_not_treated_as_approved(self) -> None:
        text = _QUESTIONS.format(status="", decision="Pending")
        assert _checks(text) == []

    @pytest.mark.parametrize("status", ["Approved", "APPROVED", "Accepted (v0.5.0)"])
    def test_an_agreed_status_is_recognised_however_it_is_spelled(
        self, status: str
    ) -> None:
        assert is_approved(f"> **Status:** {status}\n") is True

    def test_a_pending_row_outside_open_questions_is_not_reported(self) -> None:
        """PLAN's bead table marks unstarted beads ``Pending``; that is a
        status, not an undecided design question."""
        text = (
            _APPROVED + "## Beads\n\n"
            "| ID | Name | Status |\n|----|------|--------|\n"
            "| .14 | tests | Pending |\n"
        )
        assert _checks(text) == []


# ---------------------------------------------------------------------------
# 5. No unfilled placeholder
# ---------------------------------------------------------------------------


class TestUnfilledPlaceholder:
    def test_a_shipped_placeholder_is_reported(self) -> None:
        text = "# PRD: BDL-061 — [Name]\n"
        assert _checks(text, placeholders=("[Name]",)) == [UNFILLED_PLACEHOLDER]

    def test_a_filled_document_passes(self) -> None:
        text = "# PRD: BDL-061 — Enforced agentic flow\n"
        assert _checks(text, placeholders=("[Name]",)) == []

    def test_a_placeholder_inside_a_fenced_block_is_quoted_not_unfilled(self) -> None:
        """The shipped ``/templates`` command would otherwise report every
        placeholder it exists to define."""
        text = "Use this:\n\n```markdown\n# PRD: {KEY} — [Name]\n```\n"
        assert _checks(text, placeholders=("[Name]",)) == []

    def test_one_line_reports_once_however_many_placeholders_it_holds(self) -> None:
        text = "**As** [role], **I want** [action], **so that** [result].\n"
        found = _checks(text, placeholders=("[role]", "[action]", "[result]"))
        assert found == [UNFILLED_PLACEHOLDER]

    def test_no_placeholder_vocabulary_means_the_check_reads_nothing(self) -> None:
        report = check_document("# PRD — [Name]\n", path="D.md")
        assert UNFILLED_PLACEHOLDER in report.checks_that_read_nothing


# ---------------------------------------------------------------------------
# The report says what it did NOT judge
# ---------------------------------------------------------------------------


class TestCoverageIsReported:
    def test_a_document_with_no_risks_does_not_count_as_a_verified_risk_table(
        self,
    ) -> None:
        report = check_document("## Goals\n\n- Ship 3 things.\n", path="D.md")
        assert RISK_MITIGATION in report.checks_that_read_nothing
        assert MEASURABLE_GOAL not in report.checks_that_read_nothing

    def test_every_check_is_named_in_the_report_vocabulary(self) -> None:
        report = check_document("", path="D.md")
        assert set(report.checks_that_read_nothing) == set(CHECK_NAMES)


# ---------------------------------------------------------------------------
# The population that matters: this repository's own planning documents
# ---------------------------------------------------------------------------


class TestTheCliAndTheGateReportIt:
    def test_the_cli_names_each_finding_and_its_denominator(
        self, tmp_path: Path
    ) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        doc = tmp_path / ".claude/development/docs/features/ACME-1/PRD.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("## Goals\n\n- Make it better.\n", encoding="utf-8")

        result = CliRunner().invoke(main, ["docs", "quality", "--project", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert MEASURABLE_GOAL in result.output
        assert "1 document(s) read" in result.output

    def test_strict_turns_a_warn_into_an_exit_code(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        doc = tmp_path / ".claude/development/docs/features/ACME-1/PRD.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("## Goals\n\n- Make it better.\n", encoding="utf-8")

        result = CliRunner().invoke(
            main, ["docs", "quality", "--strict", "--project", str(tmp_path)]
        )
        assert result.exit_code == 1

    def test_no_documents_says_so_rather_than_reporting_clean(
        self, tmp_path: Path
    ) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        result = CliRunner().invoke(main, ["docs", "quality", "--project", str(tmp_path)])
        assert result.exit_code == 0
        assert "nothing checked" in result.output

    def test_a_project_declares_where_its_planning_documents_live(
        self, tmp_path: Path
    ) -> None:
        """The default is a convention, not a hardcoded path — an adopter with
        their own layout must be able to point the checks at it."""
        from beadloom.application.doc_shape import planning_documents

        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "doc_quality:\n  paths:\n    - rfcs/*.md\n", encoding="utf-8"
        )
        (tmp_path / "rfcs").mkdir()
        (tmp_path / "rfcs" / "0001.md").write_text("# One\n", encoding="utf-8")

        assert [p.name for p in planning_documents(tmp_path)] == ["0001.md"]

    def test_the_gate_reports_the_findings_without_blocking(
        self, tmp_path: Path
    ) -> None:
        from beadloom.application.gate import _step_docs_quality

        doc = tmp_path / ".claude/development/docs/features/ACME-1/PRD.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("## Goals\n\n- Make it better.\n", encoding="utf-8")

        step = _step_docs_quality(tmp_path)

        assert step.passed is True
        assert step.status == "WARN"
        assert [f["rule"] for f in step.findings] == [MEASURABLE_GOAL]

    def test_a_project_with_no_planning_documents_is_a_named_skip(
        self, tmp_path: Path
    ) -> None:
        from beadloom.application.gate import _step_docs_quality

        step = _step_docs_quality(tmp_path)
        assert step.skipped is True
        assert "no planning document" in step.summary


class TestOnThisRepositorysOwnDocuments:
    @staticmethod
    @pytest.fixture(scope="class")
    def _report() -> object:
        from pathlib import Path

        from beadloom.application.doc_shape import (
            planning_documents,
            shipped_placeholders,
        )

        root = Path(__file__).resolve().parent.parent
        return check_documents(
            planning_documents(root),
            project_root=root,
            placeholders=shipped_placeholders(root),
        )

    def test_the_checks_read_this_repositorys_documents(self, _report: object) -> None:
        assert _report.documents > 100  # type: ignore[attr-defined]

    def test_a_pending_row_in_an_approved_document_is_reported(
        self, _report: object
    ) -> None:
        """The MECHANISM, not the instance.

        This test used to assert that BDL-061's own RFC still carried four
        `Pending` rows — Q1, Q2, Q3 and Q5, each decided in CONTEXT and never
        written back. That was true when the check shipped, and the check
        reporting it is what caused the debt to be paid (commit ``2ddbcf9``),
        which then reddened this test.

        A test that pins an instance dies the moment the instance is fixed, and
        takes the coverage with it. So it now asserts that the check reads a
        real population and reports the rows it finds, whatever they are — the
        two surviving ones live in BDL-021 and BDL-034, and when those are paid
        too, the assertion still holds on an empty result because the
        population, not the finding count, is what proves the check ran.
        """
        report = _report  # type: ignore[attr-defined]
        pending = [f for f in report.findings if f.check == PENDING_IN_APPROVED]
        assert PENDING_IN_APPROVED not in report.checks_that_read_nothing, (
            "the check read no rows at all — it is unproven on this repo, "
            "which is a different fact from finding nothing"
        )
        for finding in pending:
            assert finding.path, "a finding must name the document it came from"

    def test_no_check_reads_nothing_at_all(self, _report: object) -> None:
        """A check with no applicable document here would be unproven, and the
        bead requires that to be stated rather than discovered later."""
        assert _report.checks_that_read_nothing == ()  # type: ignore[attr-defined]

    def test_an_enumerated_stub_inside_a_real_heading_is_not_a_placeholder(
        self, _report: object
    ) -> None:
        """Measured: substring matching reported "Step 1 (12.12.1): Detection"
        and two more real headings of BDL-030's RFC as unfilled placeholders."""
        unfilled = [
            f
            for f in _report.findings  # type: ignore[attr-defined]
            if f.check == UNFILLED_PLACEHOLDER
        ]
        assert unfilled == []
