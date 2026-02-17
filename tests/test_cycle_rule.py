"""Tests for CycleRule — circular dependency detection in rule_engine.

Tests cover:
- CycleRule dataclass creation
- Simple cycle detection (A → B → A)
- Triangle cycle detection (A → B → C → A)
- No cycle (acyclic graph)
- max_depth limit respected
- Deep cycle detection (near max_depth)
- Multiple edge_kind filtering
- Cycle path normalization (no duplicates)
- YAML parsing for forbid_cycles rule type
- Integration with evaluate_all()
- Self-loop detection (A → A)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    CycleRule,
    Violation,
    evaluate_all,
    evaluate_cycle_rules,
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


def _insert_node(conn: sqlite3.Connection, ref_id: str, kind: str = "domain") -> None:
    """Helper to insert a node."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        (ref_id, kind, f"{ref_id} node"),
    )


def _insert_edge(
    conn: sqlite3.Connection, src: str, dst: str, kind: str = "uses"
) -> None:
    """Helper to insert an edge."""
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src, dst, kind),
    )


# ---------------------------------------------------------------------------
# TestCycleRuleDataclass
# ---------------------------------------------------------------------------


class TestCycleRuleDataclass:
    """Tests for CycleRule dataclass creation and defaults."""

    def test_create_with_defaults(self) -> None:
        rule = CycleRule(
            name="no-cycles",
            description="No circular dependencies",
            edge_kind="uses",
        )
        assert rule.name == "no-cycles"
        assert rule.description == "No circular dependencies"
        assert rule.edge_kind == "uses"
        assert rule.max_depth == 10
        assert rule.severity == "error"

    def test_create_with_custom_values(self) -> None:
        rule = CycleRule(
            name="no-cycles",
            description="No circular deps",
            edge_kind=("uses", "depends_on"),
            max_depth=5,
            severity="warn",
        )
        assert rule.edge_kind == ("uses", "depends_on")
        assert rule.max_depth == 5
        assert rule.severity == "warn"

    def test_frozen(self) -> None:
        rule = CycleRule(
            name="no-cycles",
            description="No circular deps",
            edge_kind="uses",
        )
        with pytest.raises(AttributeError):
            rule.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestEvaluateCycleRulesSimpleCycle
# ---------------------------------------------------------------------------


