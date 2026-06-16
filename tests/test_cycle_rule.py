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


# ---------------------------------------------------------------------------
# TestCycleGoldenParity (BDL-059 S3 / #124)
# ---------------------------------------------------------------------------


def _build_rich_cycle_graph(conn: sqlite3.Connection) -> None:
    """Insert a rich multi-cycle graph that exercises overlapping/nested cycles.

    Structure (edge kind ``uses`` unless noted):

    - Two-node cycle:        ``a <-> b``
    - Triangle:              ``c -> d -> e -> c``
    - Self-loop:             ``f -> f``
    - Shared-node figure-8:  ``g <-> h`` and ``h <-> i`` (``h`` in two cycles)
    - Diamond w/ two cycles: ``j -> k -> m -> j`` and ``j -> l -> m -> j``
      (distinct normalized cycles ``j,k,m`` and ``j,l,m``)
    - Non-live edge cycle:   ``p <-> q`` via a ``deprecated`` lifecycle edge
      (must NOT be reported — only ``active`` edges are live)
    - A different edge kind:  ``r -> s -> r`` via ``depends_on`` (filtered out by
      a ``uses``-only rule)
    """
    for ref in "abcdefghijklmpqrs":
        _insert_node(conn, ref)
    # a <-> b
    _insert_edge(conn, "a", "b", "uses")
    _insert_edge(conn, "b", "a", "uses")
    # c -> d -> e -> c
    _insert_edge(conn, "c", "d", "uses")
    _insert_edge(conn, "d", "e", "uses")
    _insert_edge(conn, "e", "c", "uses")
    # f -> f
    _insert_edge(conn, "f", "f", "uses")
    # g <-> h, h <-> i (shared node h)
    _insert_edge(conn, "g", "h", "uses")
    _insert_edge(conn, "h", "g", "uses")
    _insert_edge(conn, "h", "i", "uses")
    _insert_edge(conn, "i", "h", "uses")
    # j -> k -> m -> j ; j -> l -> m -> j (diamond, two distinct cycles)
    _insert_edge(conn, "j", "k", "uses")
    _insert_edge(conn, "k", "m", "uses")
    _insert_edge(conn, "m", "j", "uses")
    _insert_edge(conn, "j", "l", "uses")
    _insert_edge(conn, "l", "m", "uses")
    # p <-> q via deprecated lifecycle (not live)
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, lifecycle) VALUES (?, ?, ?, ?)",
        ("p", "q", "uses", "deprecated"),
    )
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, lifecycle) VALUES (?, ?, ?, ?)",
        ("q", "p", "uses", "deprecated"),
    )
    # r -> s -> r via depends_on
    _insert_edge(conn, "r", "s", "depends_on")
    _insert_edge(conn, "s", "r", "depends_on")
    conn.commit()


# Golden snapshot of the CURRENT evaluate_cycle_rules output on the rich graph,
# captured BEFORE the WHITE/GREY/BLACK rewrite (#124). The rewrite must
# reproduce these exact violations (fields + messages) — only the unique
# normalized cycle set, representative rotation, and ``max_depth`` are pinned;
# the deprecated ``p<->q`` edge and the ``depends_on`` ``r<->s`` cycle are
# correctly absent under a live, ``uses``-only rule.
_GOLDEN_RICH_CYCLES: list[tuple[str, str, str | None, str | None, str]] = [
    (
        "no-cycles",
        "cycle",
        "a",
        "b",
        "Circular dependency detected: a → b → a (rule 'no-cycles')",
    ),
    (
        "no-cycles",
        "cycle",
        "c",
        "e",
        "Circular dependency detected: c → d → e → c (rule 'no-cycles')",
    ),
    (
        "no-cycles",
        "cycle",
        "f",
        "f",
        "Circular dependency detected: f → f (rule 'no-cycles')",
    ),
    (
        "no-cycles",
        "cycle",
        "g",
        "h",
        "Circular dependency detected: g → h → g (rule 'no-cycles')",
    ),
    (
        "no-cycles",
        "cycle",
        "h",
        "i",
        "Circular dependency detected: h → i → h (rule 'no-cycles')",
    ),
    (
        "no-cycles",
        "cycle",
        "j",
        "m",
        "Circular dependency detected: j → k → m → j (rule 'no-cycles')",
    ),
    (
        "no-cycles",
        "cycle",
        "j",
        "m",
        "Circular dependency detected: j → l → m → j (rule 'no-cycles')",
    ),
]


