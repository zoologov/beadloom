"""Tests for `beadloom reindex` CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _minimal_project(tmp_path: Path) -> Path:
    """Create a minimal project skeleton with `.beadloom/_graph/` and `docs/`."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / "docs").mkdir()
    return project


class TestReindexCommand:
    def test_reindex_basic(self, tmp_path: Path) -> None:
        """Reindex a minimal project with one node and one doc."""
        # Arrange
        project = _minimal_project(tmp_path)
        graph_dir = project / ".beadloom" / "_graph"
        docs_dir = project / "docs"

        (graph_dir / "test.yml").write_text(
            yaml.dump(
                {
                    "nodes": [
                        {"ref_id": "F1", "kind": "feature", "summary": "Feature 1"},
                    ],
                }
            )
        )
        (docs_dir / "spec.md").write_text("## Spec\n\nContent.\n")

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "Nodes:" in result.output
        assert "Edges:" in result.output
        assert "Docs:" in result.output
        assert "Chunks:" in result.output
        assert "Symbols:" in result.output

    def test_reindex_shows_counts(self, tmp_path: Path) -> None:
        """Reindex a project and verify correct counts in output."""
        # Arrange
        project = _minimal_project(tmp_path)
        graph_dir = project / ".beadloom" / "_graph"
        docs_dir = project / "docs"

        (graph_dir / "graph.yml").write_text(
            yaml.dump(
                {
                    "nodes": [
                        {"ref_id": "F1", "kind": "feature", "summary": "Feature 1"},
                        {"ref_id": "F2", "kind": "feature", "summary": "Feature 2"},
                    ],
                    "edges": [
                        {"src": "F1", "dst": "F2", "kind": "depends_on"},
                    ],
                }
            )
        )
        (docs_dir / "overview.md").write_text("## Overview\n\nProject overview.\n")

        # Add a code file under src/ so symbols can be indexed.
        src_dir = project / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text("# beadloom:feature=F1\ndef handler():\n    pass\n")

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "Nodes:   2" in result.output
        assert "Edges:   1" in result.output
        assert "Docs:    1" in result.output

    def test_reindex_empty_project(self, tmp_path: Path) -> None:
        """Reindex an empty project (dirs exist but no files in them)."""
        # Arrange
        project = _minimal_project(tmp_path)
        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "Nodes:   0" in result.output
        assert "Edges:   0" in result.output
        assert "Docs:    0" in result.output
        assert "Chunks:  0" in result.output
        assert "Symbols: 0" in result.output

    def test_reindex_shows_warnings(self, tmp_path: Path) -> None:
        """Reindex triggers a warning when a doc is referenced by two nodes."""
        # Arrange
        project = _minimal_project(tmp_path)
        graph_dir = project / ".beadloom" / "_graph"
        docs_dir = project / "docs"

        # Two nodes both reference the same doc -- triggers doc-ref conflict.
        (graph_dir / "conflict.yml").write_text(
            yaml.dump(
                {
                    "nodes": [
                        {
                            "ref_id": "A1",
                            "kind": "feature",
                            "summary": "Alpha",
                            "docs": ["docs/shared.md"],
                        },
                        {
                            "ref_id": "A2",
                            "kind": "feature",
                            "summary": "Beta",
                            "docs": ["docs/shared.md"],
                        },
                    ],
                }
            )
        )
        (docs_dir / "shared.md").write_text("## Shared\n\nShared content.\n")

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "[warn]" in result.output

    def test_reindex_shows_errors(self, tmp_path: Path) -> None:
        """Reindex with an edge referencing a non-existent node produces a warning."""
        # Arrange
        project = _minimal_project(tmp_path)
        graph_dir = project / ".beadloom" / "_graph"

        # Edge references node "GHOST" which does not exist.
        (graph_dir / "bad_edge.yml").write_text(
            yaml.dump(
                {
                    "nodes": [
                        {"ref_id": "X1", "kind": "feature", "summary": "Existing"},
                    ],
                    "edges": [
                        {"src": "X1", "dst": "GHOST", "kind": "depends_on"},
                    ],
                }
            )
        )

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        # The graph_loader emits a warning for edges referencing missing nodes.
        assert "[warn]" in result.output
        assert "GHOST" in result.output

    def test_reindex_creates_db(self, tmp_path: Path) -> None:
        """After reindex, the SQLite database file must exist."""
        # Arrange
        project = _minimal_project(tmp_path)
        db_path = project / ".beadloom" / "beadloom.db"
        assert not db_path.exists()

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert db_path.exists()


