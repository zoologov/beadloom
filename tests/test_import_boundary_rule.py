"""Tests for ImportBoundaryRule — BEAD-05 (beadloom-j9e.5).

Tests cover:
- ImportBoundaryRule dataclass creation and frozen properties
- evaluate_import_boundary_rules() — glob matching via fnmatch
- YAML parsing for forbid_import: rule type
- Integration with evaluate_all()
- Violations include source file, line number, and import target
- Edge cases: non-matching globs, empty imports table, overlapping globs
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    DenyRule,
    ImportBoundaryRule,
    NodeMatcher,
    RequireRule,
    evaluate_all,
    evaluate_import_boundary_rules,
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
def db_with_imports(tmp_path: Path) -> sqlite3.Connection:
    """Provide a database pre-populated with code_imports for boundary testing."""
    db_path = tmp_path / "test.db"
    conn = open_db(db_path)
    create_schema(conn)

    # Import: map feature imports from calendar feature
    conn.execute(
        "INSERT INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            "components/features/map/renderer.py",
            5,
            "components.features.calendar.events",
            None,
            "hash1",
        ),
    )

    # Import: map feature imports from shared utils (allowed)
    conn.execute(
        "INSERT INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            "components/features/map/renderer.py",
            7,
            "components.shared.utils",
            None,
            "hash1",
        ),
    )

    # Import: calendar feature imports from map feature (reverse direction)
    conn.execute(
        "INSERT INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            "components/features/calendar/views.py",
            10,
            "components.features.map.tiles",
            None,
            "hash2",
        ),
    )

    # Import: auth imports from billing (for multi-rule testing)
    conn.execute(
        "INSERT INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            "services/auth/handler.py",
            3,
            "services.billing.invoice",
            None,
            "hash3",
        ),
    )

    conn.commit()
    yield conn  # type: ignore[misc]
    conn.close()


# ---------------------------------------------------------------------------
# TestImportBoundaryRuleDataclass
# ---------------------------------------------------------------------------


class TestImportBoundaryRuleDataclass:
    """Tests for ImportBoundaryRule dataclass."""

    def test_create_with_required_fields(self) -> None:
        rule = ImportBoundaryRule(
            name="no-cross-feature",
            description="Features must not import from each other",
            from_glob="components/features/map/**",
            to_glob="components/features/calendar/**",
        )
        assert rule.name == "no-cross-feature"
        assert rule.description == "Features must not import from each other"
        assert rule.from_glob == "components/features/map/**"
        assert rule.to_glob == "components/features/calendar/**"
        assert rule.severity == "error"  # default

    def test_create_with_custom_severity(self) -> None:
        rule = ImportBoundaryRule(
            name="soft-boundary",
            description="Soft warning",
            from_glob="a/**",
            to_glob="b/**",
            severity="warn",
        )
        assert rule.severity == "warn"

    def test_frozen(self) -> None:
        """ImportBoundaryRule is frozen (immutable)."""
        rule = ImportBoundaryRule(
            name="test",
            description="Test",
            from_glob="a/**",
            to_glob="b/**",
        )
        with pytest.raises(AttributeError):
            rule.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestEvaluateImportBoundaryRules
# ---------------------------------------------------------------------------


class TestEvaluateImportBoundaryRules:
    """Tests for evaluate_import_boundary_rules()."""

    def test_violation_detected_matching_globs(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """Import from map->calendar matches both from_glob and to_glob."""
        rules = [
            ImportBoundaryRule(
                name="no-map-to-calendar",
                description="Map must not import from Calendar",
                from_glob="components/features/map/**",
                to_glob="components/features/calendar/**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_name == "no-map-to-calendar"
        assert v.rule_type == "forbid_import"
        assert v.severity == "error"
        assert v.file_path == "components/features/map/renderer.py"
        assert v.line_number == 5
        assert v.from_ref_id is None  # not node-based
        assert "components.features.calendar.events" in v.message

    def test_no_violation_when_from_glob_does_not_match(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """Rule's from_glob doesn't match any source files -> no violations."""
        rules = [
            ImportBoundaryRule(
                name="no-admin-to-calendar",
                description="Admin must not import from Calendar",
                from_glob="components/features/admin/**",
                to_glob="components/features/calendar/**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        assert len(violations) == 0

    def test_no_violation_when_to_glob_does_not_match(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """Rule's to_glob doesn't match import target -> no violations."""
        rules = [
            ImportBoundaryRule(
                name="no-map-to-admin",
                description="Map must not import from Admin",
                from_glob="components/features/map/**",
                to_glob="components/features/admin/**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        assert len(violations) == 0

    def test_empty_imports_table_no_violations(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """Empty code_imports table produces zero violations."""
        rules = [
            ImportBoundaryRule(
                name="any-rule",
                description="Any rule",
                from_glob="**",
                to_glob="**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_conn, rules)
        assert len(violations) == 0

    def test_empty_rules_list(self, db_with_imports: sqlite3.Connection) -> None:
        """Empty rules list produces zero violations."""
        violations = evaluate_import_boundary_rules(db_with_imports, [])
        assert len(violations) == 0

    def test_multiple_rules_multiple_violations(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """Multiple rules can each generate violations."""
        rules = [
            ImportBoundaryRule(
                name="no-map-to-calendar",
                description="Map must not import from Calendar",
                from_glob="components/features/map/**",
                to_glob="components/features/calendar/**",
            ),
            ImportBoundaryRule(
                name="no-calendar-to-map",
                description="Calendar must not import from Map",
                from_glob="components/features/calendar/**",
                to_glob="components/features/map/**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        assert len(violations) == 2
        rule_names = {v.rule_name for v in violations}
        assert "no-map-to-calendar" in rule_names
        assert "no-calendar-to-map" in rule_names

    def test_import_path_converted_to_file_path_for_matching(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """import_path dots are converted to slashes for glob matching."""
        # The import_path "components.features.calendar.events" should match
        # to_glob "components/features/calendar/**" after dot-to-slash conversion
        rules = [
            ImportBoundaryRule(
                name="test-conversion",
                description="Test dot-to-slash conversion",
                from_glob="components/features/map/**",
                to_glob="components/features/calendar/**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        assert len(violations) == 1

    def test_violation_severity_propagated(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """Violation severity matches the rule severity."""
        rules = [
            ImportBoundaryRule(
                name="soft-boundary",
                description="Soft warning",
                from_glob="components/features/map/**",
                to_glob="components/features/calendar/**",
                severity="warn",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        assert len(violations) == 1
        assert violations[0].severity == "warn"

    def test_violation_message_includes_target(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """Violation message includes the import target for debugging."""
        rules = [
            ImportBoundaryRule(
                name="no-map-to-calendar",
                description="Map must not import from Calendar",
                from_glob="components/features/map/**",
                to_glob="components/features/calendar/**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        assert len(violations) == 1
        assert "components.features.calendar.events" in violations[0].message
        assert "components/features/map/renderer.py" in violations[0].message

    def test_wildcard_from_glob(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """Wildcard from_glob ** matches all source files."""
        rules = [
            ImportBoundaryRule(
                name="no-calendar-imports",
                description="Nobody should import from Calendar",
                from_glob="**",
                to_glob="components/features/calendar/**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        # Only map->calendar import matches to_glob
        assert len(violations) == 1
        assert violations[0].file_path == "components/features/map/renderer.py"

    def test_services_boundary(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """Test glob matching with services directory pattern."""
        rules = [
            ImportBoundaryRule(
                name="no-auth-to-billing",
                description="Auth must not import from billing",
                from_glob="services/auth/**",
                to_glob="services/billing/**",
            ),
        ]
        violations = evaluate_import_boundary_rules(db_with_imports, rules)
        assert len(violations) == 1
        assert violations[0].file_path == "services/auth/handler.py"
        assert violations[0].line_number == 3


# ---------------------------------------------------------------------------
# TestImportBoundaryYAMLParsing
# ---------------------------------------------------------------------------


class TestImportBoundaryYAMLParsing:
    """Tests for YAML parsing of forbid_import: rule type."""

    def test_parse_forbid_import_rule(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: no-cross-feature-imports\n"
            "    forbid_import:\n"
            '      from: "components/features/map/**"\n'
            '      to: "components/features/calendar/**"\n'
            '    description: "Map feature must not import from Calendar"\n'
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, ImportBoundaryRule)
        assert rule.name == "no-cross-feature-imports"
        assert rule.description == "Map feature must not import from Calendar"
        assert rule.from_glob == "components/features/map/**"
        assert rule.to_glob == "components/features/calendar/**"
        assert rule.severity == "error"

    def test_parse_forbid_import_with_severity(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: soft-boundary\n"
            "    severity: warn\n"
            "    forbid_import:\n"
            '      from: "a/**"\n'
            '      to: "b/**"\n'
            '    description: "Soft warning"\n'
        )
        rules = load_rules(rules_path)
        assert len(rules) == 1
        rule = rules[0]
        assert isinstance(rule, ImportBoundaryRule)
        assert rule.severity == "warn"

    def test_parse_forbid_import_missing_from(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: bad-rule\n"
            "    forbid_import:\n"
            '      to: "b/**"\n'
            '    description: "Missing from"\n'
        )
        with pytest.raises(ValueError, match="from"):
            load_rules(rules_path)

    def test_parse_forbid_import_missing_to(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: bad-rule\n"
            "    forbid_import:\n"
            '      from: "a/**"\n'
            '    description: "Missing to"\n'
        )
        with pytest.raises(ValueError, match="to"):
            load_rules(rules_path)

    def test_parse_forbid_import_not_a_mapping(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: bad-rule\n"
            "    forbid_import: not-a-mapping\n"
            '    description: "Bad format"\n'
        )
        with pytest.raises(ValueError, match="mapping"):
            load_rules(rules_path)

    def test_mixed_rule_types(self, tmp_path: Path) -> None:
        """Parse YAML with deny, require, and forbid_import rules."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
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
            "  - name: forbid-import-rule\n"
            '    description: "Forbid import"\n'
            "    forbid_import:\n"
            '      from: "a/**"\n'
            '      to: "b/**"\n'
        )
        rules = load_rules(rules_path)
        assert len(rules) == 3
        assert isinstance(rules[0], DenyRule)
        assert isinstance(rules[1], RequireRule)
        assert isinstance(rules[2], ImportBoundaryRule)

    def test_forbid_import_with_deny_raises(self, tmp_path: Path) -> None:
        """Rule with both forbid_import and deny is invalid."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 2\n"
            "rules:\n"
            "  - name: double-rule\n"
            '    description: "Both types"\n'
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
            "    forbid_import:\n"
            '      from: "a/**"\n'
            '      to: "b/**"\n'
        )
        with pytest.raises(ValueError, match="exactly one"):
            load_rules(rules_path)


# ---------------------------------------------------------------------------
# TestEvaluateAllWithImportBoundary
# ---------------------------------------------------------------------------


class TestEvaluateAllWithImportBoundary:
    """Tests for evaluate_all() integration with ImportBoundaryRule."""

    def test_evaluate_all_includes_import_boundary_violations(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """evaluate_all() processes ImportBoundaryRule alongside other rule types."""
        rules: list[DenyRule | RequireRule | ImportBoundaryRule] = [
            ImportBoundaryRule(
                name="no-map-to-calendar",
                description="Map must not import from Calendar",
                from_glob="components/features/map/**",
                to_glob="components/features/calendar/**",
            ),
        ]
        violations = evaluate_all(db_with_imports, rules)
        assert len(violations) == 1
        assert violations[0].rule_name == "no-map-to-calendar"
        assert violations[0].rule_type == "forbid_import"

    def test_evaluate_all_mixed_with_import_boundary(
        self, tmp_path: Path,
    ) -> None:
        """evaluate_all() handles mix of DenyRule, RequireRule, and ImportBoundaryRule."""
        db_path = tmp_path / "test.db"
        conn = open_db(db_path)
        create_schema(conn)

        # Add nodes for deny/require rules
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("billing", "domain", "Billing"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("auth", "domain", "Auth"),
        )

        # Add import for import boundary rule
        conn.execute(
            "INSERT INTO code_imports"
            " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
            " VALUES (?, ?, ?, ?, ?)",
            ("a/b.py", 1, "c.d", None, "hash1"),
        )
        conn.commit()

        rules: list[DenyRule | RequireRule | ImportBoundaryRule] = [
            RequireRule(
                name="domain-needs-edge",
                description="Domain must have edge",
                for_matcher=NodeMatcher(kind="domain"),
                has_edge_to=NodeMatcher(),
            ),
            ImportBoundaryRule(
                name="no-a-to-c",
                description="A must not import from C",
                from_glob="a/**",
                to_glob="c/**",
            ),
        ]
        violations = evaluate_all(conn, rules)
        # 2 require violations (billing + auth have no edges) + 1 import boundary
        assert len(violations) == 3
        rule_types = {v.rule_type for v in violations}
        assert "require" in rule_types
        assert "forbid_import" in rule_types
        conn.close()

    def test_evaluate_all_sorted_output(
        self, db_with_imports: sqlite3.Connection
    ) -> None:
        """evaluate_all() returns sorted violations (by rule_name, file_path)."""
        rules: list[DenyRule | RequireRule | ImportBoundaryRule] = [
            ImportBoundaryRule(
                name="z-last-rule",
                description="Should be last",
                from_glob="components/features/map/**",
                to_glob="components/features/calendar/**",
            ),
            ImportBoundaryRule(
                name="a-first-rule",
                description="Should be first",
                from_glob="components/features/calendar/**",
                to_glob="components/features/map/**",
            ),
        ]
        violations = evaluate_all(db_with_imports, rules)
        assert len(violations) == 2
        assert violations[0].rule_name == "a-first-rule"
        assert violations[1].rule_name == "z-last-rule"
