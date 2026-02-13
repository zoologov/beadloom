"""Tests for beadloom.onboarding.doc_generator — doc skeleton generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.onboarding.doc_generator import (
    _generate_mermaid,
    generate_polish_data,
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

        # Features go under their parent domain directory.
        spec = tmp_path / "docs" / "domains" / "auth" / "features" / "auth-api" / "SPEC.md"
        assert spec.exists()
        content = spec.read_text(encoding="utf-8")
        assert "## Parent" in content
        assert "auth" in content

    def test_skips_root_service(self, tmp_path: Path) -> None:
        nodes = _basic_nodes()
        edges = _basic_edges()
        generate_skeletons(tmp_path, nodes=nodes, edges=edges)

        # Root node "myproject" has no part_of edge — no service file expected.
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


# ---------------------------------------------------------------------------
# Helpers for TestGeneratePolishData
# ---------------------------------------------------------------------------


def _write_graph_yaml(tmp_path: Path, data: dict[str, Any]) -> None:
    """Write a graph YAML file so ``generate_polish_data`` can load it."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "services.yml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


def _default_graph_data() -> dict[str, Any]:
    """Return a minimal graph with root + 2 domains + 1 feature."""
    return {
        "nodes": [
            _root_node(),
            _domain_node("auth"),
            _domain_node("billing"),
            _feature_node("auth-api"),
        ],
        "edges": [
            {"src": "auth", "dst": "myproject", "kind": "part_of"},
            {"src": "billing", "dst": "myproject", "kind": "part_of"},
            {"src": "auth-api", "dst": "auth", "kind": "part_of"},
            {"src": "auth", "dst": "billing", "kind": "depends_on"},
        ],
    }


# ---------------------------------------------------------------------------
# TestGeneratePolishData
# ---------------------------------------------------------------------------


class TestGeneratePolishData:
    """Tests for :func:`generate_polish_data`."""

    def test_returns_nodes_list(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())
        result = generate_polish_data(tmp_path)
        assert "nodes" in result
        assert isinstance(result["nodes"], list)
        assert len(result["nodes"]) > 0

    def test_single_ref_id(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())
        result = generate_polish_data(tmp_path, ref_id="auth")
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["ref_id"] == "auth"

    def test_node_has_symbols_field(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())
        result = generate_polish_data(tmp_path)
        for node in result["nodes"]:
            assert "symbols" in node
            assert isinstance(node["symbols"], list)

    def test_architecture_has_mermaid(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())
        result = generate_polish_data(tmp_path)
        assert "architecture" in result
        assert isinstance(result["architecture"]["mermaid"], str)

    def test_instructions_is_string(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())
        result = generate_polish_data(tmp_path)
        assert isinstance(result["instructions"], str)
        assert len(result["instructions"]) > 0

    def test_existing_docs_included(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())

        # Create existing doc for the "auth" domain.
        doc_dir = tmp_path / "docs" / "domains" / "auth"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_content = "# Auth Domain\n\nAuthentication and authorization."
        (doc_dir / "README.md").write_text(doc_content, encoding="utf-8")

        result = generate_polish_data(tmp_path, ref_id="auth")
        auth_node = result["nodes"][0]
        assert auth_node["existing_docs"] is not None
        assert "Auth Domain" in auth_node["existing_docs"]


# ---------------------------------------------------------------------------
# TestPatchDocsField — docs: field written back to YAML
# ---------------------------------------------------------------------------


class TestPatchDocsField:
    """Tests for ``_patch_docs_field`` and its integration with ``generate_skeletons``."""

    def test_generate_skeletons_writes_docs_field(self, tmp_path: Path) -> None:
        """After skeleton generation, nodes in services.yml must have ``docs:``."""
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
                _service_node("cli"),
                _feature_node("auth-api"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
                {"src": "cli", "dst": "myproject", "kind": "part_of"},
                {"src": "auth-api", "dst": "auth", "kind": "part_of"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        # Run skeleton generation (will load from YAML automatically).
        result = generate_skeletons(tmp_path)
        assert result["files_created"] > 0

        # Re-read the YAML and verify docs: fields were written.
        yml_path = tmp_path / ".beadloom" / "_graph" / "services.yml"
        updated = yaml.safe_load(yml_path.read_text(encoding="utf-8"))

        nodes_by_id = {n["ref_id"]: n for n in updated["nodes"]}

        # Domain node should have docs field.
        assert "docs" in nodes_by_id["auth"]
        assert nodes_by_id["auth"]["docs"] == ["docs/domains/auth/README.md"]

        # Service node should have docs field.
        assert "docs" in nodes_by_id["cli"]
        assert nodes_by_id["cli"]["docs"] == ["docs/services/cli.md"]

        # Feature node should have docs field.
        assert "docs" in nodes_by_id["auth-api"]
        assert nodes_by_id["auth-api"]["docs"] == ["docs/domains/auth/features/auth-api/SPEC.md"]

    def test_existing_docs_field_not_overwritten(self, tmp_path: Path) -> None:
        """Nodes that already have ``docs:`` must keep their original value."""
        existing_docs = ["docs/custom/my-auth.md"]
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                {
                    "ref_id": "auth",
                    "kind": "domain",
                    "summary": "auth domain",
                    "source": "src/auth/",
                    "docs": existing_docs,
                },
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        # Pre-create the doc file at the custom path so _write_if_missing
        # uses the existing docs path (since docs field is set).
        custom_doc = tmp_path / "docs" / "custom" / "my-auth.md"
        custom_doc.parent.mkdir(parents=True, exist_ok=True)
        custom_doc.write_text("# Custom Auth\n", encoding="utf-8")

        generate_skeletons(tmp_path)

        # Re-read and check the docs field is unchanged.
        yml_path = tmp_path / ".beadloom" / "_graph" / "services.yml"
        updated = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        nodes_by_id = {n["ref_id"]: n for n in updated["nodes"]}

        assert nodes_by_id["auth"]["docs"] == existing_docs

    def test_docs_field_only_for_created_files(self, tmp_path: Path) -> None:
        """Skipped (already existing) doc files must NOT get ``docs:`` added."""
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
                _domain_node("billing"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
                {"src": "billing", "dst": "myproject", "kind": "part_of"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        # Pre-create the auth README so it gets skipped.
        auth_doc = tmp_path / "docs" / "domains" / "auth" / "README.md"
        auth_doc.parent.mkdir(parents=True, exist_ok=True)
        auth_doc.write_text("# Existing Auth\n", encoding="utf-8")

        generate_skeletons(tmp_path)

        yml_path = tmp_path / ".beadloom" / "_graph" / "services.yml"
        updated = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        nodes_by_id = {n["ref_id"]: n for n in updated["nodes"]}

        # auth was skipped — no docs: field should be added.
        assert "docs" not in nodes_by_id["auth"]

        # billing was created — docs: field should exist.
        assert "docs" in nodes_by_id["billing"]
        assert nodes_by_id["billing"]["docs"] == ["docs/domains/billing/README.md"]

    def test_no_graph_dir_does_not_crash(self, tmp_path: Path) -> None:
        """When called with explicit nodes/edges and no graph dir, no crash."""
        nodes = _basic_nodes()
        edges = _basic_edges()
        # No .beadloom/_graph/ directory — should not raise.
        result = generate_skeletons(tmp_path, nodes=nodes, edges=edges)
        assert result["files_created"] > 0
