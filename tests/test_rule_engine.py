"""Tests for beadloom.rule_engine — Architecture rule parsing, validation, and evaluation."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.loader import get_node_tags
from beadloom.graph.rule_engine import (
    SUPPORTED_SCHEMA_VERSIONS,
    CardinalityRule,
    DenyRule,
    ForbidEdgeRule,
    LayerDef,
    LayerRule,
    NodeMatcher,
    RequireRule,
    Violation,
    evaluate_all,
    evaluate_cardinality_rules,
    evaluate_deny_rules,
    evaluate_forbid_edge_rules,
    evaluate_layer_rules,
    evaluate_require_rules,
    load_rules,
    validate_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rule_engine import UnregisteredFeatureCandidateRule


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


@pytest.fixture()
def db_with_data(tmp_path: Path) -> sqlite3.Connection:
    """Provide a database pre-populated with nodes, edges, imports, and symbols."""
    db_path = tmp_path / "test.db"
    conn = open_db(db_path)
    create_schema(conn)

    # Nodes
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
        ("payments-svc", "service", "Payments service"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("users-svc", "service", "Users service"),
    )

    # Edges
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("payments-svc", "billing", "part_of"),
    )

    # Code imports — billing file importing from auth
    conn.execute(
        "INSERT INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        ("src/billing/invoice.py", 3, "auth.tokens", "auth", "abc123"),
    )

    # Code symbols — annotating billing file
    conn.execute(
        "INSERT INTO code_symbols"
        " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "src/billing/invoice.py",
            "Invoice",
            "class",
            1,
            50,
            json.dumps({"domain": "billing"}),
            "abc123",
        ),
    )

    conn.commit()
    yield conn  # type: ignore[misc]
    conn.close()


# ---------------------------------------------------------------------------
# TestLoadRules — parsing rules.yml
# ---------------------------------------------------------------------------


class TestLoadRules:
    """Tests for load_rules() — YAML parsing and schema validation."""

    def test_parse_deny_rule(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: test-rule\n"
            '    description: "Test deny rule"\n'
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, DenyRule)
        assert rule.name == "test-rule"
        assert rule.description == "Test deny rule"
        assert rule.from_matcher == NodeMatcher(ref_id="billing")
        assert rule.to_matcher == NodeMatcher(ref_id="auth")
        assert rule.unless_edge == ()

    def test_parse_require_rule(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: svc-needs-domain\n"
            '    description: "Service must belong to a domain"\n'
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
            "      edge_kind: part_of\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.name == "svc-needs-domain"
        assert rule.for_matcher == NodeMatcher(kind="service")
        assert rule.has_edge_to == NodeMatcher(kind="domain")
        assert rule.edge_kind == "part_of"

    def test_parse_mixed_rules(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: deny-rule\n"
            '    description: "Deny"\n'
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
            "  - name: require-rule\n"
            '    description: "Require"\n'
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 2
        assert isinstance(rules[0], DenyRule)
        assert isinstance(rules[1], RequireRule)

    def test_parse_rule_with_unless_edge(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: domain-isolation\n"
            '    description: "Cross-domain unless explicit"\n'
            "    deny:\n"
            "      from: { kind: service }\n"
            "      to: { kind: service }\n"
            "      unless_edge: [depends_on, uses]\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, DenyRule)
        assert rule.unless_edge == ("depends_on", "uses")

    def test_parse_rule_with_edge_kind(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: svc-domain\n"
            '    description: "Part of domain"\n'
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
            "      edge_kind: part_of\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.edge_kind == "part_of"

    def test_require_rule_without_edge_kind(self, tmp_path: Path) -> None:
        """edge_kind is optional — defaults to None (match any edge kind)."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: svc-domain\n"
            '    description: "Any edge to domain"\n'
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
        )
        rules = load_rules(rules_path)
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.edge_kind is None


# ---------------------------------------------------------------------------
# TestLoadRulesValidationErrors — schema error handling
# ---------------------------------------------------------------------------


class TestLoadRulesValidationErrors:
    """Tests for schema validation in load_rules()."""

    def test_missing_version(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "rules:\n"
            "  - name: test\n"
            '    description: "x"\n'
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
        )
        with pytest.raises(ValueError, match="version"):
            load_rules(rules_path)

    def test_wrong_version(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 99\n"
            "rules:\n"
            "  - name: test\n"
            '    description: "x"\n'
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
        )
        with pytest.raises(ValueError, match="version"):
            load_rules(rules_path)

    def test_rule_missing_name(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            '  - description: "no name"\n'
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
        )
        with pytest.raises(ValueError, match="name"):
            load_rules(rules_path)

    def test_rule_with_both_deny_and_require(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: both\n"
            '    description: "invalid"\n'
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
        )
        with pytest.raises(ValueError, match="exactly one"):
            load_rules(rules_path)

    def test_rule_with_neither_deny_nor_require(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text('version: 1\nrules:\n  - name: empty\n    description: "no type"\n')
        with pytest.raises(ValueError, match="exactly one"):
            load_rules(rules_path)

    def test_duplicate_rule_names(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: dup\n"
            '    description: "first"\n'
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
            "  - name: dup\n"
            '    description: "second"\n'
            "    deny:\n"
            "      from: { ref_id: c }\n"
            "      to: { ref_id: d }\n"
        )
        with pytest.raises(ValueError, match=r"[Dd]uplicate"):
            load_rules(rules_path)

    def test_node_matcher_with_no_ref_id_or_kind(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: bad-matcher\n"
            '    description: "empty matcher"\n'
            "    deny:\n"
            "      from: {}\n"
            "      to: { ref_id: b }\n"
        )
        with pytest.raises(ValueError, match=r"at least one"):
            load_rules(rules_path)

    def test_invalid_kind_in_matcher(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: bad-kind\n"
            '    description: "invalid kind"\n'
            "    deny:\n"
            "      from: { kind: module }\n"
            "      to: { ref_id: b }\n"
        )
        with pytest.raises(ValueError, match="kind"):
            load_rules(rules_path)

    def test_invalid_edge_kind_in_unless_edge(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: bad-edge\n"
            '    description: "invalid unless"\n'
            "    deny:\n"
            "      from: { kind: service }\n"
            "      to: { kind: service }\n"
            "      unless_edge: [invalid_edge]\n"
        )
        with pytest.raises(ValueError, match="edge"):
            load_rules(rules_path)


# ---------------------------------------------------------------------------
# TestValidateRules — database-aware validation (warnings)
# ---------------------------------------------------------------------------


class TestValidateRules:
    """Tests for validate_rules() — warns about unknown ref_ids."""

    def test_unknown_ref_id_warning(self, db_conn: sqlite3.Connection) -> None:
        rules = [
            DenyRule(
                name="test",
                description="Test",
                from_matcher=NodeMatcher(ref_id="nonexistent"),
                to_matcher=NodeMatcher(ref_id="also-nonexistent"),
                unless_edge=(),
            ),
        ]
        warnings = validate_rules(rules, db_conn)
        assert len(warnings) >= 1
        assert any("nonexistent" in w for w in warnings)

    def test_valid_ref_id_no_warning(self, db_with_data: sqlite3.Connection) -> None:
        rules = [
            DenyRule(
                name="test",
                description="Test",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=(),
            ),
        ]
        warnings = validate_rules(rules, db_with_data)
        assert len(warnings) == 0

    def test_kind_only_matcher_no_warning(self, db_conn: sqlite3.Connection) -> None:
        """Matchers using only 'kind' should not produce ref_id warnings."""
        rules = [
            DenyRule(
                name="test",
                description="Test",
                from_matcher=NodeMatcher(kind="service"),
                to_matcher=NodeMatcher(kind="service"),
                unless_edge=(),
            ),
        ]
        warnings = validate_rules(rules, db_conn)
        assert len(warnings) == 0


# ---------------------------------------------------------------------------
# TestEvaluateDenyRules — deny rule evaluation
# ---------------------------------------------------------------------------


class TestEvaluateDenyRules:
    """Tests for evaluate_deny_rules() — boundary enforcement."""

    def test_violation_detected(self, db_with_data: sqlite3.Connection) -> None:
        """Import from billing->auth without exemption triggers violation."""
        rules = [
            DenyRule(
                name="billing-auth-boundary",
                description="Billing must not import from auth",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=(),
            ),
        ]
        violations = evaluate_deny_rules(db_with_data, rules)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_name == "billing-auth-boundary"
        assert v.rule_type == "deny"
        assert v.from_ref_id == "billing"
        assert v.to_ref_id == "auth"
        assert v.file_path == "src/billing/invoice.py"
        assert v.line_number == 3

    def test_no_violation_same_node(self, db_with_data: sqlite3.Connection) -> None:
        """Import within the same node should not trigger violation."""
        # Add an import that resolves to the same domain
        db_with_data.execute(
            "INSERT INTO code_imports"
            " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
            " VALUES (?, ?, ?, ?, ?)",
            ("src/billing/utils.py", 1, "billing.models", "billing", "def456"),
        )
        db_with_data.execute(
            "INSERT INTO code_symbols"
            " (file_path, symbol_name, kind, line_start, line_end,"
            " annotations, file_hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "src/billing/utils.py",
                "helper",
                "function",
                1,
                10,
                json.dumps({"domain": "billing"}),
                "def456",
            ),
        )
        db_with_data.commit()
        rules = [
            DenyRule(
                name="billing-auth-boundary",
                description="Billing must not import from auth",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=(),
            ),
        ]
        violations = evaluate_deny_rules(db_with_data, rules)
        # Only the original billing->auth import should violate, not billing->billing
        assert len(violations) == 1

    def test_unless_edge_exemption(self, db_with_data: sqlite3.Connection) -> None:
        """If an edge exists between source and target, the rule is exempted."""
        # Add edge billing->auth with depends_on
        db_with_data.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("billing", "auth", "depends_on"),
        )
        db_with_data.commit()
        rules = [
            DenyRule(
                name="billing-auth-boundary",
                description="Billing must not import from auth unless depends_on",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=("depends_on",),
            ),
        ]
        violations = evaluate_deny_rules(db_with_data, rules)
        assert len(violations) == 0

    def test_unless_edge_wrong_kind(self, db_with_data: sqlite3.Connection) -> None:
        """If the edge kind doesn't match unless_edge, still a violation."""
        # Add edge billing->auth with 'uses' but rule exempts 'depends_on'
        db_with_data.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("billing", "auth", "uses"),
        )
        db_with_data.commit()
        rules = [
            DenyRule(
                name="billing-auth-boundary",
                description="Billing must not import from auth",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=("depends_on",),
            ),
        ]
        violations = evaluate_deny_rules(db_with_data, rules)
        assert len(violations) == 1

    def test_no_code_imports_no_violations(self, db_conn: sqlite3.Connection) -> None:
        """Empty code_imports table produces zero deny violations."""
        rules = [
            DenyRule(
                name="test",
                description="Test",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=(),
            ),
        ]
        violations = evaluate_deny_rules(db_conn, rules)
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# TestEvaluateRequireRules — require rule evaluation
# ---------------------------------------------------------------------------


