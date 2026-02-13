"""Tests for agent-aware constraints in context_builder."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.builder import build_context
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def db_with_constraints(tmp_path: Path) -> sqlite3.Connection:
    """Create a DB with nodes, edges, and rules for constraint tests."""
    db_path = tmp_path / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True)
    conn = open_db(db_path)
    create_schema(conn)

    # Insert nodes
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("billing", "domain", "Billing domain"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("auth", "domain", "Auth domain"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("payments", "service", "Payments service"),
    )

    # Insert edges (payments -> billing via part_of)
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("payments", "billing", "part_of"),
    )

    # Insert a deny rule relevant to billing
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            "billing-no-auth",
            "Billing must not import auth",
            "deny",
            json.dumps({"from": {"ref_id": "billing"}, "to": {"ref_id": "auth"}}),
            1,
        ),
    )

    # Insert an unrelated deny rule (shipping/inventory not in subgraph)
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            "unrelated-rule",
            "Unrelated rule",
            "deny",
            json.dumps({"from": {"ref_id": "shipping"}, "to": {"ref_id": "inventory"}}),
            1,
        ),
    )

    # Insert a require rule relevant to payments (kind=service)
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            "services-need-domain",
            "Services must be part of a domain",
            "require",
            json.dumps({"for": {"kind": "service"}, "has_edge_to": {"kind": "domain"}}),
            1,
        ),
    )

    # Insert a disabled rule (should NOT appear in constraints)
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            "disabled-rule",
            "This is disabled",
            "deny",
            json.dumps({"from": {"ref_id": "billing"}, "to": {"ref_id": "auth"}}),
            0,
        ),
    )

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def db_no_rules(tmp_path: Path) -> sqlite3.Connection:
    """Create a DB with nodes but no rules."""
    db_path = tmp_path / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True)
    conn = open_db(db_path)
    create_schema(conn)

    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("billing", "domain", "Billing domain"),
    )
    conn.commit()
    yield conn
    conn.close()


class TestContextBundleConstraints:
    """Tests for constraints field in the context bundle."""

    def test_bundle_includes_constraints_field(
        self, db_with_constraints: sqlite3.Connection
    ) -> None:
        """Context bundle must include a 'constraints' key."""
        bundle = build_context(db_with_constraints, ["billing"])
        assert "constraints" in bundle

    def test_bundle_version_is_2(self, db_with_constraints: sqlite3.Connection) -> None:
        """Context bundle version should be 2 now that constraints are included."""
        bundle = build_context(db_with_constraints, ["billing"])
        assert bundle["version"] == 2

    def test_deny_rule_relevant_to_focus_included(
        self, db_with_constraints: sqlite3.Connection
    ) -> None:
        """A deny rule whose 'from' matches the focus node should be included."""
        bundle = build_context(db_with_constraints, ["billing"])
        names = [c["rule"] for c in bundle["constraints"]]
        assert "billing-no-auth" in names

    def test_require_rule_relevant_to_subgraph_included(
        self, db_with_constraints: sqlite3.Connection
    ) -> None:
        """A require rule whose 'for' matches a subgraph node should be included."""
        bundle = build_context(db_with_constraints, ["billing"])
        # 'payments' is in the subgraph via part_of edge from payments->billing
        names = [c["rule"] for c in bundle["constraints"]]
        assert "services-need-domain" in names

    def test_unrelated_rule_excluded(self, db_with_constraints: sqlite3.Connection) -> None:
        """A rule that doesn't match any subgraph node should NOT be included."""
        bundle = build_context(db_with_constraints, ["billing"])
        names = [c["rule"] for c in bundle["constraints"]]
        assert "unrelated-rule" not in names

    def test_disabled_rule_excluded(self, db_with_constraints: sqlite3.Connection) -> None:
        """A disabled rule should NOT be included even if it matches."""
        bundle = build_context(db_with_constraints, ["billing"])
        names = [c["rule"] for c in bundle["constraints"]]
        assert "disabled-rule" not in names

    def test_no_rules_in_db_empty_constraints(self, db_no_rules: sqlite3.Connection) -> None:
        """When the rules table is empty, constraints should be an empty list."""
        bundle = build_context(db_no_rules, ["billing"])
        assert bundle["constraints"] == []

    def test_constraint_dict_structure(self, db_with_constraints: sqlite3.Connection) -> None:
        """Each constraint dict should have rule, description, type, definition keys."""
        bundle = build_context(db_with_constraints, ["billing"])
        deny_constraints = [c for c in bundle["constraints"] if c["rule"] == "billing-no-auth"]
        assert len(deny_constraints) == 1
        constraint = deny_constraints[0]
        assert constraint["rule"] == "billing-no-auth"
        assert constraint["description"] == "Billing must not import auth"
        assert constraint["type"] == "deny"
        assert constraint["definition"] == {
            "from": {"ref_id": "billing"},
            "to": {"ref_id": "auth"},
        }

    def test_multiple_rules_only_relevant_included(
        self, db_with_constraints: sqlite3.Connection
    ) -> None:
        """With multiple rules, only relevant ones should appear in constraints."""
        bundle = build_context(db_with_constraints, ["billing"])
        names = {c["rule"] for c in bundle["constraints"]}
        # billing-no-auth: relevant (from.ref_id = billing)
        # services-need-domain: relevant (for.kind = service, payments is in subgraph)
        # unrelated-rule: NOT relevant
        # disabled-rule: NOT included (disabled)
        assert "billing-no-auth" in names
        assert "services-need-domain" in names
        assert "unrelated-rule" not in names
        assert "disabled-rule" not in names
        assert len(names) == 2

    def test_deny_rule_matches_via_to_matcher(
        self, db_with_constraints: sqlite3.Connection
    ) -> None:
        """A deny rule should be included if only the 'to' matcher matches a subgraph node."""
        # auth is in the subgraph when we focus on auth directly
        bundle = build_context(db_with_constraints, ["auth"])
        names = [c["rule"] for c in bundle["constraints"]]
        # billing-no-auth has to.ref_id=auth, and auth is in the subgraph
        assert "billing-no-auth" in names
