"""Tests for refresh_claude_md — CLAUDE.md marker-based auto-refresh."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from beadloom.onboarding.scanner import (
    _auto_insert_markers,
    _parse_markers,
    _render_project_info_section,
    refresh_claude_md,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Sample content used across tests
# ---------------------------------------------------------------------------

_SAMPLE_WITH_MARKERS = """\
# CLAUDE.md

## 0.1 Project: Beadloom

<!-- beadloom:auto-start project-info -->
- **Stack:** Python 3.10+, SQLite (WAL)
- **Current version:** 0.0.0
<!-- beadloom:auto-end -->

---

## 1. Skills
Some content here.
"""

_SAMPLE_WITHOUT_MARKERS = """\
# CLAUDE.md

## 0.1 Project: Beadloom

- **Stack:** Python 3.10+, SQLite (WAL)
- **Distribution:** PyPI (`uv tool install beadloom`)
- **Tests:** pytest + pytest-cov (>=80% coverage)
- **Linter/formatter:** ruff (lint + format)
- **Type checking:** mypy --strict
- **Architecture:** DDD packages -- `infrastructure/`, `context_oracle/`
- **Current version:** 1.0.0 (Phases 1-3 done)

---

## 1. Skills
Some content here.
"""


# ---------------------------------------------------------------------------
# _parse_markers
# ---------------------------------------------------------------------------


class TestParseMarkers:
    def test_finds_marker_pair(self) -> None:
        markers = _parse_markers(_SAMPLE_WITH_MARKERS)
        assert len(markers) == 1
        name, _start, _end, content = markers[0]
        assert name == "project-info"
        assert "**Stack:**" in content

    def test_no_markers(self) -> None:
        markers = _parse_markers("# No markers here\nJust text.\n")
        assert markers == []

    def test_multiple_marker_pairs(self) -> None:
        text = (
            "before\n"
            "<!-- beadloom:auto-start section-a -->\nA content\n<!-- beadloom:auto-end -->\n"
            "middle\n"
            "<!-- beadloom:auto-start section-b -->\nB content\n<!-- beadloom:auto-end -->\n"
            "after\n"
        )
        markers = _parse_markers(text)
        assert len(markers) == 2
        assert markers[0][0] == "section-a"
        assert markers[1][0] == "section-b"
        assert "A content" in markers[0][3]
        assert "B content" in markers[1][3]

    def test_unclosed_marker_ignored(self) -> None:
        text = "<!-- beadloom:auto-start orphan -->\nno end marker\n"
        markers = _parse_markers(text)
        assert markers == []


# ---------------------------------------------------------------------------
# _auto_insert_markers
# ---------------------------------------------------------------------------


class TestAutoInsertMarkers:
    def test_inserts_markers_around_section_01(self) -> None:
        result = _auto_insert_markers(_SAMPLE_WITHOUT_MARKERS)
        assert "<!-- beadloom:auto-start project-info -->" in result
        assert "<!-- beadloom:auto-end -->" in result
        # Section heading stays outside markers
        assert "## 0.1 Project: Beadloom" in result
        # Heading should be before the start marker
        heading_pos = result.index("## 0.1 Project: Beadloom")
        marker_pos = result.index("<!-- beadloom:auto-start project-info -->")
        assert heading_pos < marker_pos

    def test_no_section_01_no_change(self) -> None:
        text = "# Just a title\n\nSome text.\n"
        result = _auto_insert_markers(text)
        assert result == text

    def test_already_has_markers_no_change(self) -> None:
        result = _auto_insert_markers(_SAMPLE_WITH_MARKERS)
        # Should not add duplicate markers
        assert result.count("<!-- beadloom:auto-start") == 1


# ---------------------------------------------------------------------------
# _render_project_info_section
# ---------------------------------------------------------------------------


class TestRenderProjectInfoSection:
    def test_returns_nonempty_string(self, tmp_path: Path) -> None:
        # Create a minimal pyproject.toml so version detection works
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test-project"\nversion = "1.0.0"\n'
        )
        src_dir = tmp_path / "src" / "test_project"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("")

        with patch("beadloom.infrastructure.doctor._get_actual_version", return_value="1.0.0"):
            result = _render_project_info_section(tmp_path)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "**Current version:**" in result

    def test_includes_packages(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test-project"\nversion = "1.0.0"\n'
        )
        src_dir = tmp_path / "src" / "test_project"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("")
        # Create a sub-package
        pkg = src_dir / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        with patch("beadloom.infrastructure.doctor._get_actual_version", return_value="1.0.0"):
            result = _render_project_info_section(tmp_path)

        # Should mention the package name
        assert "mypkg" in result


# ---------------------------------------------------------------------------
# refresh_claude_md
# ---------------------------------------------------------------------------


class TestRefreshClaudeMd:
    def test_refresh_with_markers(self, tmp_path: Path) -> None:
        """Refresh replaces content between markers."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(_SAMPLE_WITH_MARKERS)

        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "2.0.0"\n')

        with patch("beadloom.infrastructure.doctor._get_actual_version", return_value="2.0.0"):
            changed = refresh_claude_md(tmp_path)

        assert "project-info" in changed
        updated = claude_md.read_text()
        assert "2.0.0" in updated
        # Markers preserved
        assert "<!-- beadloom:auto-start project-info -->" in updated
        assert "<!-- beadloom:auto-end -->" in updated
        # Content outside markers preserved
        assert "## 1. Skills" in updated

    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        """Dry run returns changes but does not modify the file."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(_SAMPLE_WITH_MARKERS)
        original = claude_md.read_text()

        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "9.9.9"\n')

        with patch("beadloom.infrastructure.doctor._get_actual_version", return_value="9.9.9"):
            changed = refresh_claude_md(tmp_path, dry_run=True)

        assert "project-info" in changed
        # File should be unchanged
        assert claude_md.read_text() == original

    def test_auto_inserts_markers_on_first_run(self, tmp_path: Path) -> None:
        """When no markers but section 0.1 exists, markers are auto-inserted."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(_SAMPLE_WITHOUT_MARKERS)

        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "3.0.0"\n')

        with patch("beadloom.infrastructure.doctor._get_actual_version", return_value="3.0.0"):
            changed = refresh_claude_md(tmp_path)

        updated = claude_md.read_text()
        assert "<!-- beadloom:auto-start project-info -->" in updated
        assert "<!-- beadloom:auto-end -->" in updated
        assert "project-info" in changed
        # Heading stays outside markers
        assert "## 0.1 Project: Beadloom" in updated

    def test_no_change_returns_empty(self, tmp_path: Path) -> None:
        """When content matches, no sections are returned as changed."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        claude_md = claude_dir / "CLAUDE.md"

        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

        # Pre-render the section content so it matches
        with patch("beadloom.infrastructure.doctor._get_actual_version", return_value="1.0.0"):
            rendered = _render_project_info_section(tmp_path)

        content = (
            "# CLAUDE.md\n\n## 0.1 Project: Test\n\n"
            f"<!-- beadloom:auto-start project-info -->\n{rendered}\n"
            "<!-- beadloom:auto-end -->\n\n## 1. Other\n"
        )
        claude_md.write_text(content)

        with patch("beadloom.infrastructure.doctor._get_actual_version", return_value="1.0.0"):
            changed = refresh_claude_md(tmp_path)

        assert changed == []

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Missing CLAUDE.md returns empty list without error."""
        changed = refresh_claude_md(tmp_path)
        assert changed == []

    def test_preserves_content_outside_markers(self, tmp_path: Path) -> None:
        """All content outside markers is preserved exactly."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        content = (
            "# Title\n\nParagraph before.\n\n"
            "## 0.1 Project: Beadloom\n\n"
            "<!-- beadloom:auto-start project-info -->\n"
            "- old content\n"
            "<!-- beadloom:auto-end -->\n\n"
            "## 2. Important Section\n\nKeep this exactly.\n"
        )
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(content)

        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

        with patch("beadloom.infrastructure.doctor._get_actual_version", return_value="1.0.0"):
            refresh_claude_md(tmp_path)

        updated = claude_md.read_text()
        assert "# Title" in updated
        assert "Paragraph before." in updated
        assert "## 2. Important Section" in updated
        assert "Keep this exactly." in updated