class TestEvaluateRequireRules:
    """Tests for evaluate_require_rules() — structural requirements."""

    def test_violation_missing_edge(self, db_with_data: sqlite3.Connection) -> None:
        """Service without part_of edge to domain triggers violation."""
        rules = [
            RequireRule(
                name="svc-needs-domain",
                description="Every service must be part of a domain",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(kind="domain"),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_with_data, rules)
        # payments-svc has part_of -> billing (domain), users-svc does not
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_name == "svc-needs-domain"
        assert v.rule_type == "require"
        assert v.from_ref_id == "users-svc"

    def test_no_violation_edge_exists(self, db_with_data: sqlite3.Connection) -> None:
        """Service with correct edge does not trigger violation."""
        # Add edge for users-svc too
        db_with_data.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("users-svc", "auth", "part_of"),
        )
        db_with_data.commit()
        rules = [
            RequireRule(
                name="svc-needs-domain",
                description="Every service must be part of a domain",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(kind="domain"),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_with_data, rules)
        assert len(violations) == 0

    def test_edge_kind_mismatch(self, db_with_data: sqlite3.Connection) -> None:
        """Edge with wrong kind still triggers violation."""
        # users-svc -> auth with 'uses' instead of 'part_of'
        db_with_data.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("users-svc", "auth", "uses"),
        )
        db_with_data.commit()
        rules = [
            RequireRule(
                name="svc-needs-domain",
                description="Every service must be part of a domain",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(kind="domain"),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_with_data, rules)
        # users-svc has 'uses' -> auth, but rule requires 'part_of'
        assert len(violations) == 1
        assert violations[0].from_ref_id == "users-svc"


# ---------------------------------------------------------------------------
# TestEvaluateAll — combined evaluation
# ---------------------------------------------------------------------------


class TestEvaluateAll:
    """Tests for evaluate_all() — combined deny + require evaluation."""

    def test_empty_rules_no_violations(self, db_with_data: sqlite3.Connection) -> None:
        violations = evaluate_all(db_with_data, [])
        assert len(violations) == 0

    def test_combined_deny_and_require(self, db_with_data: sqlite3.Connection) -> None:
        rules: list[DenyRule | RequireRule] = [
            DenyRule(
                name="billing-auth-boundary",
                description="Billing must not import from auth",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=(),
            ),
            RequireRule(
                name="svc-needs-domain",
                description="Every service must be part of a domain",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(kind="domain"),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_all(db_with_data, rules)
        # 1 deny violation (billing->auth) + 1 require violation (users-svc no part_of)
        assert len(violations) == 2
        # Should be sorted by rule_name then file_path
        assert violations[0].rule_name <= violations[1].rule_name


# ---------------------------------------------------------------------------
# TestNodeMatcher — unit tests for matching logic
# ---------------------------------------------------------------------------


class TestNodeMatcher:
    """Tests for NodeMatcher.matches()."""

    def test_ref_id_match(self) -> None:
        m = NodeMatcher(ref_id="billing")
        assert m.matches("billing", "domain") is True
        assert m.matches("auth", "domain") is False

    def test_kind_match(self) -> None:
        m = NodeMatcher(kind="service")
        assert m.matches("payments-svc", "service") is True
        assert m.matches("billing", "domain") is False

    def test_both_ref_id_and_kind_and_logic(self) -> None:
        m = NodeMatcher(ref_id="billing", kind="domain")
        assert m.matches("billing", "domain") is True
        assert m.matches("billing", "service") is False
        assert m.matches("auth", "domain") is False

    def test_empty_matcher_matches_any_node(self) -> None:
        """NodeMatcher with both fields None matches any node."""
        m = NodeMatcher()
        assert m.matches("billing", "domain") is True
        assert m.matches("auth", "service") is True
        assert m.matches("anything", "feature") is True


# ---------------------------------------------------------------------------
# TestEmptyMatcher — empty has_edge_to in require rules
# ---------------------------------------------------------------------------


class TestEmptyMatcher:
    """Tests for empty has_edge_to matcher (matches any target node)."""

    def test_empty_matcher_parses_from_yaml(self, tmp_path: Path) -> None:
        """Parse YAML with has_edge_to: {} creates a valid RequireRule."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: domain-needs-parent\n"
            '    description: "Every domain must have a part_of edge"\n'
            "    require:\n"
            "      for: { kind: domain }\n"
            "      has_edge_to: {}\n"
            "      edge_kind: part_of\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.has_edge_to == NodeMatcher(ref_id=None, kind=None)
        assert rule.has_edge_to.matches("anything", "service") is True

    def test_empty_matcher_requires_any_outgoing_edge(
        self, db_with_data: sqlite3.Connection
    ) -> None:
        """RequireRule with empty has_edge_to matches nodes with ANY outgoing edge."""
        rules = [
            RequireRule(
                name="domain-needs-parent",
                description="Every domain must have a part_of edge",
                for_matcher=NodeMatcher(kind="domain"),
                has_edge_to=NodeMatcher(),  # empty — matches any node
                edge_kind="part_of",
            ),
        ]
        # In db_with_data: billing and auth are domains.
        # payments-svc -> billing (part_of) exists, but no edge FROM billing or auth.
        violations = evaluate_require_rules(db_with_data, rules)
        # Both billing and auth have no outgoing part_of edges → 2 violations.
        assert len(violations) == 2
        violated_refs = {v.from_ref_id for v in violations}
        assert "billing" in violated_refs
        assert "auth" in violated_refs

    def test_empty_matcher_satisfied_by_any_edge(self, db_with_data: sqlite3.Connection) -> None:
        """Adding a part_of edge from a domain to any node satisfies the rule."""
        # Add part_of edges from both domains to any target.
        db_with_data.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("billing", "payments-svc", "part_of"),
        )
        db_with_data.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("auth", "users-svc", "part_of"),
        )
        db_with_data.commit()

        rules = [
            RequireRule(
                name="domain-needs-parent",
                description="Every domain must have a part_of edge",
                for_matcher=NodeMatcher(kind="domain"),
                has_edge_to=NodeMatcher(),  # empty — matches any node
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_with_data, rules)
        assert len(violations) == 0

    def test_empty_for_matcher_still_rejected_in_deny(self, tmp_path: Path) -> None:
        """Empty matcher in deny.from position is still rejected."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: bad-matcher\n"
            '    description: "empty deny from"\n'
            "    deny:\n"
            "      from: {}\n"
            "      to: { ref_id: b }\n"
        )
        with pytest.raises(ValueError, match=r"at least one"):
            load_rules(rules_path)


# ---------------------------------------------------------------------------
# TestNodeMatcherTags — tag matching in NodeMatcher
# ---------------------------------------------------------------------------


class TestNodeMatcherTags:
    """Tests for NodeMatcher.matches() with tag support."""

    def test_tag_match(self) -> None:
        m = NodeMatcher(tag="ui-layer")
        assert m.matches("app-tabs", "service", tags={"ui-layer", "presentation"}) is True

    def test_tag_no_match(self) -> None:
        m = NodeMatcher(tag="backend")
        assert m.matches("app-tabs", "service", tags={"ui-layer", "presentation"}) is False

    def test_tag_empty_tags_set(self) -> None:
        m = NodeMatcher(tag="ui-layer")
        assert m.matches("app-tabs", "service", tags=set()) is False

    def test_tag_none_matches_any(self) -> None:
        """NodeMatcher without tag matches regardless of node tags."""
        m = NodeMatcher(ref_id="billing")
        assert m.matches("billing", "domain", tags={"some-tag"}) is True
        assert m.matches("billing", "domain", tags=set()) is True

    def test_tag_combined_with_kind(self) -> None:
        """Tag + kind are AND-combined: both must match."""
        m = NodeMatcher(kind="service", tag="ui-layer")
        assert m.matches("app-tabs", "service", tags={"ui-layer"}) is True
        assert m.matches("app-tabs", "domain", tags={"ui-layer"}) is False
        assert m.matches("app-tabs", "service", tags={"backend"}) is False

    def test_tag_combined_with_ref_id_and_kind(self) -> None:
        m = NodeMatcher(ref_id="app-tabs", kind="service", tag="ui-layer")
        assert m.matches("app-tabs", "service", tags={"ui-layer"}) is True
        assert m.matches("other", "service", tags={"ui-layer"}) is False

    def test_backward_compat_no_tags_param(self) -> None:
        """Calling matches() without tags kwarg still works for old code."""
        m = NodeMatcher(ref_id="billing")
        assert m.matches("billing", "domain") is True
        assert m.matches("auth", "domain") is False

    def test_empty_matcher_with_tags(self) -> None:
        m = NodeMatcher()
        assert m.matches("anything", "feature", tags={"x"}) is True


# ---------------------------------------------------------------------------
# TestNodeMatcherExclude — exclude filter on NodeMatcher
# ---------------------------------------------------------------------------


class TestNodeMatcherExclude:
    """Tests for NodeMatcher.matches() with exclude filter."""

    def test_exclude_single_ref_id(self) -> None:
        """Exclude a single ref_id: matches() returns False for that ref_id."""
        m = NodeMatcher(kind="service", exclude=("beadloom",))
        assert m.matches("beadloom", "service") is False

    def test_exclude_list_of_ref_ids(self) -> None:
        """Exclude multiple ref_ids: matches() returns False for all excluded."""
        m = NodeMatcher(kind="domain", exclude=("billing", "auth"))
        assert m.matches("billing", "domain") is False
        assert m.matches("auth", "domain") is False

    def test_exclude_none_backward_compatible(self) -> None:
        """Exclude=None (default): matches() behaves unchanged."""
        m = NodeMatcher(kind="service")
        assert m.exclude is None
        assert m.matches("beadloom", "service") is True
        assert m.matches("payments-svc", "service") is True

    def test_exclude_non_matching_ref_id(self) -> None:
        """Exclude with non-matching ref_id: matches() still returns True for other nodes."""
        m = NodeMatcher(kind="service", exclude=("billing",))
        assert m.matches("payments-svc", "service") is True
        assert m.matches("users-svc", "service") is True

    def test_exclude_with_ref_id_and_kind(self) -> None:
        """Exclude combined with ref_id and kind filters."""
        m = NodeMatcher(kind="domain", exclude=("billing",))
        # kind matches but excluded
        assert m.matches("billing", "domain") is False
        # kind matches and not excluded
        assert m.matches("auth", "domain") is True
        # kind does not match
        assert m.matches("billing", "service") is False

    def test_exclude_with_tags(self) -> None:
        """Exclude works alongside tag-based matching."""
        m = NodeMatcher(tag="ui-layer", exclude=("beadloom",))
        assert m.matches("beadloom", "service", tags={"ui-layer"}) is False
        assert m.matches("app-tabs", "service", tags={"ui-layer"}) is True

    def test_exclude_empty_tuple(self) -> None:
        """Empty exclude tuple does not exclude anything."""
        m = NodeMatcher(kind="service", exclude=())
        assert m.matches("beadloom", "service") is True

    def test_exclude_yaml_parsing_string(self, tmp_path: Path) -> None:
        """YAML parsing: exclude as a single string normalizes to tuple."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: svc-needs-parent\n"
            '    description: "Services need parent"\n'
            "    require:\n"
            "      for:\n"
            "        kind: service\n"
            "        exclude: beadloom\n"
            "      has_edge_to: { kind: domain }\n"
            "      edge_kind: part_of\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.for_matcher.exclude == ("beadloom",)

    def test_exclude_yaml_parsing_list(self, tmp_path: Path) -> None:
        """YAML parsing: exclude as a list normalizes to tuple."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: svc-needs-parent\n"
            '    description: "Services need parent"\n'
            "    require:\n"
            "      for:\n"
            "        kind: service\n"
            "        exclude: [beadloom, infrastructure]\n"
            "      has_edge_to: { kind: domain }\n"
            "      edge_kind: part_of\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.for_matcher.exclude == ("beadloom", "infrastructure")

    def test_exclude_yaml_not_present(self, tmp_path: Path) -> None:
        """YAML parsing: no exclude field gives exclude=None."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: svc-needs-parent\n"
            '    description: "Services need parent"\n'
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
            "      edge_kind: part_of\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.for_matcher.exclude is None


# ---------------------------------------------------------------------------
# TestGetNodeTags — helper in loader.py
# ---------------------------------------------------------------------------


class TestGetNodeTags:
    """Tests for get_node_tags() — extract tags from node extra JSON."""

    def test_node_with_tags(self, db_conn: sqlite3.Connection) -> None:
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("app-tabs", "service", "Tabs", json.dumps({"tags": ["ui-layer", "presentation"]})),
        )
        db_conn.commit()
        tags = get_node_tags(db_conn, "app-tabs")
        assert tags == {"ui-layer", "presentation"}

    def test_node_without_tags(self, db_conn: sqlite3.Connection) -> None:
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("billing", "domain", "Billing", json.dumps({})),
        )
        db_conn.commit()
        tags = get_node_tags(db_conn, "billing")
        assert tags == set()

    def test_node_not_found(self, db_conn: sqlite3.Connection) -> None:
        tags = get_node_tags(db_conn, "nonexistent")
        assert tags == set()

    def test_node_null_extra(self, db_conn: sqlite3.Connection) -> None:
        db_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("billing", "domain", "Billing", None),
        )
        db_conn.commit()
        tags = get_node_tags(db_conn, "billing")
        assert tags == set()


# ---------------------------------------------------------------------------
# TestSchemaV3 — schema version 3 support
# ---------------------------------------------------------------------------


class TestSchemaV3:
    """Tests for schema v3 support in load_rules()."""

    def test_version_3_supported(self) -> None:
        assert 3 in SUPPORTED_SCHEMA_VERSIONS

    def test_load_v3_rules(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: test-deny\n"
            '    description: "Test deny"\n'
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1

    def test_v1_backward_compat(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: test\n"
            '    description: "Test"\n'
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1

    def test_v2_backward_compat(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: test\n"
            '    description: "Test"\n'
            "    severity: warn\n"
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        assert rules[0].severity == "warn"

    def test_v3_with_tag_in_matcher(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: ui-no-db\n"
            '    description: "UI layer must not import DB layer"\n'
            "    deny:\n"
            "      from: { tag: ui-layer }\n"
            "      to: { tag: db-layer }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, DenyRule)
        assert rule.from_matcher.tag == "ui-layer"
        assert rule.to_matcher.tag == "db-layer"

    def test_v3_tag_in_require_rule(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: svc-needs-domain\n"
            '    description: "Tagged services need domain edge"\n'
            "    require:\n"
            "      for: { tag: backend }\n"
            "      has_edge_to: { kind: domain }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.for_matcher.tag == "backend"


# ---------------------------------------------------------------------------
# TestTagsBlock — top-level tags: block in rules.yml
# ---------------------------------------------------------------------------


class TestTagsBlock:
    """Tests for top-level tags: block sugar in rules.yml v3."""

    def test_tags_block_parsed(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "tags:\n"
            "  ui-layer: [app-tabs, app-auth]\n"
            "  feature-layer: [map, calendar]\n"
            "rules:\n"
            "  - name: test\n"
            '    description: "Test"\n'
            "    deny:\n"
            "      from: { tag: ui-layer }\n"
            "      to: { tag: feature-layer }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1

    def test_tags_block_returns_tag_assignments(self, tmp_path: Path) -> None:
        """load_rules_with_tags returns tag assignments when present."""
        from beadloom.graph.rule_engine import load_rules_with_tags

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "tags:\n"
            "  ui-layer: [app-tabs, app-auth]\n"
            "  feature-layer: [map, calendar]\n"
            "rules:\n"
            "  - name: test\n"
            '    description: "Test"\n'
            "    deny:\n"
            "      from: { tag: ui-layer }\n"
            "      to: { tag: feature-layer }\n"
        )
        _rules, tag_assignments = load_rules_with_tags(rules_path)
        assert tag_assignments == {
            "ui-layer": ["app-tabs", "app-auth"],
            "feature-layer": ["map", "calendar"],
        }

    def test_no_tags_block(self, tmp_path: Path) -> None:
        """Missing tags: block returns empty dict."""
        from beadloom.graph.rule_engine import load_rules_with_tags

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: test\n"
            '    description: "Test"\n'
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
        )
        rules, tag_assignments = load_rules_with_tags(rules_path)
        assert tag_assignments == {}
        assert len(rules) == 1


# ---------------------------------------------------------------------------
# TestTagsInServicesYml — tags loaded from graph YAML into extra JSON
# ---------------------------------------------------------------------------


class TestTagsInServicesYml:
    """Tests for tags in services.yml stored in extra JSON column."""

    def test_tags_stored_in_extra(self, db_conn: sqlite3.Connection, tmp_path: Path) -> None:
        from beadloom.graph.loader import load_graph

        graph_dir = tmp_path / "graph"
        graph_dir.mkdir()
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: app-tabs\n"
            "    kind: service\n"
            "    summary: Tabs\n"
            "    tags: [ui-layer, presentation]\n"
        )
        result = load_graph(graph_dir, db_conn)
        assert result.nodes_loaded == 1

        tags = get_node_tags(db_conn, "app-tabs")
        assert tags == {"ui-layer", "presentation"}

    def test_node_without_tags_has_empty_set(
        self, db_conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from beadloom.graph.loader import load_graph

        graph_dir = tmp_path / "graph"
        graph_dir.mkdir()
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: billing\n"
            "    kind: domain\n"
            "    summary: Billing\n"
        )
        load_graph(graph_dir, db_conn)
        tags = get_node_tags(db_conn, "billing")
        assert tags == set()


# ---------------------------------------------------------------------------
# TestTagAwareDenyEvaluation — deny rules using tag matchers
# ---------------------------------------------------------------------------


class TestTagAwareDenyEvaluation:
    """Tests for deny rule evaluation with tag-based matchers."""

    def test_deny_by_tag(self, db_with_data: sqlite3.Connection) -> None:
        """Deny rule using tag matcher detects violations."""
        # Add tags to nodes via extra JSON
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["critical"]}), "billing"),
        )
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["auth-layer"]}), "auth"),
        )
        db_with_data.commit()

        rules = [
            DenyRule(
                name="critical-no-auth",
                description="Critical nodes must not import auth layer",
                from_matcher=NodeMatcher(tag="critical"),
                to_matcher=NodeMatcher(tag="auth-layer"),
                unless_edge=(),
            ),
        ]
        violations = evaluate_deny_rules(db_with_data, rules)
        assert len(violations) == 1
        assert violations[0].from_ref_id == "billing"
        assert violations[0].to_ref_id == "auth"

    def test_deny_by_tag_no_match(self, db_with_data: sqlite3.Connection) -> None:
        """No violation when tag doesn't match."""
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["other"]}), "billing"),
        )
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["auth-layer"]}), "auth"),
        )
        db_with_data.commit()

        rules = [
            DenyRule(
                name="critical-no-auth",
                description="Critical nodes must not import auth layer",
                from_matcher=NodeMatcher(tag="critical"),
                to_matcher=NodeMatcher(tag="auth-layer"),
                unless_edge=(),
            ),
        ]
        violations = evaluate_deny_rules(db_with_data, rules)
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# TestTagAwareRequireEvaluation — require rules using tag matchers
# ---------------------------------------------------------------------------


