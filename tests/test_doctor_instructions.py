"""Tests for _check_agent_instructions and fact extraction helpers in doctor.py."""

from __future__ import annotations

from pathlib import Path

from beadloom.infrastructure.doctor import (
    Check,
    Severity,
    _check_agent_instructions,
    _extract_package_claims,
    _extract_version_claim,
    _get_actual_cli_commands,
    _get_actual_mcp_tool_count,
    _get_actual_packages,
    _get_actual_version,
)

# ---------------------------------------------------------------------------
# _extract_version_claim
# ---------------------------------------------------------------------------


class TestExtractVersionClaim:
    def test_extracts_version_from_claude_md(self) -> None:
        """Extracts version from standard CLAUDE.md format."""
        # Arrange
        text = "Some text\n- **Current version:** 1.7.0 (Phases 1-6)\nMore text"

        # Act
        result = _extract_version_claim(text)

        # Assert
        assert result == "1.7.0"

    def test_returns_none_when_no_version(self) -> None:
        """Returns None when text contains no version claim."""
        # Arrange
        text = "No version information here at all."

        # Act
        result = _extract_version_claim(text)

        # Assert
        assert result is None

    def test_extracts_version_with_different_format(self) -> None:
        """Handles version without extra description."""
        # Arrange
        text = "- **Current version:** 2.0.0\n"

        # Act
        result = _extract_version_claim(text)

        # Assert
        assert result == "2.0.0"


# ---------------------------------------------------------------------------
# _extract_package_claims
# ---------------------------------------------------------------------------


class TestExtractPackageClaims:
    def test_extracts_ddd_packages(self) -> None:
        """Extracts package names from architecture description."""
        # Arrange
        text = (
            "- **Architecture:** DDD packages — `infrastructure/`, `context_oracle/`, "
            "`doc_sync/`, `onboarding/`, `graph/` + `services/` (CLI, MCP) + `tui/`"
        )

        # Act
        result = _extract_package_claims(text)

        # Assert
        assert "infrastructure" in result
        assert "context_oracle" in result
        assert "doc_sync" in result
        assert "onboarding" in result
        assert "graph" in result
        assert "services" in result
        assert "tui" in result

    def test_returns_empty_set_when_no_packages(self) -> None:
        """Returns empty set when no backtick-dir patterns found."""
        # Arrange
        text = "No architecture packages mentioned."

        # Act
        result = _extract_package_claims(text)

        # Assert
        assert result == set()


# ---------------------------------------------------------------------------
# _get_actual_version
# ---------------------------------------------------------------------------


class TestGetActualVersion:
    def test_returns_version_string(self) -> None:
        """Returns a non-empty version string."""
        # Act
        result = _get_actual_version()

        # Assert
        assert result
        assert isinstance(result, str)
        # Should look like a semver
        parts = result.split(".")
        assert len(parts) >= 2


# ---------------------------------------------------------------------------
# _get_actual_cli_commands
# ---------------------------------------------------------------------------


class TestGetActualCliCommands:
    def test_returns_set_of_commands(self) -> None:
        """Returns a non-empty set of CLI command names."""
        # Act
        result = _get_actual_cli_commands()

        # Assert
        assert isinstance(result, set)
        assert len(result) > 0
        # Some known commands should be present
        assert "doctor" in result
        assert "reindex" in result or "status" in result


# ---------------------------------------------------------------------------
# _get_actual_mcp_tool_count
# ---------------------------------------------------------------------------


class TestGetActualMcpToolCount:
    def test_returns_positive_count(self) -> None:
        """MCP tool count should be a positive integer."""
        # Act
        result = _get_actual_mcp_tool_count()

        # Assert
        assert isinstance(result, int)
        assert result > 0


# ---------------------------------------------------------------------------
# _get_actual_packages
# ---------------------------------------------------------------------------