class TestCycleGoldenParity:
    """Pin the exact cycle-detection output across the algorithm rewrite (#124)."""

    def test_rich_graph_golden_output(self, db_conn: sqlite3.Connection) -> None:
        _build_rich_cycle_graph(db_conn)
        rules = [
            CycleRule(
                name="no-cycles",
                description="No circular deps",
                edge_kind="uses",
            ),
        ]
        violations = evaluate_cycle_rules(db_conn, rules)
        actual = [
            (v.rule_name, v.rule_type, v.from_ref_id, v.to_ref_id, v.message)
            for v in violations
        ]
        # Compare as multisets: discovery order is an implementation detail, but
        # the exact set of representative violations must be reproduced.
        assert sorted(actual) == sorted(_GOLDEN_RICH_CYCLES)
        assert len(violations) == len(_GOLDEN_RICH_CYCLES)
        for v in violations:
            assert v.severity == "error"
            assert v.file_path is None
            assert v.line_number is None

    def test_max_depth_bounds_rewrite(self, db_conn: sqlite3.Connection) -> None:
        """The rewrite preserves max_depth: a deep cycle past the bound is unseen."""
        for ref in "ABCDE":
            _insert_node(db_conn, ref)
        # A -> B -> C -> D -> E -> A : a 5-cycle.
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "C", "uses")
        _insert_edge(db_conn, "C", "D", "uses")
        _insert_edge(db_conn, "D", "E", "uses")
        _insert_edge(db_conn, "E", "A", "uses")
        db_conn.commit()

        shallow = evaluate_cycle_rules(
            db_conn,
            [CycleRule(name="nc", description="d", edge_kind="uses", max_depth=3)],
        )
        assert shallow == []
        deep = evaluate_cycle_rules(
            db_conn,
            [CycleRule(name="nc", description="d", edge_kind="uses", max_depth=5)],
        )
        assert len(deep) == 1


# ---------------------------------------------------------------------------
# TestCycleTopologies (BDL-059 S3 / #124 — WHITE/GREY/BLACK rewrite coverage)
# ---------------------------------------------------------------------------


def _uses_rule(max_depth: int = 10) -> CycleRule:
    """A live, ``uses``-only forbid-cycles rule (the common shape in these tests)."""
    return CycleRule(
        name="no-cycles",
        description="No circular deps",
        edge_kind="uses",
        max_depth=max_depth,
    )


def _cycle_node_sets(violations: list) -> set[frozenset[str]]:  # type: ignore[type-arg]
    """Reduce each cycle message to the *set* of its nodes (rotation-invariant).

    A message is ``"Circular dependency detected: a → b → a (rule '...')"``. We
    extract the arrow-joined path and drop the duplicated closing node, so two
    rotations of the same cycle collapse to one entry. This lets a test assert
    *which* cycles were found without pinning the representative rotation.
    """
    out: set[frozenset[str]] = set()
    for v in violations:
        # message prefix up to the first ':' is boilerplate; the path follows.
        path_part = v.message.split(": ", 1)[1].split(" (rule", 1)[0]
        nodes = [n.strip() for n in path_part.split("→")]
        # drop the closing node (== the opening one for a real cycle)
        if len(nodes) > 1 and nodes[0] == nodes[-1]:
            nodes = nodes[:-1]
        out.add(frozenset(nodes))
    return out


