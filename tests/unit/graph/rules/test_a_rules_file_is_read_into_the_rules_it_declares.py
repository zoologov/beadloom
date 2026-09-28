"""A ``rules.yml`` is read into the rules it declares, and a malformed block is named.

The loader's unit layer (BDL-074 E1): each case writes one small rules file into
``tmp_path`` and reads it with :func:`load_rules` — no index, no reindex, no other
filesystem. What is pinned is what an adopter sees: the fields a block becomes, and
the exact message a block the loader refuses produces, because that message is the
only thing an adopter reads when their ``rules.yml`` is wrong.

Three of the cases were written against mutants that survived the weekly sample on
2026-09-28 (run 36373061140): a ``check.for`` refused with no message, a
``forbid_import.exempt`` entry refused with no message, and a ``module_coverage``
``min_symbols`` read and then dropped.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import (
    CardinalityRule,
    CycleRule,
    DenyRule,
    ImportBoundaryRule,
    ModuleCoverageRule,
    NodeMatcher,
    RequireRule,
)

if TYPE_CHECKING:
    from pathlib import Path


def _rules_file(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "rules.yml"
    path.write_text(f"version: 1\nrules:\n{body}", encoding="utf-8")
    return path


def _exactly(message: str) -> str:
    """A ``pytest.raises`` pattern matching *message* and nothing longer or shorter."""
    return f"^{re.escape(message)}$"


class TestEachBlockBecomesItsRule:
    """The block's key decides the rule type; its fields arrive unchanged."""

    def test_a_deny_block_becomes_a_deny_rule_between_its_matchers(self, tmp_path: Path) -> None:
        # Arrange
        path = _rules_file(
            tmp_path,
            "  - name: no-billing-to-auth\n"
            '    description: "billing does not reach auth"\n'
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { tag: auth }\n",
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, DenyRule)
        assert (rule.name, rule.description) == (
            "no-billing-to-auth",
            "billing does not reach auth",
        )
        assert rule.from_matcher == NodeMatcher(ref_id="billing")
        assert rule.to_matcher == NodeMatcher(tag="auth")

    def test_a_require_block_keeps_its_edge_kind(self, tmp_path: Path) -> None:
        # Arrange
        path = _rules_file(
            tmp_path,
            "  - name: feature-in-domain\n"
            '    description: "every feature is part of a domain"\n'
            "    require:\n"
            "      for: { kind: feature }\n"
            "      has_edge_to: { kind: domain }\n"
            "      edge_kind: part_of\n",
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, RequireRule)
        assert rule.for_matcher == NodeMatcher(kind="feature")
        assert rule.has_edge_to == NodeMatcher(kind="domain")
        assert rule.edge_kind == "part_of"

    def test_a_forbid_cycles_block_keeps_its_depth(self, tmp_path: Path) -> None:
        # Arrange
        path = _rules_file(
            tmp_path,
            "  - name: no-cycles\n"
            '    description: "no circular dependencies"\n'
            "    forbid_cycles:\n"
            "      edge_kind: depends_on\n"
            "      max_depth: 4\n",
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, CycleRule)
        assert (rule.edge_kind, rule.max_depth) == ("depends_on", 4)

    def test_a_check_block_keeps_every_threshold_it_sets(self, tmp_path: Path) -> None:
        # Arrange
        path = _rules_file(
            tmp_path,
            "  - name: domain-size\n"
            '    description: "domains stay small"\n'
            "    check:\n"
            "      for: { kind: domain }\n"
            "      max_symbols: 200\n"
            "      max_files: 30\n"
            "      min_doc_coverage: 0.5\n",
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, CardinalityRule)
        assert (rule.max_symbols, rule.max_files, rule.min_doc_coverage) == (200, 30, 0.5)

    def test_a_module_coverage_block_keeps_the_symbol_floor_it_declares(
        self, tmp_path: Path
    ) -> None:
        """``min_symbols: 3`` is read AND carried: the default is 1, so 3 must arrive."""
        # Arrange
        path = _rules_file(
            tmp_path,
            "  - name: module-coverage\n"
            '    description: "every module is a node"\n'
            "    module_coverage:\n"
            "      min_symbols: 3\n",
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, ModuleCoverageRule)
        assert rule.min_symbols == 3

    def test_a_forbid_import_block_keeps_its_globs_and_its_exemption(self, tmp_path: Path) -> None:
        # Arrange
        path = _rules_file(
            tmp_path,
            "  - name: tui-no-infra\n"
            '    description: "the tui does not import infrastructure"\n'
            "    forbid_import:\n"
            '      from: "src/app/tui/**"\n'
            '      to: "app/infrastructure/**"\n'
            "      exempt:\n"
            '        - from: "src/app/tui/legacy.py"\n'
            '          reason: "predates the rule"\n'
            '          until: "the legacy screen is deleted"\n',
        )

        # Act
        (rule,) = load_rules(path)

        # Assert
        assert isinstance(rule, ImportBoundaryRule)
        assert (rule.from_glob, rule.to_glob) == ("src/app/tui/**", "app/infrastructure/**")
        assert [e.reason for e in rule.exempt] == ["predates the rule"]


class TestAMalformedBlockIsNamed:
    """The refusal names the rule and the key, because nothing else reaches the adopter."""

    def test_a_check_whose_for_is_not_a_mapping_names_check_for(self, tmp_path: Path) -> None:
        # Arrange
        path = _rules_file(
            tmp_path,
            "  - name: domain-size\n"
            '    description: "domains stay small"\n'
            "    check:\n"
            "      for: domain\n"
            "      max_symbols: 200\n",
        )

        # Act / Assert
        with pytest.raises(
            ValueError, match=_exactly("Rule 'domain-size': check.for must be a mapping")
        ):
            load_rules(path)

    def test_an_exemption_that_is_not_a_mapping_names_its_index(self, tmp_path: Path) -> None:
        # Arrange
        path = _rules_file(
            tmp_path,
            "  - name: tui-no-infra\n"
            '    description: "the tui does not import infrastructure"\n'
            "    forbid_import:\n"
            '      from: "src/app/tui/**"\n'
            '      to: "app/infrastructure/**"\n'
            "      exempt:\n"
            '        - "src/app/tui/legacy.py"\n',
        )

        # Act / Assert
        with pytest.raises(
            ValueError,
            match=_exactly("Rule 'tui-no-infra': forbid_import.exempt[0] must be a mapping"),
        ):
            load_rules(path)
