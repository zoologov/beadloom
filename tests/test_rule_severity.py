"""Tests for rule severity levels — BEAD-04 (beadloom-23t).

Tests cover:
- v1 rules default severity to "error"
- v2 rules with explicit severity
- evaluate_rules passes severity through Violation objects
- Linter format_rich includes severity markers
- --strict only fails on errors, --fail-on-warn fails on warnings
- Mixed error + warning output format
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    DenyRule,
    NodeMatcher,
    RequireRule,
    Violation,
    evaluate_all,
    evaluate_deny_rules,
    evaluate_require_rules,
    load_rules,
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
# TestV1RulesDefaultSeverity
# ---------------------------------------------------------------------------


class TestV1RulesDefaultSeverity:
    """v1 rules (version: 1) should default severity to 'error'."""

    def test_v1_deny_rule_defaults_to_error(self, tmp_path: Path) -> None:
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
        assert rule.severity == "error"

    def test_v1_require_rule_defaults_to_error(self, tmp_path: Path) -> None:
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
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.severity == "error"


# ---------------------------------------------------------------------------
# TestV2RulesExplicitSeverity
# ---------------------------------------------------------------------------


class TestV2RulesExplicitSeverity:
    """v2 rules (version: 2) support explicit severity field."""

    def test_v2_deny_rule_with_error_severity(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: test-rule\n"
            '    description: "Test deny rule"\n'
            "    severity: error\n"
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, DenyRule)
        assert rule.severity == "error"

    def test_v2_deny_rule_with_warn_severity(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: soft-boundary\n"
            '    description: "Soft cross-domain warning"\n'
            "    severity: warn\n"
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
        )
        rules = load_rules(rules_path)
        rule = rules[0]
        assert isinstance(rule, DenyRule)
        assert rule.severity == "warn"

    def test_v2_require_rule_with_warn_severity(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: svc-domain-soft\n"
            '    description: "Soft requirement"\n'
            "    severity: warn\n"
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
        )
        rules = load_rules(rules_path)
        rule = rules[0]
        assert isinstance(rule, RequireRule)
        assert rule.severity == "warn"

    def test_v2_rule_without_severity_defaults_to_error(self, tmp_path: Path) -> None:
        """v2 rule without severity field defaults to 'error'."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: test-rule\n"
            '    description: "No severity"\n'
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
        )
        rules = load_rules(rules_path)
        rule = rules[0]
        assert isinstance(rule, DenyRule)
        assert rule.severity == "error"

    def test_v2_invalid_severity_raises(self, tmp_path: Path) -> None:
        """v2 rule with invalid severity raises ValueError."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: test-rule\n"
            '    description: "Bad severity"\n'
            "    severity: critical\n"
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
        )
        with pytest.raises(ValueError, match="severity"):
            load_rules(rules_path)

    def test_v2_mixed_severity_rules(self, tmp_path: Path) -> None:
        """Multiple rules with different severities parse correctly."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: hard-boundary\n"
            '    description: "Hard error"\n'
            "    severity: error\n"
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
            "  - name: soft-check\n"
            '    description: "Soft warning"\n'
            "    severity: warn\n"
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 2
        assert rules[0].severity == "error"
        assert rules[1].severity == "warn"


# ---------------------------------------------------------------------------
# TestEvaluateRulesSeverity
# ---------------------------------------------------------------------------


