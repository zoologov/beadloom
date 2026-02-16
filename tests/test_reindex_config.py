"""Tests for deep config integration into bootstrap and reindex.

Verifies that read_deep_config() is called during bootstrap and reindex,
and the result is stored in the root node's nodes.extra under "config" key.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import open_db

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal Beadloom project structure."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    return tmp_path


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / ".beadloom" / "beadloom.db"


class TestReindexDeepConfig:
    """Deep config stored in root node's extra during reindex."""

    def test_reindex_stores_pyproject_config_in_root_extra(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Reindex with pyproject.toml stores config in root node's extra."""
        # Arrange: create a root node in the graph and a pyproject.toml.
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: myproject\n"
            "    kind: service\n"
            '    summary: "Root: myproject"\n'
            "    source: ''\n"
            "  - ref_id: api\n"
            "    kind: domain\n"
            '    summary: "API domain"\n'
            "edges:\n"
            "  - src: api\n"
            "    dst: myproject\n"
            "    kind: part_of\n"
        )
        (project / "pyproject.toml").write_text(
            "[project]\n"
            'name = "myproject"\n'
            "\n"
            "[project.scripts]\n"
            'myproject = "myproject.cli:main"\n'
            "\n"
            "[tool.pytest.ini_options]\n"
            'testpaths = ["tests"]\n'
        )

        # Act
        from beadloom.infrastructure.reindex import reindex

        reindex(project)

        # Assert: root node's extra has "config" with scripts and pytest sections.
        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("myproject",)).fetchone()
        assert row is not None
        extra = json.loads(row["extra"])
        assert "config" in extra
        config = extra["config"]
        assert "scripts" in config
        assert config["scripts"]["myproject"] == "myproject.cli:main"
        assert "pytest" in config
        conn.close()

    def test_reindex_stores_package_json_config(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Reindex with package.json stores config in root node's extra."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: webapp\n"
            "    kind: service\n"
            '    summary: "Root: webapp"\n'
            "    source: ''\n"
        )
        (project / "package.json").write_text(
            json.dumps(
                {
                    "name": "webapp",
                    "scripts": {
                        "dev": "next dev",
                        "build": "next build",
                    },
                    "engines": {"node": ">=18"},
                }
            )
        )

        from beadloom.infrastructure.reindex import reindex

        reindex(project)

        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("webapp",)).fetchone()
        assert row is not None
        extra = json.loads(row["extra"])
        assert "config" in extra
        config = extra["config"]
        assert "scripts" in config
        assert config["scripts"]["dev"] == "next dev"
        assert "engines" in config
        conn.close()

    def test_reindex_no_config_files_empty_config(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """When no config files exist, config is stored as empty dict."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: bare\n"
            "    kind: service\n"
            '    summary: "Root: bare"\n'
            "    source: ''\n"
        )

        from beadloom.infrastructure.reindex import reindex

        reindex(project)

        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("bare",)).fetchone()
        assert row is not None
        extra = json.loads(row["extra"])
        assert "config" in extra
        assert extra["config"] == {}
        conn.close()

    def test_reindex_no_root_node_skips_gracefully(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """When there is no root node (no empty source), reindex completes without error."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: child\n"
            "    kind: domain\n"
            '    summary: "Child node"\n'
            "    source: 'src/child/'\n"
        )
        (project / "pyproject.toml").write_text(
            "[project]\nname = 'test'\n[project.scripts]\ntest = 'test:main'\n"
        )

        from beadloom.infrastructure.reindex import reindex

        # Should not raise.
        result = reindex(project)
        assert result.nodes_loaded == 1


class TestBootstrapDeepConfig:
    """Deep config stored in root node's extra during bootstrap."""

    def test_bootstrap_stores_pyproject_config(self, tmp_path: Path) -> None:
        """bootstrap_project stores deep config in root node's extra."""
        # Arrange: create a project with pyproject.toml and source dirs.
        src_dir = tmp_path / "src" / "myapp"
        src_dir.mkdir(parents=True)
        (src_dir / "main.py").write_text("def main():\n    pass\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\n\n[project.scripts]\nmyapp = "myapp.main:main"\n'
        )

        # Act
        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)

        # Assert: root node in result has config in extra.
        nodes = result["nodes"]
        root_nodes = [n for n in nodes if n.get("source") == ""]
        assert len(root_nodes) == 1
        root_node = root_nodes[0]
        extra = json.loads(root_node.get("extra", "{}"))
        assert "config" in extra
        assert "scripts" in extra["config"]
        assert extra["config"]["scripts"]["myapp"] == "myapp.main:main"

    def test_bootstrap_stores_package_json_config(self, tmp_path: Path) -> None:
        """bootstrap_project stores package.json config in root node's extra."""
        src_dir = tmp_path / "src" / "webapp"
        src_dir.mkdir(parents=True)
        (src_dir / "index.ts").write_text("export function hello() {}\n")
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "webapp",
                    "scripts": {"dev": "vite", "build": "vite build"},
                    "workspaces": ["packages/*"],
                }
            )
        )

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)

        nodes = result["nodes"]
        root_nodes = [n for n in nodes if n.get("source") == ""]
        assert len(root_nodes) == 1
        root_node = root_nodes[0]
        extra = json.loads(root_node.get("extra", "{}"))
        assert "config" in extra
        assert "scripts" in extra["config"]
        assert extra["config"]["scripts"]["dev"] == "vite"
        assert "workspaces" in extra["config"]

    def test_bootstrap_config_preserved_with_readme_data(self, tmp_path: Path) -> None:
        """Deep config and README data coexist in root node's extra."""
        src_dir = tmp_path / "src" / "myapp"
        src_dir.mkdir(parents=True)
        (src_dir / "main.py").write_text("def main():\n    pass\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\n\n[project.scripts]\nmyapp = "myapp.main:main"\n'
        )
        (tmp_path / "README.md").write_text("# myapp\n\nA Python application.\n")

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)

        nodes = result["nodes"]
        root_nodes = [n for n in nodes if n.get("source") == ""]
        assert len(root_nodes) == 1
        root_node = root_nodes[0]
        extra = json.loads(root_node.get("extra", "{}"))
        # Both config and readme data should coexist.
        assert "config" in extra
        assert "scripts" in extra["config"]
        assert "readme_description" in extra
