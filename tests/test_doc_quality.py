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
        text = "## Goal\n\nMake the whole thing simpler and more enjoyable.\n"
        assert _checks(text) == [MEASURABLE_GOAL]


# ---------------------------------------------------------------------------
# 1b. The criterion is a witness, not a numeral (`.70`, review `.15`)
# ---------------------------------------------------------------------------


class TestAGoalIsJudgedOnWhatCanBeWitnessed:
    """The re-scope measured in `.70`.

    As shipped the check found a digit and called its absence "no measurable
    clause": on this repository it reported 154 of 235 goal statements at
    roughly 1-in-18 precision, including the two exit-code goals BDL-UX #148
    exists to demand. A check satisfied by inserting a numeral teaches an author
    to write for the checker, which is the failure #169 was fixed by NOT doing.

    What it decides now is one named form the writing standard itself rejects:
    a goal whose predicate is a QUALITY and which names nothing an observer
    could go and look at.
    """

    def test_an_exit_code_goal_is_measurable(self) -> None:
        """BDL-036/PRD.md:26, reported by the shipped check."""
        text = (
            "## Goals\n\n"
            "- `beadloom lint --strict` **fails** (non-zero) on real cycle "
            "and layer violations.\n"
        )
        assert _checks(text) == []

    def test_a_second_exit_code_goal_is_measurable(self) -> None:
        """BDL-039/PRD.md:22, reported by the shipped check."""
        text = (
            "## Goals\n\n"
            "- **G1 — Federated landscape gate.** `beadloom federate --fail-on "
            "<verdicts>` exits non-zero when the landscape drifts.\n"
        )
        assert _checks(text) == []

    def test_a_stated_property_is_measurable(self) -> None:
        """BDL-060/PRD.md:28 — atomicity is a property anyone can check for."""
        text = (
            "## Goals\n\n"
            "- **G6 — Graph-write safety.** Graph YAML writes are atomic "
            "(temp + `os.replace`), so a crash cannot truncate the graph.\n"
        )
        assert _checks(text) == []

    def test_an_artifact_named_without_backticks_is_still_an_artifact(self) -> None:
        """BDL-034/PRD.md:31. Demanding backticks would be a formatting rule
        wearing a measurability rule's name."""
        text = (
            "## Goals\n\n"
            "- AGENTS.md regeneration produces clean output without "
            "duplication.\n"
        )
        assert _checks(text) == []

    def test_a_goal_whose_predicate_is_a_quality_is_reported(self) -> None:
        """BDL-006/CONTEXT.md:13, and the standard's own example."""
        text = (
            "## Goal\n\nMake Beadloom enjoyable and intuitive — visual graph "
            "exploration, impact analysis, change visibility.\n"
        )
        assert _checks(text) == [MEASURABLE_GOAL]

    def test_an_unbounded_improvement_verb_is_reported(self) -> None:
        text = "## Goals\n\n- Improve the developer experience.\n"
        assert _checks(text) == [MEASURABLE_GOAL]

    def test_establishing_something_is_reported(self) -> None:
        """BDL-002/CONTEXT.md:12 — nothing observable separates "established"
        from "not yet"."""
        text = (
            "## Goal\n\nEstablish the agent-native architecture and clean up "
            "the codebase before building new features.\n"
        )
        assert _checks(text) == [MEASURABLE_GOAL]

    def test_an_improvement_with_a_quantity_is_not_reported(self) -> None:
        text = "## Goals\n\n- Improve the core: it shrinks from 440 to 376 lines.\n"
        assert _checks(text) == []

    def test_an_improvement_with_a_named_artifact_is_not_reported(self) -> None:
        text = (
            "## Goals\n\n- Make the loader simpler: `loader.py` splits into "
            "three modules.\n"
        )
        assert _checks(text) == []

    def test_an_improvement_with_an_observable_outcome_is_not_reported(self) -> None:
        text = "## Goals\n\n- Make the build simpler, so a cold clone passes.\n"
        assert _checks(text) == []

    def test_an_identifier_is_still_not_a_quantity(self) -> None:
        """The old necessity is gone; the old distinction is not. ``BDL-061``
        and ``v2.2`` are names with digits in them."""
        text = "## Goals\n\n- Make the tool better before BDL-061 and v2.2 ship.\n"
        assert _checks(text) == [MEASURABLE_GOAL]

    def test_the_finding_says_what_it_actually_decided(self) -> None:
        """A finding that over-claims is the defect this bead exists to fix."""
        report = check_document(
            "## Goals\n\n- Make it better.\n", path="D.md"
        )
        assert "witness" in report.findings[0].why

    @pytest.mark.parametrize(
        "abbreviation",
        ["e.g. the graph", "i.e. the graph", "and so on, etc.", "vs. last week"],
    )
    def test_an_abbreviation_is_not_a_named_artifact(self, abbreviation: str) -> None:
        """The witness that accepts a filename must not accept ordinary prose:
        a loose recognizer lowers the count silently, which is the one way this
        re-scope could be worse than the numeral it replaces."""
        text = f"## Goals\n\n- Make the tool better, {abbreviation}.\n"
        assert _checks(text) == [MEASURABLE_GOAL]

    def test_a_goal_that_states_no_improvement_is_not_reported(self) -> None:
        """BDL-027/PRD.md:27, reported by the shipped check and accepted now.

        The load-bearing half of the criterion, and the one a sabotage found
        unpinned: this statement names NO witness either — no quantity, no
        artifact, no outcome verb — and is accepted solely because its predicate
        is not an unbounded improvement. Without this row, deleting the
        improvement leg reddens nothing (sabotage S2).
        """
        text = "## Goals\n\n- Route extraction has no self-matching false positives.\n"
        assert _checks(text) == []

    def test_a_structural_goal_with_no_witness_is_not_reported(self) -> None:
        """BDL-046/PRD.md:30 — an observer opens the menu and looks."""
        text = '## Goals\n\n- **Dashboard** — a single flat item (no "Metrics" child).\n'
        assert _checks(text) == []

    def test_a_slash_separated_enumeration_is_not_a_named_artifact(self) -> None:
        """Measured: "fresh/stale/missing docs" read as a path and witnessed a
        goal that names no artifact at all."""
        text = "## Goals\n\n- Make the panel nicer for fresh/stale/missing docs.\n"
        assert _checks(text) == [MEASURABLE_GOAL]

    def test_a_horizontal_rule_is_not_a_goal_statement(self) -> None:
        """Review `.15` m1: three of the 235 statements read were ``---``."""
        report = check_document(
            "## Goal\n\nMake it better.\n\n---\n", path="D.md"
        )
        assert report.applicable[MEASURABLE_GOAL] == 1


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


