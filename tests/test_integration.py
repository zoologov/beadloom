"""End-to-end integration tests for the full beadloom pipeline.

Each test creates an isolated mini project in ``tmp_path`` (NOT the shared
``tmp_project`` fixture) and exercises one or more CLI commands through
``click.testing.CliRunner``.

The test project contains:
- ``src/myapp/core.py`` with a beadloom annotation
- ``docs/overview.md`` with Markdown sections
- ``.beadloom/_graph/services.yml`` with 2 nodes and 1 edge
- ``.git/hooks/`` directory (for hook-related tests)
"""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helper: create a realistic mini project
# ---------------------------------------------------------------------------


def _create_mini_project(tmp_path: Path, *, with_git: bool = False) -> Path:
    """Build a self-contained project directory for integration testing.

    Parameters
    ----------
    tmp_path:
        Temporary directory provided by pytest.
    with_git:
        If True, also create ``.git/hooks/`` (needed for hook tests).

    Returns
    -------
    Path
        Root of the created project.
    """
    project = tmp_path / "project"
    project.mkdir()

    # -- .beadloom/_graph/services.yml ---------------------------------
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)

    services_yml: dict[str, object] = {
        "nodes": [
            {
                "ref_id": "myapp",
                "kind": "service",
                "summary": "Test application",
                "source": "src/myapp/",
                "docs": ["docs/overview.md"],
            },
            {
                "ref_id": "core-module",
                "kind": "domain",
                "summary": "Core module",
            },
        ],
        "edges": [
            {
                "src": "core-module",
                "dst": "myapp",
                "kind": "part_of",
            },
        ],
    }
    (graph_dir / "services.yml").write_text(
        yaml.dump(services_yml, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    # -- docs/overview.md ----------------------------------------------
    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "overview.md").write_text(
        "## Overview\n\nThis is the project overview.\n\n## API\n\nPublic API description.\n",
        encoding="utf-8",
    )

    # -- src/myapp/core.py ---------------------------------------------
    src_dir = project / "src" / "myapp"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "core.py").write_text(
        "# beadloom:service=myapp\n"
        "def process() -> None:\n"
        '    """Core processing logic."""\n'
        "    pass\n",
        encoding="utf-8",
    )

    # -- .git/hooks/ (optional) ----------------------------------------
    if with_git:
        hooks_dir = project / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)

    return project


