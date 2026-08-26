# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Backwards-compatible shim for the architecture rule engine.

The rule engine was decomposed by responsibility into the
:mod:`beadloom.graph.rules` package (BDL-059 S3, cohesion-driven). This module
re-exports the full public surface — plus the one private helper that callers/
tests reference by name (``_remediation_for``) — so existing
``from beadloom.graph.rule_engine import X`` imports keep working unchanged.

New code should import from :mod:`beadloom.graph.rules` directly.

Note the deliberate split between ANNOTATION and OWNERSHIP here. The annotation
says this file belongs to the ``rule-engine`` feature — it is that feature's
back-compat public surface, and ``module-coverage`` is right to see it claimed.
The node's ``source`` is the ``rules/`` PACKAGE, because that is where the
engine's code actually lives; sourcing the node at this 84-line shim made every
symbol count, node page and size limit describe the shim instead of the engine
(the BDL-UX #157 shape). So ownership attributes this file's symbols to
``graph`` while the annotation records its feature membership — two different
questions, answered separately and on purpose.
"""

from __future__ import annotations

from beadloom.graph.rules import (
    BEAD_NOT_VERIFIED,
    DEFAULT_DOC_AREA_MIN_SUPPORT,
    DEFAULT_DOC_AREA_THRESHOLD,
    DOC_AREA_RULE_TYPE,
    EXPIRED_EXEMPTION_HINT,
    INERT_RULE_HINT,
    LIVE_EDGE_LIFECYCLES,
    LIVENESS_RULE_TYPE,
    MATCHING_FORM_HINT,
    SCENARIO_COVERAGE_RULE_TYPE,
    SUPPORTED_SCHEMA_VERSIONS,
    VALID_EDGE_KINDS,
    VALID_NODE_KINDS,
    VALID_RULE_SEVERITIES,
    CardinalityRule,
    CycleRule,
    DenyRule,
    DocAreaCoherenceRule,
    FileAttribution,
    ForbidEdgeRule,
    ImportBoundaryRule,
    ImportExemption,
    LayerDef,
    LayerRule,
    ModuleCoverageRule,
    NodeMatcher,
    NonBehaviouralNode,
    RequireRule,
    Rule,
    ScenarioCoverageRule,
    SuppressedCrossing,
    UnregisteredFeatureCandidateRule,
    Violation,
    _remediation_for,
    count_unattributed_import_files,
    evaluate_all,
    evaluate_cardinality_rules,
    evaluate_cycle_rules,
    evaluate_deny_rules,
    evaluate_doc_area_coherence_rules,
    evaluate_forbid_edge_rules,
    evaluate_import_boundary_rules,
    evaluate_layer_rules,
    evaluate_module_coverage_rules,
    evaluate_require_rules,
    evaluate_rule_liveness,
    evaluate_scenario_coverage_rules,
    evaluate_unregistered_feature_candidate_rules,
    exit_condition_deadline,
    inert_rule_names,
    load_rules,
    load_rules_with_tags,
    suppressed_crossings,
    validate_rules,
)

__all__ = [
    "BEAD_NOT_VERIFIED",
    "DEFAULT_DOC_AREA_MIN_SUPPORT",
    "DEFAULT_DOC_AREA_THRESHOLD",
    "DOC_AREA_RULE_TYPE",
    "EXPIRED_EXEMPTION_HINT",
    "INERT_RULE_HINT",
    "LIVENESS_RULE_TYPE",
    "LIVE_EDGE_LIFECYCLES",
    "MATCHING_FORM_HINT",
    "SCENARIO_COVERAGE_RULE_TYPE",
    "SUPPORTED_SCHEMA_VERSIONS",
    "VALID_EDGE_KINDS",
    "VALID_NODE_KINDS",
    "VALID_RULE_SEVERITIES",
    "CardinalityRule",
    "CycleRule",
    "DenyRule",
    "DocAreaCoherenceRule",
    "FileAttribution",
    "ForbidEdgeRule",
    "ImportBoundaryRule",
    "ImportExemption",
    "LayerDef",
    "LayerRule",
    "ModuleCoverageRule",
    "NodeMatcher",
    "NonBehaviouralNode",
    "RequireRule",
    "Rule",
    "ScenarioCoverageRule",
    "SuppressedCrossing",
    "UnregisteredFeatureCandidateRule",
    "Violation",
    "_remediation_for",
    "count_unattributed_import_files",
    "evaluate_all",
    "evaluate_cardinality_rules",
    "evaluate_cycle_rules",
    "evaluate_deny_rules",
    "evaluate_doc_area_coherence_rules",
    "evaluate_forbid_edge_rules",
    "evaluate_import_boundary_rules",
    "evaluate_layer_rules",
    "evaluate_module_coverage_rules",
    "evaluate_require_rules",
    "evaluate_rule_liveness",
    "evaluate_scenario_coverage_rules",
    "evaluate_unregistered_feature_candidate_rules",
    "exit_condition_deadline",
    "inert_rule_names",
    "load_rules",
    "load_rules_with_tags",
    "suppressed_crossings",
    "validate_rules",
]
