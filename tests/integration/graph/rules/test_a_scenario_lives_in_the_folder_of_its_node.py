"""`scenario_binding` — a scenario's `@node:` tag names the folder it lives in.

BDL-074 C3. The acceptance suite is laid out one folder per node
(`<suite>/<domain>/<node>/*.feature`), so the folder that holds a feature file
names the node its scenarios bind to, and a folder above it that names a node
names a container of that node. The rule reports each disagreement, excuses only
the files an exemption lists, and states what it judged — including the half of
the binding it does not judge: whether a scenario's steps execute its node, which
needs a runtime trace.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    SCENARIO_BINDING_RULE_TYPE,
    SUITE_POPULATION_RULE_TYPE,
    ListedExemption,
    ScenarioBindingRule,
    evaluate_all,
    evaluate_scenario_binding_rules,
    inert_rule_names,
    load_rules,
)
from tests.support.suite_index import SuiteIndex, SuiteNode, write_feature, write_rules

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules import Violation

SUITE_GLOB = "specs/**/*.feature"


def _rule(**kwargs: object) -> ScenarioBindingRule:
    defaults: dict[str, object] = {
        "name": "scenario-binding",
        "description": "a scenario lives in the folder of its node",
        "features": SUITE_GLOB,
    }
    defaults.update(kwargs)
    return ScenarioBindingRule(**defaults)  # type: ignore[arg-type]  # kwargs typed by the test


def _index() -> SuiteIndex:
    return SuiteIndex(
        nodes=[
            SuiteNode("ledger", kind="domain"),
            SuiteNode("billing", part_of=("ledger",)),
            SuiteNode("invoicing", part_of=("ledger",)),
            SuiteNode("vault", kind="domain"),
        ]
    )


def _feature(tags: str, *scenarios: str) -> str:
    body = "".join(f"  {line}\n    Given a step\n" for line in scenarios)
    return f"{tags}\nFeature: F\n\n{body}"


def _evaluate(tmp_path: Path, rule: ScenarioBindingRule) -> list[Violation]:
    conn = _index().build(tmp_path)
    try:
        return evaluate_scenario_binding_rules(conn, [rule], project_root=tmp_path)
    finally:
        conn.close()


def _of_type(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


def _findings(violations: list[Violation]) -> list[Violation]:
    return _of_type(violations, SCENARIO_BINDING_RULE_TYPE)


class TestAFeatureFileWithNoScenario:
    """First review of ``beadloom-b9ll``, n3: the statement counts every file the glob
    matched, and a file with no scenario was never judged, so one in the wrong folder
    was never reported. Its place is judged like any other file's."""

    def test_one_in_a_folder_that_names_no_node_is_reported(self, tmp_path: Path) -> None:
        write_feature(tmp_path, "specs/ledger/nowhere/empty.feature", "Feature: F\n")
        (finding,) = _findings(_evaluate(tmp_path, _rule()))
        assert finding.file_path == "specs/ledger/nowhere/empty.feature"
        assert "`nowhere`, which names no node" in finding.message

    def test_one_in_its_nodes_folder_is_not_reported(self, tmp_path: Path) -> None:
        write_feature(tmp_path, "specs/ledger/billing/empty.feature", "Feature: F\n")
        assert _findings(_evaluate(tmp_path, _rule())) == []