class TestReindexDocsDirFlag:
    """Tests for --docs-dir CLI flag."""

    def test_docs_dir_flag(self, tmp_path: Path) -> None:
        """--docs-dir flag makes reindex use custom docs directory."""
        # Arrange
        project = _minimal_project(tmp_path)
        custom_docs = project / "documentation"
        custom_docs.mkdir()
        (custom_docs / "guide.md").write_text("## Guide\n\nCustom.\n")

        runner = CliRunner()

        # Act
        result = runner.invoke(
            main,
            ["reindex", "--project", str(project), "--docs-dir", str(custom_docs)],
        )

        # Assert
        assert result.exit_code == 0, result.output
        assert "Docs:    1" in result.output

    def test_docs_dir_flag_overrides_default(self, tmp_path: Path) -> None:
        """--docs-dir flag is used instead of default docs/ directory."""
        # Arrange
        project = _minimal_project(tmp_path)
        # Default docs/ has a file
        (project / "docs" / "default.md").write_text("## Default\n\nDefault.\n")
        # Custom dir has a different file
        custom_docs = project / "doc"
        custom_docs.mkdir()
        (custom_docs / "custom.md").write_text("## Custom\n\nCustom.\n")

        runner = CliRunner()

        # Act
        result = runner.invoke(
            main,
            ["reindex", "--project", str(project), "--docs-dir", str(custom_docs)],
        )

        # Assert
        assert result.exit_code == 0, result.output
        # Should index only from custom dir (1 doc, not from default docs/)
        assert "Docs:    1" in result.output


class TestReindexMissingParserWarning:
    """Tests for missing parser warnings during reindex."""

    def test_reindex_warns_missing_parsers(self, tmp_path: Path) -> None:
        """Reindex with 0 symbols and configured languages shows a warning."""
        from unittest.mock import patch

        # Arrange
        project = _minimal_project(tmp_path)

        # Create config.yml with TypeScript language configured.
        config_content = "languages:\n- .ts\n- .tsx\nscan_paths:\n- src\n"
        (project / ".beadloom" / "config.yml").write_text(config_content)

        # Create a .ts file under src/ (no parser will be available).
        src_dir = project / "src"
        src_dir.mkdir()
        (src_dir / "app.ts").write_text("function hello(): void {}\n")

        runner = CliRunner()

        # Mock get_lang_config to return None for .ts/.tsx (parser not installed).
        def mock_config(ext: str) -> object | None:
            if ext in (".ts", ".tsx"):
                return None
            # Use the real function for other extensions.
            from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

            loader = _EXTENSION_LOADERS.get(ext)
            if loader is None:
                return None
            try:
                return loader()
            except ImportError:
                return None

        with patch(
            "beadloom.context_oracle.code_indexer.get_lang_config",
            side_effect=mock_config,
        ):
            # Also clear cache so mock is used.
            from beadloom.context_oracle.code_indexer import clear_cache

            clear_cache()
            result = runner.invoke(main, ["reindex", "--full", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "No parser available for" in result.output
        assert "beadloom[languages]" in result.output

    def test_reindex_no_warning_when_symbols_found(self, tmp_path: Path) -> None:
        """No warning when symbols are successfully extracted."""
        # Arrange
        project = _minimal_project(tmp_path)

        # Create config.yml with Python language configured.
        config_content = "languages:\n- python\nscan_paths:\n- src\n"
        (project / ".beadloom" / "config.yml").write_text(config_content)

        # Create a .py file under src/ (Python parser is always available).
        src_dir = project / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text("def handler():\n    pass\n")

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--full", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "No parser available" not in result.output

    def test_reindex_no_warning_without_config(self, tmp_path: Path) -> None:
        """No warning when there is no config.yml file."""
        # Arrange
        project = _minimal_project(tmp_path)
        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--full", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "No parser available" not in result.output
