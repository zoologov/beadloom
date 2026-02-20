"""Tests for beadloom.doc_sync.scanner — markdown fact mention scanner."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.scanner import DocScanner, Mention

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def scanner() -> DocScanner:
    return DocScanner()


def _write_md(tmp_path: Path, name: str, content: str) -> Path:
    """Helper: write a markdown file and return its path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ===========================================================================
# Mention dataclass
# ===========================================================================


class TestMentionDataclass:
    def test_mention_dataclass_frozen(self, tmp_path: Path) -> None:
        m = Mention(
            fact_name="language_count",
            value=9,
            file=tmp_path / "test.md",
            line=1,
            context="supports 9 languages",
        )
        with pytest.raises(FrozenInstanceError):
            m.fact_name = "other"  # type: ignore[misc]

    def test_mention_fields(self, tmp_path: Path) -> None:
        m = Mention(
            fact_name="version",
            value="1.7.0",
            file=tmp_path / "README.md",
            line=5,
            context="version 1.7.0",
        )
        assert m.fact_name == "version"
        assert m.value == "1.7.0"
        assert m.line == 5


# ===========================================================================
# Core scanning — keyword proximity
# ===========================================================================


class TestScanFindsNumbers:
    def test_scan_finds_number_near_keyword(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "Beadloom supports **9** programming languages.\n")
        result = scanner.scan_file(md)
        assert len(result) >= 1
        match = [m for m in result if m.fact_name == "language_count"]
        assert len(match) == 1
        assert match[0].value == 9
        assert match[0].line == 1

    def test_scan_finds_version_string(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "Current version is 1.7.0 and works great.\n")
        result = scanner.scan_file(md)
        versions = [m for m in result if m.fact_name == "version"]
        assert len(versions) == 1
        assert versions[0].value == "1.7.0"

    def test_scan_finds_version_with_v_prefix(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "Released v2.0.1 today.\n")
        result = scanner.scan_file(md)
        versions = [m for m in result if m.fact_name == "version"]
        assert len(versions) == 1
        assert versions[0].value == "v2.0.1"

    def test_multiple_mentions_per_file(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        content = (
            "# Project\n\n"
            "Supports 9 programming languages.\n\n"
            "Has 14 MCP tools available.\n\n"
            "Current version 1.7.0.\n"
        )
        md = _write_md(tmp_path, "test.md", content)
        result = scanner.scan_file(md)
        fact_names = {m.fact_name for m in result}
        assert "language_count" in fact_names
        assert "mcp_tool_count" in fact_names
        assert "version" in fact_names

    def test_scan_empty_file(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "empty.md", "")
        result = scanner.scan_file(md)
        assert result == []

    def test_case_insensitive_keywords(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "There are 5 LANGUAGES supported.\n")
        result = scanner.scan_file(md)
        matches = [m for m in result if m.fact_name == "language_count"]
        assert len(matches) == 1
        assert matches[0].value == 5


# ===========================================================================
# Proximity window
# ===========================================================================


class TestProximityWindow:
    def test_proximity_window_too_far(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        # Number is more than 5 words away from keyword
        md = _write_md(
            tmp_path,
            "test.md",
            "There are 9 different interesting and very cool things but language is here.\n",
        )
        result = scanner.scan_file(md)
        lang_matches = [m for m in result if m.fact_name == "language_count"]
        assert len(lang_matches) == 0

    def test_proximity_window_just_within(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        # Number within 5 words of keyword
        md = _write_md(
            tmp_path,
            "test.md",
            "There are 9 supported programming languages here.\n",
        )
        result = scanner.scan_file(md)
        lang_matches = [m for m in result if m.fact_name == "language_count"]
        assert len(lang_matches) == 1


# ===========================================================================
# False positive filters
# ===========================================================================


class TestFalsePositiveFilters:
    def test_scan_skips_code_blocks(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        content = (
            "Some text.\n\n"
            "```python\n"
            "x = 9  # 9 languages\n"
            "```\n\n"
            "More text.\n"
        )
        md = _write_md(tmp_path, "test.md", content)
        result = scanner.scan_file(md)
        lang_matches = [m for m in result if m.fact_name == "language_count"]
        assert len(lang_matches) == 0

    def test_scan_skips_dates(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "Updated on 2026-02-19.\n")
        result = scanner.scan_file(md)
        # Numbers from date should not be matched
        assert len(result) == 0

    def test_scan_skips_issue_ids_hash(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "See issue #123 for details.\n")
        result = scanner.scan_file(md)
        assert len(result) == 0

    def test_scan_skips_issue_ids_prefix(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "Fixed in BDL-021 release.\n")
        result = scanner.scan_file(md)
        assert len(result) == 0

    def test_scan_skips_hex_colors(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "Color is #FF0000 red.\n")
        result = scanner.scan_file(md)
        assert len(result) == 0

    def test_scan_skips_hex_prefix(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(tmp_path, "test.md", "Value is 0xFF in hex.\n")
        result = scanner.scan_file(md)
        assert len(result) == 0

    def test_scan_skips_version_pinning(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        content = "Requires >=0.80 coverage.\nAlso ^1.2.3 and ~=1.0 constraints.\n"
        md = _write_md(tmp_path, "test.md", content)
        result = scanner.scan_file(md)
        # These should all be filtered out
        assert len(result) == 0

    def test_scan_skips_line_numbers(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        content = "See file.py:15 for details.\nAlso line 42 is relevant.\nCheck L42.\n"
        md = _write_md(tmp_path, "test.md", content)
        result = scanner.scan_file(md)
        assert len(result) == 0

    def test_scan_skips_changelog(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        md = _write_md(
            tmp_path,
            "CHANGELOG.md",
            "Added 5 new languages in this release.\n",
        )
        paths = scanner.resolve_paths(tmp_path)
        assert md not in paths


# ===========================================================================
# Path resolution
# ===========================================================================


class TestResolvePaths:
    def test_resolve_paths_finds_root_md(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        _write_md(tmp_path, "README.md", "# Project")
        paths = scanner.resolve_paths(tmp_path)
        assert any(p.name == "README.md" for p in paths)

    def test_resolve_paths_finds_docs_subdir(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Guide", encoding="utf-8")
        paths = scanner.resolve_paths(tmp_path)
        assert any(p.name == "guide.md" for p in paths)

    def test_resolve_paths_excludes_changelog(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        _write_md(tmp_path, "CHANGELOG.md", "# Changelog")
        _write_md(tmp_path, "README.md", "# Readme")
        paths = scanner.resolve_paths(tmp_path)
        names = [p.name for p in paths]
        assert "CHANGELOG.md" not in names
        assert "README.md" in names

    def test_resolve_paths_custom_globs(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        _write_md(tmp_path, "README.md", "# Readme")
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        _write_md(custom_dir, "notes.md", "# Notes")
        paths = scanner.resolve_paths(tmp_path, scan_globs=["custom/**/*.md"])
        names = [p.name for p in paths]
        assert "notes.md" in names
        assert "README.md" not in names

    def test_resolve_paths_deduplicates(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        _write_md(tmp_path, "README.md", "# Readme")
        paths = scanner.resolve_paths(tmp_path, scan_globs=["*.md", "*.md"])
        readme_count = sum(1 for p in paths if p.name == "README.md")
        assert readme_count == 1


# ===========================================================================
# scan() — multi-file scan
# ===========================================================================


class TestScanMultipleFiles:
    def test_scan_multiple_files(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        _write_md(tmp_path, "a.md", "Has 9 languages supported.\n")
        _write_md(tmp_path, "b.md", "Version is 2.0.0.\n")
        paths = [tmp_path / "a.md", tmp_path / "b.md"]
        result = scanner.scan(paths)
        fact_names = {m.fact_name for m in result}
        assert "language_count" in fact_names
        assert "version" in fact_names


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """Edge case tests for scanner robustness."""

    def test_no_markdown_files_scan_returns_empty(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """resolve_paths on a directory with no .md files returns empty list."""
        (tmp_path / "data.txt").write_text("not markdown", encoding="utf-8")
        paths = scanner.resolve_paths(tmp_path)
        assert paths == []

    def test_unicode_in_markdown(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Markdown with non-ASCII content is scanned without errors."""
        content = (
            "# Projet\n\n"
            "Prend en charge 9 langages de programmation (fran\u00e7ais).\n\n"
            "\u65e5\u672c\u8a9e\u306e\u30c6\u30b9\u30c8: version 1.7.0.\n"
        )
        md = _write_md(tmp_path, "unicode.md", content)
        result = scanner.scan_file(md)
        # Should find the version string and the language count
        versions = [m for m in result if m.fact_name == "version"]
        assert len(versions) == 1
        assert versions[0].value == "1.7.0"
        lang_matches = [m for m in result if m.fact_name == "language_count"]
        assert len(lang_matches) == 1
        assert lang_matches[0].value == 9

    def test_multiple_version_strings_in_same_file(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """File with both old and new version strings produces multiple mentions."""
        content = (
            "# Changelog\n\n"
            "Updated from version 1.6.0 to version 1.7.0.\n"
        )
        md = _write_md(tmp_path, "versions.md", content)
        result = scanner.scan_file(md)
        versions = [m for m in result if m.fact_name == "version"]
        assert len(versions) == 2
        values = {m.value for m in versions}
        assert "1.6.0" in values
        assert "1.7.0" in values

    def test_scan_nonexistent_file(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """scan_file on a nonexistent file returns empty list gracefully."""
        result = scanner.scan_file(tmp_path / "nonexistent.md")
        assert result == []

    def test_scan_empty_path_list(
        self, scanner: DocScanner,
    ) -> None:
        """scan() with an empty path list returns empty list."""
        result = scanner.scan([])
        assert result == []
