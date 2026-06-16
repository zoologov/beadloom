# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Backwards-compatible shim for the architecture rule engine.

The rule engine was decomposed by responsibility into the
:mod:`beadloom.graph.rules` package (BDL-059 S3, cohesion-driven). This module
re-exports the full public surface — plus the one private helper that callers/
tests reference by name (``_remediation_for``) — so existing
``from beadloom.graph.rule_engine import X`` imports keep working unchanged.

New code should import from :mod:`beadloom.graph.rules` directly.
"""

from __future__ import annotations

from beadloom.graph.rules import (
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
    _remediation_for,
    evaluate_all,
    evaluate_cardinality_rules,
    evaluate_cycle_rules,
    evaluate_deny_rules,
    evaluate_forbid_edge_rules,
    evaluate_import_boundary_rules,
    evaluate_layer_rules,
    evaluate_module_coverage_rules,
    evaluate_require_rules,
    evaluate_unregistered_feature_candidate_rules,
    load_rules,
    load_rules_with_tags,
    validate_rules,
)

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
    "_remediation_for",
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
