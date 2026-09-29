"""The remediation derived from a finding's rule kind names what that finding names.

``_remediation_for`` fills the ``remediation`` of every finding whose evaluator wrote
none. The hint is only actionable when it names the file or the edge the finding is
about, and it must say so plainly when the finding carries no node to name.
"""

from __future__ import annotations

import pytest

from beadloom.graph.rules import (
    DOC_AREA_RULE_TYPE,
    SCENARIO_COVERAGE_RULE_TYPE,
    Violation,
    _remediation_for,
)


def _violation(rule_type: str, **kwargs: object) -> Violation:
    fields: dict[str, object] = {
        "rule_name": "r",
        "rule_description": "d",
        "rule_type": rule_type,
        "severity": "error",
        "file_path": None,
        "line_number": None,
        "from_ref_id": None,
        "to_ref_id": None,
        "message": "m",
    }
    fields.update(kwargs)
    return Violation(**fields)  # type: ignore[arg-type]  # fields typed by the test


def test_an_edge_hint_with_no_node_on_either_end_names_both_placeholders() -> None:
    hint = _remediation_for("forbid", _violation("forbid"))

    assert hint == "remove the edge `<source> -> <target>`, or route it via an allowed node"


@pytest.mark.parametrize(
    ("rule_type", "opening"),
    [
        pytest.param("unregistered_feature_candidate", "model `src/app/orphan.py` as a feature"),
        pytest.param("module_coverage", "classify `src/app/orphan.py`: model it as a feature"),
    ],
)
def test_a_module_hint_names_the_file_rather_than_the_node(rule_type: str, opening: str) -> None:
    violation = _violation(rule_type, file_path="src/app/orphan.py", from_ref_id="app")

    hint = _remediation_for(rule_type, violation)

    assert hint is not None
    assert hint.startswith(opening)


@pytest.mark.parametrize("rule_type", [DOC_AREA_RULE_TYPE, SCENARIO_COVERAGE_RULE_TYPE])
def test_a_kind_whose_evaluator_writes_its_own_remedy_gets_no_derived_hint(
    rule_type: str,
) -> None:
    hint = _remediation_for(rule_type, _violation(rule_type, file_path="docs/a.md"))

    assert hint is None
