"""What the reference leg reads as a claim, and what it reads as a form (BDL-061.62).

`.14` measured three findings in this leg and pinned them as strict xfails in
`tests/test_bead14_s4_binding.py`; those three are now ordinary assertions there.
This file holds the other half of each fix — the true positives that must SURVIVE
a false-positive removal, and the reporting the third finding asked for.

The number that matters is measured on this repository: 33 references before the
change and 33 after, so nothing an author really wrote stopped being read.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from beadloom.graph.rules.scenario_coverage import evaluate_scenario_coverage_rules
from beadloom.graph.rules.types import NodeMatcher, ScenarioCoverageRule
from beadloom.graph.scenarios import load_references, parse_scenario_references

REPO_ROOT = Path(__file__).resolve().parents[1]


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


class TestTheRepositorysOwnPopulationIsUnchanged:
    def test_no_document_this_project_ships_becomes_unreadable_or_lost(self) -> None:
        """33 references before the false-positive removal, 36 once BDL-067 landed."""
        globs = (
            ".claude/development/docs/features/**/PRD.md",
            ".claude/development/docs/features/**/BRIEF.md",
        )

        found = load_references(REPO_ROOT, globs)

        assert found.unreadable == ()
        assert found.dead_globs == ()
        assert len(found.references) == 36


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
