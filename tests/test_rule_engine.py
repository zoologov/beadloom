"""Tests for beadloom.rule_engine — Architecture rule parsing, validation, and evaluation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    DenyRule,
    NodeMatcher,
    RequireRule,
    evaluate_all,
    evaluate_deny_rules,
    evaluate_require_rules,
    load_rules,
    validate_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

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
