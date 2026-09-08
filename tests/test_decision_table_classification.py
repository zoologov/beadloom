"""What ``decision-reason`` reads as a decision table, and what it refuses to judge.

BDL-UX #213, measured on BDL-067's `ACTIVE.md`: the check reported *"the
decision carries no reason"* against three rows of a table recording
MEASUREMENTS -- the coordinator's verification of a subagent's report, written
as `Claim | Coordinator's measurement` -- plus that table's own header row. The
document was silenced by rewriting the table as a bulleted list, which changed
nothing about the check.

Two faults, and only the second one is about vocabulary:

1. **A section was read as one table.** :func:`_rows` collected every table row
   under a heading into a single list, took the first as the header and judged
   the rest against its column index. So a second table below the first was read
   as continuation rows of it, and its header row was read as data. That is what
   fired on #213, and it needs no vocabulary to fix: a table ends where the
   table rows stop.
2. **A table carrying a reason column is not thereby a decision table.** After
   the boundary is fixed the residual class survives -- a measurement table with
   a ``Reason`` or ``Why`` column of its own -- and no checker can tell it from a
   decision table by reading the cells. So the check asks whether the DOCUMENT
   declares the table as decisions, and answers ``not classified`` where it does
   not: a verdict, reported and counted, rather than a finding.

The declared forms come from the shipped templates
(:func:`shipped_decision_sections`), the same derivation
``unfilled-placeholder`` already uses for its placeholder vocabulary, so they
cannot drift away from the documents this flow tells an author to write.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.doc_shape import shipped_decision_sections
from beadloom.doc_sync.doc_quality import (
    DECISION_REASON,
    RISK_MITIGATION,
    check_document,
    declares_decisions,
)

if TYPE_CHECKING:
    from pathlib import Path

# The `ACTIVE.md` shape #213 was measured on, cut to the two tables and the one
# heading they shared. Every cell is filled: the finding came from the boundary,
# not from anything missing.
_TWO_TABLES = """\
## Notes

| Date | Decision | Reason |
|------|----------|--------|
| 2026-08-31 | the bootstrap emits the edges | option (b) ships a weaker rule |

Then the coordinator re-measured what the subagent reported.

| Claim | Coordinator's measurement |
|---|---|
| `beadloom ci` rc 0 on the tree | confirmed, rc 0, zero `::error` lines |
| 7341 passing | confirmed, `7341 passed, 11 skipped`, 0 failed |
"""


class TestATableEndsWhereItsRowsEnd:
    """The boundary fault, which is the one #213 measured."""

    def test_a_measurement_table_below_a_decision_table_is_not_judged(self) -> None:
        report = check_document(_TWO_TABLES, path="ACTIVE.md")
        assert report.findings == ()

    def test_only_the_decision_table_s_rows_are_counted_as_read(self) -> None:
        report = check_document(_TWO_TABLES, path="ACTIVE.md")
        assert report.applicable[DECISION_REASON] == 1

    def test_a_second_table_s_header_is_never_read_as_a_data_row(self) -> None:
        """The clearest tell that the boundary was wrong, kept as its own case.

        `Claim | Coordinator's measurement` was reported at its own header line.
        A check that reports a table's header as a row with a missing cell is
        not making a mistake about the content; it does not know where the table
        starts.
        """
        report = check_document(_TWO_TABLES, path="ACTIVE.md")
        assert [f.excerpt for f in report.findings] == []

    def test_the_second_table_is_still_judged_by_its_own_header(self) -> None:
        """Delimiting must not silence the second table, only re-aim it."""
        text = _TWO_TABLES + (
            "\n| Date | Decision | Reason |\n|---|---|---|\n"
            "| 2026-09-01 | the room carries the bead id |  |\n"
        )
        report = check_document(text, path="ACTIVE.md")
        assert [f.check for f in report.findings] == [DECISION_REASON]

    def test_a_risk_table_below_another_table_is_judged_by_its_own_header(self) -> None:
        """`risk-mitigation` shares the reader, so it shared the fault."""
        text = (
            "## Risks\n\n"
            "| Risk | Probability | Impact | Mitigation |\n|---|---|---|---|\n"
            "| the index goes stale | Low | High | the Gate reindexes |\n\n"
            "and separately\n\n"
            "| Risk | Mitigation |\n|---|---|\n"
            "| the room is shared | monitor it |\n"
        )
        report = check_document(text, path="RFC.md")
        assert [f.check for f in report.findings] == [RISK_MITIGATION]
        assert report.applicable[RISK_MITIGATION] == 2


