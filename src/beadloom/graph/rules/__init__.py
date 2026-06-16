# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Architecture rule engine: parse rules.yml, validate, and evaluate against the graph DB.

This package decomposes the former ``graph/rule_engine.py`` monolith by
responsibility (BDL-059 S3, cohesion-driven):

- :mod:`.types` — constants, rule dataclasses, ``NodeMatcher``, ``Violation`` (the model).
- :mod:`.loader` — ``load_rules`` / ``load_rules_with_tags`` / ``validate_rules``
  (YAML -> typed rules + DB validation).
- :mod:`.evaluators` — per-rule-type evaluation
  (deny/require/import/forbid/layer/cardinality/coverage).
- :mod:`.cycles` — colored (WHITE/GREY/BLACK) cycle detection + edge-liveness SQL helpers.

This ``__init__`` owns the :func:`evaluate_all` orchestration (dispatch by rule
kind + remediation post-pass + deterministic sort) and re-exports the public
surface so ``from beadloom.graph.rules import X`` is stable.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from beadloom.graph.rules.cycles import evaluate_cycle_rules
from beadloom.graph.rules.evaluators import (
    evaluate_cardinality_rules,
    evaluate_deny_rules,
    evaluate_forbid_edge_rules,
    evaluate_import_boundary_rules,
    evaluate_layer_rules,
    evaluate_module_coverage_rules,
    evaluate_require_rules,
    evaluate_unregistered_feature_candidate_rules,
)
from beadloom.graph.rules.loader import (
    load_rules,
    load_rules_with_tags,
    validate_rules,
)
from beadloom.graph.rules.types import (
    LIVE_EDGE_LIFECYCLES,
    SUPPORTED_SCHEMA_VERSIONS,
    VALID_EDGE_KINDS,
    VALID_NODE_KINDS,
    VALID_RULE_SEVERITIES,
    CardinalityRule,
    CycleRule,
    DenyRule,
    ForbidEdgeRule,
    ImportBoundaryRule,
    LayerDef,
    LayerRule,
    ModuleCoverageRule,
    NodeMatcher,
    RequireRule,
    Rule,
    UnregisteredFeatureCandidateRule,
    Violation,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _remediation_for(rule_type: str, violation: Violation) -> str | None:
    """Derive a templated, agent-actionable "how to fix" hint (BDL-039 F3 G2).

    Returns ``None`` when no specific hint applies for *rule_type* (so the
    field stays absent rather than carrying a vague placeholder). The hint
    names the concrete edge/node so an agent can act without re-reading the
    message prose.
    """
    src = violation.from_ref_id or "<source>"
    dst = violation.to_ref_id or "<target>"
    if rule_type in {"deny", "forbid_import"}:
        loc = violation.file_path or src
        return (
            f"remove the import `{src} -> {dst}` in `{loc}`, "
            f"or route it through an allowed intermediary"
        )
    if rule_type == "forbid":
        return f"remove the edge `{src} -> {dst}`, or route it via an allowed node"
    if rule_type == "cycle":
        return f"break the cycle by removing the edge `{src} -> {dst}`"
    if rule_type == "layer":
        return (
            f"`{src}` must not depend on upper-layer `{dst}`; "
            f"invert the dependency or extract a shared abstraction"
        )
    if rule_type == "cardinality":
        return f"`{src}` exceeds its limit ({violation.message}); split it into smaller nodes"
    if rule_type == "require":
        return f"add the required edge from `{src}` to a matching target node"
    if rule_type == "unregistered_feature_candidate":
        loc = violation.file_path or src
        return (
            f"model `{loc}` as a feature (add a node + `# beadloom:feature=` "
            f"annotation + SPEC.md), or accept it as domain-level plumbing "
            f"(list it in the domain README and add it to the rule's `exclude`)"
        )
    if rule_type == "module_coverage":
        loc = violation.file_path or src
        return (
            f"classify `{loc}`: model it as a feature or component (add a node + "
            f"`# beadloom:feature=`/`# beadloom:component=` annotation + a doc), "
            f"or add its path to the rule's `exempt` list if it is trivial glue"
        )
    return None


def _with_remediation(violation: Violation) -> Violation:
    """Return a copy of *violation* with its derived ``remediation`` populated."""
    return replace(violation, remediation=_remediation_for(violation.rule_type, violation))


def evaluate_all(
    conn: sqlite3.Connection,
    rules: list[Rule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Evaluate all rules and return sorted violations.

    Supports deny, require, cycle, import boundary, forbid edge, layer,
    and cardinality rules. Each violation is enriched with an agent-actionable
    ``remediation`` hint (BDL-039 F3 BEAD-02) as a deterministic post-pass.

    *project_root* (default: cwd) roots the on-disk module enumeration the
    ``module-coverage`` rule uses to close the zero-symbol false-negative.
    """
    deny_rules: list[DenyRule] = []
    require_rules: list[RequireRule] = []
    cycle_rules: list[CycleRule] = []
    import_boundary_rules: list[ImportBoundaryRule] = []
    forbid_edge_rules: list[ForbidEdgeRule] = []
    layer_rules: list[LayerRule] = []
    cardinality_rules: list[CardinalityRule] = []
    unregistered_rules: list[UnregisteredFeatureCandidateRule] = []
    module_coverage_rules: list[ModuleCoverageRule] = []

    for rule in rules:
        if isinstance(rule, DenyRule):
            deny_rules.append(rule)
        elif isinstance(rule, RequireRule):
            require_rules.append(rule)
        elif isinstance(rule, CycleRule):
            cycle_rules.append(rule)
        elif isinstance(rule, ImportBoundaryRule):
            import_boundary_rules.append(rule)
        elif isinstance(rule, ForbidEdgeRule):
            forbid_edge_rules.append(rule)
        elif isinstance(rule, LayerRule):
            layer_rules.append(rule)
        elif isinstance(rule, CardinalityRule):
            cardinality_rules.append(rule)
        elif isinstance(rule, UnregisteredFeatureCandidateRule):
            unregistered_rules.append(rule)
        elif isinstance(rule, ModuleCoverageRule):
            module_coverage_rules.append(rule)

    violations = (
        evaluate_deny_rules(conn, deny_rules)
        + evaluate_require_rules(conn, require_rules)
        + evaluate_cycle_rules(conn, cycle_rules)
        + evaluate_import_boundary_rules(conn, import_boundary_rules)
        + evaluate_forbid_edge_rules(conn, forbid_edge_rules)
        + evaluate_layer_rules(conn, layer_rules)
        + evaluate_cardinality_rules(conn, cardinality_rules)
        + evaluate_unregistered_feature_candidate_rules(conn, unregistered_rules)
        + evaluate_module_coverage_rules(conn, module_coverage_rules, project_root=project_root)
    )

    # Enrich each violation with an agent-actionable remediation hint.
    violations = [_with_remediation(v) for v in violations]

    # Sort by rule_name, then file_path (None sorts first)
    violations.sort(key=lambda v: (v.rule_name, v.file_path or ""))

    return violations


__all__ = [
    "LIVE_EDGE_LIFECYCLES",
    "SUPPORTED_SCHEMA_VERSIONS",
    "VALID_EDGE_KINDS",
    "VALID_NODE_KINDS",
    "VALID_RULE_SEVERITIES",
    "CardinalityRule",
    "CycleRule",
    "DenyRule",
    "ForbidEdgeRule",
    "ImportBoundaryRule",
    "LayerDef",
    "LayerRule",
    "ModuleCoverageRule",
    "NodeMatcher",
    "RequireRule",
    "Rule",
    "UnregisteredFeatureCandidateRule",
    "Violation",
    "evaluate_all",
    "evaluate_cardinality_rules",
    "evaluate_cycle_rules",
    "evaluate_deny_rules",
    "evaluate_forbid_edge_rules",
    "evaluate_import_boundary_rules",
    "evaluate_layer_rules",
    "evaluate_module_coverage_rules",
    "evaluate_require_rules",
    "evaluate_unregistered_feature_candidate_rules",
    "load_rules",
    "load_rules_with_tags",
    "validate_rules",
]
