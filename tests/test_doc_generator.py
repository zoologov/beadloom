"""Tests for beadloom.onboarding.doc_generator — doc skeleton generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.onboarding.doc_generator import (
    _generate_mermaid,
    generate_skeletons,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _root_node() -> dict[str, Any]:
    return {"ref_id": "myproject", "kind": "service", "source": "", "summary": "Root"}


def _domain_node(name: str = "auth") -> dict[str, Any]:
    return {
        "ref_id": name,
        "kind": "domain",
        "summary": f"{name} domain",
        "source": f"src/{name}/",
    }


def _service_node(name: str = "cli") -> dict[str, Any]:
    return {
        "ref_id": name,
        "kind": "service",
        "summary": f"{name} service",
        "source": f"src/services/{name}.py",
    }


def _feature_node(name: str = "auth-api") -> dict[str, Any]:
    return {
        "ref_id": name,
        "kind": "feature",
        "summary": f"{name} feature",
        "source": f"src/{name}.py",
    }


def _basic_edges() -> list[dict[str, Any]]:
    return [
        {"src": "auth", "dst": "myproject", "kind": "part_of"},
        {"src": "cli", "dst": "myproject", "kind": "part_of"},
        {"src": "auth-api", "dst": "auth", "kind": "part_of"},
        {"src": "auth", "dst": "cli", "kind": "depends_on"},
    ]


def _basic_nodes() -> list[dict[str, Any]]:
    return [_root_node(), _domain_node(), _service_node(), _feature_node()]


# ---------------------------------------------------------------------------
# TestGenerateSkeletons
# ---------------------------------------------------------------------------


class TestGenerateSkeletons:
    """Tests for :func:`generate_skeletons`."""

    def test_creates_architecture_md(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        arch = tmp_path / "docs" / "architecture.md"
        assert arch.exists()
        content = arch.read_text(encoding="utf-8")
        assert "myproject" in content
        assert "## Domains" in content
        assert "## Services" in content

    def test_creates_domain_readme(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        readme = tmp_path / "docs" / "domains" / "auth" / "README.md"
        assert readme.exists()
        content = readme.read_text(encoding="utf-8")
        assert "auth" in content
        assert "## Source" in content

    def test_creates_service_md(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        svc = tmp_path / "docs" / "services" / "cli.md"
        assert svc.exists()

    def test_creates_feature_spec(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        spec = tmp_path / "docs" / "features" / "auth-api" / "SPEC.md"
        assert spec.exists()
        content = spec.read_text(encoding="utf-8")
        assert "## Parent" in content
        assert "auth" in content

    def test_skips_root_service(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        # Root node "myproject" has empty source — no service file expected.
        root_svc = tmp_path / "docs" / "services" / "myproject.md"
        assert not root_svc.exists()

    def test_skips_existing_files(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir(parents=True)
        sentinel = "DO NOT OVERWRITE"
        (docs / "architecture.md").write_text(sentinel, encoding="utf-8")

        nodes = _basic_nodes()
        edges = _basic_edges()
        result = generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        # File content must be preserved.
        assert (docs / "architecture.md").read_text(encoding="utf-8") == sentinel
        assert result["files_skipped"] >= 1

    def test_returns_counts(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        result = generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        assert result["files_created"] > 0
        assert result["files_skipped"] == 0

    def test_loads_from_yaml_when_no_args(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)

        data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("billing"),
            ],
            "edges": [
                {"src": "billing", "dst": "myproject", "kind": "part_of"},
            ],
        }
        (graph_dir / "services.yml").write_text(
            yaml.dump(data, default_flow_style=False), encoding="utf-8"
        )

        # Call WITHOUT explicit nodes/edges — should load from YAML.
        result = generate_skeletons(tmp_path)
        assert result["files_created"] > 0

        readme = tmp_path / "docs" / "domains" / "billing" / "README.md"
        assert readme.exists()

    def test_mermaid_in_architecture(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        arch = tmp_path / "docs" / "architecture.md"
        content = arch.read_text(encoding="utf-8")
        assert "```mermaid" in content

    def test_enrich_marker(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        arch = tmp_path / "docs" / "architecture.md"
        content = arch.read_text(encoding="utf-8")
        assert "<!-- enrich with: beadloom docs polish -->" in content

        readme = tmp_path / "docs" / "domains" / "auth" / "README.md"
        content = readme.read_text(encoding="utf-8")
        assert "<!-- enrich with: beadloom docs polish -->" in content


# ---------------------------------------------------------------------------
# TestGenerateMermaid
# ---------------------------------------------------------------------------


class TestGenerateMermaid:
    """Tests for :func:`_generate_mermaid`."""

    def test_empty_edges(self) -> None:
        result = _generate_mermaid([], [])
        assert result == ""

    def test_depends_on_arrow(self) -> None:
        edges: list[dict[str, Any]] = [
            {"src": "auth", "dst": "db", "kind": "depends_on"},
        ]
        result = _generate_mermaid([], edges)
        assert "auth --> db" in result

    def test_part_of_arrow(self) -> None:
        edges: list[dict[str, Any]] = [
            {"src": "auth", "dst": "root", "kind": "part_of"},
        ]
        result = _generate_mermaid([], edges)
        assert "auth -.-> root" in result
