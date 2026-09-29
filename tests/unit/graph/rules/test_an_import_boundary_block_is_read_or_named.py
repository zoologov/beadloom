"""An import boundary block is read into its rule, and a malformed one is refused by name.

``forbid_import`` and ``test_import_boundary`` share one reader for their ``from``,
``to`` and ``exempt`` keys, so an entry means the same in both. What is pinned here
is what an adopter sees: the fields each block becomes, and the whole message a
refused block produces, which must name the rule and the block it came from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import (
    ImportBoundaryRule,
    ImportExemption,
    NodeMatcher,
    TestImportBoundaryRule,
)
from tests.support.rules_yaml import exactly, write_rules_file

if TYPE_CHECKING:
    from pathlib import Path

BOUNDARY_KEYS = ("forbid_import", "test_import_boundary")


def _boundary(key: str, lines: str) -> str:
    """One rule named ``boundary`` holding a *key* block made of *lines*."""
    return f"  - name: boundary\n    {key}:\n{lines}"


class TestTheBlockBecomesItsRule:
    """Each field the block declares arrives on the rule unchanged."""

    def test_a_test_import_boundary_block_becomes_the_rule_it_declares(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            "  - name: domain-unit-tests-no-infra\n"
            '    description: "a domain unit test imports no infrastructure"\n'
            "    severity: warn\n"
            "    test_import_boundary:\n"
            '      from: "tests/unit/**"\n'
            '      to: "pkg/infrastructure/**"\n',
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert rule == TestImportBoundaryRule(
            name="domain-unit-tests-no-infra",
            description="a domain unit test imports no infrastructure",
            from_glob="tests/unit/**",
            to_glob="pkg/infrastructure/**",
            of_matcher=None,
            severity="warn",
            exempt=(),
        )

    def test_a_test_import_boundary_of_is_read_as_a_node_matcher(self, tmp_path: Path) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _boundary(
                "test_import_boundary",
                '      from: "tests/unit/**"\n'
                '      to: "pkg/infrastructure/**"\n'
                "      of: { tag: layer-domain }\n",
            ),
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, TestImportBoundaryRule)
        assert rule.of_matcher == NodeMatcher(tag="layer-domain")

    @pytest.mark.parametrize("key", BOUNDARY_KEYS)
    def test_an_exemption_naming_only_its_importer_exempts_every_target(
        self, tmp_path: Path, key: str
    ) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _boundary(
                key,
                '      from: "a/**"\n'
                '      to: "b/**"\n'
                "      exempt:\n"
                '        - from: "a/legacy.py"\n'
                '          reason: "predates the boundary"\n'
                '          until: "legacy.py is split"\n',
            ),
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, (ImportBoundaryRule, TestImportBoundaryRule))
        assert rule.exempt == (
            ImportExemption(
                to_glob="*",
                from_glob="a/legacy.py",
                reason="predates the boundary",
                until="legacy.py is split",
            ),
        )


class TestAMalformedBlockIsRefusedByName:
    """The refusal names the rule, the block and the key that is wrong."""

    @pytest.mark.parametrize("key", BOUNDARY_KEYS)
    @pytest.mark.parametrize("field", ["from", "to"])
    @pytest.mark.parametrize("value", ['"   "', "5"], ids=["blank", "not-a-string"])
    def test_a_glob_that_is_not_a_non_empty_string_is_refused(
        self, tmp_path: Path, key: str, field: str, value: str
    ) -> None:
        # Arrange
        globs = {"from": '"a/**"', "to": '"b/**"', field: value}
        path = write_rules_file(
            tmp_path,
            _boundary(key, f"      from: {globs['from']}\n      to: {globs['to']}\n"),
        )

        # Act / Assert
        with pytest.raises(
            ValueError, match=exactly(f"Rule 'boundary': {key}.{field} must be a non-empty string")
        ):
            load_rules(path)

    @pytest.mark.parametrize("key", BOUNDARY_KEYS)
    def test_an_exempt_that_is_not_a_list_is_refused(self, tmp_path: Path, key: str) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _boundary(key, '      from: "a/**"\n      to: "b/**"\n      exempt: "a/legacy.py"\n'),
        )

        # Act / Assert
        with pytest.raises(
            ValueError, match=exactly(f"Rule 'boundary': {key}.exempt must be a list")
        ):
            load_rules(path)

    @pytest.mark.parametrize("key", BOUNDARY_KEYS)
    def test_an_exempt_entry_that_is_not_a_mapping_is_refused_under_its_block(
        self, tmp_path: Path, key: str
    ) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _boundary(
                key, '      from: "a/**"\n      to: "b/**"\n      exempt: ["a/legacy.py"]\n'
            ),
        )

        # Act / Assert
        with pytest.raises(
            ValueError, match=exactly(f"Rule 'boundary': {key}.exempt[0] must be a mapping")
        ):
            load_rules(path)

    def test_an_of_that_is_not_a_mapping_is_refused(self, tmp_path: Path) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _boundary(
                "test_import_boundary",
                '      from: "a/**"\n      to: "b/**"\n      of: layer-domain\n',
            ),
        )

        # Act / Assert
        with pytest.raises(
            ValueError,
            match=exactly("Rule 'boundary': test_import_boundary.of must be a mapping"),
        ):
            load_rules(path)

    def test_an_of_matcher_naming_nothing_is_refused_under_its_block(self, tmp_path: Path) -> None:
        # Arrange
        path = write_rules_file(
            tmp_path,
            _boundary(
                "test_import_boundary",
                '      from: "a/**"\n      to: "b/**"\n      of: {}\n',
            ),
        )

        # Act / Assert
        with pytest.raises(
            ValueError,
            match=exactly(
                "Rule 'boundary' test_import_boundary.of: node matcher must have at "
                "least one of 'ref_id', 'kind', or 'tag'"
            ),
        ):
            load_rules(path)