class TestEvaluateCycleRulesSimpleCycle:
    """Tests for simple cycle detection (A → B → A)."""

    def test_simple_cycle_detected(self, db_conn: sqlite3.Connection) -> None:
        """A → B → A should produce one cycle violation."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "A", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_name == "no-cycles"
        assert v.rule_type == "cycle"
        assert v.severity == "error"
        # The message should contain the cycle path with arrow notation
        assert "\u2192" in v.message  # → arrow
        # Both nodes should appear in the message
        assert "A" in v.message
        assert "B" in v.message

    def test_self_loop_detected(self, db_conn: sqlite3.Connection) -> None:
        """A → A should be detected as a cycle."""
        _insert_node(db_conn, "A")
        _insert_edge(db_conn, "A", "A", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-self-loops",
                description="No self-referencing",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 1
        assert "A" in violations[0].message


# ---------------------------------------------------------------------------
# TestEvaluateCycleRulesTriangle
# ---------------------------------------------------------------------------


class TestEvaluateCycleRulesTriangle:
    """Tests for triangle cycle detection (A → B → C → A)."""

    def test_triangle_cycle_detected(self, db_conn: sqlite3.Connection) -> None:
        """A → B → C → A should produce one cycle violation with full path."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_node(db_conn, "C")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "C", "uses")
        _insert_edge(db_conn, "C", "A", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 1
        msg = violations[0].message
        # All three nodes in the path
        assert "A" in msg
        assert "B" in msg
        assert "C" in msg


# ---------------------------------------------------------------------------
# TestEvaluateCycleRulesNoCycle
# ---------------------------------------------------------------------------


class TestEvaluateCycleRulesNoCycle:
    """Tests for acyclic graphs — no violations."""

    def test_no_cycle_linear(self, db_conn: sqlite3.Connection) -> None:
        """A → B → C (no cycle) produces no violations."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_node(db_conn, "C")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "C", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 0

    def test_no_edges_no_violations(self, db_conn: sqlite3.Connection) -> None:
        """Empty edges table produces no violations."""
        _insert_node(db_conn, "A")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 0

    def test_empty_rules_no_violations(self, db_conn: sqlite3.Connection) -> None:
        """Empty rules list produces no violations."""
        violations = evaluate_cycle_rules(db_conn, [])
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# TestEvaluateCycleRulesMaxDepth
# ---------------------------------------------------------------------------


class TestEvaluateCycleRulesMaxDepth:
    """Tests for max_depth limit in cycle detection."""

    def test_max_depth_prevents_deep_cycle_detection(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """Cycle at depth 5 should NOT be detected with max_depth=3."""
        # Build chain: N0 → N1 → N2 → N3 → N4 → N0 (cycle at depth 5)
        for i in range(5):
            _insert_node(db_conn, f"N{i}")
        for i in range(4):
            _insert_edge(db_conn, f"N{i}", f"N{i+1}", "uses")
        _insert_edge(db_conn, "N4", "N0", "uses")  # close the cycle
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
                max_depth=3,
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 0

    def test_max_depth_allows_shallow_cycle_detection(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """Cycle at depth 2 should be detected with max_depth=3."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "A", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
                max_depth=3,
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 1

    def test_deep_cycle_at_max_depth_boundary(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """Cycle at exactly max_depth should be detected."""
        # Build chain: N0 → N1 → N2 → N0 (cycle at depth 3)
        for i in range(3):
            _insert_node(db_conn, f"N{i}")
        for i in range(2):
            _insert_edge(db_conn, f"N{i}", f"N{i+1}", "uses")
        _insert_edge(db_conn, "N2", "N0", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
                max_depth=3,
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# TestEvaluateCycleRulesEdgeKind
# ---------------------------------------------------------------------------


class TestEvaluateCycleRulesEdgeKind:
    """Tests for edge_kind filtering in cycle detection."""

    def test_edge_kind_filter_single(self, db_conn: sqlite3.Connection) -> None:
        """Cycle in 'depends_on' edges should NOT be detected when rule checks 'uses'."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_edge(db_conn, "A", "B", "depends_on")
        _insert_edge(db_conn, "B", "A", "depends_on")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-uses-cycles",
                description="No circular uses",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 0

    def test_edge_kind_filter_tuple(self, db_conn: sqlite3.Connection) -> None:
        """Cycle across mixed edge kinds should be detected when both kinds are specified."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "A", "depends_on")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps via uses or depends_on",
                edge_kind=("uses", "depends_on"),
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# TestCycleNormalization
# ---------------------------------------------------------------------------


class TestCycleNormalization:
    """Tests for cycle path normalization to avoid duplicate reports."""

    def test_same_cycle_reported_once(self, db_conn: sqlite3.Connection) -> None:
        """A → B → C → A is the same as B → C → A → B — report only once."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_node(db_conn, "C")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "C", "uses")
        _insert_edge(db_conn, "C", "A", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        # Only one violation for the single cycle, not three
        assert len(violations) == 1

    def test_two_distinct_cycles_reported_separately(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """Two separate cycles should produce two violations."""
        # Cycle 1: A → B → A
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "A", "uses")
        # Cycle 2: C → D → C
        _insert_node(db_conn, "C")
        _insert_node(db_conn, "D")
        _insert_edge(db_conn, "C", "D", "uses")
        _insert_edge(db_conn, "D", "C", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 2


# ---------------------------------------------------------------------------
# TestCycleRuleYamlParsing
# ---------------------------------------------------------------------------


class TestCycleRuleYamlParsing:
    """Tests for YAML parsing of forbid_cycles rule type."""

    def test_parse_forbid_cycles_rule(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: no-circular-deps\n"
            '    description: "No circular dependencies allowed"\n'
            "    forbid_cycles:\n"
            "      edge_kind: uses\n"
            "      max_depth: 10\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, CycleRule)
        assert rule.name == "no-circular-deps"
        assert rule.description == "No circular dependencies allowed"
        assert rule.edge_kind == "uses"
        assert rule.max_depth == 10

    def test_parse_forbid_cycles_with_tuple_edge_kind(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: no-circular-deps\n"
            '    description: "No circular deps"\n'
            "    forbid_cycles:\n"
            "      edge_kind:\n"
            "        - uses\n"
            "        - depends_on\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, CycleRule)
        assert rule.edge_kind == ("uses", "depends_on")

    def test_parse_forbid_cycles_default_max_depth(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: no-circular-deps\n"
            '    description: "No circular deps"\n'
            "    forbid_cycles:\n"
            "      edge_kind: uses\n"
        )
        rules = load_rules(rules_path)
        rule = rules[0]
        assert isinstance(rule, CycleRule)
        assert rule.max_depth == 10  # default

    def test_parse_forbid_cycles_with_severity(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: no-circular-deps\n"
            '    description: "Soft cycle warning"\n'
            "    severity: warn\n"
            "    forbid_cycles:\n"
            "      edge_kind: uses\n"
        )
        rules = load_rules(rules_path)
        rule = rules[0]
        assert isinstance(rule, CycleRule)
        assert rule.severity == "warn"

    def test_parse_forbid_cycles_missing_edge_kind_raises(
        self, tmp_path: Path
    ) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: no-circular-deps\n"
            '    description: "Missing edge_kind"\n'
            "    forbid_cycles:\n"
            "      max_depth: 5\n"
        )
        with pytest.raises(ValueError, match="edge_kind"):
            load_rules(rules_path)

    def test_parse_forbid_cycles_invalid_edge_kind_raises(
        self, tmp_path: Path
    ) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: no-circular-deps\n"
            '    description: "Invalid edge"\n'
            "    forbid_cycles:\n"
            "      edge_kind: invalid_edge\n"
        )
        with pytest.raises(ValueError, match="edge"):
            load_rules(rules_path)

    def test_parse_mixed_rule_types(self, tmp_path: Path) -> None:
        """forbid_cycles can coexist with deny and require rules."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: deny-rule\n"
            '    description: "Deny"\n'
            "    deny:\n"
            "      from: { ref_id: billing }\n"
            "      to: { ref_id: auth }\n"
            "  - name: no-cycles\n"
            '    description: "No cycles"\n'
            "    forbid_cycles:\n"
            "      edge_kind: uses\n"
            "  - name: require-rule\n"
            '    description: "Require"\n'
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
        )
        rules = load_rules(rules_path)
        assert len(rules) == 3
        from beadloom.graph.rule_engine import DenyRule, RequireRule

        assert isinstance(rules[0], DenyRule)
        assert isinstance(rules[1], CycleRule)
        assert isinstance(rules[2], RequireRule)


# ---------------------------------------------------------------------------
# TestEvaluateAllWithCycleRules
# ---------------------------------------------------------------------------


class TestEvaluateAllWithCycleRules:
    """Tests for integration of CycleRule with evaluate_all()."""

    def test_evaluate_all_includes_cycle_violations(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """evaluate_all() should detect cycle violations."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "A", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_all(db_conn, rules)
        assert len(violations) == 1
        assert violations[0].rule_type == "cycle"

    def test_evaluate_all_mixed_rule_types(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """evaluate_all() handles deny + require + cycle rules together."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "A", "uses")
        db_conn.commit()

        from beadloom.graph.rule_engine import DenyRule, NodeMatcher, RequireRule

        rules: list[DenyRule | RequireRule | CycleRule] = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
            RequireRule(
                name="needs-domain",
                description="Every domain needs part_of",
                for_matcher=NodeMatcher(kind="domain"),
                has_edge_to=NodeMatcher(),
                edge_kind="part_of",
            ),
        ]
        violations = evaluate_all(db_conn, rules)
        # Should have cycle violations + require violations
        rule_types = {v.rule_type for v in violations}
        assert "cycle" in rule_types
        assert "require" in rule_types


# ---------------------------------------------------------------------------
# TestCycleRuleViolationMessage
# ---------------------------------------------------------------------------


class TestCycleRuleViolationMessage:
    """Tests for cycle violation message format."""

    def test_violation_message_contains_full_path(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """Message should contain the full cycle path with arrows."""
        _insert_node(db_conn, "alpha")
        _insert_node(db_conn, "beta")
        _insert_node(db_conn, "gamma")
        _insert_edge(db_conn, "alpha", "beta", "uses")
        _insert_edge(db_conn, "beta", "gamma", "uses")
        _insert_edge(db_conn, "gamma", "alpha", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 1
        msg = violations[0].message
        # Should contain arrow-separated path ending back at start
        assert "\u2192" in msg  # → arrow
        # All three nodes in the path
        assert "alpha" in msg
        assert "beta" in msg
        assert "gamma" in msg

    def test_violation_fields(self, db_conn: sqlite3.Connection) -> None:
        """Cycle violation should have correct field values."""
        _insert_node(db_conn, "A")
        _insert_node(db_conn, "B")
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "A", "uses")
        db_conn.commit()

        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
                severity="warn",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_name == "no-cycles"
        assert v.rule_description == "No circular deps"
        assert v.rule_type == "cycle"
        assert v.severity == "warn"
        assert v.file_path is None  # cycles are graph-level, no file
        assert v.line_number is None
