"""Tests for docs audit: comparator logic + CLI command."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.audit import Fact
from beadloom.doc_sync.scanner import Mention

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _project_with_pyproject(tmp_path: Path) -> Path:
    """Create a minimal project with pyproject.toml for version fact."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".beadloom").mkdir()
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "2.0.0"\n',
        encoding="utf-8",
    )
    return proj


# ---------------------------------------------------------------------------
# compare_facts — stale / fresh / unmatched
# ---------------------------------------------------------------------------


class TestCompareFacts:
    """Tests for compare_facts() comparator logic."""

    def test_compare_facts_stale_version(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import compare_facts

        facts = {
            "version": Fact(name="version", value="2.0.0", source="pyproject.toml"),
        }
        mentions = [
            Mention(
                fact_name="version",
                value="1.7.0",
                file=tmp_path / "README.md",
                line=3,
                context="Beadloom v1.7.0",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert len(result.findings) == 1
        assert result.findings[0].status == "stale"
        assert result.findings[0].mention.value == "1.7.0"
        assert result.findings[0].fact.value == "2.0.0"
        assert result.findings[0].tolerance == 0.0

    def test_compare_facts_fresh_version(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import compare_facts

        facts = {
            "version": Fact(name="version", value="2.0.0", source="pyproject.toml"),
        }
        mentions = [
            Mention(
                fact_name="version",
                value="2.0.0",
                file=tmp_path / "README.md",
                line=3,
                context="Beadloom v2.0.0",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert len(result.findings) == 1
        assert result.findings[0].status == "fresh"

    def test_compare_facts_stale_count(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import compare_facts

        facts = {
            "mcp_tool_count": Fact(name="mcp_tool_count", value=14, source="MCP server"),
        }
        mentions = [
            Mention(
                fact_name="mcp_tool_count",
                value=13,
                file=tmp_path / "README.md",
                line=42,
                context="13 MCP tools",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert len(result.findings) == 1
        assert result.findings[0].status == "stale"

    def test_compare_facts_fresh_count(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import compare_facts

        facts = {
            "node_count": Fact(name="node_count", value=32, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="node_count",
                value=32,
                file=tmp_path / "README.md",
                line=10,
                context="32 nodes",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert len(result.findings) == 1
        assert result.findings[0].status == "fresh"

    def test_compare_facts_unmatched(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import compare_facts

        facts = {
            "version": Fact(name="version", value="2.0.0", source="pyproject.toml"),
        }
        mentions = [
            Mention(
                fact_name="unknown_fact",
                value=42,
                file=tmp_path / "README.md",
                line=8,
                context="some number 42",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert len(result.findings) == 0
        assert len(result.unmatched) == 1
        assert result.unmatched[0].fact_name == "unknown_fact"

    def test_compare_facts_mixed(self, tmp_path: Path) -> None:
        """Mix of stale, fresh, and unmatched mentions.

        Uses mcp_tool_count (exact tolerance=0.0) for the stale case
        so the mismatch produces a deterministic stale finding regardless
        of the tolerance system defaults.
        """
        from beadloom.doc_sync.audit import compare_facts

        facts = {
            "version": Fact(name="version", value="2.0.0", source="pyproject.toml"),
            "mcp_tool_count": Fact(name="mcp_tool_count", value=14, source="MCP server"),
        }
        mentions = [
            Mention(
                fact_name="version",
                value="2.0.0",
                file=tmp_path / "README.md",
                line=1,
                context="v2.0.0",
            ),
            Mention(
                fact_name="mcp_tool_count",
                value=13,
                file=tmp_path / "README.md",
                line=5,
                context="13 MCP tools",
            ),
            Mention(
                fact_name="no_match",
                value=99,
                file=tmp_path / "README.md",
                line=10,
                context="99 widgets",
            ),
        ]
        result = compare_facts(facts, mentions)
        fresh = [f for f in result.findings if f.status == "fresh"]
        stale = [f for f in result.findings if f.status == "stale"]
        assert len(fresh) == 1
        assert len(stale) == 1
        assert len(result.unmatched) == 1

    def test_compare_facts_empty_inputs(self) -> None:
        from beadloom.doc_sync.audit import compare_facts

        result = compare_facts({}, [])
        assert result.findings == []
        assert result.unmatched == []
        assert result.facts == {}


# ---------------------------------------------------------------------------
# AuditResult dataclass
# ---------------------------------------------------------------------------


class TestAuditResultDataclass:
    """Tests for AuditResult frozen dataclass."""

    def test_audit_result_dataclass(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import AuditFinding, AuditResult

        fact = Fact(name="version", value="2.0.0", source="pyproject.toml")
        mention = Mention(
            fact_name="version",
            value="1.7.0",
            file=tmp_path / "README.md",
            line=3,
            context="v1.7.0",
        )
        finding = AuditFinding(
            mention=mention,
            fact=fact,
            status="stale",
            tolerance=0.0,
        )
        result = AuditResult(
            facts={"version": fact},
            findings=[finding],
            unmatched=[],
        )
        assert result.facts["version"].value == "2.0.0"
        assert len(result.findings) == 1
        assert result.findings[0].status == "stale"
        assert result.unmatched == []

    def test_audit_result_frozen(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import AuditResult

        result = AuditResult(facts={}, findings=[], unmatched=[])
        with pytest.raises(AttributeError):
            result.facts = {}  # type: ignore[misc]

    def test_audit_finding_frozen(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import AuditFinding

        fact = Fact(name="version", value="2.0.0", source="pyproject.toml")
        mention = Mention(
            fact_name="version",
            value="1.7.0",
            file=tmp_path / "README.md",
            line=3,
            context="v1.7.0",
        )
        finding = AuditFinding(
            mention=mention,
            fact=fact,
            status="stale",
            tolerance=0.0,
        )
        with pytest.raises(AttributeError):
            finding.status = "fresh"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# run_audit integration
# ---------------------------------------------------------------------------


class TestRunAuditIntegration:
    """Integration test for run_audit() facade."""

    def test_run_audit_integration(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import run_audit
        from beadloom.infrastructure.db import create_schema, open_db

        # Set up project
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "3.0.0"\n',
            encoding="utf-8",
        )

        # Create a README that mentions the wrong version
        (proj / "README.md").write_text(
            "# Demo\n\nDemo v2.0.0 is the current release.\n",
            encoding="utf-8",
        )

        # Set up DB
        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)

        result = run_audit(proj, conn)
        conn.close()

        # Should find a stale version mention
        stale = [f for f in result.findings if f.status == "stale"]
        assert len(stale) >= 1
        assert stale[0].fact.value == "3.0.0"
        assert stale[0].mention.value == "v2.0.0"

    def test_run_audit_empty_project(self, tmp_path: Path) -> None:
        """Empty project: no markdown, no manifest, empty DB -> graceful empty result."""
        from beadloom.doc_sync.audit import run_audit
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "empty_proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()

        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)

        result = run_audit(proj, conn)
        conn.close()

        # No markdown -> no mentions -> no findings, no unmatched
        assert result.findings == []
        assert result.unmatched == []
        # Facts should still have DB counts (all zeros)
        assert result.facts["node_count"].value == 0

    def test_run_audit_no_markdown_files(self, tmp_path: Path) -> None:
        """Project with manifest but no markdown files -> empty findings."""
        from beadloom.doc_sync.audit import run_audit
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "no_md_proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "3.0.0"\n',
            encoding="utf-8",
        )

        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)

        result = run_audit(proj, conn)
        conn.close()

        assert result.findings == []
        assert result.unmatched == []
        # But facts should be collected (version from pyproject.toml)
        assert "version" in result.facts
        assert result.facts["version"].value == "3.0.0"


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


class TestCliDocsAudit:
    """Tests for ``beadloom docs audit`` CLI command."""

    @staticmethod
    def _setup_project(tmp_path: Path) -> Path:
        """Create a minimal project for CLI testing."""
        proj = tmp_path / "proj"
        proj.mkdir()
        beadloom_dir = proj / ".beadloom"
        beadloom_dir.mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "3.0.0"\n',
            encoding="utf-8",
        )
        (proj / "README.md").write_text(
            "# Demo\n\nDemo v2.0.0 is the current release.\n\n"
            "We have 15 MCP tools available.\n",
            encoding="utf-8",
        )

        # Create DB via reindex-like schema
        from beadloom.infrastructure.db import create_schema, open_db

        db_path = beadloom_dir / "beadloom.db"
        conn = open_db(db_path)
        create_schema(conn)
        conn.close()

        return proj

    def test_cli_docs_audit_basic(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "audit", "--project", str(proj)])

        assert result.exit_code == 0, result.output
        # Should display the title
        assert "Documentation Audit" in result.output

    def test_cli_docs_audit_json(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "audit", "--json", "--project", str(proj)])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "facts" in data
        assert "stale" in data
        assert "fresh" in data
        assert "unmatched" in data
        assert "summary" in data
        assert isinstance(data["summary"]["stale_count"], int)
        assert isinstance(data["summary"]["fresh_count"], int)
        assert isinstance(data["summary"]["unmatched_count"], int)

    def test_cli_docs_audit_stale_only(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["docs", "audit", "--stale-only", "--project", str(proj)]
        )

        assert result.exit_code == 0, result.output
        # Should NOT contain "Fresh" section header when --stale-only
        # (it may contain "fresh" in other contexts like counts)
        assert "Fresh (verified)" not in result.output

    def test_cli_docs_audit_verbose(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["docs", "audit", "--verbose", "--project", str(proj)]
        )

        assert result.exit_code == 0, result.output
        # Verbose shows unmatched section
        # (there may or may not be unmatched items, but the command should succeed)

    def test_cli_docs_audit_no_db(self, tmp_path: Path) -> None:
        """Command should error gracefully when no DB exists."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = tmp_path / "empty"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\n',
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(main, ["docs", "audit", "--project", str(proj)])

        # Should exit with error about missing DB
        assert result.exit_code != 0

    def test_cli_docs_audit_json_structure(self, tmp_path: Path) -> None:
        """Verify JSON output has correct structure for each item."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "audit", "--json", "--project", str(proj)])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)

        # Verify facts structure
        for _fact_name, fact_val in data["facts"].items():
            assert "value" in fact_val
            assert "source" in fact_val

        # Verify stale items structure (if any)
        for item in data["stale"]:
            assert "file" in item
            assert "line" in item
            assert "fact" in item
            assert "mentioned" in item
            assert "actual" in item


# ---------------------------------------------------------------------------
# Issue #55 — test_count label shows "(symbols)" suffix
# ---------------------------------------------------------------------------


class TestFactLabelSuffix:
    """test_count should be labeled with (symbols) suffix in Rich output."""

    @staticmethod
    def _setup_project_with_test_count(tmp_path: Path) -> Path:
        """Create a project with test_count fact."""
        proj = tmp_path / "proj"
        proj.mkdir()
        beadloom_dir = proj / ".beadloom"
        beadloom_dir.mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "1.0.0"\n',
            encoding="utf-8",
        )
        (proj / "README.md").write_text(
            "# Demo\n\nVersion 1.0.0 is current.\n",
            encoding="utf-8",
        )

        from beadloom.infrastructure.db import create_schema, open_db

        db_path = beadloom_dir / "beadloom.db"
        conn = open_db(db_path)
        create_schema(conn)
        # Insert a node with test_count in extra
        extra = json.dumps(
            {"tests": {"test_count": 50, "framework": "pytest"}}
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra)"
            " VALUES (?, ?, ?, ?)",
            ("test-node", "feature", "test", extra),
        )
        conn.commit()
        conn.close()
        return proj

    def test_test_count_label_has_symbols_suffix(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project_with_test_count(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "audit", "--project", str(proj)])

        assert result.exit_code == 0, result.output
        # The label for test_count should include "(symbols)"
        assert "test count (symbols)" in result.output


# ---------------------------------------------------------------------------
# Issue #56 — Show relative path instead of basename
# ---------------------------------------------------------------------------


class TestRelativePath:
    """Rich output should show relative path from project root, not basename."""

    @staticmethod
    def _setup_project_with_subdoc(tmp_path: Path) -> Path:
        """Create a project with a doc in a subdirectory."""
        proj = tmp_path / "proj"
        proj.mkdir()
        beadloom_dir = proj / ".beadloom"
        beadloom_dir.mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "3.0.0"\n',
            encoding="utf-8",
        )
        docs_dir = proj / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text(
            "# Guide\n\nDemo v2.0.0 is the current release.\n",
            encoding="utf-8",
        )

        from beadloom.infrastructure.db import create_schema, open_db

        db_path = beadloom_dir / "beadloom.db"
        conn = open_db(db_path)
        create_schema(conn)
        conn.close()
        return proj

    def test_rich_output_shows_relative_path(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project_with_subdoc(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "audit", "--project", str(proj)])

        assert result.exit_code == 0, result.output
        # Should show "docs/guide.md" not just "guide.md"
        assert "docs/guide.md" in result.output


# ---------------------------------------------------------------------------
# Issue #57 — Dynamic versioning detection
# ---------------------------------------------------------------------------


class TestDynamicVersioning:
    """FactRegistry should detect dynamic versioning via Hatch and importlib.metadata."""

    def test_hatch_dynamic_version(self, tmp_path: Path) -> None:
        """When pyproject has dynamic=['version'] + [tool.hatch.version], read from source."""
        from beadloom.doc_sync.audit import FactRegistry
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\ndynamic = ["version"]\n\n'
            '[tool.hatch.version]\npath = "src/demo/__init__.py"\n',
            encoding="utf-8",
        )
        src_dir = proj / "src" / "demo"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text(
            '__version__ = "4.2.0"\n', encoding="utf-8"
        )

        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)

        registry = FactRegistry()
        facts: dict[str, object] = {}
        registry._collect_version(proj, facts)  # type: ignore[arg-type]
        conn.close()

        assert "version" in facts
        fact = facts["version"]
        assert fact.value == "4.2.0"  # type: ignore[union-attr]

    def test_importlib_metadata_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When dynamic versioning has no hatch config, fall back to importlib.metadata."""
        from beadloom.doc_sync.audit import FactRegistry

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo-pkg"\ndynamic = ["version"]\n',
            encoding="utf-8",
        )

        # Mock importlib.metadata.version to return a known value
        import importlib.metadata

        monkeypatch.setattr(
            importlib.metadata, "version", lambda name: "5.0.0" if name == "demo-pkg" else None
        )

        registry = FactRegistry()
        facts: dict[str, object] = {}
        registry._collect_version(proj, facts)  # type: ignore[arg-type]

        assert "version" in facts
        fact = facts["version"]
        assert fact.value == "5.0.0"  # type: ignore[union-attr]

    def test_static_version_still_works(self, tmp_path: Path) -> None:
        """Static version in pyproject.toml should still be detected."""
        from beadloom.doc_sync.audit import FactRegistry
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "1.0.0"\n',
            encoding="utf-8",
        )

        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)

        registry = FactRegistry()
        facts: dict[str, object] = {}
        registry._collect_version(proj, facts)  # type: ignore[arg-type]
        conn.close()

        assert "version" in facts
        fact = facts["version"]
        assert fact.value == "1.0.0"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# parse_fail_condition edge cases
# ---------------------------------------------------------------------------


class TestParseFailCondition:
    """Tests for parse_fail_condition() to cover validation branches."""

    def test_valid_stale_gt(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        metric, op, threshold = parse_fail_condition("stale>0")
        assert metric == "stale"
        assert op == ">"
        assert threshold == 0

    def test_valid_stale_gte(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        metric, op, threshold = parse_fail_condition("stale>=5")
        assert metric == "stale"
        assert op == ">="
        assert threshold == 5

    def test_invalid_syntax(self) -> None:
        import click

        from beadloom.doc_sync.audit import parse_fail_condition

        with pytest.raises(click.BadParameter, match="Invalid"):
            parse_fail_condition("not-valid")

    def test_unsupported_metric(self) -> None:
        import click

        from beadloom.doc_sync.audit import parse_fail_condition

        with pytest.raises(click.BadParameter, match="Unsupported metric"):
            parse_fail_condition("unknown>0")


# ---------------------------------------------------------------------------
# _load_tolerances_from_config edge cases
# ---------------------------------------------------------------------------


class TestLoadTolerancesFromConfig:
    """Tests for _load_tolerances_from_config() config loading branches."""

    def test_no_config_file(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import _load_tolerances_from_config

        result = _load_tolerances_from_config(tmp_path)
        assert result is None

    def test_valid_config(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import _load_tolerances_from_config

        config_dir = tmp_path / ".beadloom"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "docs_audit:\n  tolerances:\n    test_count: 0.10\n    node_count: 0.05\n",
            encoding="utf-8",
        )
        result = _load_tolerances_from_config(tmp_path)
        assert result is not None
        assert result["test_count"] == 0.10
        assert result["node_count"] == 0.05

    def test_empty_tolerances(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import _load_tolerances_from_config

        config_dir = tmp_path / ".beadloom"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "docs_audit:\n  tolerances: {}\n",
            encoding="utf-8",
        )
        result = _load_tolerances_from_config(tmp_path)
        assert result is None  # empty dict returns None

    def test_no_docs_audit_section(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import _load_tolerances_from_config

        config_dir = tmp_path / ".beadloom"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "other_section:\n  key: value\n",
            encoding="utf-8",
        )
        result = _load_tolerances_from_config(tmp_path)
        assert result is None

    def test_non_numeric_tolerance_skipped(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import _load_tolerances_from_config

        config_dir = tmp_path / ".beadloom"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "docs_audit:\n  tolerances:\n    test_count: 'invalid'\n    node_count: 0.05\n",
            encoding="utf-8",
        )
        result = _load_tolerances_from_config(tmp_path)
        assert result is not None
        assert "test_count" not in result
        assert result["node_count"] == 0.05

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import _load_tolerances_from_config

        config_dir = tmp_path / ".beadloom"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "not: [valid: yaml: {{{\n",
            encoding="utf-8",
        )
        result = _load_tolerances_from_config(tmp_path)
        assert result is None

    def test_not_a_dict(self, tmp_path: Path) -> None:
        from beadloom.doc_sync.audit import _load_tolerances_from_config

        config_dir = tmp_path / ".beadloom"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "just a string\n",
            encoding="utf-8",
        )
        result = _load_tolerances_from_config(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# FactRegistry collector edge cases
# ---------------------------------------------------------------------------


class TestFactRegistryCollectors:
    """Edge cases for FactRegistry database collector methods."""

    def test_collect_db_counts(self, tmp_path: Path) -> None:
        """node_count and edge_count are collected from DB."""
        from beadloom.doc_sync.audit import FactRegistry
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("n1", "feature", "N1"),
        )
        conn.commit()

        registry = FactRegistry()
        facts: dict[str, object] = {}
        registry._collect_db_counts(conn, facts)
        conn.close()

        assert "node_count" in facts
        assert facts["node_count"].value == 1

    def test_collect_language_count(self, tmp_path: Path) -> None:
        """language_count is derived from code_symbols file extensions."""
        from beadloom.doc_sync.audit import FactRegistry
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, "
            "line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/mod.py", "f", "function", 1, 1, "{}", "h"),
        )
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, "
            "line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/app.ts", "g", "function", 1, 1, "{}", "h2"),
        )
        conn.commit()

        registry = FactRegistry()
        facts: dict[str, Fact] = {}
        registry._collect_language_count(conn, facts)
        conn.close()

        assert "language_count" in facts
        assert facts["language_count"].value == 2  # Python + TypeScript

    def test_collect_test_count(self, tmp_path: Path) -> None:
        """test_count sums tests.test_count from nodes.extra JSON."""
        from beadloom.doc_sync.audit import FactRegistry
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)
        extra = json.dumps({"tests": {"test_count": 42, "framework": "pytest"}})
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("n1", "feature", "N1", extra),
        )
        conn.commit()

        registry = FactRegistry()
        facts: dict[str, Fact] = {}
        registry._collect_test_count(conn, facts)
        conn.close()

        assert "test_count" in facts
        assert facts["test_count"].value == 42

    def test_collect_framework_count(self, tmp_path: Path) -> None:
        """framework_count counts nodes with non-empty framework in extra."""
        from beadloom.doc_sync.audit import FactRegistry
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)
        extra = json.dumps({"tests": {"test_count": 10, "framework": "pytest"}})
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            ("n1", "feature", "N1", extra),
        )
        conn.commit()

        registry = FactRegistry()
        facts: dict[str, Fact] = {}
        registry._collect_framework_count(conn, facts)
        conn.close()

        assert "framework_count" in facts
        assert facts["framework_count"].value == 1

    def test_collect_rule_type_count(self, tmp_path: Path) -> None:
        """rule_type_count counts rules in the rules table."""
        from beadloom.doc_sync.audit import FactRegistry
        from beadloom.infrastructure.db import create_schema, open_db

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        db_path = proj / ".beadloom" / "test.db"
        conn = open_db(db_path)
        create_schema(conn)
        conn.execute(
            "INSERT INTO rules (name, rule_type, rule_json) VALUES (?, ?, ?)",
            ("test-rule", "require", '{"pattern": "*.py"}'),
        )
        conn.commit()

        registry = FactRegistry()
        facts: dict[str, Fact] = {}
        registry._collect_rule_type_count(conn, facts)
        conn.close()

        assert "rule_type_count" in facts
        assert facts["rule_type_count"].value == 1

    def test_collect_extra_facts_from_config(self, tmp_path: Path) -> None:
        """Extra facts loaded from .beadloom/config.yml."""
        from beadloom.doc_sync.audit import FactRegistry

        proj = tmp_path / "proj"
        proj.mkdir()
        config_dir = proj / ".beadloom"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "docs_audit:\n"
            "  extra_facts:\n"
            "    custom_metric:\n"
            "      value: 42\n"
            "      source: manual\n",
            encoding="utf-8",
        )

        registry = FactRegistry()
        facts: dict[str, Fact] = {}
        registry._collect_extra_facts(proj, facts)

        assert "custom_metric" in facts
        assert facts["custom_metric"].value == 42
        assert facts["custom_metric"].source == "manual"

    def test_collect_extra_facts_skips_malformed(self, tmp_path: Path) -> None:
        """Malformed extra facts (no value, wrong type) are skipped."""
        from beadloom.doc_sync.audit import FactRegistry

        proj = tmp_path / "proj"
        proj.mkdir()
        config_dir = proj / ".beadloom"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "docs_audit:\n"
            "  extra_facts:\n"
            "    no_value:\n"
            "      source: manual\n"
            "    bad_type:\n"
            "      value: [1, 2, 3]\n"
            "      source: manual\n"
            "    good_one:\n"
            "      value: 99\n"
            "      source: manual\n"
            "    also_bad:\n"
            "      not_a_dict_value: true\n",
            encoding="utf-8",
        )

        registry = FactRegistry()
        facts: dict[str, Fact] = {}
        registry._collect_extra_facts(proj, facts)

        # Only the good fact should be collected
        assert "good_one" in facts
        assert facts["good_one"].value == 99
        assert "no_value" not in facts
        assert "bad_type" not in facts

    def test_version_from_package_json(self, tmp_path: Path) -> None:
        """Version can be read from package.json."""
        from beadloom.doc_sync.audit import FactRegistry

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        (proj / "package.json").write_text(
            json.dumps({"name": "my-app", "version": "2.5.0"}),
            encoding="utf-8",
        )

        registry = FactRegistry()
        facts: dict[str, Fact] = {}
        registry._collect_version(proj, facts)  # type: ignore[arg-type]

        assert "version" in facts
        assert facts["version"].value == "2.5.0"

    def test_version_from_cargo_toml(self, tmp_path: Path) -> None:
        """Version can be read from Cargo.toml."""
        from beadloom.doc_sync.audit import FactRegistry

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".beadloom").mkdir()
        (proj / "Cargo.toml").write_text(
            '[package]\nname = "my-crate"\nversion = "0.3.1"\n',
            encoding="utf-8",
        )

        registry = FactRegistry()
        facts: dict[str, Fact] = {}
        registry._collect_version(proj, facts)  # type: ignore[arg-type]

        assert "version" in facts
        assert facts["version"].value == "0.3.1"