class TestTagAwareRequireEvaluation:
    """Tests for require rule evaluation with tag-based matchers."""

    def test_require_by_tag(self, db_with_data: sqlite3.Connection) -> None:
        """Require rule using tag matcher on for_matcher works."""
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["backend"]}), "payments-svc"),
        )
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["backend"]}), "users-svc"),
        )
        db_with_data.commit()

        rules = [
            RequireRule(
                name="backend-needs-domain",
                description="Backend-tagged nodes need a domain edge",
                for_matcher=NodeMatcher(tag="backend"),
                has_edge_to=NodeMatcher(kind="domain"),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_with_data, rules)
        # payments-svc has part_of -> billing, users-svc doesn't
        assert len(violations) == 1
        assert violations[0].from_ref_id == "users-svc"


# ---------------------------------------------------------------------------
# TestLayerRule — LayerDef / LayerRule dataclasses
# ---------------------------------------------------------------------------


class TestLayerRuleDataclass:
    """Tests for LayerDef and LayerRule dataclass construction."""

    def test_layer_def_creation(self) -> None:
        ld = LayerDef(name="presentation", tag="ui-layer")
        assert ld.name == "presentation"
        assert ld.tag == "ui-layer"

    def test_layer_def_frozen(self) -> None:
        ld = LayerDef(name="presentation", tag="ui-layer")
        with pytest.raises(AttributeError):
            ld.name = "other"  # type: ignore[misc]

    def test_layer_rule_creation(self) -> None:
        layers = (
            LayerDef(name="presentation", tag="ui-layer"),
            LayerDef(name="features", tag="feature-layer"),
            LayerDef(name="shared", tag="shared-layer"),
        )
        rule = LayerRule(
            name="layer-direction",
            description="Architecture layers must follow top-down",
            layers=layers,
            enforce="top-down",
        )
        assert rule.name == "layer-direction"
        assert len(rule.layers) == 3
        assert rule.enforce == "top-down"
        assert rule.allow_skip is True  # default
        assert rule.edge_kind == "uses"  # default
        assert rule.severity == "error"  # default

    def test_layer_rule_no_skip(self) -> None:
        layers = (
            LayerDef(name="a", tag="a-tag"),
            LayerDef(name="b", tag="b-tag"),
        )
        rule = LayerRule(
            name="strict",
            description="Strict layers",
            layers=layers,
            enforce="top-down",
            allow_skip=False,
        )
        assert rule.allow_skip is False

    def test_layer_rule_custom_edge_kind(self) -> None:
        layers = (
            LayerDef(name="a", tag="a-tag"),
            LayerDef(name="b", tag="b-tag"),
        )
        rule = LayerRule(
            name="dep-layers",
            description="Dependency layers",
            layers=layers,
            enforce="top-down",
            edge_kind="depends_on",
        )
        assert rule.edge_kind == "depends_on"


# ---------------------------------------------------------------------------
# TestParseLayerRule — YAML parsing for layer rules
# ---------------------------------------------------------------------------


class TestParseLayerRule:
    """Tests for parsing layer rules from YAML."""

    def test_parse_layer_rule_basic(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: layer-direction\n"
            '    description: "Architecture layers"\n'
            "    layers:\n"
            "      - { name: presentation, tag: ui-layer }\n"
            "      - { name: features, tag: feature-layer }\n"
            "      - { name: shared, tag: shared-layer }\n"
            "    enforce: top-down\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, LayerRule)
        assert rule.name == "layer-direction"
        assert rule.description == "Architecture layers"
        assert len(rule.layers) == 3
        assert rule.layers[0] == LayerDef(name="presentation", tag="ui-layer")
        assert rule.layers[1] == LayerDef(name="features", tag="feature-layer")
        assert rule.layers[2] == LayerDef(name="shared", tag="shared-layer")
        assert rule.enforce == "top-down"
        assert rule.allow_skip is True
        assert rule.edge_kind == "uses"

    def test_parse_layer_rule_with_options(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: strict-layers\n"
            '    description: "Strict top-down"\n'
            "    severity: warn\n"
            "    layers:\n"
            "      - { name: ui, tag: ui-layer }\n"
            "      - { name: logic, tag: logic-layer }\n"
            "      - { name: data, tag: data-layer }\n"
            "    enforce: top-down\n"
            "    allow_skip: false\n"
            "    edge_kind: depends_on\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, LayerRule)
        assert rule.allow_skip is False
        assert rule.edge_kind == "depends_on"
        assert rule.severity == "warn"

    def test_parse_layer_rule_missing_enforce(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad-layers\n"
            '    description: "Missing enforce"\n'
            "    layers:\n"
            "      - { name: a, tag: a-tag }\n"
            "      - { name: b, tag: b-tag }\n"
        )
        with pytest.raises(ValueError, match="enforce"):
            load_rules(rules_path)

    def test_parse_layer_rule_invalid_enforce(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad-enforce\n"
            '    description: "Invalid enforce"\n'
            "    layers:\n"
            "      - { name: a, tag: a-tag }\n"
            "      - { name: b, tag: b-tag }\n"
            "    enforce: bottom-up\n"
        )
        with pytest.raises(ValueError, match="enforce"):
            load_rules(rules_path)

    def test_parse_layer_rule_too_few_layers(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: one-layer\n"
            '    description: "Only one layer"\n'
            "    layers:\n"
            "      - { name: a, tag: a-tag }\n"
            "    enforce: top-down\n"
        )
        with pytest.raises(ValueError, match="at least 2"):
            load_rules(rules_path)

    def test_parse_layer_rule_missing_tag(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad-layer\n"
            '    description: "Missing tag"\n'
            "    layers:\n"
            "      - { name: a }\n"
            "      - { name: b, tag: b-tag }\n"
            "    enforce: top-down\n"
        )
        with pytest.raises(ValueError, match="tag"):
            load_rules(rules_path)

    def test_parse_layer_rule_missing_name(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad-layer\n"
            '    description: "Missing layer name"\n'
            "    layers:\n"
            "      - { tag: a-tag }\n"
            "      - { name: b, tag: b-tag }\n"
            "    enforce: top-down\n"
        )
        with pytest.raises(ValueError, match="name"):
            load_rules(rules_path)

    def test_parse_layer_rule_invalid_edge_kind(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad-edge\n"
            '    description: "Invalid edge kind"\n'
            "    layers:\n"
            "      - { name: a, tag: a-tag }\n"
            "      - { name: b, tag: b-tag }\n"
            "    enforce: top-down\n"
            "    edge_kind: invalid_kind\n"
        )
        with pytest.raises(ValueError, match="edge"):
            load_rules(rules_path)

    def test_parse_mixed_with_layer_rule(self, tmp_path: Path) -> None:
        """Layer rules can coexist with deny/require rules."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: deny-rule\n"
            '    description: "Deny"\n'
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
            "  - name: layer-rule\n"
            '    description: "Layers"\n'
            "    layers:\n"
            "      - { name: ui, tag: ui-layer }\n"
            "      - { name: data, tag: data-layer }\n"
            "    enforce: top-down\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 2
        assert isinstance(rules[0], DenyRule)
        assert isinstance(rules[1], LayerRule)


# ---------------------------------------------------------------------------
# Fixtures for layer evaluation tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_with_layers(tmp_path: Path) -> sqlite3.Connection:
    """Database with layered nodes and edges for testing layer rules.

    Layers (top to bottom):
      - presentation: app-tabs (index 0)
      - features: map-feature (index 1)
      - shared: shared-utils (index 2)
      - services: api-service (index 3)

    Edges (uses):
      - app-tabs -> map-feature (top -> 1 down, valid)
      - map-feature -> shared-utils (1 -> 2, valid)
      - shared-utils -> api-service (2 -> 3, valid)
      - api-service -> app-tabs (3 -> 0, VIOLATION: bottom -> top)
    """
    db_path = tmp_path / "test.db"
    conn = open_db(db_path)
    create_schema(conn)

    # Nodes with tags
    nodes = [
        ("app-tabs", "service", "Tabs UI", json.dumps({"tags": ["ui-layer"]})),
        ("map-feature", "feature", "Map", json.dumps({"tags": ["feature-layer"]})),
        ("shared-utils", "service", "Shared utils", json.dumps({"tags": ["shared-layer"]})),
        ("api-service", "service", "API service", json.dumps({"tags": ["service-layer"]})),
    ]
    for ref_id, kind, summary, extra in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, extra),
        )

    # Edges — valid top-down flow + one violation
    edges = [
        ("app-tabs", "map-feature", "uses"),        # presentation -> features (valid)
        ("map-feature", "shared-utils", "uses"),     # features -> shared (valid)
        ("shared-utils", "api-service", "uses"),     # shared -> services (valid)
        ("api-service", "app-tabs", "uses"),          # services -> presentation (VIOLATION)
    ]
    for src, dst, kind in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )

    conn.commit()
    yield conn  # type: ignore[misc]
    conn.close()


# ---------------------------------------------------------------------------
# TestEvaluateLayerRules — layer rule evaluation
# ---------------------------------------------------------------------------


class TestEvaluateLayerRules:
    """Tests for evaluate_layer_rules() — top-down layer enforcement."""

    def _make_4_layer_rule(
        self,
        *,
        allow_skip: bool = True,
        edge_kind: str = "uses",
        severity: str = "error",
    ) -> LayerRule:
        """Create a standard 4-layer rule for testing."""
        return LayerRule(
            name="layer-direction",
            description="Architecture layers must follow top-down",
            layers=(
                LayerDef(name="presentation", tag="ui-layer"),
                LayerDef(name="features", tag="feature-layer"),
                LayerDef(name="shared", tag="shared-layer"),
                LayerDef(name="services", tag="service-layer"),
            ),
            enforce="top-down",
            allow_skip=allow_skip,
            edge_kind=edge_kind,
            severity=severity,
        )

    def test_bottom_to_top_violation(self, db_with_layers: sqlite3.Connection) -> None:
        """Edge from lower layer to upper layer is a violation."""
        rule = self._make_4_layer_rule()
        violations = evaluate_layer_rules(db_with_layers, [rule])
        # api-service (index 3) -> app-tabs (index 0) = violation
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_name == "layer-direction"
        assert v.rule_type == "layer"
        assert v.from_ref_id == "api-service"
        assert v.to_ref_id == "app-tabs"
        assert v.severity == "error"
        assert "api-service" in v.message
        assert "app-tabs" in v.message

    def test_top_to_bottom_no_violation(self, db_with_layers: sqlite3.Connection) -> None:
        """Edges from upper layer to lower layer are valid."""
        # Remove the violating edge
        db_with_layers.execute(
            "DELETE FROM edges WHERE src_ref_id = ? AND dst_ref_id = ?",
            ("api-service", "app-tabs"),
        )
        db_with_layers.commit()

        rule = self._make_4_layer_rule()
        violations = evaluate_layer_rules(db_with_layers, [rule])
        assert len(violations) == 0

    def test_same_layer_no_violation(self, db_with_layers: sqlite3.Connection) -> None:
        """Edges within the same layer are not violations."""
        # Add another node in features layer
        db_with_layers.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("calendar", "feature", "Calendar", json.dumps({"tags": ["feature-layer"]})),
        )
        # features -> features edge
        db_with_layers.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("map-feature", "calendar", "uses"),
        )
        db_with_layers.commit()

        # Remove the known violation
        db_with_layers.execute(
            "DELETE FROM edges WHERE src_ref_id = ? AND dst_ref_id = ?",
            ("api-service", "app-tabs"),
        )
        db_with_layers.commit()

        rule = self._make_4_layer_rule()
        violations = evaluate_layer_rules(db_with_layers, [rule])
        assert len(violations) == 0

    def test_allow_skip_true(self, db_with_layers: sqlite3.Connection) -> None:
        """With allow_skip=True, skipping layers is fine (presentation -> shared)."""
        # Add a skip edge: presentation -> shared (skip features)
        db_with_layers.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("app-tabs", "shared-utils", "uses"),
        )
        db_with_layers.commit()

        # Remove the known violation
        db_with_layers.execute(
            "DELETE FROM edges WHERE src_ref_id = ? AND dst_ref_id = ?",
            ("api-service", "app-tabs"),
        )
        db_with_layers.commit()

        rule = self._make_4_layer_rule(allow_skip=True)
        violations = evaluate_layer_rules(db_with_layers, [rule])
        assert len(violations) == 0

    def test_allow_skip_false_violation(self, db_with_layers: sqlite3.Connection) -> None:
        """With allow_skip=False, skipping layers is a violation."""
        # Add a skip edge: presentation -> shared (skip features)
        db_with_layers.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("app-tabs", "shared-utils", "uses"),
        )
        db_with_layers.commit()

        # Remove the known bottom-to-top violation to isolate skip test
        db_with_layers.execute(
            "DELETE FROM edges WHERE src_ref_id = ? AND dst_ref_id = ?",
            ("api-service", "app-tabs"),
        )
        db_with_layers.commit()

        rule = self._make_4_layer_rule(allow_skip=False)
        violations = evaluate_layer_rules(db_with_layers, [rule])
        # app-tabs (0) -> shared-utils (2): skip distance = 2, only 1 allowed
        skip_violations = [
            v for v in violations if v.from_ref_id == "app-tabs" and v.to_ref_id == "shared-utils"
        ]
        assert len(skip_violations) == 1
        assert "skip" in skip_violations[0].message.lower()

    def test_allow_skip_false_adjacent_ok(self, db_with_layers: sqlite3.Connection) -> None:
        """With allow_skip=False, adjacent layer edges are fine."""
        # Remove the known violation
        db_with_layers.execute(
            "DELETE FROM edges WHERE src_ref_id = ? AND dst_ref_id = ?",
            ("api-service", "app-tabs"),
        )
        db_with_layers.commit()

        rule = self._make_4_layer_rule(allow_skip=False)
        violations = evaluate_layer_rules(db_with_layers, [rule])
        # All remaining edges are adjacent: 0->1, 1->2, 2->3
        assert len(violations) == 0

    def test_edge_kind_filtering(self, db_with_layers: sqlite3.Connection) -> None:
        """Only edges matching the rule's edge_kind are checked."""
        # The violating edge api-service -> app-tabs is kind="uses"
        # If we filter for depends_on, no violations
        rule = self._make_4_layer_rule(edge_kind="depends_on")
        violations = evaluate_layer_rules(db_with_layers, [rule])
        assert len(violations) == 0

    def test_node_not_in_any_layer_skipped(
        self, db_with_layers: sqlite3.Connection
    ) -> None:
        """Nodes not belonging to any layer are ignored."""
        # Add a node with no layer tag
        db_with_layers.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("orphan", "service", "Orphan", json.dumps({"tags": ["unrelated"]})),
        )
        # Add edge from orphan to top layer
        db_with_layers.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("orphan", "app-tabs", "uses"),
        )
        db_with_layers.commit()

        # Remove known violation
        db_with_layers.execute(
            "DELETE FROM edges WHERE src_ref_id = ? AND dst_ref_id = ?",
            ("api-service", "app-tabs"),
        )
        db_with_layers.commit()

        rule = self._make_4_layer_rule()
        violations = evaluate_layer_rules(db_with_layers, [rule])
        assert len(violations) == 0

    def test_empty_rules_no_violations(self, db_with_layers: sqlite3.Connection) -> None:
        """Empty rules list produces no violations."""
        violations = evaluate_layer_rules(db_with_layers, [])
        assert len(violations) == 0

    def test_severity_propagation(self, db_with_layers: sqlite3.Connection) -> None:
        """Severity from rule propagates to violations."""
        rule = self._make_4_layer_rule(severity="warn")
        violations = evaluate_layer_rules(db_with_layers, [rule])
        assert len(violations) == 1
        assert violations[0].severity == "warn"

    def test_multiple_violations(self, db_with_layers: sqlite3.Connection) -> None:
        """Multiple upward edges are each reported."""
        # Add another violation: shared -> presentation
        db_with_layers.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("shared-utils", "app-tabs", "uses"),
        )
        db_with_layers.commit()

        rule = self._make_4_layer_rule()
        violations = evaluate_layer_rules(db_with_layers, [rule])
        # api-service -> app-tabs + shared-utils -> app-tabs
        assert len(violations) == 2
        from_refs = {v.from_ref_id for v in violations}
        assert "api-service" in from_refs
        assert "shared-utils" in from_refs


