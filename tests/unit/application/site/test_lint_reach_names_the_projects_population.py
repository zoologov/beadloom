"""The portal states the population lint ran over (BDL-080 S4a, `beadloom-5pxv`).

A card that says `Rule findings: none` reads the same whether lint found nothing
on the node or never ran (BDL-UX #305). The data file therefore carries lint's
totals for the whole project — errors, warnings and how many nodes carry a
finding — and the findings bound to no node, which no card could show before.
"""

from __future__ import annotations

from dataclasses import dataclass

from beadloom.application.site.lint_reach import LintReach, NodelessFinding, lint_reach_of
from beadloom.graph.linter import LintResult


@dataclass(frozen=True)
class _Violation:
    """The fields of a lint violation the projection reads, and no others.

    A stand-in rather than the rule engine's own type: importing that type puts
    this file in the mutation pool of the rule engine, which it does not test.
    """

    rule_name: str
    severity: str
    from_ref_id: str | None
    message: str
    file_path: str | None = None
    line_number: int | None = None


def _violation(
    rule: str,
    severity: str,
    node: str | None,
    message: str,
    *,
    file_path: str | None = None,
    line: int | None = None,
) -> _Violation:
    return _Violation(rule, severity, node, message, file_path, line)


def _result(*violations: _Violation) -> LintResult:
    return LintResult(violations=list(violations))  # type: ignore[arg-type]  # a stand-in


def test_the_totals_are_lints_own_counts_over_every_finding() -> None:
    reach = lint_reach_of(
        _result(
            _violation("tier-order", "error", "core", "core reaches up"),
            _violation("tier-order", "warn", "store", "store reaches up"),
            _violation("docs", "warn", "store", "store has no doc"),
            _violation("inert", "warn", None, "inert cannot fire"),
        )
    )

    assert (reach.errors, reach.warnings) == (1, 3)
    assert reach.nodes_with_findings == 2


def test_a_finding_bound_to_no_node_is_kept_with_where_it_points() -> None:
    reach = lint_reach_of(
        _result(
            _violation("scenarios", "warn", None, "no scenario", file_path="PRD.md", line=12),
            _violation("inert", "warn", None, "inert cannot fire"),
            _violation("tier-order", "warn", "store", "store reaches up"),
        )
    )

    assert reach.nodeless == (
        NodelessFinding(
            rule="inert", severity="warn", message="inert cannot fire", file="", line=None
        ),
        NodelessFinding(
            rule="scenarios", severity="warn", message="no scenario", file="PRD.md", line=12
        ),
    )


def test_the_data_file_shape_names_every_key() -> None:
    reach = lint_reach_of(
        _result(
            _violation("tier-order", "warn", "store", "store reaches up"),
            _violation("inert", "warn", None, "inert cannot fire"),
        )
    )

    assert reach.as_dict() == {
        "errors": 0,
        "warnings": 2,
        "nodes_with_findings": 1,
        "nodeless": [
            {
                "rule": "inert",
                "severity": "warn",
                "message": "inert cannot fire",
                "file": "",
                "line": None,
            }
        ],
    }


def test_a_clean_run_is_zeros_not_an_absence() -> None:
    assert lint_reach_of(_result()) == LintReach(
        errors=0, warnings=0, nodes_with_findings=0, nodeless=()
    )
