"""The `.feature` file is the source of truth — what a scenario binds itself to.

BDL-061 S4 (`beadloom-mr2l.13`). CONTEXT's decision: the executable artifact holds
the text, and the PRD states intent and *references* it. So the parser here is not
a convenience — it is the only thing that knows what the acceptance suite claims,
and every check the rule engine makes about behaviour coverage is downstream of it.

Two properties get more attention than the happy path, because both are ways a
check silently reads zero and calls it clean:

* a scenario name inside a doc-string or a fenced block is **not** a scenario;
* a dialect the parser does not know is **reported**, never counted as a file
  with no scenarios (`.46`/`.47` — unverifiable is not clean).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.graph.scenarios import (
    BEAD_TAG_PREFIX,
    DEFAULT_FEATURE_GLOB,
    NODE_TAG_PREFIX,
    load_references,
    load_suite,
    parse_feature,
    parse_scenario_references,
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Parsing one feature file
# ---------------------------------------------------------------------------


class TestParseFeature:
    def test_scenario_inherits_feature_level_binding(self) -> None:
        text = (
            "@bead:proj-1 @node:rule-engine\n"
            "Feature: a rule reports what it cannot check\n"
            "\n"
            "  Scenario: an inert rule is reported\n"
            "    Given a rule whose matcher selects nothing\n"
            "    Then the rule is reported as inert\n"
        )
        scenarios, unreadable = parse_feature(text, path="tests/acceptance/features/a.feature")
        assert unreadable is None
        assert len(scenarios) == 1
        assert scenarios[0].name == "an inert rule is reported"
        assert scenarios[0].feature == "a rule reports what it cannot check"
        assert scenarios[0].beads == ("proj-1",)
        assert scenarios[0].nodes == ("rule-engine",)
        assert scenarios[0].line == 4

    def test_scenario_level_tags_add_to_the_feature_level_ones(self) -> None:
        text = (
            "@node:rule-engine\n"
            "Feature: F\n"
            "\n"
            "  @bead:proj-2 @node:scenario-binding\n"
            "  Scenario: S\n"
            "    Given a step\n"
        )
        scenarios, _ = parse_feature(text, path="f.feature")
        assert scenarios[0].beads == ("proj-2",)
        assert scenarios[0].nodes == ("rule-engine", "scenario-binding")

    def test_rule_level_tags_are_inherited(self) -> None:
        text = (
            "Feature: F\n"
            "\n"
            "  @node:rule-engine\n"
            "  Rule: a rule that cannot fire is reported\n"
            "\n"
            "    @bead:proj-3\n"
            "    Scenario: S\n"
            "      Given a step\n"
        )
        scenarios, _ = parse_feature(text, path="f.feature")
        assert scenarios[0].nodes == ("rule-engine",)
        assert scenarios[0].beads == ("proj-3",)

    def test_a_second_rule_does_not_inherit_the_first_rules_tags(self) -> None:
        text = (
            "Feature: F\n"
            "  @node:alpha\n"
            "  Rule: one\n"
            "    Scenario: first\n"
            "      Given a step\n"
            "  @node:beta\n"
            "  Rule: two\n"
            "    Scenario: second\n"
            "      Given a step\n"
        )
        scenarios, _ = parse_feature(text, path="f.feature")
        by_name = {s.name: s for s in scenarios}
        assert by_name["first"].nodes == ("alpha",)
        assert by_name["second"].nodes == ("beta",)

    def test_scenario_outline_and_example_are_scenarios(self) -> None:
        text = (
            "Feature: F\n"
            "  Scenario Outline: outlined\n"
            "    Given <x>\n"
            "    Examples:\n"
            "      | x |\n"
            "      | 1 |\n"
            "  Example: exampled\n"
            "    Given a step\n"
        )
        scenarios, _ = parse_feature(text, path="f.feature")
        assert [s.name for s in scenarios] == ["outlined", "exampled"]

    def test_examples_table_header_is_not_a_scenario(self) -> None:
        text = (
            "Feature: F\n"
            "  Scenario Outline: outlined\n"
            "    Given <x>\n"
            "    Examples: the interesting values\n"
            "      | x |\n"
            "      | 1 |\n"
        )
        scenarios, _ = parse_feature(text, path="f.feature")
        assert [s.name for s in scenarios] == ["outlined"]

    def test_a_scenario_line_inside_a_docstring_is_not_a_scenario(self) -> None:
        """The bite: a step's payload may quote Gherkin, and quoting is not declaring."""
        text = (
            "Feature: F\n"
            "  Scenario: the real one\n"
            "    Given the file\n"
            '      """\n'
            "      Scenario: not a scenario\n"
            '      """\n'
            "    Then it is one scenario\n"
        )
        scenarios, _ = parse_feature(text, path="f.feature")
        assert [s.name for s in scenarios] == ["the real one"]

    def test_a_comment_is_not_a_scenario(self) -> None:
        text = "Feature: F\n  # Scenario: commented out\n  Scenario: live\n    Given a step\n"
        scenarios, _ = parse_feature(text, path="f.feature")
        assert [s.name for s in scenarios] == ["live"]

    def test_a_comment_between_tags_and_the_scenario_does_not_drop_the_tags(self) -> None:
        text = (
            "Feature: F\n"
            "  @bead:proj-4\n"
            "  # why this scenario exists\n"
            "  Scenario: S\n"
            "    Given a step\n"
        )
        scenarios, _ = parse_feature(text, path="f.feature")
        assert scenarios[0].beads == ("proj-4",)

    def test_bindings_are_deduplicated_and_ordered_by_first_appearance(self) -> None:
        text = (
            "@node:alpha @bead:proj-5\n"
            "Feature: F\n"
            "  @node:alpha @node:beta @bead:proj-5\n"
            "  Scenario: S\n"
            "    Given a step\n"
        )
        scenarios, _ = parse_feature(text, path="f.feature")
        assert scenarios[0].nodes == ("alpha", "beta")
        assert scenarios[0].beads == ("proj-5",)

    def test_an_unbound_scenario_reports_empty_bindings(self) -> None:
        text = "Feature: F\n  Scenario: S\n    Given a step\n"
        scenarios, _ = parse_feature(text, path="f.feature")
        assert scenarios[0].beads == ()
        assert scenarios[0].nodes == ()

    def test_tag_prefixes_are_the_documented_ones(self) -> None:
        assert BEAD_TAG_PREFIX == "@bead:"
        assert NODE_TAG_PREFIX == "@node:"

    def test_default_glob_is_the_layout_q3_chose(self) -> None:
        assert DEFAULT_FEATURE_GLOB == "tests/acceptance/features/**/*.feature"