class TestPerKindCoverage:
    """A whole document KIND no check enters (review `.15` M2).

    ``checks_that_read_nothing`` is a global OR over the corpus, so it goes
    permanently silent the moment ONE document carries ONE row. It can see a
    check that is blind everywhere; it cannot see one that is blind on an entire
    shipped document kind. Measured on this repository, all eleven ``BRIEF.md``
    contribute zero to all four content checks by template construction, and the
    anti-vacuity guard was green throughout — the blind spot it was built to
    prevent, one level down.
    """

    @staticmethod
    def _corpus(root: Path) -> object:
        """A PRD every check reads, beside a BRIEF none of them enters."""
        features = root / "docs"
        features.mkdir(parents=True, exist_ok=True)
        (features / "PRD.md").write_text(
            _APPROVED
            + "## Goals\n\n- Ship 3 things.\n\n"
            "## Decisions\n\n| Decision | Reason |\n|---|---|\n| A | because |\n\n"
            "## Risks\n\n| Risk | Mitigation |\n|---|---|\n| R | page on-call |\n\n"
            "## Open Questions\n\n| Q | Status |\n|---|---|\n| Q1 | Decided |\n",
            encoding="utf-8",
        )
        (features / "BRIEF.md").write_text(
            "# Brief\n\n## Problem\n\nSomething is wrong.\n\n"
            "## Solution\n\nFix it.\n",
            encoding="utf-8",
        )
        # A non-empty placeholder vocabulary, so `unfilled-placeholder` reads
        # both documents — which is exactly what makes the BRIEF hole invisible
        # to a five-check judgement.
        return check_documents(
            sorted(features.glob("*.md")), project_root=root, placeholders=("TBD",)
        )

    def test_a_kind_no_content_check_enters_is_named(self, tmp_path: Path) -> None:
        # Act
        report = self._corpus(tmp_path)

        # Assert
        assert report.kinds_that_read_nothing == ("BRIEF",)  # type: ignore[attr-defined]

    def test_the_global_guard_structurally_cannot_see_it(self, tmp_path: Path) -> None:
        """The finding inside the finding, asserted rather than argued."""
        # Act
        report = self._corpus(tmp_path)

        # Assert — every check read SOMETHING, and a whole kind was still unjudged
        assert report.checks_that_read_nothing == ()  # type: ignore[attr-defined]
        assert report.kinds_that_read_nothing  # type: ignore[attr-defined]

    def test_a_kind_every_check_enters_is_not_named(self, tmp_path: Path) -> None:
        """The non-vacuity guard: "every kind is unread" must not pass."""
        # Act
        report = self._corpus(tmp_path)

        # Assert
        by_kind = {c.kind: c for c in report.by_kind}  # type: ignore[attr-defined]
        assert by_kind["PRD"].checks_that_read_nothing == ()
        assert not by_kind["PRD"].is_unread

    def test_each_kind_carries_its_own_denominator(self, tmp_path: Path) -> None:
        # Act
        report = self._corpus(tmp_path)

        # Assert
        by_kind = {c.kind: c for c in report.by_kind}  # type: ignore[attr-defined]
        assert by_kind["BRIEF"].documents == 1
        assert by_kind["BRIEF"].applicable[MEASURABLE_GOAL] == 0
        assert by_kind["PRD"].applicable[MEASURABLE_GOAL] == 1

    def test_the_placeholder_check_does_not_make_an_unread_kind_look_read(
        self, tmp_path: Path
    ) -> None:
        """``unfilled-placeholder`` counts documents OPENED, not items.

        It therefore reads every kind by construction, and judging "was this kind
        entered" over all five checks would report every kind as read — a second
        vacuous guard in place of the first.
        """
        # Arrange
        report = self._corpus(tmp_path)
        by_kind = {c.kind: c for c in report.by_kind}  # type: ignore[attr-defined]

        # Assert
        assert by_kind["BRIEF"].applicable[UNFILLED_PLACEHOLDER] == 1
        assert by_kind["BRIEF"].is_unread

    def test_every_document_is_in_exactly_one_kind(self, tmp_path: Path) -> None:
        """The per-kind denominators must add up to the corpus, or one hides."""
        # Act
        report = self._corpus(tmp_path)

        # Assert
        assert sum(c.documents for c in report.by_kind) == report.documents  # type: ignore[attr-defined]

    def test_an_unreadable_document_is_named_not_counted_as_unread_content(
        self, tmp_path: Path
    ) -> None:
        """A file nobody read is not evidence about what its kind carries.

        Counting it as a document of its kind with nothing read would make an
        undecodable file into a statement about the project's templates. It is
        reported on the kind's ``unreadable`` channel instead — the shape the
        critical fix chose: name what could not be judged rather than letting it
        shrink a count.
        """
        # Arrange
        root = tmp_path / "p"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "PRD.md").write_bytes(b"## Goals\n\n- Ship 3.\n")
        (root / "docs" / "SUMMARY.md").write_bytes(
            "## Goals\n\n- Отчёт\n".encode("cp1251")
        )

        # Act
        report = check_documents(
            sorted((root / "docs").glob("*.md")), project_root=root
        )

        # Assert
        by_kind = {c.kind: c for c in report.by_kind}
        assert by_kind["SUMMARY"].unreadable == 1
        assert by_kind["SUMMARY"].documents == 0
        assert "SUMMARY" not in report.kinds_that_read_nothing, (
            "a kind nobody could read is unverified, not a kind no check enters"
        )


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

    @staticmethod
    def _two_kinds(root: Path) -> Path:
        """A PRD every check reads beside a BRIEF none of them enters."""
        where = root / ".claude/development/docs/features/ACME-1"
        where.mkdir(parents=True)
        (where / "PRD.md").write_text(
            "## Goals\n\n- Ship 3 things.\n\n"
            "## Decisions\n\n| Decision | Reason |\n|---|---|\n| A | because |\n\n"
            "## Risks\n\n| Risk | Mitigation |\n|---|---|\n| R | page on-call |\n\n"
            "## Open Questions\n\n| Q | Status |\n|---|---|\n| Q1 | Decided |\n",
            encoding="utf-8",
        )
        (where / "BRIEF.md").write_text(
            "# Brief\n\n## Problem\n\nSomething is wrong.\n", encoding="utf-8"
        )
        return root

    def test_the_cli_names_a_document_kind_no_check_enters(
        self, tmp_path: Path
    ) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        # Arrange
        self._two_kinds(tmp_path)

        # Act
        result = CliRunner().invoke(main, ["docs", "quality", "--project", str(tmp_path)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "BRIEF" in result.output
        assert "NO CHECK READS" in result.output

    def test_the_json_payload_carries_the_per_kind_population(
        self, tmp_path: Path
    ) -> None:
        """`--json` and exit codes, never line counts (#148) — and it must PARSE."""
        import json as _json

        from click.testing import CliRunner

        from beadloom.services.cli import main

        # Arrange
        self._two_kinds(tmp_path)

        # Act
        result = CliRunner().invoke(
            main, ["docs", "quality", "--json", "--project", str(tmp_path)]
        )

        # Assert — one JSON document on stdout and nothing after it
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.stdout)
        assert payload["kinds_read_by_nothing"] == ["BRIEF"]
        assert payload["kinds"]["BRIEF"]["documents"] == 1
        assert payload["kinds"]["PRD"]["read"][MEASURABLE_GOAL] == 1

    def test_the_gate_warns_when_a_whole_kind_is_unjudged(
        self, tmp_path: Path
    ) -> None:
        """Every check read something, and 1 of 2 documents was judged by none.

        `not_verified` and not `passed=False`: the documents are not broken and a
        project must not go red on upgrade. But a step that could not check part
        of what it reports on prints WARN, because unverifiable is not clean.
        """
        from beadloom.application.gate import _step_docs_quality

        # Arrange
        self._two_kinds(tmp_path)

        # Act
        step = _step_docs_quality(tmp_path)

        # Assert
        assert step.passed is True
        assert step.status == "WARN"
        assert "NO CHECK READS: BRIEF" in step.summary

    def test_the_gate_names_a_document_it_could_not_read(self, tmp_path: Path) -> None:
        """The critical's channel, surfaced: it was populated and printed nowhere."""
        from beadloom.application.gate import _step_docs_quality

        # Arrange
        where = tmp_path / ".claude/development/docs/features/ACME-1"
        where.mkdir(parents=True)
        (where / "PRD.md").write_bytes(
            b"## Goals\n\n- Ship 3 things.\n"
        )
        (where / "RFC.md").write_bytes("## Goals\n\n- Отчёт\n".encode("cp1251"))

        # Act
        step = _step_docs_quality(tmp_path)

        # Assert
        assert step.passed is True
        assert step.status == "WARN"
        assert "UNREADABLE: 1" in step.summary

    def test_the_cli_names_a_document_it_could_not_read(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        # Arrange
        where = tmp_path / ".claude/development/docs/features/ACME-1"
        where.mkdir(parents=True)
        (where / "PRD.md").write_bytes(b"## Goals\n\n- Ship 3 things.\n")
        (where / "RFC.md").write_bytes("## Goals\n\n- Отчёт\n".encode("cp1251"))

        # Act
        result = CliRunner().invoke(main, ["docs", "quality", "--project", str(tmp_path)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "RFC.md" in result.output
        assert "UNREADABLE" in result.output

    def test_a_clean_project_says_nothing_about_kinds_or_readability(
        self, tmp_path: Path
    ) -> None:
        """The noise guard: these lines must appear only when they say something."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        # Arrange — one PRD every check enters
        where = tmp_path / ".claude/development/docs/features/ACME-1"
        where.mkdir(parents=True)
        (where / "PRD.md").write_text(
            "## Goals\n\n- Ship 3 things.\n\n"
            "## Decisions\n\n| Decision | Reason |\n|---|---|\n| A | because |\n\n"
            "## Risks\n\n| Risk | Mitigation |\n|---|---|\n| R | page on-call |\n\n"
            "## Open Questions\n\n| Q | Status |\n|---|---|\n| Q1 | Decided |\n",
            encoding="utf-8",
        )

        # Act
        result = CliRunner().invoke(main, ["docs", "quality", "--project", str(tmp_path)])

        # Assert
        assert "NO CHECK READS" not in result.output
        assert "UNREADABLE" not in result.output

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

    def test_every_document_falls_in_exactly_one_kind(self, _report: object) -> None:
        """The INVARIANT, not the instance (the lesson of the rewritten RFC pin).

        Pinning "BRIEF reads nothing on this repo" would redden the day the
        template gains a Goal — which is the outcome the per-kind report exists
        to produce. What must hold whatever the documents say is that the
        per-kind denominators account for the corpus: a kind that silently
        dropped documents would understate exactly the hole this is for.
        """
        report = _report  # type: ignore[attr-defined]
        assert len({c.kind for c in report.by_kind}) > 1, "one kind is not a population"
        assert sum(c.documents for c in report.by_kind) == report.documents

    def test_the_per_kind_counts_sum_to_the_global_ones(self, _report: object) -> None:
        """Two counters over one corpus must not be free to disagree (#171)."""
        report = _report  # type: ignore[attr-defined]
        for name in CHECK_NAMES:
            per_kind = sum(c.applicable.get(name, 0) for c in report.by_kind)
            assert per_kind == report.applicable[name], name

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

class TestAnUnreadableDocumentIsUnverifiedNotAbsent:
    """BDL-061.66 / review .15's critical.

    `check_documents` caught only `OSError`. `UnicodeDecodeError` is a
    `ValueError`, so a single non-UTF-8 planning document raised straight out of
    the `docs-quality` gate step and took down the whole `beadloom ci` run: a
    traceback and NO step results, for every check in the gate. Measured by the
    reviewer at rc 1.

    Fifth instance of one family in this epic -- a handler narrower than what its
    call can raise, around text decoded without an explicit rule (.36 found two,
    .37 the probes, .40 four call sites, .42 swept ~40). This module was written
    after all four.
    """

    def _docs(self, tmp_path: Path) -> list[Path]:
        good = tmp_path / "GOOD.md"
        good.write_text(
            "# Goal\n\nShip it in under 200ms.\n", encoding="utf-8"
        )
        bad = tmp_path / "BAD.md"
        bad.write_bytes(b"# Goal\n\n\xff\xfe not utf-8 at all\n")
        return [good, bad]

    def test_an_undecodable_document_does_not_escape_the_run(
        self, tmp_path: Path
    ) -> None:
        """The whole point: no exception leaves this call."""
        report = check_documents(
            self._docs(tmp_path), project_root=tmp_path
        )
        assert report is not None

    def test_the_readable_document_is_still_judged(self, tmp_path: Path) -> None:
        """A run must not lose its other answers to one bad file."""
        report = check_documents(self._docs(tmp_path), project_root=tmp_path)
        assert report.documents == 1

    def test_the_undecodable_document_is_named_with_its_reason(
        self, tmp_path: Path
    ) -> None:
        """Unverifiable is not clean: it is reported, not dropped."""
        report = check_documents(self._docs(tmp_path), project_root=tmp_path)
        assert [where for where, _ in report.unreadable] == ["BAD.md"]
        reason = report.unreadable[0][1]
        assert "UnicodeDecodeError" in reason

    def test_a_readable_only_run_reports_nothing_unreadable(
        self, tmp_path: Path
    ) -> None:
        """The channel must be silent when there is nothing to say."""
        good = tmp_path / "GOOD.md"
        good.write_text("# Goal\n\nShip it in under 200ms.\n", encoding="utf-8")
        report = check_documents([good], project_root=tmp_path)
        assert report.unreadable == ()