class TestGetActualPackages:
    def test_returns_packages_for_real_project(self) -> None:
        """Returns DDD package names for the beadloom project root."""
        # Arrange
        # Use the actual project root (two levels up from src/beadloom/)
        project_root = Path(__file__).parent.parent

        # Act
        result = _get_actual_packages(project_root)

        # Assert
        assert isinstance(result, set)
        assert "infrastructure" in result
        assert "graph" in result

    def test_returns_empty_for_nonexistent_path(self, tmp_path: Path) -> None:
        """Returns empty set when src/beadloom/ doesn't exist."""
        # Arrange & Act
        result = _get_actual_packages(tmp_path)

        # Assert
        assert result == set()


# ---------------------------------------------------------------------------
# _check_agent_instructions — integration
# ---------------------------------------------------------------------------


class TestCheckAgentInstructions:
    def test_returns_checks_for_project_with_claude_md(self, tmp_path: Path) -> None:
        """When CLAUDE.md exists, returns list of checks."""
        # Arrange
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(
            "# Project\n"
            "- **Current version:** 1.7.0\n"
            "- **Stack:** Python 3.10+, SQLite\n"
            "- **Tests:** pytest + pytest-cov\n"
            "- **Architecture:** DDD packages — `infrastructure/`, `graph/`\n",
            encoding="utf-8",
        )

        # Act
        checks = _check_agent_instructions(tmp_path)

        # Assert
        assert isinstance(checks, list)
        assert len(checks) > 0
        assert all(isinstance(c, Check) for c in checks)

    def test_returns_empty_list_when_no_files(self, tmp_path: Path) -> None:
        """When neither CLAUDE.md nor AGENTS.md exist, returns empty list."""
        # Act
        checks = _check_agent_instructions(tmp_path)

        # Assert
        assert checks == []

    def test_version_mismatch_produces_warning(self, tmp_path: Path) -> None:
        """Version claim that doesn't match actual version -> WARNING."""
        # Arrange
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(
            "- **Current version:** 0.0.1-fake\n",
            encoding="utf-8",
        )

        # Act
        checks = _check_agent_instructions(tmp_path)

        # Assert
        version_checks = [c for c in checks if c.name == "agent_instructions_version"]
        assert len(version_checks) == 1
        assert version_checks[0].severity == Severity.WARNING

    def test_version_match_produces_ok(self, tmp_path: Path) -> None:
        """Version claim matching actual version -> OK."""
        # Arrange
        actual_version = _get_actual_version()
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(
            f"- **Current version:** {actual_version}\n",
            encoding="utf-8",
        )

        # Act
        checks = _check_agent_instructions(tmp_path)

        # Assert
        version_checks = [c for c in checks if c.name == "agent_instructions_version"]
        assert len(version_checks) == 1
        assert version_checks[0].severity == Severity.OK

    def test_agents_md_is_also_checked(self, tmp_path: Path) -> None:
        """Checks are also produced from .beadloom/AGENTS.md."""
        # Arrange
        beadloom_dir = tmp_path / ".beadloom"
        beadloom_dir.mkdir()
        agents_md = beadloom_dir / "AGENTS.md"
        agents_md.write_text(
            "# Beadloom Agent Instructions\n"
            "## Available MCP Tools\n"
            "| `prime` | Compact context |\n"
            "| `get_context` | Full context |\n",
            encoding="utf-8",
        )

        # Act
        checks = _check_agent_instructions(tmp_path)

        # Assert
        assert isinstance(checks, list)
        # Should have at least MCP tool count check
        mcp_checks = [c for c in checks if c.name == "agent_instructions_mcp_tools"]
        assert len(mcp_checks) == 1

    def test_package_mismatch_warning(self, tmp_path: Path) -> None:
        """Package claim that doesn't match actual packages -> WARNING."""
        # Arrange
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(
            "- **Architecture:** DDD packages — `fake_pkg/`, `nonexistent/`\n",
            encoding="utf-8",
        )

        # Act
        checks = _check_agent_instructions(tmp_path)

        # Assert
        pkg_checks = [c for c in checks if c.name == "agent_instructions_packages"]
        assert len(pkg_checks) == 1
        assert pkg_checks[0].severity == Severity.WARNING
