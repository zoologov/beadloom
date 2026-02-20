"""Tests for beadloom.doc_sync.audit — Fact Registry."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.audit import Fact, FactRegistry
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory for fact registry tests."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".beadloom").mkdir()
    return proj


@pytest.fixture()
def conn(project: Path) -> sqlite3.Connection:
    """Open an in-memory-equivalent test DB with schema."""
    db_path = project / ".beadloom" / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


class TestFactDataclass:
    """Tests for the Fact frozen dataclass."""

    def test_fact_creation(self) -> None:
        fact = Fact(name="version", value="1.0.0", source="pyproject.toml")
        assert fact.name == "version"
        assert fact.value == "1.0.0"
        assert fact.source == "pyproject.toml"

    def test_fact_frozen(self) -> None:
        fact = Fact(name="version", value="1.0.0", source="pyproject.toml")
        with pytest.raises(AttributeError):
            fact.name = "other"  # type: ignore[misc]

    def test_fact_with_int_value(self) -> None:
        fact = Fact(name="node_count", value=42, source="graph DB")
        assert fact.value == 42

    def test_fact_equality(self) -> None:
        f1 = Fact(name="version", value="1.0.0", source="pyproject.toml")
        f2 = Fact(name="version", value="1.0.0", source="pyproject.toml")
        assert f1 == f2


class TestVersionFact:
    """Tests for version extraction from manifests."""

    def test_collect_version_from_pyproject_static(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Extracts version from pyproject.toml with static version field."""
        (project / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\nversion = "2.5.1"\n'
        )
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert "version" in facts
        assert facts["version"].value == "2.5.1"
        assert facts["version"].source == "pyproject.toml"

    def test_collect_version_from_pyproject_poetry(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Extracts version from pyproject.toml with Poetry format."""
        (project / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "myapp"\nversion = "3.0.0"\n'
        )
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert "version" in facts
        assert facts["version"].value == "3.0.0"

    def test_collect_version_from_package_json(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Falls back to package.json when pyproject.toml is absent."""
        (project / "package.json").write_text('{"name": "myapp", "version": "1.2.3"}')
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert "version" in facts
        assert facts["version"].value == "1.2.3"
        assert facts["version"].source == "package.json"

    def test_collect_version_from_cargo_toml(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Falls back to Cargo.toml when higher-priority manifests are absent."""
        (project / "Cargo.toml").write_text('[package]\nname = "myapp"\nversion = "0.1.0"\n')
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert "version" in facts
        assert facts["version"].value == "0.1.0"
        assert facts["version"].source == "Cargo.toml"

    def test_collect_missing_manifest_graceful(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """No manifest file — version fact is skipped, no error."""
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert "version" not in facts

    def test_collect_malformed_pyproject(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Malformed pyproject.toml — version is skipped gracefully."""
        (project / "pyproject.toml").write_text("this is not valid toml at all {{{")
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert "version" not in facts


class TestDbCountFacts:
    """Tests for database count facts (nodes, edges, languages, tests)."""

    def test_collect_node_count(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("n1", "domain", "Domain 1"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("n2", "feature", "Feature 1"),
        )
        conn.commit()

        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert facts["node_count"].value == 2
        assert facts["node_count"].source == "graph DB"

    def test_collect_edge_count(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("n1", "domain", "Domain 1"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("n2", "feature", "Feature 1"),
        )
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("n2", "n1", "part_of"),
        )
        conn.commit()

        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert facts["edge_count"].value == 1
        assert facts["edge_count"].source == "graph DB"

    def test_collect_language_count(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Language count derived from distinct file extensions in code_symbols."""
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("src/main.py", "main", "function", 1, 5, "abc"),
        )
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("src/app.ts", "App", "class", 1, 10, "def"),
        )
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("src/util.py", "helper", "function", 1, 3, "ghi"),
        )
        conn.commit()

        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert facts["language_count"].value == 2  # .py and .ts

    def test_collect_test_count_from_extra(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Test count is summed from nodes.extra JSON tests.test_count."""
        extra_with_tests = json.dumps(
            {"tests": {"framework": "pytest", "test_count": 15, "test_files": []}}
        )
        extra_no_tests = json.dumps({})
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("n1", "domain", "Domain 1", extra_with_tests),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("n2", "feature", "Feature 1", extra_no_tests),
        )
        conn.commit()

        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert facts["test_count"].value == 15

    def test_collect_framework_count(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Framework count = nodes with non-empty tests.framework in extra."""
        extra_with_fw = json.dumps(
            {"tests": {"framework": "pytest", "test_count": 5, "test_files": []}}
        )
        extra_without_fw = json.dumps({"tests": {"framework": "", "test_count": 0}})
        extra_no_tests = json.dumps({})
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("n1", "domain", "D1", extra_with_fw),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("n2", "domain", "D2", extra_without_fw),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("n3", "feature", "F1", extra_no_tests),
        )
        conn.commit()

        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert facts["framework_count"].value == 1

    def test_collect_empty_db_returns_zero_counts(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Empty DB returns zero for all count facts."""
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert facts["node_count"].value == 0
        assert facts["edge_count"].value == 0
        assert facts["language_count"].value == 0
        assert facts["test_count"].value == 0
        assert facts["framework_count"].value == 0

    def test_collect_rule_type_count(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Rule type count from the rules table."""
        conn.execute(
            "INSERT INTO rules (name, rule_type, rule_json) VALUES (?, ?, ?)",
            ("no-cross", "deny", '{"src": "*", "dst": "*"}'),
        )
        conn.execute(
            "INSERT INTO rules (name, rule_type, rule_json) VALUES (?, ?, ?)",
            ("must-parent", "require", '{"src": "*"}'),
        )
        conn.execute(
            "INSERT INTO rules (name, rule_type, rule_json) VALUES (?, ?, ?)",
            ("another-deny", "deny", '{"src": "a"}'),
        )
        conn.commit()

        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert facts["rule_type_count"].value == 3


class TestMcpToolCount:
    """Tests for MCP tool count fact."""

    def test_collect_mcp_tool_count(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Counts MCP tools from the _TOOLS list in mcp_server module."""
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        # MCP tools are introspected from the actual module; count should be >= 0
        assert "mcp_tool_count" in facts
        assert isinstance(facts["mcp_tool_count"].value, int)
        assert facts["mcp_tool_count"].value >= 0


class TestCliCommandCount:
    """Tests for CLI command count fact."""

    def test_collect_cli_command_count(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Counts CLI commands from the Click main group."""
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert "cli_command_count" in facts
        assert isinstance(facts["cli_command_count"].value, int)
        assert facts["cli_command_count"].value >= 0


class TestExtraFacts:
    """Tests for config-driven extra facts."""

    def test_collect_extra_facts_from_config(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Extra facts defined in config.yml are collected."""
        config_dir = project / ".beadloom"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.yml").write_text(
            "docs_audit:\n"
            "  extra_facts:\n"
            "    custom_metric:\n"
            "      value: 42\n"
            '      source: "manual config"\n'
        )

        registry = FactRegistry()
        facts = registry.collect(project, conn)
        assert "custom_metric" in facts
        assert facts["custom_metric"].value == 42
        assert facts["custom_metric"].source == "manual config"

    def test_collect_no_extra_facts_without_config(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """No extra facts when config.yml is absent."""
        registry = FactRegistry()
        facts = registry.collect(project, conn)
        # Only built-in facts should be present
        assert "custom_metric" not in facts

    def test_collect_extra_facts_malformed_config(
        self, project: Path, conn: sqlite3.Connection
    ) -> None:
        """Malformed config.yml extra_facts section — gracefully skipped."""
        config_dir = project / ".beadloom"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.yml").write_text(
            "docs_audit:\n"
            "  extra_facts: not_a_dict\n"
        )

        registry = FactRegistry()
        facts = registry.collect(project, conn)
        # Should not crash; extra facts just not collected
        assert "node_count" in facts  # built-in facts still work


class TestDbMissingTables:
    """Tests for graceful handling of missing/broken DB tables."""

    def test_collect_missing_nodes_table(
        self, project: Path, tmp_path: Path
    ) -> None:
        """DB without nodes table — count facts gracefully skipped."""
        import sqlite3

        db_path = tmp_path / "empty.db"
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT, value TEXT)")
        c.commit()

        registry = FactRegistry()
        facts = registry.collect(project, c)
        # Should not crash; facts that need tables just won't be present
        assert "node_count" not in facts
