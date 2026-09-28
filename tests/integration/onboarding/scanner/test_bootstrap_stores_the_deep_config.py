"""The bootstrap stores the project's deep config in the root node's extra.

Verifies that read_deep_config() is called during bootstrap, and the result is
stored in the root node's extra under "config" key. Split out of
``tests/test_reindex_config.py`` (BDL-074 ``beadloom-2mj3.7``); the reindex's half
is under ``tests/integration/application/reindex/``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


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
