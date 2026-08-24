"""`scenario-coverage` — the rule that says which behaviour has no executable claim.

BDL-061 S4 (`beadloom-mr2l.13`). The rule binds both ways: a behaviour-bearing node
with no scenario is reported, and a scenario that names no bead — or names a node
that is not in the graph — is reported too. A scenario a PRD claims exists and the
suite does not is the third direction.

`severity: warn`, and the reason is the one `.48` and `.49` settled on: a finding
about declared *configuration* or *intent* is not a finding about code, and `error`
would redden every adopter on upgrade. Loudness replaces blocking — the finding is
printed by default, typed in `--json`, and every message states the population it
is a fraction of.

Two standing rules shape this file. **A check that cannot fail is not a check**
(`.48` found four of nine rule types counting clean while unable to match, `.10`
found a `config-check` verifying nothing): every leg below has a test that proves
it reports, and the inert cases are proved to report *themselves*. **A green count
is not a checked count**: the messages are asserted to carry the denominator.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    NodeMatcher,
    NonBehaviouralNode,
    ScenarioCoverageRule,
    evaluate_all,
    evaluate_scenario_coverage_rules,
    load_rules,
)
from beadloom.graph.scenarios import DEFAULT_FEATURE_GLOB
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules import Violation

SCENARIO_COVERAGE = "scenario_coverage"


def _db(tmp_path: Path, nodes: tuple[tuple[str, str], ...]) -> sqlite3.Connection:
    conn = open_db(tmp_path / "graph.db")
    create_schema(conn)
    for ref_id, kind in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)", (ref_id, kind, "")
        )
    conn.commit()
    return conn


def _feature(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rule(**kwargs: object) -> ScenarioCoverageRule:
    defaults: dict[str, object] = {
        "name": "scenario-coverage",
        "description": "behaviour carries an executable claim",
        "for_matcher": NodeMatcher(kind="feature"),
    }
    defaults.update(kwargs)
    return ScenarioCoverageRule(**defaults)  # type: ignore[arg-type]


def _of_type(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


def _messages(violations: list[Violation]) -> str:
    return "\n".join(v.message for v in violations)


# ---------------------------------------------------------------------------
# The bite: a node that should have a scenario and does not
# ---------------------------------------------------------------------------


class TestNodeWithoutScenario:
    def test_a_behaviour_bearing_node_with_no_scenario_is_reported(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("rule-engine", "feature"), ("scenario-binding", "feature")))
        _feature(
            tmp_path,
            "tests/acceptance/features/covered.feature",
            "@bead:proj-1 @node:rule-engine\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        uncovered = [v.from_ref_id for v in _of_type(violations, SCENARIO_COVERAGE)]
        assert uncovered == ["scenario-binding"]

    def test_the_message_states_the_population_it_is_a_fraction_of(self, tmp_path: Path) -> None:
        """A green count is not a checked count: `no scenario` needs a denominator."""
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/other.feature",
            "@node:beta\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        message = _messages([v for v in violations if v.from_ref_id == "alpha"])
        assert "1 scenario" in message
        assert "1 file" in message

    def test_every_covered_node_is_silent(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        assert violations == []

    def test_a_node_the_matcher_excludes_is_not_the_rules_business(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"), ("infra", "domain")))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        assert violations == []

    def test_severity_is_the_rules_and_defaults_to_warn(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(tmp_path, "tests/acceptance/features/a.feature", "Feature: F\n  Scenario: S\n")
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        assert _rule().severity == "warn"
        assert {v.severity for v in _of_type(violations, SCENARIO_COVERAGE)} == {"warn"}


# ---------------------------------------------------------------------------
# The other direction: what a scenario claims
# ---------------------------------------------------------------------------


class TestScenarioBindings:
    def test_a_scenario_naming_no_bead_is_reported(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@node:alpha\nFeature: F\n  Scenario: unbound\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        unbound = [v for v in violations if v.file_path == "tests/acceptance/features/a.feature"]
        assert len(unbound) == 1
        assert unbound[0].line_number == 3
        assert "unbound" in unbound[0].message
        assert "@bead:" in (unbound[0].remediation or unbound[0].message)

    def test_the_finding_says_the_bead_itself_was_not_verified(self, tmp_path: Path) -> None:
        """The tracker is not readable from the rule engine, and the report says so."""
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@node:alpha\nFeature: F\n  Scenario: unbound\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        text = "\n".join(f"{v.message} {v.remediation}" for v in violations)
        assert "not verified" in text

    def test_a_scenario_naming_a_node_outside_the_graph_is_reported(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha @node:typo-node\n"
            "Feature: F\n"
            "  Scenario: S\n"
            "    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        assert [v.to_ref_id for v in violations] == ["typo-node"]

    def test_an_unreadable_feature_file_is_reported(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        _feature(
            tmp_path, "tests/acceptance/features/ja.feature", "# language: ja\n機能: なにか\n"
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        paths = [v.file_path for v in violations]
        assert "tests/acceptance/features/ja.feature" in paths

    def test_a_feature_file_declaring_no_scenario_is_reported(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        _feature(tmp_path, "tests/acceptance/features/hollow.feature", "Feature: nothing yet\n")
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        hollow = [
            v for v in violations if v.file_path == "tests/acceptance/features/hollow.feature"
        ]
        assert len(hollow) == 1
        assert "no scenario" in hollow[0].message


# ---------------------------------------------------------------------------
# A PRD-referenced scenario that is not in the suite
# ---------------------------------------------------------------------------


class TestReferencedScenarios:
    def test_a_referenced_scenario_absent_from_the_suite_is_reported(
        self, tmp_path: Path
    ) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: written\n    Given a step\n",
        )
        prd = tmp_path / "docs/PRD.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text(
            "## Acceptance Criteria\n\n- [ ] Scenario: `written`\n- [ ] Scenario: `promised`\n",
            encoding="utf-8",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule(references=("docs/**/PRD.md",))], project_root=tmp_path
            )
        finally:
            conn.close()
        missing = [v for v in violations if v.file_path == "docs/PRD.md"]
        assert len(missing) == 1
        assert "promised" in missing[0].message
        assert missing[0].line_number == 4

    def test_a_reference_glob_matching_no_document_reports_itself(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule(references=("docs/**/PRD.md",))], project_root=tmp_path
            )
        finally:
            conn.close()
        inert = _of_type(violations, LIVENESS_RULE_TYPE)
        assert len(inert) == 1
        assert "docs/**/PRD.md" in inert[0].message


# ---------------------------------------------------------------------------
# A chore may declare itself non-behavioural
# ---------------------------------------------------------------------------


class TestNonBehavioural:
    def test_a_declared_node_is_accepted_and_not_reported_as_uncovered(
        self, tmp_path: Path
    ) -> None:
        """Accepted means the coverage leg lets it through — the bite of the mechanism."""
        conn = _db(tmp_path, (("alpha", "feature"), ("types", "feature")))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        rule = _rule(
            non_behavioural=(
                NonBehaviouralNode(node="types", reason="frozen dataclasses; no behaviour"),
            )
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()
        assert not [v for v in violations if v.from_ref_id == "types"], _messages(violations)

    def test_a_live_declaration_states_what_it_took_out_of_the_population(
        self, tmp_path: Path
    ) -> None:
        """PLAN's criterion was "accepted WITH A NAMED REASON" (review `.15` M1b).

        Accepted in silence is not that: the excused node leaves the population,
        the coverage fraction improves, and until now nothing said the
        denominator had moved. `.63`'s option 2 — print the denominator beside
        the fraction — was implemented in no form at all.
        """
        conn = _db(tmp_path, (("alpha", "feature"), ("types", "feature")))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        rule = _rule(
            non_behavioural=(
                NonBehaviouralNode(node="types", reason="frozen dataclasses; no behaviour"),
            )
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()
        assert len(violations) == 1, _messages(violations)
        message = violations[0].message
        assert "1 of 2" in message, message
        assert "frozen dataclasses; no behaviour" in message, message

    def test_nothing_is_said_when_nothing_is_excused(self, tmp_path: Path) -> None:
        """A line about zero excused nodes on every lint is how a real one goes unread."""
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        assert violations == []

    def test_a_dead_declaration_excuses_nothing_and_is_not_counted_as_excusing(
        self, tmp_path: Path
    ) -> None:
        """The non-vacuity guard: "state something for every declaration" must not pass."""
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        rule = _rule(
            non_behavioural=(NonBehaviouralNode(node="gone", reason="it was deleted"),)
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()
        assert len(violations) == 1, _messages(violations)
        assert "excuses nothing" in violations[0].message

    def test_the_statement_is_warn_even_when_the_rule_declares_error(
        self, tmp_path: Path
    ) -> None:
        """Doing the thing PLAN says is accepted must never redden a pipeline."""
        conn = _db(tmp_path, (("alpha", "feature"), ("types", "feature")))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        rule = _rule(
            severity="error",
            non_behavioural=(
                NonBehaviouralNode(node="types", reason="frozen dataclasses; no behaviour"),
            ),
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()
        assert [v.severity for v in violations] == ["warn"], _messages(violations)

    def test_a_declaration_naming_a_node_outside_the_population_is_reported(
        self, tmp_path: Path
    ) -> None:
        """A dead declaration is the exit condition firing (`.49`), not a silent pass."""
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        rule = _rule(
            non_behavioural=(NonBehaviouralNode(node="gone", reason="it was deleted"),)
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()
        assert len(violations) == 1
        assert "gone" in violations[0].message

    def test_a_declared_node_that_has_a_scenario_anyway_is_reported(
        self, tmp_path: Path
    ) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        rule = _rule(
            non_behavioural=(NonBehaviouralNode(node="alpha", reason="no behaviour here"),)
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()
        assert len(violations) == 1
        assert "alpha" in violations[0].message


# ---------------------------------------------------------------------------
# The rule that cannot fire reports itself (the S2b standard)
# ---------------------------------------------------------------------------


class TestLiveness:
    def test_a_features_glob_matching_nothing_reports_itself(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        assert [v.rule_type for v in violations] == [LIVENESS_RULE_TYPE]
        assert DEFAULT_FEATURE_GLOB in violations[0].message
        assert violations[0].severity == "warn"

    def test_an_empty_suite_does_not_also_report_every_node(self, tmp_path: Path) -> None:
        """One configuration error must not print as N architecture findings."""
        conn = _db(tmp_path, (("a", "feature"), ("b", "feature"), ("c", "feature")))
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        assert _of_type(violations, SCENARIO_COVERAGE) == []

    def test_a_for_matcher_selecting_nothing_reports_itself(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "domain"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@bead:proj-1 @node:alpha\nFeature: F\n  Scenario: S\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        inert = _of_type(violations, LIVENESS_RULE_TYPE)
        assert len(inert) == 1
        assert "kind=feature" in inert[0].message

    def test_the_scenario_legs_still_run_when_only_the_coverage_leg_is_inert(
        self, tmp_path: Path
    ) -> None:
        """Per-LEG liveness: one dead leg must not stand the whole rule down."""
        conn = _db(tmp_path, (("alpha", "domain"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "Feature: F\n  Scenario: unbound\n    Given a step\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn, [_rule()], project_root=tmp_path
            )
        finally:
            conn.close()
        assert _of_type(violations, SCENARIO_COVERAGE) != []


# ---------------------------------------------------------------------------
# Configuration: rules.yml, dispatch, and the index
# ---------------------------------------------------------------------------


class TestYamlParsing:
    def test_a_full_rule_parses(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: scenario-coverage\n"
            "    description: behaviour carries an executable claim\n"
            "    scenario_coverage:\n"
            "      for: { kind: feature }\n"
            "      features: 'spec/**/*.feature'\n"
            "      references:\n"
            "        - 'docs/**/PRD.md'\n"
            "      non_behavioural:\n"
            "        - node: types\n"
            "          reason: frozen dataclasses; no behaviour\n",
            encoding="utf-8",
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, ScenarioCoverageRule)
        assert rule.for_matcher == NodeMatcher(kind="feature")
        assert rule.features == "spec/**/*.feature"
        assert rule.references == ("docs/**/PRD.md",)
        assert rule.non_behavioural == (
            NonBehaviouralNode(node="types", reason="frozen dataclasses; no behaviour"),
        )
        assert rule.severity == "warn"

    def test_defaults_when_omitted(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: scenario-coverage\n"
            "    description: d\n"
            "    scenario_coverage: {}\n",
            encoding="utf-8",
        )
        rule = load_rules(rules_path)[0]
        assert isinstance(rule, ScenarioCoverageRule)
        assert rule.features == DEFAULT_FEATURE_GLOB
        assert rule.references == ()
        assert rule.severity == "warn"

    def test_a_declaration_without_a_reason_is_a_configuration_error(
        self, tmp_path: Path
    ) -> None:
        """CONTEXT: an unnamed exclusion is how a gate is quietly switched off."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: scenario-coverage\n"
            "    description: d\n"
            "    scenario_coverage:\n"
            "      non_behavioural:\n"
            "        - node: types\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="reason"):
            load_rules(rules_path)

    def test_a_declaration_without_a_node_is_a_configuration_error(
        self, tmp_path: Path
    ) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: scenario-coverage\n"
            "    description: d\n"
            "    scenario_coverage:\n"
            "      non_behavioural:\n"
            "        - reason: because\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="node"):
            load_rules(rules_path)

    def test_a_bare_for_exclude_is_a_configuration_error(self, tmp_path: Path) -> None:
        """The same rule as `non_behavioural`, applied to the other exit (review `.15` M1a).

        `NodeMatcher.exclude` takes a node out of the population with no reason,
        no report and no expiry, and `_matcher_description` does not even print
        it — so a matcher excluded down to nothing reports "the `for` matcher
        (kind=feature) selects no node" without saying why. CONTEXT's standing
        decision is that every exclusion carries a reason.
        """
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: scenario-coverage\n"
            "    description: d\n"
            "    scenario_coverage:\n"
            "      for: { kind: feature, exclude: [types] }\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="non_behavioural"):
            load_rules(rules_path)

    def test_the_error_names_the_excluded_nodes(self, tmp_path: Path) -> None:
        """An author must be able to move each one without re-reading the file."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: scenario-coverage\n"
            "    description: d\n"
            "    scenario_coverage:\n"
            "      for: { kind: feature, exclude: [types, vocabulary] }\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="types, vocabulary"):
            load_rules(rules_path)

    def test_a_for_matcher_without_exclude_still_parses(self, tmp_path: Path) -> None:
        """The non-vacuity guard: rejecting every `for` block would pass the two above."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: scenario-coverage\n"
            "    description: d\n"
            "    scenario_coverage:\n"
            "      for: { kind: feature }\n",
            encoding="utf-8",
        )
        rule = load_rules(rules_path)[0]
        assert isinstance(rule, ScenarioCoverageRule)
        assert rule.for_matcher == NodeMatcher(kind="feature")

    def test_exclude_is_still_accepted_on_every_other_rule_type(
        self, tmp_path: Path
    ) -> None:
        """Scoped deliberately: `exclude` is shared, and widening is its own decision.

        Requiring a reason on every rule type would turn an adopter's green
        project red on upgrade for rules this epic never touched. This rule type
        ships in the same release as the requirement, so nobody has written one
        yet.
        """
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: no-peer-domains\n"
            "    description: d\n"
            "    deny:\n"
            "      from: { kind: domain, exclude: [types] }\n"
            "      to: { kind: domain }\n",
            encoding="utf-8",
        )
        rule = load_rules(rules_path)[0]
        assert rule.from_matcher.exclude == ("types",)  # type: ignore[union-attr]

    def test_not_a_mapping_is_rejected(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: scenario-coverage\n"
            "    description: d\n"
            "    scenario_coverage: not-a-mapping\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="must be a mapping"):
            load_rules(rules_path)


class TestEvaluateAllDispatch:
    def test_evaluate_all_dispatches_the_new_rule_type(self, tmp_path: Path) -> None:
        conn = _db(tmp_path, (("alpha", "feature"),))
        _feature(
            tmp_path,
            "tests/acceptance/features/a.feature",
            "@node:alpha\nFeature: F\n  Scenario: unbound\n    Given a step\n",
        )
        try:
            violations = evaluate_all(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()
        assert _of_type(violations, SCENARIO_COVERAGE) != []

    def test_the_index_accepts_the_new_rule_type(self, tmp_path: Path) -> None:
        """A rule type the DB rejects is a reindex that dies on somebody's laptop."""
        from beadloom.application.reindex.rules_loader import _serialize_rule

        rule_type, rule_def = _serialize_rule(_rule(references=("docs/PRD.md",)))
        assert rule_type == SCENARIO_COVERAGE
        conn = _db(tmp_path, ())
        try:
            conn.execute(
                "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
                "VALUES (?, ?, ?, ?, 1)",
                ("scenario-coverage", "d", rule_type, "{}"),
            )
            conn.commit()
        finally:
            conn.close()
        assert rule_def["features"] == DEFAULT_FEATURE_GLOB

    def test_a_database_created_before_this_release_accepts_the_rule(
        self, tmp_path: Path
    ) -> None:
        """The CHECK was a second source of truth for the rule vocabulary (#171)."""
        from beadloom.infrastructure.db import ensure_schema_migrations

        db_path = tmp_path / "old.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE rules ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  name TEXT NOT NULL UNIQUE,"
            "  description TEXT NOT NULL DEFAULT '',"
            "  rule_type TEXT NOT NULL CHECK(rule_type IN ("
            "    'deny', 'require', 'forbid_cycles', 'layers',"
            "    'cardinality', 'forbid_import', 'forbid_edge',"
            "    'unregistered_feature_candidate', 'module_coverage'"
            "  )),"
            "  rule_json TEXT NOT NULL,"
            "  enabled INTEGER NOT NULL DEFAULT 1"
            ")"
        )
        conn.execute(
            "INSERT INTO rules (name, description, rule_type, rule_json) VALUES (?,?,?,?)",
            ("old", "d", "deny", "{}"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO rules (name, description, rule_type, rule_json) VALUES (?,?,?,?)",
                ("new", "d", SCENARIO_COVERAGE, "{}"),
            )
        conn.rollback()

        ensure_schema_migrations(conn)
        conn.execute(
            "INSERT INTO rules (name, description, rule_type, rule_json) VALUES (?,?,?,?)",
            ("new", "d", SCENARIO_COVERAGE, "{}"),
        )
        conn.commit()
        rows = conn.execute("SELECT name FROM rules ORDER BY name").fetchall()
        conn.close()
        assert [r[0] for r in rows] == ["new", "old"]


class TestAnAdopterThatIsNotUs:
    def test_a_typescript_project_with_its_own_layout_is_read(self, tmp_path: Path) -> None:
        """S3b's lesson: a fixture that is not Beadloom, or the claim is local."""
        from tests.adopter_project import beadloom_local_facts_in, typescript_project

        project = typescript_project(tmp_path / "orders-web")
        _feature(
            project.root,
            "spec/acceptance/orders.feature",
            "@node:orders\nFeature: orders\n  Scenario: an order is placed\n    Given a cart\n",
        )
        conn = _db(tmp_path, (("orders", "feature"), ("checkout", "feature")))
        try:
            violations = evaluate_scenario_coverage_rules(
                conn,
                [_rule(features="spec/**/*.feature")],
                project_root=project.root,
            )
        finally:
            conn.close()
        text = "\n".join(
            f"{v.file_path} {v.from_ref_id} {v.message} {v.remediation}" for v in violations
        )
        assert beadloom_local_facts_in(text) == []
        assert "checkout" in text
        assert "spec/acceptance/orders.feature" in text
        assert DEFAULT_FEATURE_GLOB not in text
