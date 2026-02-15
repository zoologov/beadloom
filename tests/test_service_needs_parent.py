"""Tests for the service-needs-parent rule: generation and lint evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.graph.rule_engine import (
    NodeMatcher,
    RequireRule,
    evaluate_require_rules,
    load_rules,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.onboarding.scanner import generate_rules

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    """Provide an empty database with full schema."""
    db_path = tmp_path / "test.db"
    conn = open_db(db_path)
    create_schema(conn)
    yield conn  # type: ignore[misc]
    conn.close()


# ---------------------------------------------------------------------------
# Test: rule generation — service nodes present
# ---------------------------------------------------------------------------


class TestGenerateRulesServiceNeedsParent:
    """Tests for generate_rules() producing the service-needs-parent rule."""

    def test_rule_generated_when_service_nodes_exist(self, tmp_path: Path) -> None:
        """service-needs-parent rule is generated when service nodes are present."""
        nodes = [
            {"ref_id": "api-svc", "kind": "service", "summary": "API service"},
            {"ref_id": "core", "kind": "domain", "summary": "Core domain"},
        ]
        edges = [
            {"src": "api-svc", "dst": "core", "kind": "part_of"},
        ]
        rules_path = tmp_path / "rules.yml"

        count = generate_rules(nodes, edges, "test-project", rules_path)

        assert count >= 1
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rule_names = [r["name"] for r in data["rules"]]
        assert "service-needs-parent" in rule_names

        # Verify the rule structure
        svc_rule = next(r for r in data["rules"] if r["name"] == "service-needs-parent")
        assert svc_rule["description"] == "Every service must have a part_of edge to a parent"
        assert svc_rule["require"]["for"] == {"kind": "service"}
        assert svc_rule["require"]["has_edge_to"] == {}
        assert svc_rule["require"]["edge_kind"] == "part_of"

    def test_rule_not_generated_when_no_service_nodes(self, tmp_path: Path) -> None:
        """service-needs-parent rule is NOT generated when no service nodes exist."""
        nodes = [
            {"ref_id": "core", "kind": "domain", "summary": "Core domain"},
            {"ref_id": "login", "kind": "feature", "summary": "Login feature"},
        ]
        edges: list[dict[str, str]] = []
        rules_path = tmp_path / "rules.yml"

        count = generate_rules(nodes, edges, "test-project", rules_path)

        assert count >= 1
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rule_names = [r["name"] for r in data["rules"]]
        assert "service-needs-parent" not in rule_names

    def test_rule_coexists_with_domain_and_feature_rules(self, tmp_path: Path) -> None:
        """All three rules generated when domains, features, and services exist."""
        nodes = [
            {"ref_id": "core", "kind": "domain", "summary": "Core domain"},
            {"ref_id": "login", "kind": "feature", "summary": "Login feature"},
            {"ref_id": "api-svc", "kind": "service", "summary": "API service"},
        ]
        edges: list[dict[str, str]] = []
        rules_path = tmp_path / "rules.yml"

        count = generate_rules(nodes, edges, "test-project", rules_path)

        assert count == 3
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rule_names = [r["name"] for r in data["rules"]]
        assert "domain-needs-parent" in rule_names
        assert "feature-needs-domain" in rule_names
        assert "service-needs-parent" in rule_names

    def test_generated_rule_parses_correctly(self, tmp_path: Path) -> None:
        """Generated rules.yml is parseable by the rule engine."""
        nodes = [
            {"ref_id": "api-svc", "kind": "service", "summary": "API service"},
        ]
        edges: list[dict[str, str]] = []
        rules_path = tmp_path / "rules.yml"

        generate_rules(nodes, edges, "test-project", rules_path)

        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.name == "service-needs-parent"
        assert rule.for_matcher == NodeMatcher(kind="service")
        assert rule.has_edge_to == NodeMatcher()  # empty = any node
        assert rule.edge_kind == "part_of"


# ---------------------------------------------------------------------------
# Test: lint evaluation — service with and without part_of edge
# ---------------------------------------------------------------------------


class TestServiceNeedsParentEvaluation:
    """Tests for lint evaluation of the service-needs-parent rule."""

    def test_lint_passes_when_service_has_part_of_edge(self, db_conn: sqlite3.Connection) -> None:
        """No violation when service has a part_of edge to any parent."""
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("api-svc", "service", "API service"),
        )
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("core", "domain", "Core domain"),
        )
        db_conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("api-svc", "core", "part_of"),
        )
        db_conn.commit()

        rules = [
            RequireRule(
                name="service-needs-parent",
                description="Every service must have a part_of edge to a parent",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_conn, rules)
        assert len(violations) == 0

    def test_lint_fails_when_service_missing_part_of_edge(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """Violation when service has no part_of edge."""
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("orphan-svc", "service", "Orphan service"),
        )
        db_conn.commit()

        rules = [
            RequireRule(
                name="service-needs-parent",
                description="Every service must have a part_of edge to a parent",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_conn, rules)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_name == "service-needs-parent"
        assert v.rule_type == "require"
        assert v.from_ref_id == "orphan-svc"

    def test_multiple_services_mixed_compliance(self, db_conn: sqlite3.Connection) -> None:
        """Only services without part_of edges produce violations."""
        # Service with parent
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("api-svc", "service", "API service"),
        )
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("root", "domain", "Root"),
        )
        db_conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("api-svc", "root", "part_of"),
        )

        # Service without parent
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("worker-svc", "service", "Worker service"),
        )

        # Another service without parent
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("cron-svc", "service", "Cron service"),
        )

        # Service with wrong edge kind (uses, not part_of)
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("mailer-svc", "service", "Mailer service"),
        )
        db_conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("mailer-svc", "root", "uses"),
        )

        db_conn.commit()

        rules = [
            RequireRule(
                name="service-needs-parent",
                description="Every service must have a part_of edge to a parent",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_conn, rules)

        # api-svc has part_of -> passes
        # worker-svc, cron-svc have no edges -> fail
        # mailer-svc has 'uses' but not 'part_of' -> fail
        assert len(violations) == 3
        violated_refs = {v.from_ref_id for v in violations}
        assert "worker-svc" in violated_refs
        assert "cron-svc" in violated_refs
        assert "mailer-svc" in violated_refs
        assert "api-svc" not in violated_refs

    def test_non_service_nodes_not_affected(self, db_conn: sqlite3.Connection) -> None:
        """Rule only applies to service nodes, not domains or features."""
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("core", "domain", "Core domain"),
        )
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("login", "feature", "Login feature"),
        )
        db_conn.commit()

        rules = [
            RequireRule(
                name="service-needs-parent",
                description="Every service must have a part_of edge to a parent",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_conn, rules)
        assert len(violations) == 0
