"""A suite rule's population statement is a warning that carries its rule, with nothing to fix.

``population_finding`` builds the line a suite rule prints on every run, clean or
not, stating how much it judged. It is never a verdict, so it is always ``warn``,
names no file or node, and its remediation says there is nothing to fix. The
remediation is written by the finding itself: the engine's post-pass keeps a
remediation already present, so this text is the one an adopter reads.
"""

from __future__ import annotations

from beadloom.graph.rules.types import (
    SUITE_POPULATION_RULE_TYPE,
    Violation,
    population_finding,
)


def test_a_population_statement_is_a_warning_carrying_its_rule_and_nothing_to_fix() -> None:
    # Arrange
    rule_name = "test-files-bind-to-a-node"
    rule_description = "every test file binds to a node"
    message = "judged 12 test file(s): 9 bound, 3 excused"

    # Act
    finding = population_finding(
        rule_name=rule_name, rule_description=rule_description, message=message
    )

    # Assert
    assert finding == Violation(
        rule_name=rule_name,
        rule_description=rule_description,
        rule_type=SUITE_POPULATION_RULE_TYPE,
        severity="warn",
        file_path=None,
        line_number=None,
        from_ref_id=None,
        to_ref_id=None,
        message=message,
        remediation=(
            "nothing to fix: this states the rule's reach, so a count of findings "
            "can be read as a fraction of what was judged"
        ),
    )