class TestDialects:
    def test_a_russian_dialect_file_parses(self) -> None:
        """#136's population: a team that writes its scenarios in its own language."""
        text = (
            "# language: ru\n"
            "@node:rule-engine\n"
            "Функция: правило сообщает, что не смогло проверить\n"
            "\n"
            "  @bead:proj-6\n"
            "  Сценарий: инертное правило попадает в отчёт\n"
            "    Дано правило без совпадений\n"
        )
        scenarios, unreadable = parse_feature(text, path="f.feature")
        assert unreadable is None
        assert [s.name for s in scenarios] == ["инертное правило попадает в отчёт"]
        assert scenarios[0].nodes == ("rule-engine",)
        assert scenarios[0].beads == ("proj-6",)

    def test_an_unknown_dialect_is_reported_not_counted_as_empty(self) -> None:
        """Unverifiable is not clean: zero scenarios must not be the answer here."""
        text = "# language: ja\n機能: なにか\n  シナリオ: なにか\n"
        scenarios, unreadable = parse_feature(text, path="f.feature")
        assert scenarios == ()
        assert unreadable is not None
        assert "ja" in unreadable
        assert "en" in unreadable  # the reason names the dialects that do parse


class TestAgreementWithTheRunner:
    """What this parser accepts and a runner refuses is a false green, not leniency."""

    def test_a_second_feature_in_one_file_is_reported(self) -> None:
        text = (
            "Feature: one\n  Scenario: a\n    Given a step\n"
            "Feature: two\n  Scenario: b\n    Given a step\n"
        )
        scenarios, unreadable = parse_feature(text, path="f.feature")
        assert scenarios == ()
        assert unreadable is not None
        assert "one `Feature:`" in unreadable

    def test_our_own_suite_parses_the_way_the_reference_parser_reads_it(self) -> None:
        """Cross-check against `gherkin-official`, the parser `pytest-bdd` uses."""
        gherkin = pytest.importorskip(
            "gherkin.parser",
            reason="gherkin-official absent — this run does not answer for parser agreement",
        )
        from gherkin.token_scanner import TokenScanner

        root = Path(__file__).resolve().parent.parent
        files = sorted((root / "tests" / "acceptance" / "features").glob("*.feature"))
        assert files, "the acceptance suite is empty — the cross-check would be vacuous"
        for path in files:
            document = gherkin.Parser().parse(TokenScanner(str(path)))
            reference = [
                child["scenario"]["name"]
                for child in document["feature"]["children"]
                if "scenario" in child
            ]
            mine, unreadable = parse_feature(
                path.read_text(encoding="utf-8"), path=path.name
            )
            assert unreadable is None, path.name
            assert [s.name for s in mine] == reference, path.name