# ---------------------------------------------------------------------------
# TestLayerRulesInEvaluateAll — integration with evaluate_all()
# ---------------------------------------------------------------------------


class TestLayerRulesInEvaluateAll:
    """Tests for layer rules working through evaluate_all()."""

    def test_layer_rule_in_evaluate_all(self, db_with_layers: sqlite3.Connection) -> None:
        """Layer rules are evaluated as part of evaluate_all()."""
        rule = LayerRule(
            name="layer-direction",
            description="Top-down layers",
            layers=(
                LayerDef(name="presentation", tag="ui-layer"),
                LayerDef(name="features", tag="feature-layer"),
                LayerDef(name="shared", tag="shared-layer"),
                LayerDef(name="services", tag="service-layer"),
            ),
            enforce="top-down",
        )
        violations = evaluate_all(db_with_layers, [rule])
        assert len(violations) == 1
        assert violations[0].rule_type == "layer"

    def test_layer_plus_deny_rules(self, db_with_layers: sqlite3.Connection) -> None:
        """Layer rules and deny rules both work in evaluate_all()."""
        layer_rule = LayerRule(
            name="layer-direction",
            description="Top-down layers",
            layers=(
                LayerDef(name="presentation", tag="ui-layer"),
                LayerDef(name="features", tag="feature-layer"),
                LayerDef(name="shared", tag="shared-layer"),
                LayerDef(name="services", tag="service-layer"),
            ),
            enforce="top-down",
        )
        deny_rule = DenyRule(
            name="z-deny",
            description="Deny rule",
            from_matcher=NodeMatcher(ref_id="nonexistent"),
            to_matcher=NodeMatcher(ref_id="also-nonexistent"),
            unless_edge=(),
        )
        violations = evaluate_all(db_with_layers, [layer_rule, deny_rule])
        # Only layer violation expected (deny rule won't match any imports)
        layer_violations = [v for v in violations if v.rule_type == "layer"]
        assert len(layer_violations) == 1


# ---------------------------------------------------------------------------
# TestForbidEdgeRule — ForbidEdgeRule dataclass and YAML parsing
# ---------------------------------------------------------------------------


