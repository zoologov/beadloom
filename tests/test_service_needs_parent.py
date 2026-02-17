"""Tests verifying service-needs-parent rule is NOT generated.

The rule was removed because the root service node (created during bootstrap)
has no parent by definition, causing lint to always fail on fresh projects.
The domain-needs-parent and feature-needs-domain rules are sufficient.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from beadloom.onboarding.scanner import generate_rules

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Test: service-needs-parent rule is never generated
# ---------------------------------------------------------------------------


class TestServiceNeedsParentNotGenerated:
    """Verify generate_rules() does NOT produce service-needs-parent."""

    def test_not_generated_with_service_and_domain_nodes(self, tmp_path: Path) -> None:
        """service-needs-parent is NOT generated even when service nodes exist."""
        nodes = [
            {"ref_id": "api-svc", "kind": "service", "summary": "API service"},
            {"ref_id": "core", "kind": "domain", "summary": "Core domain"},
        ]
        edges = [
            {"src": "api-svc", "dst": "core", "kind": "part_of"},
        ]
        rules_path = tmp_path / "rules.yml"

        count = generate_rules(nodes, edges, "test-project", rules_path)

        assert count == 1  # only domain-needs-parent
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rule_names = [r["name"] for r in data["rules"]]
        assert "service-needs-parent" not in rule_names
        assert "domain-needs-parent" in rule_names

    def test_not_generated_with_service_only(self, tmp_path: Path) -> None:
        """Service-only graph produces 0 rules (no service-needs-parent)."""
        nodes = [
            {"ref_id": "root-svc", "kind": "service", "summary": "Root service"},
        ]
        edges: list[dict[str, str]] = []
        rules_path = tmp_path / "rules.yml"

        count = generate_rules(nodes, edges, "test-project", rules_path)

        assert count == 0
        assert not rules_path.exists()

    def test_not_generated_with_all_node_kinds(self, tmp_path: Path) -> None:
        """With domain + feature + service nodes, only 2 rules generated."""
        nodes = [
            {"ref_id": "core", "kind": "domain", "summary": "Core domain"},
            {"ref_id": "login", "kind": "feature", "summary": "Login feature"},
            {"ref_id": "api-svc", "kind": "service", "summary": "API service"},
        ]
        edges: list[dict[str, str]] = []
        rules_path = tmp_path / "rules.yml"

        count = generate_rules(nodes, edges, "test-project", rules_path)

        assert count == 2
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rule_names = [r["name"] for r in data["rules"]]
        assert "domain-needs-parent" in rule_names
        assert "feature-needs-domain" in rule_names
        assert "service-needs-parent" not in rule_names

    def test_domain_and_feature_rules_still_generated(self, tmp_path: Path) -> None:
        """domain-needs-parent and feature-needs-domain remain intact."""
        nodes = [
            {"ref_id": "myproj", "kind": "service", "summary": "Root"},
            {"ref_id": "auth", "kind": "domain", "summary": "Auth domain"},
            {"ref_id": "login", "kind": "feature", "summary": "Login feature"},
        ]
        edges = [
            {"src": "auth", "dst": "myproj", "kind": "part_of"},
            {"src": "login", "dst": "auth", "kind": "part_of"},
        ]
        rules_path = tmp_path / "rules.yml"

        count = generate_rules(nodes, edges, "myproj", rules_path)

        assert count == 2
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))

        domain_rule = next(r for r in data["rules"] if r["name"] == "domain-needs-parent")
        assert domain_rule["require"]["for"] == {"kind": "domain"}
        assert domain_rule["require"]["has_edge_to"] == {}
        assert domain_rule["require"]["edge_kind"] == "part_of"

        feature_rule = next(r for r in data["rules"] if r["name"] == "feature-needs-domain")
        assert feature_rule["require"]["for"] == {"kind": "feature"}
        assert feature_rule["require"]["has_edge_to"] == {"kind": "domain"}
        assert feature_rule["require"]["edge_kind"] == "part_of"
