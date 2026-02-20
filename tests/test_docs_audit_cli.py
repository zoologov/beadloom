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
            "We have 5 MCP tools available.\n",
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
