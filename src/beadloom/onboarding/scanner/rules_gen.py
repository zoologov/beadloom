"""Generate rules.yml from a discovered graph + read rule metadata."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.graph.rules.loader import AUTHORING_KEYS
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


#: The authoring keys whose label in the agent instructions is not the key
#: itself, kept for the names the generated `.beadloom/AGENTS.md` has always
#: printed: ``check`` reads as ``cardinality`` and ``forbid`` as ``forbid_edge``.
_LABEL_FOR_KEY: dict[str, str] = {"check": "cardinality", "forbid": "forbid_edge"}


def _detect_rule_type(rule: dict[str, object]) -> str:
    """Label a rules.yml rule entry by the authoring key that selects its type.

    WHICH keys select a type is read from `graph.rules.loader.AUTHORING_KEYS`, the
    keys of the loader's own dispatch table, rather than from a twelve-key copy
    here: a copy fell behind the loader once, and the rules it did not know read
    "unknown" in the generated `.beadloom/AGENTS.md` (BDL-062 `.4`). What the
    label SAYS stays here, in `_LABEL_FOR_KEY`, because the loader has no display
    names to share — its table maps a key to a parser, and the evaluators' own
    ``rule_type`` strings (``cycle``, ``layer``) are a third vocabulary that the
    agent instructions have never used.

    The rule's own keys are walked in the order its author wrote them, so a rule
    naming two kinds — which the loader rejects — is labelled by the first.
    """
    for key in rule:
        if key in AUTHORING_KEYS:
            return _LABEL_FOR_KEY.get(key, key)
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
