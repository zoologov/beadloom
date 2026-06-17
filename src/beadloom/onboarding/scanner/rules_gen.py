"""Generate rules.yml from a discovered graph + read rule metadata."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.infrastructure.atomic_io import write_yaml_atomic

if TYPE_CHECKING:
    from pathlib import Path


def generate_rules(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    project_name: str,
    rules_path: Path,
) -> int:
    """Generate ``rules.yml`` from discovered graph structure.

    Only creates structural *require* rules — no *deny* rules by default.
    Returns the number of rules written.
    """
    kinds = {n["kind"] for n in nodes}
    rules: list[dict[str, Any]] = []

    # Rule 1: every domain must have a part_of edge (to any node).
    # Using an empty matcher so sub-domains pointing at a parent domain
    # (rather than the root) are not flagged as violations.
    if "domain" in kinds:
        rules.append(
            {
                "name": "domain-needs-parent",
                "description": "Every domain must have a part_of edge",
                "require": {
                    "for": {"kind": "domain"},
                    "has_edge_to": {},
                    "edge_kind": "part_of",
                },
            }
        )

    # Rule 2: every feature must have a part_of edge (to any node).
    # Using an empty matcher so features placed under a service parent
    # (e.g. `core-rest` part_of the `core` service) are not flagged as
    # violations.  The bootstrap classifier legitimately nests feature
    # dirs (api/rest/graphql) inside service dirs (core/tasks/workers);
    # requiring a `domain` parent makes a clean bootstrap fail its own
    # `lint --strict` gate out of the box (BDL-UX-Issues #71).
    if "feature" in kinds:
        rules.append(
            {
                "name": "feature-needs-parent",
                "description": "Every feature must have a part_of edge",
                "require": {
                    "for": {"kind": "feature"},
                    "has_edge_to": {},
                    "edge_kind": "part_of",
                },
            }
        )

    # Note: service-needs-parent rule was intentionally removed.
    # The root service node has no parent by definition, so the rule
    # always fails on freshly bootstrapped projects. The domain-needs-parent
    # and feature-needs-parent rules are sufficient for structural enforcement.

    if not rules:
        return 0

    data: dict[str, Any] = {"version": 1, "rules": rules}
    write_yaml_atomic(rules_path, data, default_flow_style=False, allow_unicode=True)
    return len(rules)


def _detect_rule_type(rule: dict[str, object]) -> str:
    """Detect the rule type from a rules.yml rule entry.

    Maps YAML keys to canonical type strings used in DB and display:
    - ``require`` -> ``"require"``
    - ``deny`` -> ``"deny"``
    - ``forbid_cycles`` -> ``"forbid_cycles"``
    - ``layers`` -> ``"layers"``
    - ``check`` -> ``"cardinality"``
    - ``forbid_import`` -> ``"forbid_import"``
    - ``forbid`` -> ``"forbid_edge"``
    """
    yaml_key_to_type: dict[str, str] = {
        "require": "require",
        "deny": "deny",
        "forbid_cycles": "forbid_cycles",
        "layers": "layers",
        "check": "cardinality",
        "forbid_import": "forbid_import",
        "forbid": "forbid_edge",
    }
    for key, rule_type in yaml_key_to_type.items():
        if key in rule:
            return rule_type
    return "unknown"


def _read_rules_data(project_root: Path) -> list[dict[str, str]]:
    """Read architecture rules from rules.yml as structured data."""
    rules_path = project_root / ".beadloom" / "_graph" / "rules.yml"
    if not rules_path.exists():
        return []
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    if not data or not data.get("rules"):
        return []
    result: list[dict[str, str]] = []
    for rule in data["rules"]:
        rule_type = _detect_rule_type(rule)
        result.append(
            {
                "name": rule.get("name", "unnamed"),
                "type": rule_type,
                "description": rule.get("description", ""),
            }
        )
    return result
