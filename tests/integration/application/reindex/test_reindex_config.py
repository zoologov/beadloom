"""The reindex stores the project's deep config in the root node's ``nodes.extra``.

Verifies that read_deep_config() is called during reindex, and the result is
stored in the root node's nodes.extra under "config" key. The bootstrap's half
is under ``tests/integration/onboarding/scanner/`` (split by node, BDL-074
``beadloom-2mj3.7``).
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
        from beadloom.application.reindex import reindex

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

        from beadloom.application.reindex import reindex

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

        from beadloom.application.reindex import reindex

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

        from beadloom.application.reindex import reindex

        # Should not raise.
        result = reindex(project)
        assert result.nodes_loaded == 1