class TestForbidEdgeRuleParsing:
    """Tests for ForbidEdgeRule YAML parsing via load_rules()."""

    def test_parse_forbid_rule_basic(self, tmp_path: Path) -> None:
        """Parse a basic forbid rule from YAML."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: ui-no-native\n"
            '    description: "UI layer must not depend on native modules directly"\n'
            "    forbid:\n"
            "      from: { tag: ui-layer }\n"
            "      to: { tag: native-layer }\n"
            "      edge_kind: uses\n"
            "    severity: error\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, ForbidEdgeRule)
        assert rule.name == "ui-no-native"
        assert rule.description == "UI layer must not depend on native modules directly"
        assert rule.from_matcher == NodeMatcher(tag="ui-layer")
        assert rule.to_matcher == NodeMatcher(tag="native-layer")
        assert rule.edge_kind == "uses"
        assert rule.severity == "error"

    def test_parse_forbid_rule_without_edge_kind(self, tmp_path: Path) -> None:
        """edge_kind is optional -- defaults to None (match any edge kind)."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: no-cross-domain\n"
            '    description: "No cross-domain edges"\n'
            "    forbid:\n"
            "      from: { kind: domain }\n"
            "      to: { kind: domain }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, ForbidEdgeRule)
        assert rule.edge_kind is None

    def test_parse_forbid_rule_with_ref_id(self, tmp_path: Path) -> None:
        """Forbid rule using ref_id matchers."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: billing-no-auth\n"
            '    description: "Billing must not have edges to auth"\n'
            "    forbid:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, ForbidEdgeRule)
        assert rule.from_matcher.ref_id == "billing"
        assert rule.to_matcher.ref_id == "auth"

    def test_parse_forbid_rule_severity_warn(self, tmp_path: Path) -> None:
        """Forbid rule with severity=warn."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: soft-boundary\n"
            '    description: "Soft boundary"\n'
            "    severity: warn\n"
            "    forbid:\n"
            "      from: { kind: service }\n"
            "      to: { kind: entity }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        assert rules[0].severity == "warn"

    def test_parse_forbid_rule_bad_from(self, tmp_path: Path) -> None:
        """Invalid from: in forbid block raises ValueError."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad\n"
            '    description: "Bad"\n'
            "    forbid:\n"
            "      from: not-a-dict\n"
            "      to: { ref_id: b }\n"
        )
        with pytest.raises(ValueError, match=r"forbid\.from"):
            load_rules(rules_path)

    def test_parse_forbid_rule_bad_to(self, tmp_path: Path) -> None:
        """Invalid to: in forbid block raises ValueError."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad\n"
            '    description: "Bad"\n'
            "    forbid:\n"
            "      from: { ref_id: a }\n"
            "      to: not-a-dict\n"
        )
        with pytest.raises(ValueError, match=r"forbid\.to"):
            load_rules(rules_path)

    def test_parse_forbid_rule_invalid_edge_kind(self, tmp_path: Path) -> None:
        """Invalid edge_kind in forbid block raises ValueError."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad-edge\n"
            '    description: "Bad edge"\n'
            "    forbid:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
            "      edge_kind: invalid_kind\n"
        )
        with pytest.raises(ValueError, match="edge_kind"):
            load_rules(rules_path)

    def test_parse_forbid_rule_empty_from_rejected(self, tmp_path: Path) -> None:
        """Empty from: {} in forbid block is rejected."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: bad\n"
            '    description: "Bad"\n'
            "    forbid:\n"
            "      from: {}\n"
            "      to: { ref_id: b }\n"
        )
        with pytest.raises(ValueError, match="at least one"):
            load_rules(rules_path)

    def test_parse_forbid_mixed_with_other_rules(self, tmp_path: Path) -> None:
        """Forbid rules coexist with deny and require rules."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: deny-rule\n"
            '    description: "Deny"\n'
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
            "  - name: require-rule\n"
            '    description: "Require"\n'
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
            "  - name: forbid-rule\n"
            '    description: "Forbid"\n'
            "    forbid:\n"
            "      from: { tag: ui-layer }\n"
            "      to: { tag: native-layer }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 3
        assert isinstance(rules[0], DenyRule)
        assert isinstance(rules[1], RequireRule)
        assert isinstance(rules[2], ForbidEdgeRule)


# ---------------------------------------------------------------------------
# TestEvaluateForbidEdgeRules — ForbidEdgeRule evaluation
# ---------------------------------------------------------------------------


class TestEvaluateForbidEdgeRules:
    """Tests for evaluate_forbid_edge_rules() -- forbidden edge detection."""

    def test_basic_forbid_by_ref_id(self, db_with_data: sqlite3.Connection) -> None:
        """Forbid rule by ref_id detects existing edge."""
        # db_with_data has edge: payments-svc -> billing (part_of)
        rules = [
            ForbidEdgeRule(
                name="no-svc-to-billing",
                description="Services must not link to billing directly",
                from_matcher=NodeMatcher(ref_id="payments-svc"),
                to_matcher=NodeMatcher(ref_id="billing"),
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_with_data, rules)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_name == "no-svc-to-billing"
        assert v.rule_type == "forbid"
        assert v.from_ref_id == "payments-svc"
        assert v.to_ref_id == "billing"
        assert v.severity == "error"

    def test_forbid_no_violation(self, db_with_data: sqlite3.Connection) -> None:
        """No violation when no matching edge exists."""
        rules = [
            ForbidEdgeRule(
                name="no-auth-to-billing",
                description="Auth must not link to billing",
                from_matcher=NodeMatcher(ref_id="auth"),
                to_matcher=NodeMatcher(ref_id="billing"),
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_with_data, rules)
        assert len(violations) == 0

    def test_forbid_by_tag(self, db_with_data: sqlite3.Connection) -> None:
        """Forbid rule using tag matchers detects violations."""
        # Tag payments-svc as "payment" and billing as "finance"
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["payment"]}), "payments-svc"),
        )
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["finance"]}), "billing"),
        )
        db_with_data.commit()

        rules = [
            ForbidEdgeRule(
                name="payment-no-finance",
                description="Payment nodes must not have edges to finance nodes",
                from_matcher=NodeMatcher(tag="payment"),
                to_matcher=NodeMatcher(tag="finance"),
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_with_data, rules)
        assert len(violations) == 1
        assert violations[0].from_ref_id == "payments-svc"
        assert violations[0].to_ref_id == "billing"

    def test_forbid_by_tag_no_match(self, db_with_data: sqlite3.Connection) -> None:
        """No violation when tags do not match."""
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["other"]}), "payments-svc"),
        )
        db_with_data.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["finance"]}), "billing"),
        )
        db_with_data.commit()

        rules = [
            ForbidEdgeRule(
                name="payment-no-finance",
                description="Payment nodes must not have edges to finance nodes",
                from_matcher=NodeMatcher(tag="payment"),
                to_matcher=NodeMatcher(tag="finance"),
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_with_data, rules)
        assert len(violations) == 0

    def test_forbid_with_edge_kind_filter(self, db_with_data: sqlite3.Connection) -> None:
        """Forbid rule with edge_kind only matches that specific edge kind."""
        # db_with_data has: payments-svc -> billing (part_of)
        # Rule forbids "uses" edges -- should NOT trigger for "part_of"
        rules = [
            ForbidEdgeRule(
                name="no-svc-uses-billing",
                description="Services must not 'use' billing",
                from_matcher=NodeMatcher(ref_id="payments-svc"),
                to_matcher=NodeMatcher(ref_id="billing"),
                edge_kind="uses",
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_with_data, rules)
        assert len(violations) == 0

    def test_forbid_with_edge_kind_match(self, db_with_data: sqlite3.Connection) -> None:
        """Forbid rule with matching edge_kind triggers violation."""
        # db_with_data has: payments-svc -> billing (part_of)
        rules = [
            ForbidEdgeRule(
                name="no-svc-part-of-billing",
                description="Services must not be part_of billing",
                from_matcher=NodeMatcher(ref_id="payments-svc"),
                to_matcher=NodeMatcher(ref_id="billing"),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_with_data, rules)
        assert len(violations) == 1

    def test_forbid_by_kind_matcher(self, db_with_data: sqlite3.Connection) -> None:
        """Forbid rule using kind matchers."""
        # db_with_data has: payments-svc (service) -> billing (domain) (part_of)
        rules = [
            ForbidEdgeRule(
                name="service-no-domain",
                description="Services must not directly edge to domains",
                from_matcher=NodeMatcher(kind="service"),
                to_matcher=NodeMatcher(kind="domain"),
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_with_data, rules)
        # payments-svc -> billing matches
        assert len(violations) == 1
        assert violations[0].from_ref_id == "payments-svc"

    def test_forbid_empty_rules(self, db_with_data: sqlite3.Connection) -> None:
        """Empty rules list produces no violations."""
        violations = evaluate_forbid_edge_rules(db_with_data, [])
        assert len(violations) == 0

    def test_forbid_empty_db(self, db_conn: sqlite3.Connection) -> None:
        """Empty database produces no violations."""
        rules = [
            ForbidEdgeRule(
                name="test",
                description="Test",
                from_matcher=NodeMatcher(ref_id="a"),
                to_matcher=NodeMatcher(ref_id="b"),
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_conn, rules)
        assert len(violations) == 0

    def test_forbid_violation_message(self, db_with_data: sqlite3.Connection) -> None:
        """Violation message includes rule name and description."""
        rules = [
            ForbidEdgeRule(
                name="no-svc-to-billing",
                description="Forbidden edge",
                from_matcher=NodeMatcher(ref_id="payments-svc"),
                to_matcher=NodeMatcher(ref_id="billing"),
            ),
        ]
        violations = evaluate_forbid_edge_rules(db_with_data, rules)
        assert len(violations) == 1
        assert "no-svc-to-billing" in violations[0].message
        assert "Forbidden edge" in violations[0].message
        assert "payments-svc" in violations[0].message
        assert "billing" in violations[0].message


# ---------------------------------------------------------------------------
# TestForbidEdgeRuleInEvaluateAll — integration with evaluate_all
# ---------------------------------------------------------------------------


class TestForbidEdgeRuleInEvaluateAll:
    """Tests for ForbidEdgeRule integration with evaluate_all()."""

    def test_evaluate_all_includes_forbid(self, db_with_data: sqlite3.Connection) -> None:
        """evaluate_all() picks up ForbidEdgeRule violations."""
        rules = [
            ForbidEdgeRule(
                name="no-svc-to-billing",
                description="Forbidden",
                from_matcher=NodeMatcher(ref_id="payments-svc"),
                to_matcher=NodeMatcher(ref_id="billing"),
            ),
        ]
        violations = evaluate_all(db_with_data, rules)
        assert len(violations) == 1
        assert violations[0].rule_type == "forbid"

    def test_evaluate_all_mixed_with_forbid(self, db_with_data: sqlite3.Connection) -> None:
        """evaluate_all() handles mix of deny, require, and forbid rules."""
        rules: list[DenyRule | RequireRule | ForbidEdgeRule] = [
            DenyRule(
                name="billing-auth-boundary",
                description="Billing must not import from auth",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=(),
            ),
            RequireRule(
                name="svc-needs-domain",
                description="Every service must be part of a domain",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(kind="domain"),
                edge_kind="part_of",
            ),
            ForbidEdgeRule(
                name="no-svc-to-billing",
                description="Forbidden edge",
                from_matcher=NodeMatcher(ref_id="payments-svc"),
                to_matcher=NodeMatcher(ref_id="billing"),
            ),
        ]
        violations = evaluate_all(db_with_data, rules)
        # 1 deny (billing->auth import) + 1 require (users-svc no part_of)
        # + 1 forbid (payments-svc->billing edge)
        assert len(violations) == 3
        rule_types = {v.rule_type for v in violations}
        assert "deny" in rule_types
        assert "require" in rule_types
        assert "forbid" in rule_types


# ---------------------------------------------------------------------------
# CardinalityRule tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def cardinality_db() -> sqlite3.Connection:
    """In-memory DB with nodes, symbols, files, and sync_state for cardinality tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)

    # Nodes
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        ("auth", "domain", "Authentication", "src/auth/", json.dumps({"tags": ["core"]})),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        ("billing", "domain", "Billing system", "src/billing/", json.dumps({})),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        ("api", "service", "API gateway", "src/api/", json.dumps({})),
    )

    # Symbols: auth has 5, billing has 2
    sym_sql = (
        "INSERT INTO code_symbols"
        " (file_path, symbol_name, kind, line_start, line_end, file_hash)"
        " VALUES (?, ?, ?, ?, ?, ?)"
    )
    for i in range(5):
        conn.execute(
            sym_sql,
            (f"src/auth/module{i}.py", f"func_{i}", "function", 1, 10, f"hash{i}"),
        )
    for i in range(2):
        conn.execute(
            sym_sql,
            (f"src/billing/bill{i}.py", f"bill_{i}", "function", 1, 10, f"bhash{i}"),
        )

    # Files: auth has 3, billing has 1
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
        ("src/auth/a.py", "h1", "code", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
        ("src/auth/b.py", "h2", "code", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
        ("src/auth/c.py", "h3", "code", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
        ("src/billing/x.py", "h4", "code", "2026-01-01"),
    )

    # Sync state: auth has 2 docs (1 ok, 1 stale), billing has 0
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status, symbols_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("docs/auth/README.md", "src/auth/", "auth", "ch1", "dh1", "2026-01-01", "ok", "abc"),
    )
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status, symbols_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("docs/auth/API.md", "src/auth/api/", "auth", "ch2", "dh2", "2026-01-01", "stale", "def"),
    )

    conn.commit()
    return conn


class TestCardinalityRuleDataclass:
    def test_create_with_defaults(self) -> None:
        rule = CardinalityRule(
            name="test",
            description="test desc",
            for_matcher=NodeMatcher(kind="domain"),
        )
        assert rule.max_symbols is None
        assert rule.max_files is None
        assert rule.min_doc_coverage is None
        assert rule.severity == "warn"

    def test_create_with_all_fields(self) -> None:
        rule = CardinalityRule(
            name="size-check",
            description="Size limit",
            for_matcher=NodeMatcher(kind="domain"),
            max_symbols=200,
            max_files=30,
            min_doc_coverage=0.5,
            severity="error",
        )
        assert rule.max_symbols == 200
        assert rule.max_files == 30
        assert rule.min_doc_coverage == 0.5
        assert rule.severity == "error"


class TestCardinalityRuleYamlParsing:
    def test_parse_check_rule(self, tmp_path: Path) -> None:
        rules_file = tmp_path / "rules.yml"
        rules_file.write_text(
            "version: 3\nrules:\n"
            "  - name: domain-size\n"
            "    description: Domain should not be too large\n"
            "    check:\n"
            "      for: { kind: domain }\n"
            "      max_symbols: 200\n"
            "      max_files: 30\n"
            "    severity: warn\n"
        )
        rules = load_rules(rules_file)
        assert len(rules) == 1
        assert isinstance(rules[0], CardinalityRule)
        assert rules[0].max_symbols == 200
        assert rules[0].max_files == 30
        assert rules[0].min_doc_coverage is None

    def test_parse_doc_coverage_rule(self, tmp_path: Path) -> None:
        rules_file = tmp_path / "rules.yml"
        rules_file.write_text(
            "version: 3\nrules:\n"
            "  - name: doc-coverage\n"
            "    description: Domains need docs\n"
            "    check:\n"
            "      for: { kind: domain }\n"
            "      min_doc_coverage: 0.5\n"
            "    severity: warn\n"
        )
        rules = load_rules(rules_file)
        assert len(rules) == 1
        assert isinstance(rules[0], CardinalityRule)
        assert rules[0].min_doc_coverage == 0.5


