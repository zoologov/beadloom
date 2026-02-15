"""Tests for beadloom.onboarding.doc_generator — doc skeleton generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.onboarding.doc_generator import (
    _generate_mermaid,
    format_polish_text,
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


# ---------------------------------------------------------------------------
# Helpers for SQLite edge tests
# ---------------------------------------------------------------------------


def _create_sqlite_db(tmp_path: Path) -> Path:
    """Create a minimal beadloom.db with nodes and edges tables."""
    import sqlite3

    db_dir = tmp_path / ".beadloom"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "beadloom.db"

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS nodes ("
        "  ref_id TEXT PRIMARY KEY,"
        "  kind TEXT NOT NULL,"
        "  summary TEXT NOT NULL DEFAULT '',"
        "  source TEXT,"
        "  extra TEXT DEFAULT '{}'"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS edges ("
        "  src_ref_id TEXT NOT NULL,"
        "  dst_ref_id TEXT NOT NULL,"
        "  kind TEXT NOT NULL,"
        "  extra TEXT DEFAULT '{}',"
        "  PRIMARY KEY (src_ref_id, dst_ref_id, kind)"
        ")"
    )
    conn.commit()
    conn.close()
    return db_path


def _insert_nodes(db_path: Path, nodes: list[dict[str, Any]]) -> None:
    """Insert node records into the database."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    for n in nodes:
        conn.execute(
            "INSERT OR REPLACE INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (n["ref_id"], n.get("kind", "domain"), n.get("summary", ""), n.get("source", "")),
        )
    conn.commit()
    conn.close()