class TestTheTagAndTheFolder:
    def test_a_scenario_tagged_with_its_folder_node_is_not_reported(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@node:billing", "Scenario: S")
        )

        assert _findings(_evaluate(tmp_path, _rule())) == []

    def test_a_scenario_tagged_with_another_node_is_reported_where_it_is(
        self, tmp_path: Path
    ) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@node:invoicing", "Scenario: S")
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule()))
        assert finding.file_path == "specs/ledger/billing/a.feature"
        assert finding.line_number == 4
        assert finding.from_ref_id == "billing"
        assert "`@node:invoicing`" in finding.message
        assert finding.severity == "warn"

    def test_a_scenario_level_tag_beside_the_folder_node_agrees(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path,
            "specs/ledger/billing/a.feature",
            "@node:billing\nFeature: F\n\n  @node:vault\n  Scenario: S\n    Given a step\n",
        )

        assert _findings(_evaluate(tmp_path, _rule())) == []

    def test_a_scenario_with_no_node_tag_in_a_node_folder_is_reported(
        self, tmp_path: Path
    ) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@bead:x-1", "Scenario: S")
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule()))
        assert "names no node" in finding.message

    def test_a_file_whose_folder_names_no_node_is_reported_once(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path,
            "specs/features/a.feature",
            _feature("@node:billing", "Scenario: S1", "Scenario: S2"),
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule()))
        assert finding.file_path == "specs/features/a.feature"
        assert "`features`" in finding.message
        assert "2 scenario(s)" in finding.message

    def test_a_file_in_the_suite_root_is_in_no_node_folder(self, tmp_path: Path) -> None:
        write_feature(tmp_path, "specs/a.feature", _feature("@node:billing", "Scenario: S"))

        (finding,) = _findings(_evaluate(tmp_path, _rule()))
        assert "no node folder" in finding.message

    def test_an_enclosing_folder_naming_a_node_must_contain_the_folder_node(
        self, tmp_path: Path
    ) -> None:
        write_feature(
            tmp_path, "specs/vault/billing/a.feature", _feature("@node:billing", "Scenario: S")
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule()))
        assert "`vault`" in finding.message
        assert "part_of" in finding.message

    def test_an_enclosing_folder_naming_no_node_is_not_judged(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path, "specs/services/billing/a.feature", _feature("@node:billing", "Scenario: S")
        )

        assert _findings(_evaluate(tmp_path, _rule())) == []

    def test_the_finding_carries_the_rule_severity(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@node:invoicing", "Scenario: S")
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule(severity="error")))
        assert finding.severity == "error"


class TestExemptions:
    def test_a_listed_file_is_excused_and_counted(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path, "specs/features/a.feature", _feature("@node:billing", "Scenario: S")
        )
        rule = _rule(
            exempt=(
                ListedExemption(
                    entries=("specs/features/a.feature",), reason="rewrite", until="E1"
                ),
            )
        )

        violations = _evaluate(tmp_path, rule)

        assert _findings(violations) == []
        (population,) = _of_type(violations, SUITE_POPULATION_RULE_TYPE)
        assert "1 in 1 file(s) excused by an exemption" in population.message

    def test_a_listed_file_that_now_agrees_is_reported_as_dead(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@node:billing", "Scenario: S")
        )
        rule = _rule(
            exempt=(
                ListedExemption(
                    entries=("specs/ledger/billing/a.feature",), reason="r", until="u"
                ),
            )
        )

        violations = _evaluate(tmp_path, rule)

        (dead,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert "specs/ledger/billing/a.feature" in dead.message


class TestPopulationAndLiveness:
    def test_the_population_names_the_half_it_does_not_judge(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@node:billing", "Scenario: S")
        )
        write_feature(
            tmp_path, "specs/ledger/invoicing/b.feature", _feature("@node:billing", "Scenario: S")
        )

        violations = _evaluate(tmp_path, _rule())

        (population,) = _of_type(violations, SUITE_POPULATION_RULE_TYPE)
        assert "judged 2 scenario(s) in 2 file(s)" in population.message
        assert "1 agree with their folder, 1 do not" in population.message
        assert "execute" in population.message
        assert "not judged" in population.message

    def test_an_absent_suite_is_reported_and_counted_inert(self, tmp_path: Path) -> None:
        conn = _index().build(tmp_path)
        try:
            violations = evaluate_all(conn, [_rule()], project_root=tmp_path)
            inert = inert_rule_names(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        (liveness,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert SUITE_GLOB in liveness.message
        assert inert == {"scenario-binding"}

    def test_a_live_suite_is_not_counted_inert(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@node:billing", "Scenario: S")
        )
        conn = _index().build(tmp_path)
        try:
            inert = inert_rule_names(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert inert == set()


#: A file in the suite root, one in a folder naming no node, and one under a folder that
#: names a node the folder's own node is not part of.
MISPLACED = [
    pytest.param("specs/a.feature", id="in the suite root"),
    pytest.param("specs/ledger/nowhere/a.feature", id="in a folder naming no node"),
    pytest.param("specs/vault/billing/a.feature", id="under the wrong container"),
]

MOVE_HINT = (
    "move the file to the folder of the node its scenarios bind to, "
    "`specs/<domain>/<node>/`; a file whose tag cannot be settled yet is exempted by path, "
    "with a reason and an exit condition"
)


class TestWhatAMisplacedFileIsToldToDo:
    @pytest.mark.parametrize("path", MISPLACED)
    def test_it_is_reported_at_its_own_path(self, tmp_path: Path, path: str) -> None:
        write_feature(tmp_path, path, _feature("@node:billing", "Scenario: S"))

        (finding,) = _findings(_evaluate(tmp_path, _rule()))

        assert finding.file_path == path

    @pytest.mark.parametrize("path", MISPLACED)
    def test_it_is_told_to_move_under_the_suite_root(self, tmp_path: Path, path: str) -> None:
        write_feature(tmp_path, path, _feature("@node:billing", "Scenario: S"))

        (finding,) = _findings(_evaluate(tmp_path, _rule()))

        assert finding.remediation == MOVE_HINT

    def test_under_the_wrong_container_it_is_reported_against_its_folder_node(
        self, tmp_path: Path
    ) -> None:
        write_feature(
            tmp_path, "specs/vault/billing/a.feature", _feature("@node:billing", "Scenario: S")
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule()))

        assert finding.from_ref_id == "billing"

    def test_every_enclosing_folder_is_judged_not_only_the_first(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path,
            "specs/services/vault/billing/a.feature",
            _feature("@node:billing", "Scenario: S"),
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule()))

        assert finding.message.startswith("the folder `vault` names a node")


class TestWhatAMistaggedScenarioIsToldToDo:
    def test_the_finding_names_every_node_the_scenario_carries(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path,
            "specs/ledger/billing/a.feature",
            _feature("@node:invoicing @node:vault", "Scenario: S"),
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule()))

        assert "names `@node:invoicing`, `@node:vault`, but" in finding.message

    def test_it_is_told_to_take_its_folder_node_tag_or_move(self, tmp_path: Path) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@node:vault", "Scenario: S")
        )

        (finding,) = _findings(_evaluate(tmp_path, _rule()))

        assert finding.remediation == (
            "tag the scenario `@node:billing` if it binds there, or move it to the folder "
            "of the node it binds to"
        )


