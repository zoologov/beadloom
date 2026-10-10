"""A ``test_binding`` or ``scenario_binding`` block is read into its rule, or refused by name.

Both rules judge the test suite and both take a listed ``exempt``: each entry lists
its subjects under exactly one key, with a reason and an exit condition. What is
pinned here is what an adopter sees: the fields each block becomes, and the whole
message a refused block produces, which names the rule, the block and the entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import (
    ListedExemption,
    NodeMatcher,
    ScenarioBindingRule,
    TestBindingRule,
)
from beadloom.graph.scenarios import DEFAULT_FEATURE_GLOB
from tests.support.rules_yaml import exactly, write_rules_file

if TYPE_CHECKING:
    from pathlib import Path

#: Each suite rule's key, a leg that lets it take a ``files`` exemption, and the
#: keys its exemption entries may list their subjects under, as the message quotes them.
SUITE_BLOCKS = [
    pytest.param(
        "test_binding", '      files: "tests/**"\n', "'files', 'nodes'", id="test_binding"
    ),
    pytest.param("scenario_binding", "", "'files'", id="scenario_binding"),
]

_REASON_AND_EXIT = '          reason: "tests two nodes"\n          until: "split by node"\n'


def _suite_rule(key: str, lines: str) -> str:
    """One rule named ``suite`` holding a *key* block made of *lines*."""
    return f"  - name: suite\n    {key}:\n{lines}"


class TestTheBlockBecomesItsRule:
    """Each field the block declares arrives on the rule unchanged."""

    def test_a_test_binding_block_becomes_the_rule_it_declares(self, tmp_path: Path) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            "  - name: test-binding\n"
            '    description: "every test file binds to a node"\n'
            "    severity: error\n"
            "    test_binding:\n"
            '      files: "tests/**"\n'
            "      for: { kind: feature }\n"
            "      exempt:\n"
            "        - files: [tests/test_mixed.py]\n"
            '          reason: "tests several nodes"\n'
            '          until: "split by node"\n'
            "        - nodes: [billing]\n"
            '          reason: "tested only end to end"\n'
            '          until: "billing has a unit layer"\n',
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert rule == TestBindingRule(
            name="test-binding",
            description="every test file binds to a node",
            for_matcher=NodeMatcher(kind="feature"),
            files="tests/**",
            exempt_files=(
                ListedExemption(
                    entries=("tests/test_mixed.py",),
                    reason="tests several nodes",
                    until="split by node",
                ),
            ),
            exempt_nodes=(
                ListedExemption(
                    entries=("billing",),
                    reason="tested only end to end",
                    until="billing has a unit layer",
                ),
            ),
            severity="error",
        )

    def test_a_scenario_binding_block_becomes_the_rule_it_declares(self, tmp_path: Path) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            "  - name: scenario-binding\n"
            '    description: "a scenario lives in its node folder"\n'
            "    severity: error\n"
            "    scenario_binding:\n"
            '      features: "tests/acceptance/**/*.feature"\n'
            "      exempt:\n"
            "        - files: [tests/acceptance/checkout.feature]\n"
            '          reason: "its tag names the node its steps run through"\n'
            '          until: "the feature is rewritten against its node"\n',
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert rule == ScenarioBindingRule(
            name="scenario-binding",
            description="a scenario lives in its node folder",
            features="tests/acceptance/**/*.feature",
            exempt=(
                ListedExemption(
                    entries=("tests/acceptance/checkout.feature",),
                    reason="its tag names the node its steps run through",
                    until="the feature is rewritten against its node",
                ),
            ),
            severity="error",
        )

    def test_a_scenario_binding_naming_no_features_reads_the_default_glob(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        path = write_rules_file(tmp_path, "  - name: scenario-binding\n    scenario_binding: {}\n")

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, ScenarioBindingRule)
        assert rule.features == DEFAULT_FEATURE_GLOB


class TestAMalformedTestBindingIsRefusedByName:
    """The refusal names the rule and the part of ``test_binding`` that is wrong."""

    def test_a_for_that_is_not_a_mapping_is_refused(self, tmp_path: Path) -> None:
        # Arrange
        path = write_rules_file(tmp_path, _suite_rule("test_binding", "      for: feature\n"))

        # Act / Assert
        with pytest.raises(
            ValueError, match=exactly("Rule 'suite': test_binding.for must be a mapping")
        ):
            load_rules(path)

    def test_a_for_matcher_naming_nothing_is_refused_under_its_block(self, tmp_path: Path) -> None:
        # Arrange
        path = write_rules_file(tmp_path, _suite_rule("test_binding", "      for: {}\n"))

        # Act / Assert
        with pytest.raises(
            ValueError,
            match=exactly(
                "Rule 'suite' test_binding.for: node matcher must have at least one of "
                "'ref_id', 'kind', 'tag', or 'tag_prefix'"
            ),
        ):
            load_rules(path)

    def test_a_files_exemption_without_a_files_leg_is_refused(self, tmp_path: Path) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _suite_rule(
                "test_binding",
                "      for: { kind: feature }\n"
                "      exempt:\n"
                "        - files: [tests/test_mixed.py]\n" + _REASON_AND_EXIT,
            ),
        )

        # Act / Assert
        with pytest.raises(
            ValueError,
            match=exactly("Rule 'suite': test_binding exempts files but declares no 'files' leg"),
        ):
            load_rules(path)


class TestAMalformedExemptionIsRefusedByName:
    """An ``exempt`` entry is refused with the rule, the block and the entry's index."""

    @pytest.mark.parametrize(("key", "leg", "allowed"), SUITE_BLOCKS)
    def test_an_exempt_that_is_not_a_list_is_refused(
        self, tmp_path: Path, key: str, leg: str, allowed: str
    ) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path, _suite_rule(key, leg + "      exempt: tests/test_mixed.py\n")
        )

        # Act / Assert
        with pytest.raises(
            ValueError, match=exactly(f"Rule 'suite': {key}.exempt must be a list")
        ):
            load_rules(path)

    @pytest.mark.parametrize(("key", "leg", "allowed"), SUITE_BLOCKS)
    def test_an_entry_that_is_not_a_mapping_is_refused(
        self, tmp_path: Path, key: str, leg: str, allowed: str
    ) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path, _suite_rule(key, leg + "      exempt: [tests/test_mixed.py]\n")
        )

        # Act / Assert
        with pytest.raises(
            ValueError, match=exactly(f"Rule 'suite': {key}.exempt[0] must be a mapping")
        ):
            load_rules(path)

    @pytest.mark.parametrize(("key", "leg", "allowed"), SUITE_BLOCKS)
    def test_an_entry_listing_no_subject_key_is_refused_with_the_keys_allowed(
        self, tmp_path: Path, key: str, leg: str, allowed: str
    ) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _suite_rule(
                key, leg + "      exempt:\n        - paths: [tests/x.py]\n" + _REASON_AND_EXIT
            ),
        )

        # Act / Assert
        with pytest.raises(
            ValueError,
            match=exactly(f"Rule 'suite': {key}.exempt[0] must list exactly one of {allowed}"),
        ):
            load_rules(path)

    @pytest.mark.parametrize(("key", "leg", "allowed"), SUITE_BLOCKS)
    @pytest.mark.parametrize("files", ["tests/test_mixed.py", "[]"], ids=["a-string", "empty"])
    def test_files_that_are_not_a_non_empty_list_are_refused(
        self, tmp_path: Path, key: str, leg: str, allowed: str, files: str
    ) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _suite_rule(
                key, leg + f"      exempt:\n        - files: {files}\n" + _REASON_AND_EXIT
            ),
        )

        # Act / Assert
        with pytest.raises(
            ValueError,
            match=exactly(f"Rule 'suite': {key}.exempt[0].files must be a non-empty list"),
        ):
            load_rules(path)