class TestATableTheDocumentDeclaresAsDecisions:
    """The residual class: a reason column is not a declaration."""

    def test_a_decision_column_declares_the_table(self) -> None:
        text = (
            "## Notes\n\n| Date | Decision | Reason |\n|---|---|---|\n"
            "| 2026-09-01 | the room carries the bead id |  |\n"
        )
        assert [f.check for f in check_document(text, path="D.md").findings] == [
            DECISION_REASON
        ]

    def test_a_section_the_templates_declare_declares_the_table(self) -> None:
        """The `Axes` table names its decision `In scope`, not `Decision`.

        It is judged because the shipped RFC template puts a reason-carrying
        table under `## Axes`, not because anything here lists the word.
        """
        text = (
            "## Axes\n\n| Axis | Node | Sites | In scope | Why |\n|---|---|---|---|---|\n"
            "| co-writers | graph | 4 | no |  |\n"
        )
        report = check_document(text, path="RFC.md", decision_sections=("axes",))
        assert [f.check for f in report.findings] == [DECISION_REASON]

    def test_an_undeclared_table_with_an_empty_reason_is_not_classified(self) -> None:
        text = (
            "## Deviations from RFC\n\n"
            "| Item | RFC plan | Actual | Reason |\n|---|---|---|---|\n"
            "| the seed | derived | derived |  |\n"
        )
        report = check_document(text, path="RFC.md")
        assert report.findings == ()
        assert [t.header for t in report.unclassified] == [
            "Item | RFC plan | Actual | Reason"
        ]

    def test_an_unclassified_table_contributes_nothing_to_the_read_count(self) -> None:
        """A row nothing judged must not be counted as a row something read.

        This is the half that keeps ``not classified`` from being a quieter way
        of passing: the population the check entered shrinks with it, so a
        reader can see how much of the corpus went unjudged.
        """
        text = (
            "## Deviations from RFC\n\n"
            "| Item | RFC plan | Actual | Reason |\n|---|---|---|---|\n"
            "| the seed | derived | derived | it was |\n"
        )
        report = check_document(text, path="RFC.md")
        assert report.applicable[DECISION_REASON] == 0
        assert [t.rows for t in report.unclassified] == [1]

    def test_an_unclassified_table_names_where_the_reader_must_look(self) -> None:
        text = (
            "## Deviations from RFC\n\n"
            "| Item | Reason |\n|---|---|\n| the seed | it was |\n"
        )
        table = check_document(text, path="RFC.md").unclassified[0]
        assert (table.path, table.line, table.section) == (
            "RFC.md",
            3,
            "Deviations from RFC",
        )

    def test_a_declared_table_is_never_reported_as_unclassified(self) -> None:
        text = (
            "## Notes\n\n| Date | Decision | Reason |\n|---|---|---|\n"
            "| 2026-09-01 | the room carries the bead id | two agents shared one |\n"
        )
        assert check_document(text, path="D.md").unclassified == ()

    def test_a_table_with_no_reason_column_is_neither_judged_nor_unclassified(
        self,
    ) -> None:
        """Out of the population entirely, which is where the #213 table lands.

        ``not classified`` is for a table this check might have judged. A table
        stating no reason at all was never its business, and reporting it would
        turn the verdict into noise.
        """
        text = "## Beads\n\n| ID | Status |\n|---|---|\n| .13 | Done |\n"
        report = check_document(text, path="D.md")
        assert report.findings == ()
        assert report.unclassified == ()


class TestDeclaresDecisions:
    """The predicate on its own, so its two legs can be told apart."""

    def test_a_decision_column_is_enough(self) -> None:
        assert declares_decisions("Notes", ["Date", "Decision", "Reason"])

    def test_a_declared_section_is_enough(self) -> None:
        assert declares_decisions(
            "Axes", ["Axis", "In scope", "Why"], declared_sections=("axes",)
        )

    def test_a_numbered_heading_still_names_its_section(self) -> None:
        """`## 9. Decision Log` is the same section as `## Decision Log`."""
        assert declares_decisions(
            "9. Architectural Decisions",
            ["Item", "Why"],
            declared_sections=("architectural decisions",),
        )

    def test_neither_leg_leaves_the_table_undeclared(self) -> None:
        assert not declares_decisions(
            "Deviations from RFC",
            ["Item", "RFC plan", "Actual", "Reason"],
            declared_sections=("axes", "architectural decisions"),
        )

    def test_a_section_named_nowhere_in_the_templates_is_not_declared(self) -> None:
        """Without the derivation, only the column speaks — no built-in list."""
        assert not declares_decisions("Axes", ["Axis", "In scope", "Why"])


class TestTheDeclaredSectionsAreDerived:
    """From the shipped templates, not from a list kept in this repository."""

    def test_the_shipped_templates_declare_the_sections_this_flow_writes(
        self, tmp_path: Path
    ) -> None:
        del tmp_path
        from pathlib import Path as _Path

        sections = shipped_decision_sections(_Path.cwd())
        assert "architectural decisions" in sections
        assert "axes" in sections

    def test_a_project_whose_flow_config_will_not_parse_declares_nothing(
        self, tmp_path: Path
    ) -> None:
        """The same answer ``shipped_placeholders`` gives, for the same reason.

        A ``flow.yml`` that will not parse is reported by ``config-check`` under
        its own name. Here it means no section is declared, so every table with
        a reason column is answered ``not classified`` — the check goes quiet
        rather than judging a corpus against templates it could not compose.
        """
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(": [", encoding="utf-8")
        assert shipped_decision_sections(tmp_path) == ()

    def test_a_bare_directory_still_declares_the_shipped_sections(
        self, tmp_path: Path
    ) -> None:
        """A project with no config composes the SHIPPED templates, not nothing."""
        assert shipped_decision_sections(tmp_path) == (
            "architectural decisions",
            "axes",
            "non-behavioural declaration",
        )
