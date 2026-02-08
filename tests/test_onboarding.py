"""Tests for beadloom.onboarding — project bootstrap and import."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from beadloom.onboarding import (
    bootstrap_project,
    classify_doc,
    import_docs,
    interactive_init,
    scan_project,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestScanProject:
    def test_detects_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
        (tmp_path / "src").mkdir()
        result = scan_project(tmp_path)
        assert "pyproject.toml" in result["manifests"]

    def test_detects_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        result = scan_project(tmp_path)
        assert "package.json" in result["manifests"]

    def test_detects_source_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "lib").mkdir()
        result = scan_project(tmp_path)
        assert "src" in result["source_dirs"]
        assert "lib" in result["source_dirs"]

    def test_counts_files(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')")
        (src / "utils.py").write_text("pass")
        result = scan_project(tmp_path)
        assert result["file_count"] >= 2

    def test_empty_project(self, tmp_path: Path) -> None:
        result = scan_project(tmp_path)
        assert result["manifests"] == []
        assert result["source_dirs"] == []


class TestClassifyDoc:
    def test_adr(self, tmp_path: Path) -> None:
        doc = tmp_path / "adr-001.md"
        doc.write_text("# ADR-001\n\n## Status: Accepted\n\n## Decision\nUse SQLite.\n")
        assert classify_doc(doc) == "adr"

    def test_feature(self, tmp_path: Path) -> None:
        doc = tmp_path / "feature.md"
        doc.write_text("# Feature\n\n## User story\nAs a user...\n")
        assert classify_doc(doc) == "feature"

    def test_architecture(self, tmp_path: Path) -> None:
        doc = tmp_path / "arch.md"
        doc.write_text("# Architecture\n\n## System design\nMicroservices.\n")
        assert classify_doc(doc) == "architecture"

    def test_other(self, tmp_path: Path) -> None:
        doc = tmp_path / "readme.md"
        doc.write_text("# README\n\nJust a readme.\n")
        assert classify_doc(doc) == "other"


class TestBootstrapProject:
    def test_creates_graph_dir(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "api.py").write_text("def handler():\n    pass\n")
        bootstrap_project(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        assert graph_dir.is_dir()

    def test_creates_config(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        bootstrap_project(tmp_path)
        config = tmp_path / ".beadloom" / "config.yml"
        assert config.exists()

    def test_creates_yaml_files(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        services = src / "api"
        services.mkdir()
        (services / "__init__.py").write_text("")
        (services / "routes.py").write_text("def list_items():\n    pass\n")
        bootstrap_project(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        yml_files = list(graph_dir.glob("*.yml"))
        assert len(yml_files) >= 1

    def test_generated_yaml_is_valid(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("class App:\n    pass\n")
        bootstrap_project(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        for yml_path in graph_dir.glob("*.yml"):
            data = yaml.safe_load(yml_path.read_text())
            assert data is not None
            if "nodes" in data:
                for node in data["nodes"]:
                    assert "ref_id" in node
                    assert "kind" in node

    def test_idempotent(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        bootstrap_project(tmp_path)
        # Second call should not crash.
        bootstrap_project(tmp_path)


class TestImportDocs:
    def test_classifies_docs(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "adr-001.md").write_text("# ADR\n\n## Decision\nUse X.\n")
        (docs / "readme.md").write_text("# README\n\nHello.\n")
        result = import_docs(tmp_path, docs)
        assert len(result) >= 2
        kinds = {r["kind"] for r in result}
        assert "adr" in kinds

    def test_creates_graph_yaml(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "spec.md").write_text("# Feature Spec\n\n## User story\nStory.\n")
        (tmp_path / ".beadloom" / "_graph").mkdir(parents=True)
        import_docs(tmp_path, docs)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        yml_files = list(graph_dir.glob("*.yml"))
        assert len(yml_files) >= 1

    def test_empty_docs(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        result = import_docs(tmp_path, docs)
        assert result == []


class TestInitCli:
    def test_init_bootstrap(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.cli import main

        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    pass\n")
        runner = CliRunner()
        result = runner.invoke(
            main, ["init", "--bootstrap", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".beadloom" / "_graph").is_dir()

    def test_init_import(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.cli import main

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hello\n\nWorld.\n")
        (tmp_path / ".beadloom" / "_graph").mkdir(parents=True)
        runner = CliRunner()
        result = runner.invoke(
            main, ["init", "--import", str(docs), "--project", str(tmp_path)]
        )
        assert result.exit_code == 0, result.output

    def test_init_interactive_bootstrap(self, tmp_path: Path) -> None:
        """init without flags should trigger interactive mode."""
        from unittest.mock import patch

        from click.testing import CliRunner

        from beadloom.cli import main

        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    pass\n")

        # Mock rich.prompt to avoid actual terminal interaction.
        with patch("rich.prompt.Prompt.ask", return_value="bootstrap"), \
             patch("rich.console.Console"):
            runner = CliRunner()
            result = runner.invoke(
                main, ["init", "--project", str(tmp_path)]
            )
        assert result.exit_code == 0, result.output


class TestInteractiveInit:
    """Tests for interactive init mode."""

    def test_bootstrap_mode(self, tmp_path: Path) -> None:
        """Interactive init with bootstrap selection."""
        from unittest.mock import patch

        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    pass\n")

        with patch("rich.prompt.Prompt.ask", return_value="bootstrap"), \
             patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        assert (tmp_path / ".beadloom" / "_graph").is_dir()

    def test_import_mode(self, tmp_path: Path) -> None:
        """Interactive init with import selection."""
        from unittest.mock import patch

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hello\n\nWorld.\n")

        with patch("rich.prompt.Prompt.ask", return_value="import"), \
             patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "import"

    def test_reinit_cancel(self, tmp_path: Path) -> None:
        """Re-init detection with cancel choice."""
        from unittest.mock import patch

        (tmp_path / ".beadloom").mkdir()

        with patch("rich.prompt.Prompt.ask", return_value="cancel"), \
             patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "cancelled"
        assert result["reinit"] is False

    def test_reinit_overwrite(self, tmp_path: Path) -> None:
        """Re-init detection with overwrite choice."""
        from unittest.mock import patch

        (tmp_path / ".beadloom").mkdir()
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    pass\n")

        with patch("rich.prompt.Prompt.ask", side_effect=["overwrite", "bootstrap"]), \
             patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["reinit"] is True
        assert result["mode"] == "bootstrap"