class TestCycleTopologies:
    """Per-topology coverage of the WHITE/GREY/BLACK rewrite (#124).

    The golden parity test pins exact byte output on one combined graph; these
    isolate each topology so a regression points at the specific shape that
    broke (nested, self-loop, disjoint multi-cycle, deprecated-edge exclusion).
    """

    def test_nested_cycles_inner_and_outer_both_reported(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """A small cycle nested inside a larger one yields BOTH distinct cycles.

        Edges: A→B→C→A (outer triangle) plus a chord B→A (inner 2-cycle A↔B).
        The colored DFS must surface the inner {A,B} cycle and the outer
        {A,B,C} cycle as two separate normalized violations.
        """
        for ref in "ABC":
            _insert_node(db_conn, ref)
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "C", "uses")
        _insert_edge(db_conn, "C", "A", "uses")
        _insert_edge(db_conn, "B", "A", "uses")  # chord -> inner 2-cycle
        db_conn.commit()

        violations = evaluate_cycle_rules(db_conn, [_uses_rule()])
        node_sets = _cycle_node_sets(violations)
        assert frozenset({"A", "B"}) in node_sets
        assert frozenset({"A", "B", "C"}) in node_sets

    def test_self_loop_only_one_node_in_path(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """A→A is a length-1 cycle: exactly one violation over a single node."""
        _insert_node(db_conn, "solo")
        _insert_edge(db_conn, "solo", "solo", "uses")
        db_conn.commit()

        violations = evaluate_cycle_rules(db_conn, [_uses_rule()])
        assert len(violations) == 1
        assert violations[0].from_ref_id == "solo"
        assert violations[0].to_ref_id == "solo"
        assert _cycle_node_sets(violations) == {frozenset({"solo"})}

    def test_disjoint_multi_cycle_each_reported_once(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """Three disjoint cycles (a 2-cycle, a triangle, a self-loop) -> 3 violations.

        Disjoint components must each be discovered independently — the
        WHITE/GREY/BLACK sweep restarts from every still-WHITE node.
        """
        for ref in "ABCDEF":
            _insert_node(db_conn, ref)
        # A <-> B
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "B", "A", "uses")
        # C -> D -> E -> C
        _insert_edge(db_conn, "C", "D", "uses")
        _insert_edge(db_conn, "D", "E", "uses")
        _insert_edge(db_conn, "E", "C", "uses")
        # F -> F
        _insert_edge(db_conn, "F", "F", "uses")
        db_conn.commit()

        violations = evaluate_cycle_rules(db_conn, [_uses_rule()])
        assert len(violations) == 3
        assert _cycle_node_sets(violations) == {
            frozenset({"A", "B"}),
            frozenset({"C", "D", "E"}),
            frozenset({"F"}),
        }

    def test_deprecated_edge_cycle_excluded(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """A cycle formed only by a non-live (deprecated) edge is NOT reported.

        Only ``active`` lifecycle edges are live; a ``deprecated`` edge closing
        the loop means the cycle does not exist in the live graph.
        """
        _insert_node(db_conn, "x")
        _insert_node(db_conn, "y")
        _insert_edge(db_conn, "x", "y", "uses")  # live
        db_conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, lifecycle) "
            "VALUES (?, ?, ?, ?)",
            ("y", "x", "uses", "deprecated"),  # non-live closing edge
        )
        db_conn.commit()

        violations = evaluate_cycle_rules(db_conn, [_uses_rule()])
        assert violations == []

    def test_live_cycle_reported_alongside_excluded_deprecated_cycle(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """A live cycle is reported while a separate deprecated-only cycle is not.

        x↔y is a live 2-cycle; p↔q is closed only by a deprecated edge. The
        per-edge liveness filter must keep {x,y} and drop {p,q} — proving
        exclusion is scoped to the non-live edge, not a global suppression.
        """
        for ref in ("x", "y", "p", "q"):
            _insert_node(db_conn, ref)
        _insert_edge(db_conn, "x", "y", "uses")  # live
        _insert_edge(db_conn, "y", "x", "uses")  # live -> closes a live cycle
        _insert_edge(db_conn, "p", "q", "uses")  # live half
        db_conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, lifecycle) "
            "VALUES (?, ?, ?, ?)",
            ("q", "p", "uses", "deprecated"),  # non-live closing edge for p,q
        )
        db_conn.commit()

        violations = evaluate_cycle_rules(db_conn, [_uses_rule()])
        assert _cycle_node_sets(violations) == {frozenset({"x", "y"})}

    def test_shared_node_two_cycles_both_reported(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """A node shared by two cycles (figure-8) yields both, not a merged blob.

        g↔h and h↔i share node h; the rewrite must report {g,h} and {h,i}
        separately rather than collapsing them through the shared vertex.
        """
        for ref in "ghi":
            _insert_node(db_conn, ref)
        _insert_edge(db_conn, "g", "h", "uses")
        _insert_edge(db_conn, "h", "g", "uses")
        _insert_edge(db_conn, "h", "i", "uses")
        _insert_edge(db_conn, "i", "h", "uses")
        db_conn.commit()

        violations = evaluate_cycle_rules(db_conn, [_uses_rule()])
        assert _cycle_node_sets(violations) == {
            frozenset({"g", "h"}),
            frozenset({"h", "i"}),
        }

    def test_dag_with_diamond_no_false_cycle(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """A diamond DAG (two paths to a sink, no back-edge) reports no cycle.

        A→B→D and A→C→D re-converge at D but never loop back: a node reached on
        two forward paths (GREY-then-BLACK) must not be mistaken for a cycle.
        """
        for ref in "ABCD":
            _insert_node(db_conn, ref)
        _insert_edge(db_conn, "A", "B", "uses")
        _insert_edge(db_conn, "A", "C", "uses")
        _insert_edge(db_conn, "B", "D", "uses")
        _insert_edge(db_conn, "C", "D", "uses")
        db_conn.commit()

        assert evaluate_cycle_rules(db_conn, [_uses_rule()]) == []
