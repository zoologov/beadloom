"""What the reference leg reads as a claim, and what it reads as a form (BDL-061.62).

`.14` measured three findings in this leg and pinned them as strict xfails in
`tests/test_bead14_s4_binding.py`; those three are now ordinary assertions there.
This file holds the other half of each fix — the true positives that must SURVIVE
a false-positive removal, and the reporting the third finding asked for.

The number that matters was measured on this repository: 33 references before the
change and 33 after, so nothing an author really wrote stopped being read. That
number is DERIVED where the assertion runs rather than written down beside it —
see `TestNoDocumentThisProjectShipsIsLostOrUnreadable` for which half of the check
is derived and which half deliberately is not (`beadloom-0mdo.79`).
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from beadloom.graph.rules.scenario_coverage import evaluate_scenario_coverage_rules
from beadloom.graph.rules.types import NodeMatcher, ScenarioCoverageRule
from beadloom.graph.scenarios import (
    load_references,
    parse_scenario_references,
)

if TYPE_CHECKING:
    from pathlib import Path


def _names(text: str) -> list[str]:
    return [reference.name for reference in parse_scenario_references(text, path="PRD.md")]


class TestAProseShapedKeywordStillWorksWhenItIsMarked:
    """`Example:` is only refused as a BARE line — the keyword is not withdrawn."""

    def test_a_backticked_example_is_a_reference(self) -> None:
        assert _names("`Example: an order is placed`\n") == ["an order is placed"]

    def test_a_bulleted_example_is_a_reference(self) -> None:
        assert _names("- Example: an order is placed\n") == ["an order is placed"]

    def test_a_checkbox_example_is_a_reference(self) -> None:
        assert _names("- [ ] `Example: an order is placed`\n") == ["an order is placed"]

    def test_the_russian_prose_shaped_keyword_follows_the_same_rule(self) -> None:
        assert _names("Пример: заказ размещён.\n") == []
        assert _names("- `Пример: заказ размещён`\n") == ["заказ размещён"]

    def test_a_scenario_keyword_needs_no_mark_because_it_is_not_a_word(self) -> None:
        """`Scenario:` opens no ordinary English sentence, so nothing is asked of it."""
        assert _names("Scenario: an order is placed\n") == ["an order is placed"]


class TestIndentationIsMarkdownsOtherCodeSyntax:
    def test_a_four_space_gherkin_form_is_not_a_claim(self) -> None:
        assert _names("The shape:\n\n    Scenario: an order is placed\n") == []

    def test_a_tab_indented_form_is_not_a_claim(self) -> None:
        assert _names("The shape:\n\n\tScenario: an order is placed\n") == []

    def test_a_deeply_nested_bullet_is_a_claim_and_not_code(self) -> None:
        """Indented, but bulleted: an author who bulleted a reference meant one."""
        assert _names("      - `Scenario: an order is placed`\n") == ["an order is placed"]

    def test_a_deeply_indented_quote_is_a_claim(self) -> None:
        assert _names("      > Scenario: an order is placed\n") == ["an order is placed"]


class TestTheThirdOutcomeIsReportedAndNotLeftToSilence:
    """A document the globs matched and the reader READ, named as such.

    ``dead_globs`` and ``unreadable`` already named two of the three outcomes;
    a document that was read was reported only through the references it
    happened to state, so a document that states none was indistinguishable
    from a document that was never opened.
    """

    def test_a_document_that_states_no_scenario_is_still_reported_as_read(
        self, tmp_path: Path
    ) -> None:
        """The case a reference count is blind to."""
        document = tmp_path / "docs" / "PRD.md"
        document.parent.mkdir(parents=True)
        document.write_text("# a plan with no scenarios\n", encoding="utf-8")

        found = load_references(tmp_path, ["docs/**/PRD.md"])

        assert found.references == ()
        assert found.documents == ("docs/PRD.md",)

    def test_an_undecodable_document_is_reported_unreadable_and_not_read(
        self, tmp_path: Path
    ) -> None:
        """The two lists partition what the globs matched; nothing is in both."""
        document = tmp_path / "docs" / "PRD.md"
        document.parent.mkdir(parents=True)
        document.write_bytes(
            "- `\u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0439: "
            "\u0437\u0430\u043a\u0430\u0437`\n".encode("cp1251")
        )

        found = load_references(tmp_path, ["docs/**/PRD.md"])

        assert found.documents == ()
        assert [item.path for item in found.unreadable] == ["docs/PRD.md"]

    def test_a_document_two_globs_match_is_reported_once(self, tmp_path: Path) -> None:
        """The de-duplication a caller would otherwise have to know to do."""
        document = tmp_path / "docs" / "PRD.md"
        document.parent.mkdir(parents=True)
        document.write_text("Scenario: an order is placed\n", encoding="utf-8")

        found = load_references(tmp_path, ["docs/**/PRD.md", "docs/*.md"])

        assert found.documents == ("docs/PRD.md",)

    def test_a_dead_glob_contributes_no_document(self, tmp_path: Path) -> None:
        """The outcome that was already named, held apart from the new one."""
        found = load_references(tmp_path, ["nowhere/**/*.md"])

        assert found.documents == ()
        assert found.dead_globs == ("nowhere/**/*.md",)


class TestAnUndecodableDocumentLeavesAReport:
    def test_the_reference_set_names_the_document_and_the_reason(self, tmp_path: Path) -> None:
        document = tmp_path / "docs" / "PRD.md"
        document.parent.mkdir(parents=True)
        document.write_bytes("- `Сценарий: заказ размещён`\n".encode("cp1251"))

        found = load_references(tmp_path, ["docs/**/PRD.md"])

        assert found.references == ()
        assert found.dead_globs == ()
        assert [item.path for item in found.unreadable] == ["docs/PRD.md"]

    def test_the_rule_reports_it_instead_of_reading_intent_as_met(self, tmp_path: Path) -> None:
        """The finding is the whole point: the leg is silent about it otherwise."""
        _write_suite(tmp_path)
        document = tmp_path / "docs" / "PRD.md"
        document.parent.mkdir(parents=True)
        document.write_bytes("- `Сценарий: заказ размещён`\n".encode("cp1251"))
        conn = _graph_with_one_feature(tmp_path)
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()

        unknown = [v for v in violations if "UNKNOWN" in v.message]
        assert [v.file_path for v in unknown] == ["docs/PRD.md"]


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _write_suite(root: Path) -> None:
    feature = root / "tests" / "acceptance" / "features" / "billing.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        encoding="utf-8",
    )


def _graph_with_one_feature(root: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE nodes (ref_id TEXT PRIMARY KEY, kind TEXT)")
    conn.execute("INSERT INTO nodes VALUES ('billing', 'feature')")
    conn.commit()
    return conn


def _rule() -> ScenarioCoverageRule:
    return ScenarioCoverageRule(
        name="scenario-coverage",
        description="behaviour carries an executable claim",
        severity="warn",
        for_matcher=NodeMatcher(kind="feature"),
        features="tests/acceptance/features/**/*.feature",
        references=("docs/**/PRD.md",),
    )
