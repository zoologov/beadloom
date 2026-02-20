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
        md = _write_md(tmp_path, "test.md", "Beadloom supports **12** programming languages.\n")
        result = scanner.scan_file(md)
        assert len(result) >= 1
        match = [m for m in result if m.fact_name == "language_count"]
        assert len(match) == 1
        assert match[0].value == 12
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
            "Supports 12 programming languages.\n\n"
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
        md = _write_md(tmp_path, "test.md", "There are 15 LANGUAGES supported.\n")
        result = scanner.scan_file(md)
        matches = [m for m in result if m.fact_name == "language_count"]
        assert len(matches) == 1
        assert matches[0].value == 15


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
            "There are 12 different interesting and very cool things but language is here.\n",
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
            "There are 12 supported programming languages here.\n",
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
            "x = 12  # 12 languages\n"
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
        _write_md(tmp_path, "a.md", "Has 12 languages supported.\n")
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
            "Prend en charge 12 langages de programmation (fran\u00e7ais).\n\n"
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
        assert lang_matches[0].value == 12

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


# ===========================================================================
# Issue #52 — Small numbers (<10) should be skipped for count facts
# ===========================================================================


class TestSmallNumberSkip:
    """Numbers < 10 should not match count-type facts (node_count, edge_count, etc.).

    Small numbers like 2, 3, 5 in SPEC.md examples match too aggressively.
    Version facts are unaffected — only count facts are filtered.
    """

    def test_small_number_skipped_for_node_count(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Number 5 near 'node' keyword should NOT match node_count."""
        md = _write_md(tmp_path, "spec.md", "The graph has 5 nodes in the example.\n")
        result = scanner.scan_file(md)
        node_matches = [m for m in result if m.fact_name == "node_count"]
        assert len(node_matches) == 0

    def test_small_number_skipped_for_edge_count(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Number 3 near 'edge' keyword should NOT match edge_count."""
        md = _write_md(tmp_path, "spec.md", "Connected by 3 edges in this example.\n")
        result = scanner.scan_file(md)
        edge_matches = [m for m in result if m.fact_name == "edge_count"]
        assert len(edge_matches) == 0

    def test_number_10_still_matches_count_fact(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Number 10 (boundary) should still match count facts."""
        md = _write_md(tmp_path, "test.md", "Project has 10 nodes total.\n")
        result = scanner.scan_file(md)
        node_matches = [m for m in result if m.fact_name == "node_count"]
        assert len(node_matches) == 1
        assert node_matches[0].value == 10

    def test_large_number_still_matches_count_fact(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Large numbers should still match count facts normally."""
        md = _write_md(tmp_path, "test.md", "Architecture has 489 nodes.\n")
        result = scanner.scan_file(md)
        node_matches = [m for m in result if m.fact_name == "node_count"]
        assert len(node_matches) == 1
        assert node_matches[0].value == 489

    def test_small_number_2_skipped_for_mcp_tool_count(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Number 2 near 'tool' keyword should NOT match mcp_tool_count."""
        md = _write_md(tmp_path, "spec.md", "Uses 2 tools in the pipeline.\n")
        result = scanner.scan_file(md)
        tool_matches = [m for m in result if m.fact_name == "mcp_tool_count"]
        assert len(tool_matches) == 0


# ===========================================================================
# Issue #53 — Standalone year should be masked as false positive
# ===========================================================================


class TestStandaloneYearFilter:
    """Standalone 4-digit years like '2026' should not match count facts."""

    def test_standalone_year_not_matched(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Standalone year 2026 near 'tool' should NOT match mcp_tool_count."""
        md = _write_md(
            tmp_path, "test.md", "Released in 2026, the tool is stable.\n"
        )
        result = scanner.scan_file(md)
        tool_matches = [m for m in result if m.fact_name == "mcp_tool_count"]
        assert len(tool_matches) == 0

    def test_standalone_year_2025_not_matched(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Year 2025 should also be filtered."""
        md = _write_md(
            tmp_path, "test.md", "Since 2025 the tool count has grown.\n"
        )
        result = scanner.scan_file(md)
        tool_matches = [m for m in result if m.fact_name == "mcp_tool_count"]
        assert len(tool_matches) == 0

    def test_year_in_iso_date_still_filtered(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """ISO date (existing filter) should still work."""
        md = _write_md(tmp_path, "test.md", "Updated 2026-02-20 with new tools.\n")
        result = scanner.scan_file(md)
        assert len(result) == 0


# ===========================================================================
# Issue #54 — SPEC.md files excluded by default
# ===========================================================================


class TestSpecMdExclude:
    """SPEC.md files under _graph/features/ should be excluded by default."""

    def test_spec_md_excluded_from_graph_features(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """_graph/features/*/SPEC.md should be excluded."""
        spec_dir = tmp_path / "_graph" / "features" / "docs-audit"
        spec_dir.mkdir(parents=True)
        _write_md(spec_dir, "SPEC.md", "Has 5 nodes in the example.\n")
        # Also create a normal md file to ensure it IS included
        _write_md(tmp_path, "README.md", "# Project\n")
        paths = scanner.resolve_paths(tmp_path)
        spec_paths = [p for p in paths if "SPEC.md" in str(p)]
        assert len(spec_paths) == 0

    def test_spec_md_excluded_from_beadloom_graph_features(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """.beadloom/_graph/features/*/SPEC.md should be excluded."""
        spec_dir = tmp_path / ".beadloom" / "_graph" / "features" / "docs-audit"
        spec_dir.mkdir(parents=True)
        _write_md(spec_dir, "SPEC.md", "Has 3 edges.\n")
        _write_md(tmp_path, "README.md", "# Project\n")
        paths = scanner.resolve_paths(tmp_path)
        spec_paths = [p for p in paths if "SPEC.md" in str(p)]
        assert len(spec_paths) == 0

    def test_config_exclude_paths(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """docs_audit.exclude_paths from config.yml should exclude matching files."""
        # Create config with exclude pattern
        beadloom_dir = tmp_path / ".beadloom"
        beadloom_dir.mkdir()
        config = beadloom_dir / "config.yml"
        config.write_text(
            "docs_audit:\n  exclude_paths:\n    - 'custom/**/*.md'\n",
            encoding="utf-8",
        )
        # Create files
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        _write_md(custom_dir, "notes.md", "# Notes\n")
        _write_md(tmp_path, "README.md", "# Project\n")
        paths = scanner.resolve_paths(
            tmp_path, config_path=config
        )
        custom_files = [p for p in paths if "custom" in str(p)]
        assert len(custom_files) == 0
        assert any(p.name == "README.md" for p in paths)
