"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/integration/infrastructure/exit_condition/test_exit_condition_expiry.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from datetime import date

from beadloom.graph.rule_engine import (
    ImportBoundaryRule,
    exit_condition_deadline,
    load_rules,
)
from tests.support.repository_root import REPO_ROOT


class TestBeadloomsOwnExemptions:
    """The suite reddens the day one of this project's own baselines outlives its date."""

    def test_no_shipped_exemption_has_expired(self) -> None:
        root = REPO_ROOT
        rules = load_rules(root / ".beadloom" / "_graph" / "rules.yml")

        expired = [
            (rule.name, exemption.until)
            for rule in rules
            if isinstance(rule, ImportBoundaryRule)
            for exemption in rule.exempt
            if (deadline := exit_condition_deadline(exemption.until)) is not None
            and deadline < date.today()
        ]

        assert expired == [], f"exit conditions that have passed: {expired}"