class TestEvaluateCardinalityRules:
    def test_max_symbols_exceeded(self, cardinality_db: sqlite3.Connection) -> None:
        rules = [
            CardinalityRule(
                name="sym-limit",
                description="Max 3 symbols",
                for_matcher=NodeMatcher(kind="domain"),
                max_symbols=3,
            )
        ]
        violations = evaluate_cardinality_rules(cardinality_db, rules)
        # auth has 5 symbols > 3, billing has 2 <= 3
        assert len(violations) == 1
        assert violations[0].from_ref_id == "auth"
        assert "5 symbols" in violations[0].message
        assert violations[0].rule_type == "cardinality"

    def test_max_symbols_not_exceeded(self, cardinality_db: sqlite3.Connection) -> None:
        rules = [
            CardinalityRule(
                name="sym-limit",
                description="Max 10 symbols",
                for_matcher=NodeMatcher(kind="domain"),
                max_symbols=10,
            )
        ]
        violations = evaluate_cardinality_rules(cardinality_db, rules)
        assert len(violations) == 0

    def test_max_files_exceeded(self, cardinality_db: sqlite3.Connection) -> None:
        rules = [
            CardinalityRule(
                name="file-limit",
                description="Max 2 files",
                for_matcher=NodeMatcher(kind="domain"),
                max_files=2,
            )
        ]
        violations = evaluate_cardinality_rules(cardinality_db, rules)
        # auth has 3 files > 2, billing has 1 <= 2
        assert len(violations) == 1
        assert violations[0].from_ref_id == "auth"
        assert "3 files" in violations[0].message

    def test_min_doc_coverage_not_met(self, cardinality_db: sqlite3.Connection) -> None:
        rules = [
            CardinalityRule(
                name="doc-cov",
                description="Need 80% doc coverage",
                for_matcher=NodeMatcher(kind="domain"),
                min_doc_coverage=0.8,
            )
        ]
        violations = evaluate_cardinality_rules(cardinality_db, rules)
        # auth: 1 ok / 2 total = 50% < 80%
        # billing: 0 total -> coverage 0% < 80%
        assert len(violations) == 2

    def test_all_passing(self, cardinality_db: sqlite3.Connection) -> None:
        rules = [
            CardinalityRule(
                name="easy-check",
                description="Very generous limits",
                for_matcher=NodeMatcher(kind="domain"),
                max_symbols=100,
                max_files=100,
                min_doc_coverage=0.0,
            )
        ]
        violations = evaluate_cardinality_rules(cardinality_db, rules)
        assert len(violations) == 0

    def test_matcher_filters_by_kind(self, cardinality_db: sqlite3.Connection) -> None:
        rules = [
            CardinalityRule(
                name="service-only",
                description="Only check services",
                for_matcher=NodeMatcher(kind="service"),
                max_symbols=0,
            )
        ]
        violations = evaluate_cardinality_rules(cardinality_db, rules)
        # api service has no symbols under src/api/
        assert len(violations) == 0

    def test_matcher_filters_by_tag(self, cardinality_db: sqlite3.Connection) -> None:
        rules = [
            CardinalityRule(
                name="core-only",
                description="Only check core nodes",
                for_matcher=NodeMatcher(tag="core"),
                max_symbols=3,
            )
        ]
        violations = evaluate_cardinality_rules(cardinality_db, rules)
        # Only auth has "core" tag, has 5 symbols > 3
        assert len(violations) == 1
        assert violations[0].from_ref_id == "auth"

    def test_empty_rules(self, cardinality_db: sqlite3.Connection) -> None:
        violations = evaluate_cardinality_rules(cardinality_db, [])
        assert violations == []

    def test_integration_with_evaluate_all(self, cardinality_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import Rule as RuleType

        rules: list[RuleType] = [
            CardinalityRule(
                name="sym-limit",
                description="Max 3 symbols",
                for_matcher=NodeMatcher(kind="domain"),
                max_symbols=3,
            )
        ]
        violations = evaluate_all(cardinality_db, rules)
        assert len(violations) == 1
        assert violations[0].rule_type == "cardinality"


# ---------------------------------------------------------------------------
# TestRemediation — agent-actionable hints (BDL-039 F3 BEAD-02)
# ---------------------------------------------------------------------------


class TestRemediation:
    """`Violation.remediation` + `_remediation_for` per rule kind."""

    def _v(self, rule_type: str, **kw: object) -> Violation:
        base: dict[str, object] = {
            "rule_name": "r",
            "rule_description": "d",
            "rule_type": rule_type,
            "severity": "error",
            "file_path": None,
            "line_number": None,
            "from_ref_id": "alpha",
            "to_ref_id": "beta",
            "message": "msg",
        }
        base.update(kw)
        return Violation(**base)  # type: ignore[arg-type]

    def test_violation_remediation_defaults_none(self) -> None:
        """Additive field: existing constructions default to None."""
        v = self._v("deny")
        assert v.remediation is None

    def test_deny_remediation_names_import(self) -> None:
        from beadloom.graph.rule_engine import _remediation_for

        v = self._v("deny", file_path="src/billing/x.py")
        hint = _remediation_for("deny", v)
        assert hint is not None
        assert "alpha -> beta" in hint
        assert "src/billing/x.py" in hint

    def test_forbid_remediation_names_edge(self) -> None:
        from beadloom.graph.rule_engine import _remediation_for

        hint = _remediation_for("forbid", self._v("forbid"))
        assert hint is not None
        assert "alpha -> beta" in hint

    def test_cycle_remediation_breaks_edge(self) -> None:
        from beadloom.graph.rule_engine import _remediation_for

        hint = _remediation_for("cycle", self._v("cycle"))
        assert hint is not None
        assert "break the cycle" in hint
        assert "alpha -> beta" in hint

    def test_layer_remediation_invert_or_extract(self) -> None:
        from beadloom.graph.rule_engine import _remediation_for

        hint = _remediation_for("layer", self._v("layer"))
        assert hint is not None
        assert "invert" in hint or "extract" in hint

    def test_cardinality_remediation_split(self) -> None:
        from beadloom.graph.rule_engine import _remediation_for

        hint = _remediation_for("cardinality", self._v("cardinality"))
        assert hint is not None
        assert "split" in hint

    def test_require_remediation_add_edge(self) -> None:
        from beadloom.graph.rule_engine import _remediation_for

        hint = _remediation_for("require", self._v("require"))
        assert hint is not None
        assert "add" in hint

    def test_unknown_rule_type_returns_none(self) -> None:
        from beadloom.graph.rule_engine import _remediation_for

        assert _remediation_for("nonexistent", self._v("nonexistent")) is None

    def test_evaluate_all_populates_remediation(
        self, cardinality_db: sqlite3.Connection
    ) -> None:
        from beadloom.graph.rule_engine import Rule as RuleType

        rules: list[RuleType] = [
            CardinalityRule(
                name="sym-limit",
                description="Max 3 symbols",
                for_matcher=NodeMatcher(kind="domain"),
                max_symbols=3,
            )
        ]
        violations = evaluate_all(cardinality_db, rules)
        assert len(violations) == 1
        assert violations[0].remediation is not None
        assert "split" in violations[0].remediation


# ---------------------------------------------------------------------------
# UnregisteredFeatureCandidateRule tests (BDL-051 S1 / BEAD-01)
# ---------------------------------------------------------------------------


def _insert_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    symbol_name: str,
    annotations: dict[str, str],
) -> None:
    """Insert a single code_symbols row with the given annotations JSON."""
    conn.execute(
        "INSERT INTO code_symbols"
        " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, "function", 1, 10, json.dumps(annotations), "h"),
    )


@pytest.fixture()
def sprawl_db() -> sqlite3.Connection:
    """In-memory DB with a domain that has a domain-only file + a featured file."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)

    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("onboarding", "domain", "Onboarding", "src/beadloom/onboarding/"),
    )

    # Domain-only candidate file: 6 indexed symbols, domain= but no feature=.
    for i in range(6):
        _insert_symbol(
            conn,
            "src/beadloom/onboarding/branch_protection.py",
            f"public_fn_{i}",
            {"domain": "onboarding"},
        )

    # A registered-feature file: domain= AND feature= -> never a candidate.
    for i in range(8):
        _insert_symbol(
            conn,
            "src/beadloom/onboarding/scanner.py",
            f"scan_fn_{i}",
            {"domain": "onboarding", "feature": "agent-prime"},
        )

    # A small plumbing helper: domain-only but below the threshold.
    for i in range(2):
        _insert_symbol(
            conn,
            "src/beadloom/onboarding/config_reader.py",
            f"cfg_fn_{i}",
            {"domain": "onboarding"},
        )

    conn.commit()
    return conn


class TestUnregisteredFeatureCandidateDataclass:
    def test_create_with_defaults(self) -> None:
        from beadloom.graph.rule_engine import UnregisteredFeatureCandidateRule

        rule = UnregisteredFeatureCandidateRule(
            name="sprawl",
            description="desc",
            for_matcher=NodeMatcher(kind="domain"),
        )
        assert rule.min_symbols == 5
        assert rule.exclude == ()
        assert rule.severity == "warn"


class TestUnregisteredFeatureCandidateYamlParsing:
    def test_parse_rule(self, tmp_path: Path) -> None:
        from beadloom.graph.rule_engine import UnregisteredFeatureCandidateRule

        rules_file = tmp_path / "rules.yml"
        rules_file.write_text(
            "version: 3\nrules:\n"
            "  - name: unregistered-feature-candidate\n"
            "    description: Flag domain-only modules\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
            "      min_symbols: 7\n"
            "      exclude:\n"
            "        - '**/config_reader.py'\n"
            "    severity: warn\n"
        )
        rules = load_rules(rules_file)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, UnregisteredFeatureCandidateRule)
        assert rule.min_symbols == 7
        assert rule.exclude == ("**/config_reader.py",)
        assert rule.severity == "warn"

    def test_parse_rule_defaults(self, tmp_path: Path) -> None:
        from beadloom.graph.rule_engine import UnregisteredFeatureCandidateRule

        rules_file = tmp_path / "rules.yml"
        rules_file.write_text(
            "version: 3\nrules:\n"
            "  - name: sprawl\n"
            "    description: d\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
            "    severity: warn\n"
        )
        rules = load_rules(rules_file)
        assert isinstance(rules[0], UnregisteredFeatureCandidateRule)
        assert rules[0].min_symbols == 5
        assert rules[0].exclude == ()


class TestEvaluateUnregisteredFeatureCandidateRules:
    def test_flags_domain_only_file(self, sprawl_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import (
            UnregisteredFeatureCandidateRule,
            evaluate_unregistered_feature_candidate_rules,
        )

        rules = [
            UnregisteredFeatureCandidateRule(
                name="sprawl",
                description="Flag domain-only modules",
                for_matcher=NodeMatcher(kind="domain"),
                min_symbols=5,
            )
        ]
        violations = evaluate_unregistered_feature_candidate_rules(sprawl_db, rules)
        assert len(violations) == 1
        v = violations[0]
        assert v.severity == "warn"
        assert v.rule_type == "unregistered_feature_candidate"
        assert v.from_ref_id == "onboarding"
        assert v.file_path == "src/beadloom/onboarding/branch_protection.py"
        assert "6 symbols" in v.message
        assert "branch_protection.py" in v.message

    def test_does_not_flag_featured_file(self, sprawl_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import (
            UnregisteredFeatureCandidateRule,
            evaluate_unregistered_feature_candidate_rules,
        )

        rules = [
            UnregisteredFeatureCandidateRule(
                name="sprawl",
                description="d",
                for_matcher=NodeMatcher(kind="domain"),
                min_symbols=5,
            )
        ]
        violations = evaluate_unregistered_feature_candidate_rules(sprawl_db, rules)
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/scanner.py" not in flagged

    def test_respects_threshold(self, sprawl_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import (
            UnregisteredFeatureCandidateRule,
            evaluate_unregistered_feature_candidate_rules,
        )

        rules = [
            UnregisteredFeatureCandidateRule(
                name="sprawl",
                description="d",
                for_matcher=NodeMatcher(kind="domain"),
                min_symbols=7,  # branch_protection only has 6 public -> below
            )
        ]
        violations = evaluate_unregistered_feature_candidate_rules(sprawl_db, rules)
        assert violations == []

    def test_respects_exclude_glob(self, sprawl_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import (
            UnregisteredFeatureCandidateRule,
            evaluate_unregistered_feature_candidate_rules,
        )

        rules = [
            UnregisteredFeatureCandidateRule(
                name="sprawl",
                description="d",
                for_matcher=NodeMatcher(kind="domain"),
                min_symbols=5,
                exclude=("**/branch_protection.py",),
            )
        ]
        violations = evaluate_unregistered_feature_candidate_rules(sprawl_db, rules)
        assert violations == []

    def test_evaluate_all_includes_candidate(self, sprawl_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import (
            Rule as RuleType,
        )
        from beadloom.graph.rule_engine import (
            UnregisteredFeatureCandidateRule,
        )

        rules: list[RuleType] = [
            UnregisteredFeatureCandidateRule(
                name="sprawl",
                description="d",
                for_matcher=NodeMatcher(kind="domain"),
                min_symbols=5,
            )
        ]
        violations = evaluate_all(sprawl_db, rules)
        assert len(violations) == 1
        assert violations[0].rule_type == "unregistered_feature_candidate"


class TestUnregisteredFeatureCandidateRealRepo:
    """Run the lint against the real Beadloom index (BDL-051 dogfood).

    Slice 1 only asserts the lint SEES the onboarding sprawl as warns;
    Slice 3 will re-model those modules into features. The build must NOT
    fail from these warns (warn severity).
    """

    def test_flags_real_onboarding_candidates(self) -> None:
        import pathlib

        from beadloom.graph.rule_engine import (
            UnregisteredFeatureCandidateRule,
            evaluate_unregistered_feature_candidate_rules,
        )
        from beadloom.infrastructure.db import open_db

        repo_root = pathlib.Path(__file__).resolve().parents[1]
        db_path = repo_root / ".beadloom" / "beadloom.db"
        if not db_path.is_file():
            pytest.skip("real index db not present")

        conn = open_db(db_path)
        try:
            rules = [
                UnregisteredFeatureCandidateRule(
                    name="unregistered-feature-candidate",
                    description="domain-only modules",
                    for_matcher=NodeMatcher(kind="domain"),
                    min_symbols=5,
                )
            ]
            violations = evaluate_unregistered_feature_candidate_rules(conn, rules)
        finally:
            conn.close()

        flagged = {v.file_path for v in violations}
        expected = {
            "src/beadloom/onboarding/config_sync.py",
            "src/beadloom/onboarding/branch_protection.py",
            "src/beadloom/onboarding/agentic_flow_setup.py",
            "src/beadloom/onboarding/ai_techwriter_setup.py",
        }
        # The lint must SEE each known onboarding sprawl candidate.
        assert expected.issubset(flagged), f"missing: {expected - flagged}"
        # All findings are advisory warns (never fail the build).
        assert all(v.severity == "warn" for v in violations)


# ---------------------------------------------------------------------------
# UnregisteredFeatureCandidateRule — HARDENING edge cases (BDL-051 S1 / BEAD-02)
# ---------------------------------------------------------------------------


def _ufc_rule(
    *,
    min_symbols: int = 5,
    exclude: tuple[str, ...] = (),
) -> UnregisteredFeatureCandidateRule:
    """Build a domain-scoped UnregisteredFeatureCandidateRule for tests."""
    from beadloom.graph.rule_engine import UnregisteredFeatureCandidateRule

    return UnregisteredFeatureCandidateRule(
        name="unregistered-feature-candidate",
        description="domain-only modules",
        for_matcher=NodeMatcher(kind="domain"),
        min_symbols=min_symbols,
        exclude=exclude,
    )


@pytest.fixture()
def domain_db() -> sqlite3.Connection:
    """In-memory DB with a single ``graph`` domain node and no symbols yet.

    Tests populate ``code_symbols`` themselves so each can target a precise
    threshold / annotation shape without sharing state with other tests.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("graph", "domain", "Graph domain", "src/beadloom/graph/"),
    )
    conn.commit()
    yield conn  # type: ignore[misc]
    conn.close()