class TestLoadSuite:
    def test_files_are_found_and_sorted(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "tests/acceptance/features/b.feature",
            "Feature: B\n  Scenario: sb\n    Given a step\n",
        )
        _write(
            tmp_path / "tests/acceptance/features/nested/a.feature",
            "Feature: A\n  Scenario: sa\n    Given a step\n",
        )
        suite = load_suite(tmp_path, DEFAULT_FEATURE_GLOB)
        assert suite.files == (
            "tests/acceptance/features/b.feature",
            "tests/acceptance/features/nested/a.feature",
        )
        assert {s.name for s in suite.scenarios} == {"sa", "sb"}
        assert suite.is_empty is False

    def test_a_glob_that_matches_nothing_is_an_empty_suite(self, tmp_path: Path) -> None:
        suite = load_suite(tmp_path, DEFAULT_FEATURE_GLOB)
        assert suite.files == ()
        assert suite.is_empty is True

    def test_a_feature_file_with_no_scenario_is_named(self, tmp_path: Path) -> None:
        _write(tmp_path / "tests/acceptance/features/empty.feature", "Feature: nothing here\n")
        suite = load_suite(tmp_path, DEFAULT_FEATURE_GLOB)
        assert suite.files == ("tests/acceptance/features/empty.feature",)
        assert suite.scenarios == ()
        assert [u.path for u in suite.unreadable] == []
        assert suite.empty_files == ("tests/acceptance/features/empty.feature",)

    def test_an_undecodable_file_is_reported_with_its_reason(self, tmp_path: Path) -> None:
        path = tmp_path / "tests/acceptance/features/bad.feature"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Feature: \xff\xfe not utf-8\nScenario: s\n")
        suite = load_suite(tmp_path, DEFAULT_FEATURE_GLOB)
        assert suite.scenarios == ()
        assert len(suite.unreadable) == 1
        assert suite.unreadable[0].path == "tests/acceptance/features/bad.feature"
        assert "utf-8" in suite.unreadable[0].reason.lower()

    def test_a_configured_glob_finds_a_project_that_is_not_us(self, tmp_path: Path) -> None:
        """Q3: the default is the proven layout; the location is configuration."""
        _write(
            tmp_path / "spec/acceptance/orders.feature",
            "@node:orders\nFeature: orders\n  Scenario: an order is placed\n    Given a cart\n",
        )
        suite = load_suite(tmp_path, "spec/**/*.feature")
        assert [s.name for s in suite.scenarios] == ["an order is placed"]


# ---------------------------------------------------------------------------
# References from a TO-BE document
# ---------------------------------------------------------------------------


class TestScenarioReferences:
    def test_a_bulleted_reference_is_found(self) -> None:
        text = "## Acceptance Criteria\n\n- [ ] Scenario: `an inert rule is reported`\n"
        refs = parse_scenario_references(text, path="PRD.md")
        assert [r.name for r in refs] == ["an inert rule is reported"]
        assert refs[0].line == 3

    def test_emphasis_and_trailing_punctuation_are_stripped(self) -> None:
        text = "- **Scenario:** *an order is placed*.\n"
        refs = parse_scenario_references(text, path="PRD.md")
        assert [r.name for r in refs] == ["an order is placed"]

    def test_prose_mentioning_a_scenario_mid_sentence_is_not_a_reference(self) -> None:
        text = "The rule is proved by one scenario: the inert one, which we wrote first.\n"
        assert parse_scenario_references(text, path="PRD.md") == ()

    def test_a_fenced_block_is_a_template_not_a_reference(self) -> None:
        """templates.md ships the scenario FORM in a fence; a form is not a claim."""
        text = (
            "Acceptance criteria are scenarios:\n"
            "\n"
            "```gherkin\n"
            "Scenario: [what the user can observe]\n"
            "```\n"
            "\n"
            "- [ ] Scenario: a real claim\n"
        )
        refs = parse_scenario_references(text, path="templates.md")
        assert [r.name for r in refs] == ["a real claim"]

    def test_a_backtick_delimited_reference_ends_at_the_closing_backtick(self) -> None:
        """The form this epic's own PRD already uses: the backticks ARE the delimiter."""
        text = (
            "- [ ] `Scenario: A guard leaves the index unchanged` (read-only, #147)\n"
            "- [ ] `Scenario: A mutation target is reported` — declaring a target that\n"
            "      runs zero mutants is a gate that does not exist\n"
        )
        refs = parse_scenario_references(text, path="PRD.md")
        assert [r.name for r in refs] == [
            "A guard leaves the index unchanged",
            "A mutation target is reported",
        ]

    def test_an_unclosed_backtick_still_yields_the_name(self) -> None:
        refs = parse_scenario_references("- [ ] `Scenario: half open\n", path="PRD.md")
        assert [r.name for r in refs] == ["half open"]

    def test_an_empty_reference_name_is_ignored(self) -> None:
        assert parse_scenario_references("- Scenario:\n", path="PRD.md") == ()

    def test_load_references_reports_the_globs_that_matched_nothing(self, tmp_path: Path) -> None:
        _write(tmp_path / "docs/PRD.md", "- [ ] Scenario: a real claim\n")
        refs, dead = load_references(tmp_path, ("docs/**/PRD.md", "nowhere/**/*.md"))
        assert [r.name for r in refs] == ["a real claim"]
        assert dead == ("nowhere/**/*.md",)