class TestEveryFindingCarriesTheRuleDescription:
    @pytest.mark.parametrize(
        ("path", "text", "exempt", "rule_type"),
        [
            pytest.param(
                "specs/a.feature", "@node:billing", (), SCENARIO_BINDING_RULE_TYPE, id="file"
            ),
            pytest.param(
                "specs/ledger/billing/a.feature",
                "@node:vault",
                (),
                SCENARIO_BINDING_RULE_TYPE,
                id="scenario",
            ),
            pytest.param(
                "specs/ledger/billing/a.feature",
                "@node:billing",
                ("specs/ledger/billing/a.feature",),
                LIVENESS_RULE_TYPE,
                id="dead exemption entry",
            ),
            pytest.param(
                "specs/ledger/billing/a.feature",
                "@node:billing",
                (),
                SUITE_POPULATION_RULE_TYPE,
                id="population",
            ),
        ],
    )
    def test_on_a_suite_it_judged(
        self,
        tmp_path: Path,
        path: str,
        text: str,
        exempt: tuple[str, ...],
        rule_type: str,
    ) -> None:
        write_feature(tmp_path, path, _feature(text, "Scenario: S"))
        exemptions = (ListedExemption(entries=exempt, reason="r", until="u"),) if exempt else ()

        violations = _evaluate(tmp_path, _rule(exempt=exemptions))

        (finding,) = _of_type(violations, rule_type)
        assert finding.rule_description == "a scenario lives in the folder of its node"

    def test_on_a_suite_it_could_not_find(self, tmp_path: Path) -> None:
        (liveness,) = _of_type(_evaluate(tmp_path, _rule()), LIVENESS_RULE_TYPE)

        assert liveness.rule_description == "a scenario lives in the folder of its node"