def _insert_edges(db_path: Path, edges: list[tuple[str, str, str]]) -> None:
    """Insert edge records into the database.

    Each edge is a tuple of ``(src_ref_id, dst_ref_id, kind)``.
    """
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    for src, dst, kind in edges:
        conn.execute(
            "INSERT OR REPLACE INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# TestPolishDataSQLiteEdges
# ---------------------------------------------------------------------------


class TestPolishDataSQLiteEdges:
    """Tests that ``generate_polish_data`` reads depends_on edges from SQLite."""

    def test_polish_data_includes_sqlite_edges(self, tmp_path: Path) -> None:
        """Edges from SQLite are merged into polish data nodes."""
        # Write YAML graph — only part_of edges.
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

        # Create SQLite DB with depends_on edges (simulates post-reindex).
        db_path = _create_sqlite_db(tmp_path)
        _insert_nodes(db_path, graph_data["nodes"])
        _insert_edges(
            db_path,
            [
                ("auth", "billing", "depends_on"),
            ],
        )

        result = generate_polish_data(tmp_path, ref_id="auth")
        auth_node = result["nodes"][0]

        # auth depends_on billing (from SQLite).
        assert "billing" in auth_node["depends_on"]

    def test_polish_data_includes_used_by_from_sqlite(self, tmp_path: Path) -> None:
        """Reverse depends_on edges appear as used_by."""
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

        db_path = _create_sqlite_db(tmp_path)
        _insert_nodes(db_path, graph_data["nodes"])
        _insert_edges(
            db_path,
            [
                ("billing", "auth", "depends_on"),
            ],
        )

        result = generate_polish_data(tmp_path, ref_id="auth")
        auth_node = result["nodes"][0]

        # billing depends_on auth => auth used_by billing.
        assert "billing" in auth_node["used_by"]

    def test_polish_data_no_duplicate_edges(self, tmp_path: Path) -> None:
        """Edges present in both YAML and SQLite are not duplicated."""
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
                _domain_node("billing"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
                {"src": "billing", "dst": "myproject", "kind": "part_of"},
                {"src": "auth", "dst": "billing", "kind": "depends_on"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        # Same edge in SQLite.
        db_path = _create_sqlite_db(tmp_path)
        _insert_nodes(db_path, graph_data["nodes"])
        _insert_edges(
            db_path,
            [
                ("auth", "billing", "depends_on"),
            ],
        )

        result = generate_polish_data(tmp_path, ref_id="auth")
        auth_node = result["nodes"][0]

        # Should have exactly one entry for billing.
        assert auth_node["depends_on"].count("billing") == 1

    def test_polish_text_without_db(self, tmp_path: Path) -> None:
        """Polish data works gracefully when no SQLite DB exists."""
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        # No SQLite DB created — should not raise.
        result = generate_polish_data(tmp_path)
        assert "nodes" in result
        assert len(result["nodes"]) > 0


# ---------------------------------------------------------------------------
# TestFormatPolishText
# ---------------------------------------------------------------------------


class TestFormatPolishText:
    """Tests for :func:`format_polish_text`."""

    def test_polish_text_format_multiline(self, tmp_path: Path) -> None:
        """Text output contains multiple lines with node info and instructions."""
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
                _domain_node("billing"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
                {"src": "billing", "dst": "myproject", "kind": "part_of"},
                {"src": "auth", "dst": "billing", "kind": "depends_on"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        data = generate_polish_data(tmp_path)
        text = format_polish_text(data)

        lines = text.strip().split("\n")
        # Must be multi-line (not a single AI prompt string).
        assert len(lines) > 5

        # Must contain project name.
        assert "myproject" in text

        # Must contain node ref_ids.
        assert "auth" in text
        assert "billing" in text

        # Must contain section markers.
        assert "## auth (domain)" in text
        assert "## billing (domain)" in text

        # Must contain dependency info.
        assert "Depends on:" in text
        assert "Used by:" in text

        # Must contain instructions at the end.
        assert "---" in text
        assert "enriching documentation" in text

    def test_polish_text_contains_node_count(self, tmp_path: Path) -> None:
        """Text header shows count of nodes needing enrichment."""
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        data = generate_polish_data(tmp_path)
        text = format_polish_text(data)

        assert "Nodes needing enrichment:" in text

    def test_polish_text_shows_doc_status(self, tmp_path: Path) -> None:
        """Text output shows doc path and status for each node."""
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        data = generate_polish_data(tmp_path)
        text = format_polish_text(data)

        assert "Doc:" in text
        # The auth domain doc should show as missing (not created yet).
        assert "missing" in text

    def test_polish_text_with_existing_doc(self, tmp_path: Path) -> None:
        """Text shows 'exists' status when doc file is present."""
        graph_data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
            ],
        }
        _write_graph_yaml(tmp_path, graph_data)

        # Create the doc file.
        doc_dir = tmp_path / "docs" / "domains" / "auth"
        doc_dir.mkdir(parents=True, exist_ok=True)
        (doc_dir / "README.md").write_text("# Auth\n", encoding="utf-8")

        data = generate_polish_data(tmp_path, ref_id="auth")
        text = format_polish_text(data)

        assert "(exists)" in text

    def test_format_polish_text_standalone(self) -> None:
        """format_polish_text works with manually constructed data dict."""
        data: dict[str, Any] = {
            "nodes": [
                {
                    "ref_id": "my-node",
                    "kind": "domain",
                    "summary": "Test node",
                    "source": "src/my_node/",
                    "symbols": [
                        {"symbol_name": "my_func", "kind": "function"},
                        {"symbol_name": "_private", "kind": "function"},
                    ],
                    "depends_on": ["other-node"],
                    "used_by": [],
                    "doc_path": "docs/domains/my-node/README.md",
                    "doc_status": "exists",
                },
            ],
            "architecture": {"project_name": "testproject"},
            "instructions": "Enrich the docs.",
        }
        text = format_polish_text(data)

        assert "# testproject" in text
        assert "## my-node (domain)" in text
        assert "my_func" in text
        # Private symbol should be filtered out.
        assert "_private" not in text
        assert "Depends on: other-node" in text
        assert "Used by: (none)" in text
        assert "Enrich the docs." in text


# ---------------------------------------------------------------------------
# TestGenerateBeadloomReadme
# ---------------------------------------------------------------------------


class TestGenerateBeadloomReadme:
    """Tests for :func:`_generate_beadloom_readme`."""

    def test_generate_beadloom_readme(self, tmp_path: Path) -> None:
        """Test that _generate_beadloom_readme creates .beadloom/README.md."""
        from beadloom.onboarding.doc_generator import _generate_beadloom_readme

        beadloom_dir = tmp_path / ".beadloom"
        beadloom_dir.mkdir()

        result = _generate_beadloom_readme(tmp_path, "test-project")

        assert result == beadloom_dir / "README.md"
        assert result.exists()
        content = result.read_text()
        assert "test-project" in content
        assert "AI Agent Native Architecture Graph" in content
        assert "beadloom status" in content

    def test_generate_beadloom_readme_does_not_overwrite(self, tmp_path: Path) -> None:
        """Existing .beadloom/README.md must not be overwritten."""
        from beadloom.onboarding.doc_generator import _generate_beadloom_readme

        beadloom_dir = tmp_path / ".beadloom"
        beadloom_dir.mkdir()
        existing = beadloom_dir / "README.md"
        existing.write_text("DO NOT OVERWRITE", encoding="utf-8")

        _generate_beadloom_readme(tmp_path, "test-project")

        assert existing.read_text(encoding="utf-8") == "DO NOT OVERWRITE"

    def test_generate_skeletons_creates_beadloom_readme(self, tmp_path: Path) -> None:
        """Test that generate_skeletons creates .beadloom/README.md."""
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)

        data: dict[str, Any] = {
            "nodes": [
                _root_node(),
                _domain_node("auth"),
            ],
            "edges": [
                {"src": "auth", "dst": "myproject", "kind": "part_of"},
            ],
        }
        (graph_dir / "services.yml").write_text(
            yaml.dump(data, default_flow_style=False), encoding="utf-8"
        )

        generate_skeletons(tmp_path)

        readme = tmp_path / ".beadloom" / "README.md"
        assert readme.exists()
        content = readme.read_text(encoding="utf-8")
        assert "myproject" in content
        assert "AI Agent Native Architecture Graph" in content