def _populate(
    conn: sqlite3.Connection,
    file_path: str,
    count: int,
    annotations: dict[str, str],
) -> None:
    """Insert *count* symbols for *file_path* all sharing *annotations*."""
    for i in range(count):
        _insert_symbol(conn, file_path, f"sym_{i}", annotations)
    conn.commit()


class TestUnregisteredFeatureCandidateParseValidation:
    """Parser error and edge paths for the unregistered_feature_candidate block."""

    def test_for_must_be_mapping(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: sprawl\n"
            "    description: d\n"
            "    unregistered_feature_candidate:\n"
            "      for: not-a-mapping\n"
        )
        with pytest.raises(ValueError, match="for must be a mapping"):
            load_rules(rules_path)

    def test_negative_min_symbols_rejected(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: sprawl\n"
            "    description: d\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
            "      min_symbols: -1\n"
        )
        with pytest.raises(ValueError, match="min_symbols must be non-negative"):
            load_rules(rules_path)

    def test_exclude_null_normalizes_to_empty(self, tmp_path: Path) -> None:
        from beadloom.graph.rule_engine import UnregisteredFeatureCandidateRule

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: sprawl\n"
            "    description: d\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
            "      exclude: null\n"
        )
        rules = load_rules(rules_path)
        assert isinstance(rules[0], UnregisteredFeatureCandidateRule)
        assert rules[0].exclude == ()

    def test_exclude_non_list_rejected(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: sprawl\n"
            "    description: d\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
            "      exclude: '*/single.py'\n"
        )
        with pytest.raises(ValueError, match="exclude must be a list"):
            load_rules(rules_path)

    def test_block_must_be_mapping(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: sprawl\n"
            "    description: d\n"
            "    unregistered_feature_candidate: not-a-mapping\n"
        )
        with pytest.raises(ValueError, match="must be a mapping"):
            load_rules(rules_path)

    def test_defaults_to_warn_when_severity_omitted(self, tmp_path: Path) -> None:
        """Advisory rule defaults to warn severity even with no explicit severity."""
        from beadloom.graph.rule_engine import UnregisteredFeatureCandidateRule

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: sprawl\n"
            "    description: d\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
        )
        rules = load_rules(rules_path)
        assert isinstance(rules[0], UnregisteredFeatureCandidateRule)
        assert rules[0].severity == "warn"


class TestUnregisteredFeatureCandidateThreshold:
    """Exact threshold N: == N flagged, N-1 not; custom min_symbols honored."""

    def test_exactly_n_symbols_flagged(self, domain_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/widget.py", 5, {"domain": "graph"})
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        assert [v.file_path for v in violations] == ["src/beadloom/graph/widget.py"]

    def test_n_minus_one_symbols_not_flagged(self, domain_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/widget.py", 4, {"domain": "graph"})
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        assert violations == []

    @pytest.mark.parametrize(
        ("min_symbols", "symbol_count", "expected_flagged"),
        [
            (3, 3, True),  # exactly the custom threshold
            (3, 2, False),  # one below the custom threshold
            (10, 10, True),  # higher custom threshold met exactly
            (10, 9, False),  # higher custom threshold missed by one
        ],
    )
    def test_custom_min_symbols_honored(
        self,
        domain_db: sqlite3.Connection,
        min_symbols: int,
        symbol_count: int,
        expected_flagged: bool,
    ) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/widget.py", symbol_count, {"domain": "graph"})
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=min_symbols)]
        )
        assert bool(violations) is expected_flagged


class TestUnregisteredFeatureCandidateFeaturePresent:
    """A file carrying a ``feature`` annotation is never flagged."""

    def test_feature_present_never_flagged_even_when_huge(
        self, domain_db: sqlite3.Connection
    ) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        # 50 symbols, well over any threshold, but it models a feature.
        _populate(
            domain_db,
            "src/beadloom/graph/loader.py",
            50,
            {"domain": "graph", "feature": "graph-loader"},
        )
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        assert violations == []

    def test_feature_on_some_rows_suppresses_whole_file(
        self, domain_db: sqlite3.Connection
    ) -> None:
        """If ANY symbol row in a file declares a feature, the file is excused.

        Annotations are per-symbol; a single feature-bearing symbol marks the
        file as feature-modeled, so it must not be flagged as a candidate.
        """
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        path = "src/beadloom/graph/loader.py"
        for i in range(6):
            _insert_symbol(domain_db, path, f"plain_{i}", {"domain": "graph"})
        _insert_symbol(domain_db, path, "featured", {"domain": "graph", "feature": "graph-loader"})
        domain_db.commit()

        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        assert violations == []


class TestUnregisteredFeatureCandidateExclude:
    """Exclude allow-list: excluded glob skipped; non-excluded sibling flagged."""

    def test_excluded_glob_not_flagged_but_sibling_is(
        self, domain_db: sqlite3.Connection
    ) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/presets.py", 6, {"domain": "graph"})
        _populate(domain_db, "src/beadloom/graph/resolver.py", 6, {"domain": "graph"})

        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5, exclude=("*/presets.py",))]
        )
        flagged = {v.file_path for v in violations}
        assert flagged == {"src/beadloom/graph/resolver.py"}

    def test_double_star_glob_matches_nested_path(
        self, domain_db: sqlite3.Connection
    ) -> None:
        """fnmatch semantics: ``**/presets.py`` matches the full slash path."""
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/presets.py", 6, {"domain": "graph"})
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5, exclude=("**/presets.py",))]
        )
        assert violations == []

    def test_non_matching_glob_does_not_suppress(
        self, domain_db: sqlite3.Connection
    ) -> None:
        """A glob that does not match the candidate path leaves it flagged."""
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/resolver.py", 6, {"domain": "graph"})
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5, exclude=("*/unrelated.py",))]
        )
        assert {v.file_path for v in violations} == {"src/beadloom/graph/resolver.py"}


class TestUnregisteredFeatureCandidateAnnotationRobustness:
    """Malformed / empty / NULL annotations are handled without crashing."""

    @pytest.mark.parametrize(
        "raw_annotations",
        [
            "not-json{",  # malformed JSON
            "",  # empty string
            "[1, 2, 3]",  # valid JSON but not a dict
            "null",  # JSON null
            '"a string"',  # JSON scalar
        ],
    )
    def test_malformed_annotations_not_spuriously_flagged(
        self, domain_db: sqlite3.Connection, raw_annotations: str
    ) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        for i in range(6):
            domain_db.execute(
                "INSERT INTO code_symbols"
                " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("src/beadloom/graph/broken.py", f"s{i}", "function", 1, 10, raw_annotations, "h"),
            )
        domain_db.commit()

        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        # No domain attribution can be parsed → not a candidate, and no crash.
        assert violations == []

    def test_null_annotations_not_flagged(self, domain_db: sqlite3.Connection) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        for i in range(6):
            domain_db.execute(
                "INSERT INTO code_symbols"
                " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("src/beadloom/graph/nullann.py", f"s{i}", "function", 1, 10, None, "h"),
            )
        domain_db.commit()

        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        assert violations == []

    def test_domain_without_feature_key_is_flagged(
        self, domain_db: sqlite3.Connection
    ) -> None:
        """A clean domain-only file (domain key, no feature key) is a candidate."""
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/widget.py", 6, {"domain": "graph"})
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        assert {v.file_path for v in violations} == {"src/beadloom/graph/widget.py"}


class TestUnregisteredFeatureCandidateDomainAttribution:
    """A candidate is counted under the RIGHT domain, with no cross-domain leak."""

    def test_no_cross_domain_leak(self) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("graph", "domain", "Graph", "src/beadloom/graph/"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("onboarding", "domain", "Onboarding", "src/beadloom/onboarding/"),
        )
        conn.commit()

        # An onboarding-annotated file living under the onboarding source prefix.
        _populate(conn, "src/beadloom/onboarding/setup.py", 6, {"domain": "onboarding"})
        # A graph-annotated file under the graph source prefix.
        _populate(conn, "src/beadloom/graph/resolver.py", 6, {"domain": "graph"})

        try:
            violations = evaluate_unregistered_feature_candidate_rules(conn, [_ufc_rule()])
        finally:
            conn.close()

        # Each candidate is attributed to exactly its own domain.
        attribution = {(v.from_ref_id, v.file_path) for v in violations}
        assert attribution == {
            ("onboarding", "src/beadloom/onboarding/setup.py"),
            ("graph", "src/beadloom/graph/resolver.py"),
        }

    def test_wrong_domain_annotation_under_prefix_not_attributed(
        self, domain_db: sqlite3.Connection
    ) -> None:
        """A file under graph/ but annotated domain=other is NOT a graph candidate.

        The rule keys on the ``annotations.domain`` value, not merely the path
        prefix, so a mis-annotated file does not leak into the graph findings.
        """
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/stray.py", 6, {"domain": "onboarding"})
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        assert violations == []


class TestUnregisteredFeatureCandidateSourceHandling:
    """Source-prefix handling: NULL source skipped; message uses a relative path."""

    def test_domain_with_null_source_is_skipped(self) -> None:
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        # Domain node with NULL source — no prefix to group files under.
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("graph", "domain", "Graph", None),
        )
        conn.commit()
        _populate(conn, "src/beadloom/graph/widget.py", 6, {"domain": "graph"})

        try:
            violations = evaluate_unregistered_feature_candidate_rules(conn, [_ufc_rule()])
        finally:
            conn.close()
        assert violations == []

    def test_message_uses_domain_relative_path(self, domain_db: sqlite3.Connection) -> None:
        """The finding message rewrites the source prefix to ``<domain>/...``."""
        from beadloom.graph.rule_engine import (
            evaluate_unregistered_feature_candidate_rules,
        )

        _populate(domain_db, "src/beadloom/graph/widget.py", 6, {"domain": "graph"})
        violations = evaluate_unregistered_feature_candidate_rules(
            domain_db, [_ufc_rule(min_symbols=5)]
        )
        assert len(violations) == 1
        # Prefix "src/beadloom/graph/" is rewritten to "graph/".
        assert "graph/widget.py" in violations[0].message
        assert "6 symbols" in violations[0].message


class TestUnregisteredFeatureCandidateRemediation:
    """evaluate_all enriches UFC findings with an actionable remediation hint."""

    def test_remediation_hint_present(self, sprawl_db: sqlite3.Connection) -> None:
        violations = evaluate_all(sprawl_db, [_ufc_rule(min_symbols=5)])
        assert len(violations) == 1
        remediation = violations[0].remediation
        assert remediation is not None
        assert "model" in remediation
        assert "exclude" in remediation


class TestUnregisteredFeatureCandidateSeverity:
    """The warn-severity rule never flips ``lint --strict`` to a failure."""

    def test_warn_violation_does_not_set_has_errors(
        self, sprawl_db: sqlite3.Connection
    ) -> None:
        from beadloom.graph.linter import LintResult

        violations = evaluate_all(sprawl_db, [_ufc_rule(min_symbols=5)])
        assert len(violations) == 1
        result = LintResult(violations=violations)
        # The strict exit path keys on has_errors; warn-only must stay clean.
        assert result.has_errors is False
        assert result.error_count == 0
        assert result.warning_count == 1


class TestUnregisteredFeatureCandidateSerializationRoundTrip:
    """The rule survives reindex serialization: serialize → DB CHECK → reload."""

    def test_serialize_round_trip_through_db(self, tmp_path: Path) -> None:
        from beadloom.application.reindex import _serialize_rule
        from beadloom.graph.rule_engine import load_rules

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: unregistered-feature-candidate\n"
            "    description: domain-only modules\n"
            "    severity: warn\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
            "      min_symbols: 5\n"
            "      exclude:\n"
            "        - '**/config_reader.py'\n"
        )
        rule = load_rules(rules_path)[0]

        rule_type, rule_def = _serialize_rule(rule)
        assert rule_type == "unregistered_feature_candidate"
        assert rule_def["min_symbols"] == 5
        assert rule_def["exclude"] == ["**/config_reader.py"]

        # The rules-table CHECK must accept this rule_type (no IntegrityError).
        conn = sqlite3.connect(":memory:")
        try:
            create_schema(conn)
            conn.execute(
                "INSERT INTO rules (name, description, rule_type, rule_json, enabled)"
                " VALUES (?, ?, ?, ?, 1)",
                (rule.name, rule.description, rule_type, json.dumps(rule_def)),
            )
            conn.commit()
            row = conn.execute(
                "SELECT rule_type, rule_json FROM rules WHERE name = ?", (rule.name,)
            ).fetchone()
        finally:
            conn.close()

        assert row[0] == "unregistered_feature_candidate"
        assert json.loads(row[1])["min_symbols"] == 5

    def test_serialize_without_exclude_omits_key(self, tmp_path: Path) -> None:
        """exclude=() serializes without an ``exclude`` key (clean default)."""
        from beadloom.application.reindex import _serialize_rule
        from beadloom.graph.rule_engine import load_rules

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: sprawl\n"
            "    description: d\n"
            "    severity: warn\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
        )
        rule = load_rules(rules_path)[0]
        rule_type, rule_def = _serialize_rule(rule)
        assert rule_type == "unregistered_feature_candidate"
        assert "exclude" not in rule_def

    def test_db_check_rejects_unknown_rule_type(self) -> None:
        """Regression guard: the CHECK constraint is genuinely enforced."""
        conn = sqlite3.connect(":memory:")
        try:
            create_schema(conn)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO rules (name, description, rule_type, rule_json, enabled)"
                    " VALUES (?, ?, ?, ?, 1)",
                    ("bogus", "d", "totally_unknown_type", "{}"),
                )
        finally:
            conn.close()