class TestEvaluateRulesSeverity:
    """evaluate_rules passes severity through to Violation objects."""

    def test_deny_violation_has_severity(self, db_with_data: sqlite3.Connection) -> None:
        """Deny violation includes severity from the rule."""
        rules = [
            DenyRule(
                name="billing-auth-boundary",
                description="Billing must not import from auth",
                severity="warn",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=(),
            ),
        ]
        violations = evaluate_deny_rules(db_with_data, rules)
        assert len(violations) == 1
        assert violations[0].severity == "warn"

    def test_require_violation_has_severity(self, db_with_data: sqlite3.Connection) -> None:
        """Require violation includes severity from the rule."""
        rules = [
            RequireRule(
                name="svc-needs-domain",
                description="Every service must be part of a domain",
                severity="warn",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(kind="domain"),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_require_rules(db_with_data, rules)
        assert len(violations) >= 1
        assert all(v.severity == "warn" for v in violations)

    def test_evaluate_all_mixed_severities(self, db_with_data: sqlite3.Connection) -> None:
        """evaluate_all preserves different severities across violations."""
        rules: list[DenyRule | RequireRule] = [
            DenyRule(
                name="billing-auth-boundary",
                description="Hard boundary",
                severity="error",
                from_matcher=NodeMatcher(ref_id="billing"),
                to_matcher=NodeMatcher(ref_id="auth"),
                unless_edge=(),
            ),
            RequireRule(
                name="svc-needs-domain",
                description="Soft requirement",
                severity="warn",
                for_matcher=NodeMatcher(kind="service"),
                has_edge_to=NodeMatcher(kind="domain"),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_all(db_with_data, rules)
        assert len(violations) >= 2
        severities = {v.severity for v in violations}
        assert "error" in severities
        assert "warn" in severities

    def test_violation_dataclass_has_severity_field(self) -> None:
        """Violation dataclass includes severity field."""
        v = Violation(
            rule_name="test",
            rule_description="Test",
            rule_type="deny",
            severity="warn",
            file_path="test.py",
            line_number=1,
            from_ref_id="a",
            to_ref_id="b",
            message="Test violation",
        )
        assert v.severity == "warn"


# ---------------------------------------------------------------------------
# TestLinterFormatSeverity
# ---------------------------------------------------------------------------


class TestLinterFormatSeverity:
    """Linter formatters include severity in output."""

    def test_format_rich_includes_severity_markers(self) -> None:
        """format_rich shows severity markers for errors and warnings."""
        from beadloom.graph.linter import LintResult, format_rich

        result = LintResult(
            violations=[
                Violation(
                    rule_name="hard-boundary",
                    rule_description="Hard error",
                    rule_type="deny",
                    severity="error",
                    file_path="src/a.py",
                    line_number=10,
                    from_ref_id="a",
                    to_ref_id="b",
                    message="Violation message",
                ),
                Violation(
                    rule_name="soft-check",
                    rule_description="Soft warning",
                    rule_type="require",
                    severity="warn",
                    file_path=None,
                    line_number=None,
                    from_ref_id="c",
                    to_ref_id=None,
                    message="Warning message",
                ),
            ],
            rules_evaluated=2,
        )
        output = format_rich(result)
        assert "[ERROR]" in output
        assert "[WARN]" in output

    def test_format_rich_summary_includes_counts(self) -> None:
        """format_rich summary line includes error and warning counts."""
        from beadloom.graph.linter import LintResult, format_rich

        result = LintResult(
            violations=[
                Violation(
                    rule_name="err-rule",
                    rule_description="Error",
                    rule_type="deny",
                    severity="error",
                    file_path="a.py",
                    line_number=1,
                    from_ref_id="a",
                    to_ref_id="b",
                    message="err",
                ),
                Violation(
                    rule_name="warn-rule",
                    rule_description="Warning",
                    rule_type="require",
                    severity="warn",
                    file_path=None,
                    line_number=None,
                    from_ref_id="c",
                    to_ref_id=None,
                    message="warn",
                ),
            ],
            rules_evaluated=2,
        )
        output = format_rich(result)
        assert "Errors: 1" in output
        assert "Warnings: 1" in output

    def test_format_json_includes_severity(self) -> None:
        """format_json includes severity in violation objects."""
        from beadloom.graph.linter import LintResult, format_json

        result = LintResult(
            violations=[
                Violation(
                    rule_name="test",
                    rule_description="Test",
                    rule_type="deny",
                    severity="warn",
                    file_path="a.py",
                    line_number=1,
                    from_ref_id="a",
                    to_ref_id="b",
                    message="msg",
                ),
            ],
            rules_evaluated=1,
        )
        output = format_json(result)
        parsed = json.loads(output)
        assert parsed["violations"][0]["severity"] == "warn"
        assert "error_count" in parsed["summary"]
        assert "warning_count" in parsed["summary"]

    def test_format_porcelain_includes_severity(self) -> None:
        """format_porcelain includes severity in output lines."""
        from beadloom.graph.linter import LintResult, format_porcelain

        result = LintResult(
            violations=[
                Violation(
                    rule_name="test",
                    rule_description="Test",
                    rule_type="deny",
                    severity="warn",
                    file_path="a.py",
                    line_number=1,
                    from_ref_id="a",
                    to_ref_id="b",
                    message="msg",
                ),
            ],
            rules_evaluated=1,
        )
        output = format_porcelain(result)
        assert "warn" in output


# ---------------------------------------------------------------------------
# TestStrictAndFailOnWarn
# ---------------------------------------------------------------------------


class TestStrictAndFailOnWarn:
    """Test --strict and --fail-on-warn CLI behavior via LintResult helpers."""

    def test_has_errors_true_when_errors_exist(self) -> None:
        from beadloom.graph.linter import LintResult

        result = LintResult(
            violations=[
                Violation(
                    rule_name="test",
                    rule_description="Test",
                    rule_type="deny",
                    severity="error",
                    file_path="a.py",
                    line_number=1,
                    from_ref_id="a",
                    to_ref_id="b",
                    message="msg",
                ),
            ],
            rules_evaluated=1,
        )
        assert result.has_errors is True

    def test_has_errors_false_when_only_warnings(self) -> None:
        from beadloom.graph.linter import LintResult

        result = LintResult(
            violations=[
                Violation(
                    rule_name="test",
                    rule_description="Test",
                    rule_type="require",
                    severity="warn",
                    file_path=None,
                    line_number=None,
                    from_ref_id="a",
                    to_ref_id=None,
                    message="msg",
                ),
            ],
            rules_evaluated=1,
        )
        assert result.has_errors is False

    def test_error_count_and_warning_count(self) -> None:
        from beadloom.graph.linter import LintResult

        result = LintResult(
            violations=[
                Violation(
                    rule_name="err",
                    rule_description="Error",
                    rule_type="deny",
                    severity="error",
                    file_path="a.py",
                    line_number=1,
                    from_ref_id="a",
                    to_ref_id="b",
                    message="err",
                ),
                Violation(
                    rule_name="warn1",
                    rule_description="Warn 1",
                    rule_type="require",
                    severity="warn",
                    file_path=None,
                    line_number=None,
                    from_ref_id="c",
                    to_ref_id=None,
                    message="warn",
                ),
                Violation(
                    rule_name="warn2",
                    rule_description="Warn 2",
                    rule_type="require",
                    severity="warn",
                    file_path=None,
                    line_number=None,
                    from_ref_id="d",
                    to_ref_id=None,
                    message="warn",
                ),
            ],
            rules_evaluated=3,
        )
        assert result.error_count == 1
        assert result.warning_count == 2
