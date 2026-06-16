# beadloom:domain=application
# beadloom:feature=reindex
"""Reindex rules loading: serialize parsed architecture rules into the DB.

This module owns one responsibility — translating the typed ``Rule`` objects
produced by :mod:`beadloom.graph.rules` into the JSON rows of the ``rules``
table. It serializes each rule type (and its ``NodeMatcher`` operands) to a
JSON-safe dict and inserts them, recording the count on the result.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.application.reindex.models import ReindexResult


def _serialize_node_matcher(matcher: object) -> dict[str, object]:
    """Serialize a NodeMatcher to a JSON-safe dict (non-None fields only)."""
    from beadloom.graph.rule_engine import NodeMatcher

    assert isinstance(matcher, NodeMatcher)
    result: dict[str, object] = {}
    if matcher.ref_id is not None:
        result["ref_id"] = matcher.ref_id
    if matcher.kind is not None:
        result["kind"] = matcher.kind
    if matcher.tag is not None:
        result["tag"] = matcher.tag
    if matcher.exclude is not None:
        result["exclude"] = list(matcher.exclude)
    return result


def _serialize_rule(rule: object) -> tuple[str, dict[str, object]]:
    """Serialize a parsed Rule object to (rule_type, rule_json_dict).

    Supports all v3 rule types: DenyRule, RequireRule, CycleRule,
    ImportBoundaryRule, ForbidEdgeRule, LayerRule, CardinalityRule,
    UnregisteredFeatureCandidateRule, ModuleCoverageRule.
    """
    from beadloom.graph.rule_engine import (
        CardinalityRule,
        CycleRule,
        DenyRule,
        ForbidEdgeRule,
        ImportBoundaryRule,
        LayerRule,
        ModuleCoverageRule,
        RequireRule,
        UnregisteredFeatureCandidateRule,
    )

    rule_def: dict[str, object]

    if isinstance(rule, DenyRule):
        rule_def = {
            "from": _serialize_node_matcher(rule.from_matcher),
            "to": _serialize_node_matcher(rule.to_matcher),
        }
        if rule.unless_edge:
            rule_def["unless_edge"] = list(rule.unless_edge)
        return ("deny", rule_def)

    if isinstance(rule, RequireRule):
        rule_def = {
            "for": _serialize_node_matcher(rule.for_matcher),
            "has_edge_to": _serialize_node_matcher(rule.has_edge_to),
        }
        if rule.edge_kind is not None:
            rule_def["edge_kind"] = rule.edge_kind
        return ("require", rule_def)

    if isinstance(rule, CycleRule):
        edge_kind: str | list[str] = (
            list(rule.edge_kind) if isinstance(rule.edge_kind, tuple) else rule.edge_kind
        )
        rule_def = {
            "edge_kind": edge_kind,
            "max_depth": rule.max_depth,
        }
        return ("forbid_cycles", rule_def)

    if isinstance(rule, LayerRule):
        rule_def = {
            "layers": [{"name": ld.name, "tag": ld.tag} for ld in rule.layers],
            "enforce": rule.enforce,
            "allow_skip": rule.allow_skip,
            "edge_kind": rule.edge_kind,
        }
        return ("layers", rule_def)

    if isinstance(rule, CardinalityRule):
        rule_def = {
            "for": _serialize_node_matcher(rule.for_matcher),
        }
        if rule.max_symbols is not None:
            rule_def["max_symbols"] = rule.max_symbols
        if rule.max_files is not None:
            rule_def["max_files"] = rule.max_files
        if rule.min_doc_coverage is not None:
            rule_def["min_doc_coverage"] = rule.min_doc_coverage
        return ("cardinality", rule_def)

    if isinstance(rule, ImportBoundaryRule):
        rule_def = {
            "from_glob": rule.from_glob,
            "to_glob": rule.to_glob,
        }
        return ("forbid_import", rule_def)

    if isinstance(rule, ForbidEdgeRule):
        rule_def = {
            "from": _serialize_node_matcher(rule.from_matcher),
            "to": _serialize_node_matcher(rule.to_matcher),
        }
        if rule.edge_kind is not None:
            rule_def["edge_kind"] = rule.edge_kind
        return ("forbid_edge", rule_def)

    if isinstance(rule, UnregisteredFeatureCandidateRule):
        rule_def = {
            "for": _serialize_node_matcher(rule.for_matcher),
            "min_symbols": rule.min_symbols,
        }
        if rule.exclude:
            rule_def["exclude"] = list(rule.exclude)
        return ("unregistered_feature_candidate", rule_def)

    if isinstance(rule, ModuleCoverageRule):
        rule_def = {
            "source_root": rule.source_root,
            "min_symbols": rule.min_symbols,
        }
        if rule.exempt:
            rule_def["exempt"] = list(rule.exempt)
        return ("module_coverage", rule_def)

    # Should never happen with known Rule types, but guard against future additions.
    msg = f"Unknown rule type: {type(rule).__name__}"
    raise TypeError(msg)


def _load_rules_into_db(
    rules_path: Path,
    conn: sqlite3.Connection,
    result: ReindexResult,
) -> None:
    """Load architecture rules from rules.yml into the rules table."""
    from beadloom.graph.rule_engine import load_rules

    try:
        rules = load_rules(rules_path)
    except ValueError as exc:
        result.errors.append(f"Rules loading error: {exc}")
        return

    for rule in rules:
        rule_type, rule_def = _serialize_rule(rule)

        conn.execute(
            "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
            "VALUES (?, ?, ?, ?, 1)",
            (rule.name, rule.description, rule_type, json.dumps(rule_def)),
        )
        result.rules_loaded += 1

    conn.commit()