class TestUnregisteredFeatureCandidateReindexSurvival:
    """A full reindex loads the rule into the DB without raising."""

    def test_reindex_loads_rule_into_db(self, tmp_path: Path) -> None:
        from beadloom.application.reindex import ReindexResult, _load_rules_into_db

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: unregistered-feature-candidate\n"
            "    description: domain-only modules\n"
            "    severity: warn\n"
            "    unregistered_feature_candidate:\n"
            "      for: { kind: domain }\n"
            "      min_symbols: 5\n"
        )
        conn = sqlite3.connect(":memory:")
        try:
            create_schema(conn)
            result = ReindexResult()
            _load_rules_into_db(rules_path, conn, result)
            conn.commit()
            assert result.errors == []
            row = conn.execute(
                "SELECT rule_type FROM rules WHERE name = ?",
                ("unregistered-feature-candidate",),
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert row[0] == "unregistered_feature_candidate"


# ---------------------------------------------------------------------------
# component node kind (BDL-051 S3a / BEAD-07)
# ---------------------------------------------------------------------------


class TestComponentNodeKind:
    """The 'component' node kind is a first-class, valid node kind."""

    def test_component_in_valid_node_kinds(self) -> None:
        from beadloom.graph.rule_engine import VALID_NODE_KINDS

        assert "component" in VALID_NODE_KINDS

    def test_matcher_parses_component_kind(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: comp-rule\n"
            "    description: components need a parent\n"
            "    require:\n"
            "      for: { kind: component }\n"
            "      has_edge_to: { kind: domain }\n"
            "      edge_kind: part_of\n"
        )
        rules = load_rules(rules_path)
        assert isinstance(rules[0], RequireRule)
        assert rules[0].for_matcher.kind == "component"

    def test_component_node_round_trips_through_loader(self, tmp_path: Path) -> None:
        """A component node loads into the nodes table without 'Unknown kind'."""
        from beadloom.graph.loader import load_graph

        graph_dir = tmp_path / "_graph"
        graph_dir.mkdir()
        (graph_dir / "services.yml").write_text(
            "version: 1\n"
            "nodes:\n"
            "  - ref_id: beadloom\n"
            "    kind: service\n"
            "    summary: root\n"
            "  - ref_id: graph\n"
            "    kind: domain\n"
            "    summary: graph domain\n"
            "    source: src/beadloom/graph/\n"
            "  - ref_id: graph-loader\n"
            "    kind: component\n"
            "    summary: the loader building block\n"
            "    source: src/beadloom/graph/loader.py\n"
            "edges:\n"
            "  - src: graph\n"
            "    dst: beadloom\n"
            "    kind: part_of\n"
            "  - src: graph-loader\n"
            "    dst: graph\n"
            "    kind: part_of\n"
        )
        conn = sqlite3.connect(":memory:")
        try:
            create_schema(conn)
            result = load_graph(graph_dir, conn)
            conn.commit()
            assert result.errors == []
            row = conn.execute(
                "SELECT kind FROM nodes WHERE ref_id = ?", ("graph-loader",)
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert row[0] == "component"


# ---------------------------------------------------------------------------
# ModuleCoverageRule — coverage lint (BDL-051 S3a / BEAD-07)
# ---------------------------------------------------------------------------


def _coverage_db() -> sqlite3.Connection:
    """In-memory DB: a covered (component), covered (feature), node-source, and
    uncovered (domain-only) module, plus an exempt-style trivial module."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)

    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("onboarding", "domain", "Onboarding", "src/beadloom/onboarding/"),
    )
    # A component node whose source IS a module file -> that module is covered
    # by being a node's source.
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("onb-scanner", "component", "scanner", "src/beadloom/onboarding/scanner.py"),
    )

    # Uncovered: domain-only, no feature/component annotation.
    for i in range(6):
        _insert_symbol(
            conn,
            "src/beadloom/onboarding/branch_protection.py",
            f"public_fn_{i}",
            {"domain": "onboarding"},
        )
    # Covered via component= annotation.
    for i in range(4):
        _insert_symbol(
            conn,
            "src/beadloom/onboarding/config_sync.py",
            f"sync_fn_{i}",
            {"domain": "onboarding", "component": "config-check"},
        )
    # Covered via feature= annotation.
    for i in range(3):
        _insert_symbol(
            conn,
            "src/beadloom/onboarding/agentic_flow_setup.py",
            f"flow_fn_{i}",
            {"domain": "onboarding", "feature": "agentic-flow-setup"},
        )
    # Covered because the module path equals a node's source.
    for i in range(5):
        _insert_symbol(
            conn,
            "src/beadloom/onboarding/scanner.py",
            f"scan_fn_{i}",
            {"domain": "onboarding"},
        )
    # Trivial/plumbing module (will be exempted by glob in some tests).
    for i in range(2):
        _insert_symbol(
            conn,
            "src/beadloom/onboarding/presets.py",
            f"preset_fn_{i}",
            {"domain": "onboarding"},
        )

    conn.commit()
    return conn


def _coverage_rule(
    *,
    source_root: str = "src/beadloom/",
    min_symbols: int = 1,
    exempt: tuple[str, ...] = (),
    severity: str = "warn",
) -> object:
    """Build a ModuleCoverageRule for tests."""
    from beadloom.graph.rule_engine import ModuleCoverageRule

    return ModuleCoverageRule(
        name="module-coverage",
        description="every src module must be a node or exempt",
        source_root=source_root,
        min_symbols=min_symbols,
        exempt=exempt,
        severity=severity,
    )


class TestModuleCoverageDataclass:
    def test_create_with_defaults(self) -> None:
        from beadloom.graph.rule_engine import ModuleCoverageRule

        rule = ModuleCoverageRule(name="module-coverage", description="d")
        assert rule.source_root == "src/beadloom/"
        assert rule.min_symbols == 1
        assert rule.exempt == ()
        assert rule.severity == "warn"


class TestModuleCoverageYamlParsing:
    def test_parse_full_rule(self, tmp_path: Path) -> None:
        from beadloom.graph.rule_engine import ModuleCoverageRule

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: module-coverage\n"
            "    description: coverage\n"
            "    severity: warn\n"
            "    module_coverage:\n"
            "      source_root: src/beadloom/\n"
            "      min_symbols: 1\n"
            "      exempt:\n"
            "        - '**/__init__.py'\n"
            "        - '**/presets.py'\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, ModuleCoverageRule)
        assert rule.source_root == "src/beadloom/"
        assert rule.min_symbols == 1
        assert rule.exempt == ("**/__init__.py", "**/presets.py")

    def test_defaults_when_omitted(self, tmp_path: Path) -> None:
        from beadloom.graph.rule_engine import ModuleCoverageRule

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: module-coverage\n"
            "    description: coverage\n"
            "    module_coverage: {}\n"
        )
        rules = load_rules(rules_path)
        assert isinstance(rules[0], ModuleCoverageRule)
        assert rules[0].min_symbols == 1
        assert rules[0].severity == "warn"

    def test_negative_min_symbols_rejected(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: module-coverage\n"
            "    description: coverage\n"
            "    module_coverage:\n"
            "      min_symbols: -1\n"
        )
        with pytest.raises(ValueError, match="min_symbols must be non-negative"):
            load_rules(rules_path)

    def test_not_a_mapping_rejected(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: module-coverage\n"
            "    description: coverage\n"
            "    module_coverage: not-a-mapping\n"
        )
        with pytest.raises(ValueError, match="must be a mapping"):
            load_rules(rules_path)


class TestEvaluateModuleCoverage:
    def test_uncovered_module_flagged(self) -> None:
        from beadloom.graph.rule_engine import evaluate_module_coverage_rules

        conn = _coverage_db()
        try:
            violations = evaluate_module_coverage_rules(conn, [_coverage_rule()])  # type: ignore[list-item]
        finally:
            conn.close()
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/branch_protection.py" in flagged

    def test_component_annotation_covers(self) -> None:
        from beadloom.graph.rule_engine import evaluate_module_coverage_rules

        conn = _coverage_db()
        try:
            violations = evaluate_module_coverage_rules(conn, [_coverage_rule()])  # type: ignore[list-item]
        finally:
            conn.close()
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/config_sync.py" not in flagged

    def test_feature_annotation_covers(self) -> None:
        from beadloom.graph.rule_engine import evaluate_module_coverage_rules

        conn = _coverage_db()
        try:
            violations = evaluate_module_coverage_rules(conn, [_coverage_rule()])  # type: ignore[list-item]
        finally:
            conn.close()
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/agentic_flow_setup.py" not in flagged

    def test_node_source_covers(self) -> None:
        from beadloom.graph.rule_engine import evaluate_module_coverage_rules

        conn = _coverage_db()
        try:
            violations = evaluate_module_coverage_rules(conn, [_coverage_rule()])  # type: ignore[list-item]
        finally:
            conn.close()
        flagged = {v.file_path for v in violations}
        # scanner.py has only domain= annotation but it IS a component node's source.
        assert "src/beadloom/onboarding/scanner.py" not in flagged

    def test_exempt_glob_honored(self) -> None:
        from beadloom.graph.rule_engine import evaluate_module_coverage_rules

        conn = _coverage_db()
        try:
            violations = evaluate_module_coverage_rules(
                conn, [_coverage_rule(exempt=("**/presets.py",))]  # type: ignore[list-item]
            )
        finally:
            conn.close()
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/presets.py" not in flagged

    def test_not_exempt_when_glob_misses(self) -> None:
        from beadloom.graph.rule_engine import evaluate_module_coverage_rules

        conn = _coverage_db()
        try:
            violations = evaluate_module_coverage_rules(
                conn, [_coverage_rule(exempt=("**/other.py",))]  # type: ignore[list-item]
            )
        finally:
            conn.close()
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/presets.py" in flagged

    def test_message_names_file_and_symbol_count(self) -> None:
        from beadloom.graph.rule_engine import evaluate_module_coverage_rules

        conn = _coverage_db()
        try:
            violations = evaluate_module_coverage_rules(conn, [_coverage_rule()])  # type: ignore[list-item]
        finally:
            conn.close()
        v = next(
            v
            for v in violations
            if v.file_path == "src/beadloom/onboarding/branch_protection.py"
        )
        assert "branch_protection.py" in v.message
        assert "6 symbols" in v.message
        assert "not covered" in v.message
        assert v.rule_type == "module_coverage"
        assert v.severity == "warn"

    def test_below_min_symbols_not_flagged(self) -> None:
        from beadloom.graph.rule_engine import evaluate_module_coverage_rules

        conn = _coverage_db()
        try:
            # presets.py has 2 symbols; require >=3 -> not flagged.
            violations = evaluate_module_coverage_rules(
                conn, [_coverage_rule(min_symbols=3)]  # type: ignore[list-item]
            )
        finally:
            conn.close()
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/presets.py" not in flagged


class TestModuleCoverageSeverityWarn:
    def test_warn_severity_does_not_fail_strict(self) -> None:
        """A module-coverage finding is severity warn (does not block lint --strict)."""
        conn = _coverage_db()
        try:
            violations = evaluate_all(conn, [_coverage_rule()])  # type: ignore[list-item]
        finally:
            conn.close()
        coverage = [v for v in violations if v.rule_type == "module_coverage"]
        assert coverage  # there is at least one finding
        assert all(v.severity == "warn" for v in coverage)
        # lint --strict fails only on error-severity violations.
        assert not any(v.severity == "error" for v in coverage)


class TestModuleCoverageSerializationRoundTrip:
    def test_serialize_and_reindex(self, tmp_path: Path) -> None:
        from beadloom.application.reindex import (
            ReindexResult,
            _load_rules_into_db,
            _serialize_rule,
        )
        from beadloom.graph.rule_engine import load_rules

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: module-coverage\n"
            "    description: coverage\n"
            "    severity: warn\n"
            "    module_coverage:\n"
            "      source_root: src/beadloom/\n"
            "      min_symbols: 1\n"
            "      exempt:\n"
            "        - '**/__init__.py'\n"
        )
        rules = load_rules(rules_path)
        rule_type, rule_def = _serialize_rule(rules[0])
        assert rule_type == "module_coverage"
        assert rule_def["min_symbols"] == 1
        assert rule_def["exempt"] == ["**/__init__.py"]

        conn = sqlite3.connect(":memory:")
        try:
            create_schema(conn)
            result = ReindexResult()
            _load_rules_into_db(rules_path, conn, result)
            conn.commit()
            assert result.errors == []
            row = conn.execute(
                "SELECT rule_type FROM rules WHERE name = ?", ("module-coverage",)
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert row[0] == "module_coverage"