class TestWhatAnExemptionExcusesAndHowItIsCounted:
    def test_a_glob_entry_excuses_every_file_it_matches(self, tmp_path: Path) -> None:
        for name in ("a", "b"):
            write_feature(
                tmp_path,
                f"specs/features/{name}.feature",
                _feature("@node:billing", "Scenario: S"),
            )
        exemption = ListedExemption(entries=("specs/features/*.feature",), reason="r", until="u")

        violations = _evaluate(tmp_path, _rule(exempt=(exemption,)))

        (population,) = _of_type(violations, SUITE_POPULATION_RULE_TYPE)
        assert "2 in 2 file(s) excused by an exemption, 0 reported" in population.message

    def test_only_the_disagreeing_scenarios_of_an_excused_file_are_counted_excused(
        self, tmp_path: Path
    ) -> None:
        write_feature(
            tmp_path,
            "specs/ledger/billing/a.feature",
            "Feature: F\n\n"
            "  @node:billing\n  Scenario: S1\n    Given a step\n\n"
            "  @node:vault\n  Scenario: S2\n    Given a step\n",
        )
        exemption = ListedExemption(
            entries=("specs/ledger/billing/a.feature",), reason="r", until="u"
        )

        violations = _evaluate(tmp_path, _rule(exempt=(exemption,)))

        (population,) = _of_type(violations, SUITE_POPULATION_RULE_TYPE)
        assert (
            "1 agree with their folder, 1 do not — 1 in 1 file(s) excused by an exemption, "
            "0 reported" in population.message
        )

    def test_an_excused_file_does_not_stop_the_files_after_it_being_judged(
        self, tmp_path: Path
    ) -> None:
        write_feature(
            tmp_path, "specs/features/a.feature", _feature("@node:billing", "Scenario: S")
        )
        write_feature(
            tmp_path, "specs/ledger/invoicing/b.feature", _feature("@node:billing", "Scenario: S")
        )
        exemption = ListedExemption(entries=("specs/features/a.feature",), reason="r", until="u")

        violations = _evaluate(tmp_path, _rule(exempt=(exemption,)))

        assert [f.file_path for f in _findings(violations)] == ["specs/ledger/invoicing/b.feature"]

    def test_a_dead_entry_is_reported_by_the_rule_as_excusing_no_feature_file(
        self, tmp_path: Path
    ) -> None:
        write_feature(
            tmp_path, "specs/ledger/billing/a.feature", _feature("@node:billing", "Scenario: S")
        )
        exemption = ListedExemption(
            entries=("specs/ledger/billing/a.feature",), reason="r", until="u"
        )

        violations = _evaluate(tmp_path, _rule(exempt=(exemption,)))

        (dead,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert dead.message.startswith(
            "Rule 'scenario-binding': the exemption entry `specs/ledger/billing/a.feature` "
            "excuses no feature file — "
        )


def test_an_absent_suite_is_told_to_point_features_at_it_or_delete_the_rule(
    tmp_path: Path,
) -> None:
    (liveness,) = _of_type(_evaluate(tmp_path, _rule()), LIVENESS_RULE_TYPE)

    assert liveness.remediation == (
        "point `features:` at the acceptance suite, or delete the rule — an absent suite "
        "is not a correctly placed one"
    )


class TestTheRuleIsDeclaredInRulesYml:
    def test_the_block_parses(self, tmp_path: Path) -> None:
        path = write_rules(
            tmp_path,
            "  - name: sb\n"
            "    scenario_binding:\n"
            "      features: 'specs/**/*.feature'\n"
            "      exempt:\n"
            "        - files: [specs/features/a.feature]\n"
            "          reason: its tag disagrees with the code its steps run\n"
            "          until: rewritten\n",
        )

        (rule,) = load_rules(path)

        assert isinstance(rule, ScenarioBindingRule)
        assert rule.features == SUITE_GLOB
        assert rule.exempt[0].entries == ("specs/features/a.feature",)
        assert rule.severity == "warn"

    def test_a_node_exemption_is_refused(self, tmp_path: Path) -> None:
        path = write_rules(
            tmp_path,
            "  - name: sb\n"
            "    scenario_binding:\n"
            "      exempt: [{ nodes: [billing], reason: r, until: u }]\n",
        )

        with pytest.raises(ValueError, match="files"):
            load_rules(path)


def test_the_rule_survives_being_written_to_the_index() -> None:
    from beadloom.application.reindex.rules_loader import _serialize_rule

    rule = _rule(exempt=(ListedExemption(entries=("specs/a.feature",), reason="r", until="u"),))

    rule_type, payload = _serialize_rule(rule)

    assert rule_type == "scenario_binding"
    assert payload == {
        "features": SUITE_GLOB,
        "exempt": [{"files": ["specs/a.feature"], "reason": "r", "until": "u"}],
    }