def _reindex_project(project: Path) -> None:
    """Run ``beadloom reindex`` on *project* via the CLI runner."""
    runner = CliRunner()
    result = runner.invoke(main, ["reindex", "--project", str(project)])
    assert result.exit_code == 0, f"reindex failed: {result.output}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInitBootstrap:
    """``beadloom init --bootstrap`` on a fresh project."""

    def test_bootstrap_creates_graph_and_config(self, tmp_path: Path) -> None:
        # Arrange — bare project with source code only (no .beadloom yet).
        project = tmp_path / "fresh"
        project.mkdir()
        src = project / "src" / "myapp"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("", encoding="utf-8")
        (src / "core.py").write_text("def run() -> None:\n    pass\n", encoding="utf-8")

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["init", "--bootstrap", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        graph_dir = project / ".beadloom" / "_graph"
        assert graph_dir.is_dir(), "graph directory should be created"
        yml_files = list(graph_dir.glob("*.yml"))
        assert len(yml_files) >= 1, "at least one YAML graph file expected"
        config_path = project / ".beadloom" / "config.yml"
        assert config_path.exists(), "config.yml should be created"
        # Verify the config is valid YAML.
        config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert config_data is not None
        assert "scan_paths" in config_data


class TestReindex:
    """``beadloom reindex`` on the mini project."""

    def test_reindex_creates_db_with_correct_counts(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        db_path = project / ".beadloom" / "beadloom.db"
        assert not db_path.exists()

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["reindex", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert db_path.exists(), "SQLite DB must be created"
        assert "Nodes:   2" in result.output
        assert "Edges:   1" in result.output
        assert "Docs:    1" in result.output
        # There should be at least 1 chunk (from the ## sections).
        assert "Chunks:" in result.output
        # At least one symbol from core.py (the ``process`` function).
        assert "Symbols:" in result.output

    def test_reindex_idempotent(self, tmp_path: Path) -> None:
        """Running reindex twice should not fail."""
        project = _create_mini_project(tmp_path)
        runner = CliRunner()

        first = runner.invoke(main, ["reindex", "--project", str(project)])
        assert first.exit_code == 0, first.output
        assert "Nodes:   2" in first.output

        # Second run is incremental — nothing changed, counts are 0.
        second = runner.invoke(main, ["reindex", "--project", str(project)])
        assert second.exit_code == 0, second.output

    def test_reindex_full_flag(self, tmp_path: Path) -> None:
        """--full forces a complete rebuild."""
        project = _create_mini_project(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["reindex", "--project", str(project)])

        second = runner.invoke(
            main,
            ["reindex", "--project", str(project), "--full"],
        )
        assert second.exit_code == 0, second.output
        assert "Nodes:   2" in second.output


class TestCtx:
    """``beadloom ctx`` — context bundle retrieval."""

    def test_ctx_markdown_output(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["ctx", "myapp", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert "myapp" in result.output
        assert "service" in result.output.lower()

    def test_ctx_json_output(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["ctx", "myapp", "--json", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["version"] == 2
        assert data["focus"]["ref_id"] == "myapp"
        assert data["focus"]["kind"] == "service"
        assert data["focus"]["summary"] == "Test application"
        # Graph should contain both nodes and the edge.
        node_ids = {n["ref_id"] for n in data["graph"]["nodes"]}
        assert "myapp" in node_ids
        assert "core-module" in node_ids
        assert len(data["graph"]["edges"]) >= 1

    def test_ctx_includes_text_chunks(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["ctx", "myapp", "--json", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data["text_chunks"]) >= 1, "doc chunks should be included"

    def test_ctx_includes_code_symbols(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["ctx", "myapp", "--json", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data["code_symbols"]) >= 1, "code symbols should be present"
        symbol_names = {s["symbol_name"] for s in data["code_symbols"]}
        assert "process" in symbol_names

    def test_ctx_unknown_ref_id(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["ctx", "NONEXISTENT", "--project", str(project)])

        # Assert
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestGraph:
    """``beadloom graph`` — knowledge graph output."""

    def test_graph_mermaid_output(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["graph", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        # Mermaid output starts with ``graph LR``.
        assert "graph LR" in result.output
        # Contains nodes.
        assert "myapp" in result.output
        assert "core_module" in result.output or "core-module" in result.output
        # Contains at least one edge.
        assert "-->" in result.output

    def test_graph_json_output(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["graph", "--json", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) >= 1
        node_ids = {n["ref_id"] for n in data["nodes"]}
        assert "myapp" in node_ids
        assert "core-module" in node_ids

    def test_graph_with_ref_id_filter(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["graph", "myapp", "--json", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        node_ids = {n["ref_id"] for n in data["nodes"]}
        assert "myapp" in node_ids


class TestDoctor:
    """``beadloom doctor`` — validation checks."""

    def test_doctor_passes_on_valid_project(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["doctor", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        # Should contain at least some check results.
        assert "[ok]" in result.output or "[info]" in result.output

    def test_doctor_reports_nodes_without_docs(self, tmp_path: Path) -> None:
        """core-module has no docs linked — doctor should report INFO."""
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["doctor", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        # core-module has no ``docs`` list → [info] about missing doc.
        assert "core-module" in result.output


class TestStatus:
    """``beadloom status`` — project index statistics."""

    def test_status_shows_counts(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["status", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        # Rich-formatted output contains key metrics.
        assert "Nodes:" in result.output or "Nodes" in result.output
        assert "Edges:" in result.output or "Edges" in result.output
        assert "Docs:" in result.output or "Docs" in result.output
        assert "Symbols:" in result.output or "symbols" in result.output.lower()
        # 2 nodes, at least 1 edge.
        assert "2" in result.output


class TestSyncCheck:
    """``beadloom sync-check`` — doc-code synchronization."""

    def test_sync_check_ok(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["sync-check", "--project", str(project)])

        # Assert
        # Exit code 0 means all OK (or no sync pairs).
        assert result.exit_code == 0, result.output

    def test_sync_check_porcelain(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["sync-check", "--porcelain", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        # If pairs exist, porcelain uses TAB-separated format.
        if result.output.strip():
            assert "\t" in result.output

    def test_sync_check_detects_stale(self, tmp_path: Path) -> None:
        """Modify code after reindex — sync-check should detect staleness."""
        # Arrange
        project = _create_mini_project(tmp_path)
        _reindex_project(project)

        # Mutate a code file to make the hash diverge from sync_state.
        from beadloom.infrastructure.db import open_db

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        conn.execute("UPDATE sync_state SET code_hash_at_sync = 'STALE_HASH'")
        conn.commit()
        conn.close()

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["sync-check", "--project", str(project)])

        # Assert — exit code 2 means stale pairs found.
        assert result.exit_code == 2


class TestSetupMcp:
    """``beadloom setup-mcp`` — MCP server configuration."""

    def test_setup_mcp_creates_file(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        mcp_path = project / ".mcp.json"
        assert not mcp_path.exists()

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["setup-mcp", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert mcp_path.exists()
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert "mcpServers" in data
        assert "beadloom" in data["mcpServers"]
        server = data["mcpServers"]["beadloom"]
        assert "command" in server
        assert "mcp-serve" in server["args"]

    def test_setup_mcp_preserves_existing_servers(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path)
        existing = {"mcpServers": {"other-tool": {"command": "other"}}}
        (project / ".mcp.json").write_text(json.dumps(existing), encoding="utf-8")

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["setup-mcp", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        data = json.loads((project / ".mcp.json").read_text(encoding="utf-8"))
        assert "other-tool" in data["mcpServers"]
        assert "beadloom" in data["mcpServers"]

    def test_setup_mcp_remove(self, tmp_path: Path) -> None:
        # Arrange — install first.
        project = _create_mini_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["setup-mcp", "--project", str(project)])

        # Act
        result = runner.invoke(main, ["setup-mcp", "--remove", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        data = json.loads((project / ".mcp.json").read_text(encoding="utf-8"))
        assert "beadloom" not in data["mcpServers"]


class TestInstallHooks:
    """``beadloom install-hooks`` — Git pre-commit hook management."""

    def test_install_hooks_creates_pre_commit(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path, with_git=True)
        hook_path = project / ".git" / "hooks" / "pre-commit"
        assert not hook_path.exists()

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["install-hooks", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert hook_path.exists()
        content = hook_path.read_text(encoding="utf-8")
        assert "beadloom" in content
        assert "sync-check" in content
        # Check that the file is executable.
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR

    def test_install_hooks_block_mode(self, tmp_path: Path) -> None:
        # Arrange
        project = _create_mini_project(tmp_path, with_git=True)

        runner = CliRunner()

        # Act
        result = runner.invoke(
            main, ["install-hooks", "--mode", "block", "--project", str(project)]
        )

        # Assert
        assert result.exit_code == 0, result.output
        hook_path = project / ".git" / "hooks" / "pre-commit"
        content = hook_path.read_text(encoding="utf-8")
        assert "exit 1" in content

    def test_install_hooks_remove(self, tmp_path: Path) -> None:
        # Arrange — install first.
        project = _create_mini_project(tmp_path, with_git=True)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        hook_path = project / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()

        # Act
        result = runner.invoke(main, ["install-hooks", "--remove", "--project", str(project)])

        # Assert
        assert result.exit_code == 0, result.output
        assert not hook_path.exists()

    def test_install_hooks_no_git_dir(self, tmp_path: Path) -> None:
        """Without ``.git/hooks/`` the command should fail gracefully."""
        # Arrange — no with_git=True, so .git does not exist.
        project = _create_mini_project(tmp_path, with_git=False)

        runner = CliRunner()

        # Act
        result = runner.invoke(main, ["install-hooks", "--project", str(project)])

        # Assert
        assert result.exit_code != 0


class TestFullPipeline:
    """End-to-end: bootstrap → reindex → ctx → graph → doctor → status.

    This test exercises the full lifecycle in a single test method to verify
    that the commands compose correctly.
    """

    def test_full_pipeline_flow(self, tmp_path: Path) -> None:
        """Run the complete beadloom pipeline on a realistic mini project."""
        # -- 1. Create the mini project ---------------------------------
        project = _create_mini_project(tmp_path, with_git=True)
        runner = CliRunner()

        # -- 2. Reindex -------------------------------------------------
        result = runner.invoke(main, ["reindex", "--project", str(project)])
        assert result.exit_code == 0, f"reindex failed: {result.output}"
        assert "Nodes:   2" in result.output
        assert "Edges:   1" in result.output

        # -- 3. ctx (JSON) — verify full bundle -------------------------
        result = runner.invoke(main, ["ctx", "myapp", "--json", "--project", str(project)])
        assert result.exit_code == 0, f"ctx failed: {result.output}"
        bundle = json.loads(result.output)
        assert bundle["version"] == 2
        assert bundle["focus"]["ref_id"] == "myapp"
        assert len(bundle["graph"]["nodes"]) >= 2

        # -- 4. graph (Mermaid) -----------------------------------------
        result = runner.invoke(main, ["graph", "--project", str(project)])
        assert result.exit_code == 0, f"graph failed: {result.output}"
        assert "graph LR" in result.output
        assert "-->" in result.output

        # -- 5. graph (JSON) --------------------------------------------
        result = runner.invoke(main, ["graph", "--json", "--project", str(project)])
        assert result.exit_code == 0, f"graph --json failed: {result.output}"
        graph_data = json.loads(result.output)
        assert len(graph_data["nodes"]) == 2
        assert len(graph_data["edges"]) >= 1

        # -- 6. doctor --------------------------------------------------
        result = runner.invoke(main, ["doctor", "--project", str(project)])
        assert result.exit_code == 0, f"doctor failed: {result.output}"

        # -- 7. status --------------------------------------------------
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code == 0, f"status failed: {result.output}"
        assert "Nodes:" in result.output

        # -- 8. sync-check ----------------------------------------------
        result = runner.invoke(main, ["sync-check", "--project", str(project)])
        assert result.exit_code == 0, f"sync-check failed: {result.output}"

        # -- 9. setup-mcp -----------------------------------------------
        result = runner.invoke(main, ["setup-mcp", "--project", str(project)])
        assert result.exit_code == 0, f"setup-mcp failed: {result.output}"
        mcp_data = json.loads((project / ".mcp.json").read_text(encoding="utf-8"))
        assert "beadloom" in mcp_data["mcpServers"]

        # -- 10. install-hooks ------------------------------------------
        result = runner.invoke(main, ["install-hooks", "--project", str(project)])
        assert result.exit_code == 0, f"install-hooks failed: {result.output}"
        hook = project / ".git" / "hooks" / "pre-commit"
        assert hook.exists()

        # -- 11. remove hooks -------------------------------------------
        result = runner.invoke(main, ["install-hooks", "--remove", "--project", str(project)])
        assert result.exit_code == 0, f"install-hooks --remove failed: {result.output}"
        assert not hook.exists()
