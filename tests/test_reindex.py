"""Tests for beadloom reindex — full pipeline: YAML + docs + code → SQLite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, get_meta, open_db
from beadloom.infrastructure.reindex import (
    _snapshot_sync_baselines,
    incremental_reindex,
    reindex,
)

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


class TestReindex:
    def test_creates_db_and_schema(self, project: Path, db_path: Path) -> None:
        reindex(project)
        assert db_path.exists()
        conn = open_db(db_path)
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "nodes" in tables
        assert "edges" in tables
        conn.close()

    def test_loads_graph(self, project: Path, db_path: Path) -> None:
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "domains.yml").write_text(
            'nodes:\n  - ref_id: routing\n    kind: domain\n    summary: "Routing"\n'
        )
        reindex(project)
        conn = open_db(db_path)
        row = conn.execute("SELECT * FROM nodes WHERE ref_id = ?", ("routing",)).fetchone()
        assert row is not None
        assert row["kind"] == "domain"
        conn.close()

    def test_loads_docs(self, project: Path, db_path: Path) -> None:
        docs = project / "docs"
        (docs / "readme.md").write_text("## Overview\n\nHello.\n")
        reindex(project)
        conn = open_db(db_path)
        row = conn.execute("SELECT * FROM docs").fetchone()
        assert row is not None
        assert row["path"] == "readme.md"
        chunks = conn.execute("SELECT * FROM chunks").fetchall()
        assert len(chunks) >= 1
        conn.close()

    def test_loads_code_symbols(self, project: Path, db_path: Path) -> None:
        src = project / "src"
        (src / "api.py").write_text("def handler():\n    pass\n")
        reindex(project)
        conn = open_db(db_path)
        row = conn.execute(
            "SELECT * FROM code_symbols WHERE symbol_name = ?", ("handler",)
        ).fetchone()
        assert row is not None
        assert row["kind"] == "function"
        conn.close()

    def test_sets_meta(self, project: Path, db_path: Path) -> None:
        reindex(project)
        conn = open_db(db_path)
        assert get_meta(conn, "schema_version") is not None
        assert get_meta(conn, "beadloom_version") is not None
        assert get_meta(conn, "last_reindex_at") is not None
        conn.close()

    def test_drop_and_recreate(self, project: Path, db_path: Path) -> None:
        """Second reindex should clear old data."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "d.yml").write_text(
            'nodes:\n  - ref_id: old\n    kind: domain\n    summary: "Old"\n'
        )
        reindex(project)

        # Change graph.
        (graph_dir / "d.yml").write_text(
            'nodes:\n  - ref_id: new\n    kind: domain\n    summary: "New"\n'
        )
        reindex(project)

        conn = open_db(db_path)
        rows = conn.execute("SELECT ref_id FROM nodes").fetchall()
        ref_ids = {r["ref_id"] for r in rows}
        assert "new" in ref_ids
        assert "old" not in ref_ids
        conn.close()

    def test_annotated_code_creates_edges(self, project: Path, db_path: Path) -> None:
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "f.yml").write_text(
            'nodes:\n  - ref_id: FEAT-1\n    kind: feature\n    summary: "Feature"\n'
        )
        src = project / "src"
        (src / "handler.py").write_text("# beadloom:feature=FEAT-1\ndef do_thing():\n    pass\n")
        reindex(project)
        conn = open_db(db_path)
        edges = conn.execute("SELECT * FROM edges WHERE kind = 'touches_code'").fetchall()
        assert len(edges) >= 1
        conn.close()

    def test_doc_ref_id_linking(self, project: Path, db_path: Path) -> None:
        """Docs listed in YAML nodes get linked via ref_id."""
        graph_dir = project / ".beadloom" / "_graph"
        docs = project / "docs"
        (docs / "spec.md").write_text("## Spec\n\nContent.\n")
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: F1\n"
            "    kind: feature\n"
            '    summary: "Feature"\n'
            "    docs:\n"
            "      - docs/spec.md\n"
        )
        reindex(project)
        conn = open_db(db_path)
        row = conn.execute("SELECT ref_id FROM docs WHERE path = ?", ("spec.md",)).fetchone()
        assert row is not None
        assert row["ref_id"] == "F1"
        conn.close()

    def test_empty_project(self, project: Path, db_path: Path) -> None:
        reindex(project)
        conn = open_db(db_path)
        nodes = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        assert nodes == 0
        conn.close()

    def test_returns_result(self, project: Path) -> None:
        from beadloom.infrastructure.reindex import ReindexResult

        result = reindex(project)
        assert isinstance(result, ReindexResult)
        assert result.nodes_loaded >= 0

    def test_doc_ref_map_conflict_warns(self, project: Path) -> None:
        """When two YAML nodes reference the same doc, a warning is emitted."""
        # Arrange
        graph_dir = project / ".beadloom" / "_graph"
        docs = project / "docs"
        (docs / "architecture.md").write_text("## Architecture\n\nShared doc.\n")
        (graph_dir / "a_first.yml").write_text(
            "nodes:\n"
            "  - ref_id: beadloom\n"
            "    kind: domain\n"
            '    summary: "Beadloom core"\n'
            "    docs:\n"
            "      - docs/architecture.md\n"
        )
        (graph_dir / "b_second.yml").write_text(
            "nodes:\n"
            "  - ref_id: context-oracle\n"
            "    kind: domain\n"
            '    summary: "Context Oracle"\n'
            "    docs:\n"
            "      - docs/architecture.md\n"
        )

        # Act
        result = reindex(project)

        # Assert
        conflict_warnings = [w for w in result.warnings if "architecture.md" in w]
        assert len(conflict_warnings) == 1
        assert "beadloom" in conflict_warnings[0]
        assert "context-oracle" in conflict_warnings[0]

    def test_doc_ref_map_conflict_keeps_first(self, project: Path, db_path: Path) -> None:
        """When two YAML nodes reference the same doc, the first mapping wins."""
        # Arrange
        graph_dir = project / ".beadloom" / "_graph"
        docs = project / "docs"
        (docs / "architecture.md").write_text("## Architecture\n\nShared doc.\n")
        (graph_dir / "a_first.yml").write_text(
            "nodes:\n"
            "  - ref_id: beadloom\n"
            "    kind: domain\n"
            '    summary: "Beadloom core"\n'
            "    docs:\n"
            "      - docs/architecture.md\n"
        )
        (graph_dir / "b_second.yml").write_text(
            "nodes:\n"
            "  - ref_id: context-oracle\n"
            "    kind: domain\n"
            '    summary: "Context Oracle"\n'
            "    docs:\n"
            "      - docs/architecture.md\n"
        )

        # Act
        reindex(project)

        # Assert — doc should be linked to the FIRST node (beadloom), not the last
        conn = open_db(db_path)
        row = conn.execute(
            "SELECT ref_id FROM docs WHERE path = ?", ("architecture.md",)
        ).fetchone()
        assert row is not None
        assert row["ref_id"] == "beadloom"
        conn.close()

    def test_doc_ref_map_no_conflict(self, project: Path) -> None:
        """Two nodes with different docs produce no doc-conflict warnings."""
        # Arrange
        graph_dir = project / ".beadloom" / "_graph"
        docs = project / "docs"
        (docs / "api.md").write_text("## API\n\nAPI docs.\n")
        (docs / "guide.md").write_text("## Guide\n\nUser guide.\n")
        (graph_dir / "features.yml").write_text(
            "nodes:\n"
            "  - ref_id: api-module\n"
            "    kind: feature\n"
            '    summary: "API"\n'
            "    docs:\n"
            "      - docs/api.md\n"
            "  - ref_id: guide-module\n"
            "    kind: feature\n"
            '    summary: "Guide"\n'
            "    docs:\n"
            "      - docs/guide.md\n"
        )

        # Act
        result = reindex(project)

        # Assert — no conflict warnings (other warnings like graph warnings are ok)
        conflict_warnings = [w for w in result.warnings if "referenced by both" in w]
        assert len(conflict_warnings) == 0


class TestReindexDocsDir:
    """Tests for configurable docs_dir in reindex."""

    def test_default_docs_dir_when_no_config(self, project: Path, db_path: Path) -> None:
        """Without config.yml, default 'docs/' directory is used."""
        docs = project / "docs"
        (docs / "readme.md").write_text("## Hello\n\nWorld.\n")
        result = reindex(project)
        assert result.docs_indexed == 1

        conn = open_db(db_path)
        row = conn.execute("SELECT * FROM docs").fetchone()
        assert row is not None
        assert row["path"] == "readme.md"
        conn.close()

    def test_docs_dir_from_config_yml(self, project: Path, db_path: Path) -> None:
        """docs_dir from .beadloom/config.yml is used when present."""
        import yaml

        # Create a custom docs directory.
        custom_docs = project / "documentation"
        custom_docs.mkdir()
        (custom_docs / "guide.md").write_text("## Guide\n\nCustom docs.\n")

        # Write config.yml with docs_dir setting.
        config_path = project / ".beadloom" / "config.yml"
        config_path.write_text(yaml.dump({"docs_dir": "documentation"}))

        result = reindex(project)
        assert result.docs_indexed == 1

        conn = open_db(db_path)
        row = conn.execute("SELECT * FROM docs").fetchone()
        assert row is not None
        assert row["path"] == "guide.md"
        conn.close()

    def test_explicit_docs_dir_overrides_config(self, project: Path, db_path: Path) -> None:
        """Explicit docs_dir parameter overrides config.yml."""
        import yaml

        # Config points to 'documentation/', but we pass 'doc/' explicitly.
        config_path = project / ".beadloom" / "config.yml"
        config_path.write_text(yaml.dump({"docs_dir": "documentation"}))

        explicit_docs = project / "doc"
        explicit_docs.mkdir()
        (explicit_docs / "notes.md").write_text("## Notes\n\nExplicit.\n")

        result = reindex(project, docs_dir=explicit_docs)
        assert result.docs_indexed == 1

        conn = open_db(db_path)
        row = conn.execute("SELECT * FROM docs").fetchone()
        assert row is not None
        assert row["path"] == "notes.md"
        conn.close()

    def test_config_yml_without_docs_dir_falls_back(self, project: Path, db_path: Path) -> None:
        """config.yml exists but has no docs_dir key — falls back to 'docs/'."""
        import yaml

        config_path = project / ".beadloom" / "config.yml"
        config_path.write_text(yaml.dump({"some_other_key": "value"}))

        docs = project / "docs"
        (docs / "readme.md").write_text("## Readme\n\nFallback.\n")

        result = reindex(project)
        assert result.docs_indexed == 1

        conn = open_db(db_path)
        row = conn.execute("SELECT * FROM docs").fetchone()
        assert row is not None
        assert row["path"] == "readme.md"
        conn.close()

    def test_custom_docs_dir_with_graph_ref_linking(self, project: Path, db_path: Path) -> None:
        """Doc ref linking works correctly with custom docs_dir."""
        import yaml

        custom_docs = project / "documentation"
        custom_docs.mkdir()
        (custom_docs / "spec.md").write_text("## Spec\n\nContent.\n")

        config_path = project / ".beadloom" / "config.yml"
        config_path.write_text(yaml.dump({"docs_dir": "documentation"}))

        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: F1\n"
            "    kind: feature\n"
            '    summary: "Feature"\n'
            "    docs:\n"
            "      - documentation/spec.md\n"
        )

        result = reindex(project)
        assert result.docs_indexed == 1

        conn = open_db(db_path)
        row = conn.execute("SELECT ref_id FROM docs WHERE path = ?", ("spec.md",)).fetchone()
        assert row is not None
        assert row["ref_id"] == "F1"
        conn.close()


class TestFullReindexPopulatesFileIndex:
    """Full reindex should populate file_index for subsequent incremental runs."""

    def test_file_index_populated_after_full_reindex(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: X\n    kind: domain\n    summary: X\n"
        )
        (project / "docs" / "a.md").write_text("## A\n\nContent.\n")
        (project / "src" / "f.py").write_text("def foo():\n    pass\n")

        reindex(project)

        conn = open_db(db_path)
        rows = conn.execute("SELECT path, kind FROM file_index").fetchall()
        paths = {r["path"]: r["kind"] for r in rows}
        assert ".beadloom/_graph/g.yml" in paths
        assert paths[".beadloom/_graph/g.yml"] == "graph"
        assert "docs/a.md" in paths
        assert paths["docs/a.md"] == "doc"
        assert "src/f.py" in paths
        assert paths["src/f.py"] == "code"
        conn.close()


class TestIncrementalReindex:
    """Tests for incremental_reindex."""

    def test_first_run_falls_back_to_full(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """First incremental call = full reindex + file_index populated."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        result = incremental_reindex(project)
        assert result.nodes_loaded == 1

        conn = open_db(db_path)
        fi = conn.execute("SELECT count(*) FROM file_index").fetchone()[0]
        assert fi >= 1
        conn.close()

    def test_no_changes_skips_reindex(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Nothing changed → no re-processing."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        (project / "docs" / "a.md").write_text("## A\n\nContent.\n")

        incremental_reindex(project)

        # Second run — nothing changed.
        result = incremental_reindex(project)
        assert result.nodes_loaded == 0
        assert result.docs_indexed == 0
        assert result.symbols_indexed == 0

    def test_changed_doc_reindexed(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Modified doc file is re-indexed."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        doc = project / "docs" / "spec.md"
        doc.write_text("## Spec\n\nOriginal.\n")

        incremental_reindex(project)

        # Change doc content.
        doc.write_text("## Spec\n\nUpdated content.\n")
        result = incremental_reindex(project)

        assert result.docs_indexed == 1

        conn = open_db(db_path)
        chunk = conn.execute("SELECT content FROM chunks ORDER BY id DESC LIMIT 1").fetchone()
        assert chunk is not None
        assert "Updated" in chunk["content"]
        conn.close()

    def test_added_code_file_indexed(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """New code file is picked up."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        incremental_reindex(project)

        # Add a new code file.
        (project / "src" / "new.py").write_text("def new_func():\n    pass\n")
        result = incremental_reindex(project)

        assert result.symbols_indexed >= 1

        conn = open_db(db_path)
        row = conn.execute(
            "SELECT * FROM code_symbols WHERE symbol_name = ?", ("new_func",)
        ).fetchone()
        assert row is not None
        conn.close()

    def test_deleted_doc_removed(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Deleted doc file is removed from DB."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        doc = project / "docs" / "gone.md"
        doc.write_text("## Gone\n\nWill be deleted.\n")

        incremental_reindex(project)

        conn = open_db(db_path)
        assert (
            conn.execute("SELECT count(*) FROM docs WHERE path = ?", ("gone.md",)).fetchone()[0]
            == 1
        )
        conn.close()

        # Delete the doc.
        doc.unlink()
        incremental_reindex(project)

        conn = open_db(db_path)
        assert (
            conn.execute("SELECT count(*) FROM docs WHERE path = ?", ("gone.md",)).fetchone()[0]
            == 0
        )
        conn.close()

    def test_deleted_code_file_removed(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Deleted code file symbols are removed."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        code = project / "src" / "old.py"
        code.write_text("def old_func():\n    pass\n")

        incremental_reindex(project)

        conn = open_db(db_path)
        assert (
            conn.execute(
                "SELECT count(*) FROM code_symbols WHERE file_path = ?",
                ("src/old.py",),
            ).fetchone()[0]
            >= 1
        )
        conn.close()

        # Delete code file.
        code.unlink()
        incremental_reindex(project)

        conn = open_db(db_path)
        assert (
            conn.execute(
                "SELECT count(*) FROM code_symbols WHERE file_path = ?",
                ("src/old.py",),
            ).fetchone()[0]
            == 0
        )
        conn.close()

    def test_graph_change_triggers_full_reindex(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Graph YAML change → full reindex (nodes replaced)."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: OLD\n    kind: domain\n    summary: Old\n"
        )
        incremental_reindex(project)

        # Change graph.
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: NEW\n    kind: domain\n    summary: New\n"
        )
        result = incremental_reindex(project)

        assert result.nodes_loaded == 1
        conn = open_db(db_path)
        refs = {r["ref_id"] for r in conn.execute("SELECT ref_id FROM nodes").fetchall()}
        assert "NEW" in refs
        assert "OLD" not in refs
        conn.close()

    def test_file_index_updated_after_incremental(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """file_index is updated to reflect current state."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        (project / "src" / "a.py").write_text("def a():\n    pass\n")

        incremental_reindex(project)

        # Add another file.
        (project / "src" / "b.py").write_text("def b():\n    pass\n")
        incremental_reindex(project)

        conn = open_db(db_path)
        paths = {r["path"] for r in conn.execute("SELECT path FROM file_index").fetchall()}
        assert "src/b.py" in paths
        assert "src/a.py" in paths
        conn.close()

    def test_graph_summary_edit_detected_by_incremental(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """UX #21 regression: editing a node summary in graph YAML must trigger
        a full reindex so that the updated summary appears in the DB and the
        result reports non-zero node/edge counts.
        """
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: svc-api\n"
            "    kind: service\n"
            '    summary: "API Gateway v1.0"\n'
            "  - ref_id: svc-auth\n"
            "    kind: service\n"
            '    summary: "Auth Service"\n'
            "edges:\n"
            "  - src: svc-api\n"
            "    dst: svc-auth\n"
            "    kind: depends_on\n"
        )
        (project / "docs" / "readme.md").write_text("## Hello\n\nWorld.\n")

        # Baseline: full reindex via first incremental call (empty file_index).
        r1 = incremental_reindex(project)
        assert r1.nodes_loaded == 2
        assert r1.edges_loaded == 1

        # Edit ONLY the graph summary (version bump).
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: svc-api\n"
            "    kind: service\n"
            '    summary: "API Gateway v2.0"\n'
            "  - ref_id: svc-auth\n"
            "    kind: service\n"
            '    summary: "Auth Service"\n'
            "edges:\n"
            "  - src: svc-api\n"
            "    dst: svc-auth\n"
            "    kind: depends_on\n"
        )

        # Incremental reindex MUST detect the graph change.
        r2 = incremental_reindex(project)
        assert r2.nodes_loaded == 2, f"Expected 2 nodes after graph edit, got {r2.nodes_loaded}"
        assert r2.edges_loaded == 1

        # Verify the updated summary is in the DB.
        conn = open_db(db_path)
        row = conn.execute("SELECT summary FROM nodes WHERE ref_id = ?", ("svc-api",)).fetchone()
        assert row is not None
        assert "v2.0" in row["summary"]
        conn.close()

    def test_graph_yaml_added_triggers_full_reindex(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Adding a new graph YAML file must trigger full reindex."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "base.yml").write_text(
            "nodes:\n  - ref_id: A\n    kind: domain\n    summary: A\n"
        )
        incremental_reindex(project)

        # Add a second graph YAML.
        (graph_dir / "extra.yml").write_text(
            "nodes:\n  - ref_id: B\n    kind: domain\n    summary: B\n"
        )
        result = incremental_reindex(project)

        assert result.nodes_loaded == 2
        conn = open_db(db_path)
        refs = {r["ref_id"] for r in conn.execute("SELECT ref_id FROM nodes").fetchall()}
        assert refs == {"A", "B"}
        conn.close()

    def test_graph_yaml_deleted_triggers_full_reindex(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Deleting a graph YAML file must trigger full reindex."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "a.yml").write_text(
            "nodes:\n  - ref_id: A\n    kind: domain\n    summary: A\n"
        )
        (graph_dir / "b.yml").write_text(
            "nodes:\n  - ref_id: B\n    kind: domain\n    summary: B\n"
        )
        incremental_reindex(project)

        conn = open_db(db_path)
        assert conn.execute("SELECT count(*) FROM nodes").fetchone()[0] == 2
        conn.close()

        # Delete one graph file.
        (graph_dir / "b.yml").unlink()
        result = incremental_reindex(project)

        assert result.nodes_loaded == 1
        conn = open_db(db_path)
        refs = {r["ref_id"] for r in conn.execute("SELECT ref_id FROM nodes").fetchall()}
        assert refs == {"A"}
        conn.close()

    def test_graph_change_with_concurrent_doc_change(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """When both graph YAML and a doc change, graph change takes priority
        and full reindex runs (not incremental doc-only path).
        """
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        doc = project / "docs" / "spec.md"
        doc.write_text("## Spec v1\n\nOriginal.\n")
        incremental_reindex(project)

        # Change both graph and doc.
        (graph_dir / "g.yml").write_text(
            "nodes:\n"
            "  - ref_id: N1\n    kind: domain\n    summary: N1 updated\n"
            "  - ref_id: N2\n    kind: domain\n    summary: N2 new\n"
        )
        doc.write_text("## Spec v2\n\nUpdated.\n")

        result = incremental_reindex(project)

        # Full reindex should have run — nodes_loaded reflects graph reload.
        assert result.nodes_loaded == 2
        assert result.docs_indexed == 1


# ---------------------------------------------------------------------------
# _graph_yaml_changed
# ---------------------------------------------------------------------------


class TestGraphYamlChanged:
    """Unit tests for the _graph_yaml_changed helper."""

    def test_no_graph_files_returns_false(self) -> None:
        from beadloom.infrastructure.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {
            "docs/a.md": ("abc", "doc"),
            "src/b.py": ("def", "code"),
        }
        stored: dict[str, tuple[str, str]] = {
            "docs/a.md": ("abc", "doc"),
            "src/b.py": ("def", "code"),
        }
        assert _graph_yaml_changed(current, stored) is False

    def test_same_graph_returns_false(self) -> None:
        from beadloom.infrastructure.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
            "docs/a.md": ("bbb", "doc"),
        }
        stored: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
            "docs/a.md": ("bbb", "doc"),
        }
        assert _graph_yaml_changed(current, stored) is False

    def test_changed_hash_returns_true(self) -> None:
        from beadloom.infrastructure.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("new_hash", "graph"),
        }
        stored: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("old_hash", "graph"),
        }
        assert _graph_yaml_changed(current, stored) is True

    def test_added_graph_returns_true(self) -> None:
        from beadloom.infrastructure.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
            ".beadloom/_graph/extra.yml": ("bbb", "graph"),
        }
        stored: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
        }
        assert _graph_yaml_changed(current, stored) is True

    def test_deleted_graph_returns_true(self) -> None:
        from beadloom.infrastructure.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {}
        stored: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
        }
        assert _graph_yaml_changed(current, stored) is True


# ---------------------------------------------------------------------------
# resolve_scan_paths
# ---------------------------------------------------------------------------


class TestResolveScanPaths:
    """Tests for config-driven scan path resolution."""

    def test_reads_from_config(self, tmp_path: Path) -> None:
        """scan_paths from config.yml are used."""
        from beadloom.infrastructure.reindex import resolve_scan_paths

        beadloom_dir = tmp_path / ".beadloom"
        beadloom_dir.mkdir()
        (beadloom_dir / "config.yml").write_text("scan_paths:\n- backend\n- frontend/src\n")
        result = resolve_scan_paths(tmp_path)
        assert result == ["backend", "frontend/src"]

    def test_defaults_without_config(self, tmp_path: Path) -> None:
        """Falls back to defaults when no config exists."""
        from beadloom.infrastructure.reindex import resolve_scan_paths

        result = resolve_scan_paths(tmp_path)
        assert result == ["src", "lib", "app"]

    def test_reindex_uses_config_scan_paths(self, tmp_path: Path) -> None:
        """Full reindex respects scan_paths from config.yml."""
        # Setup project with backend/ dir (not in old hardcoded list).
        beadloom_dir = tmp_path / ".beadloom"
        graph_dir = beadloom_dir / "_graph"
        graph_dir.mkdir(parents=True)
        (tmp_path / "docs").mkdir()
        (beadloom_dir / "config.yml").write_text("scan_paths:\n- backend\nlanguages:\n- python\n")
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / "views.py").write_text("# beadloom:feature=API-001\ndef index():\n    pass\n")
        result = reindex(tmp_path)
        assert result.symbols_indexed >= 1


# ---------------------------------------------------------------------------
# _snapshot_sync_baselines
# ---------------------------------------------------------------------------


class TestSnapshotSyncBaselines:
    """Tests for _snapshot_sync_baselines helper."""

    def test_returns_correct_data(self, project: Path) -> None:
        """Snapshot returns {ref_id: symbols_hash} from sync_state."""
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        create_schema(conn)

        # Insert a node (FK constraint) and sync_state row.
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", "Feature 1"),
        )
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status, symbols_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("spec.md", "src/api.py", "F1", "ch1", "dh1", "2025-01-01", "ok", "abc123"),
        )
        conn.commit()

        result = _snapshot_sync_baselines(conn)
        assert result == {"F1": "abc123"}
        conn.close()

    def test_returns_empty_dict_when_no_table(self, tmp_path: Path) -> None:
        """Returns empty dict when sync_state table does not exist."""
        db_path = tmp_path / "empty.db"
        conn = open_db(db_path)
        # Do NOT create schema — table doesn't exist.
        result = _snapshot_sync_baselines(conn)
        assert result == {}
        conn.close()

    def test_skips_empty_hash(self, project: Path) -> None:
        """Entries with empty symbols_hash are excluded."""
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        create_schema(conn)

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", "Feature 1"),
        )
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status, symbols_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("spec.md", "src/api.py", "F1", "ch1", "dh1", "2025-01-01", "ok", ""),
        )
        conn.commit()

        result = _snapshot_sync_baselines(conn)
        assert result == {}
        conn.close()


# ---------------------------------------------------------------------------
# Full reindex preserves sync baselines
# ---------------------------------------------------------------------------


class TestReindexPreservesBaseline:
    """Full reindex preserves symbols_hash baseline for drift detection."""

    def test_full_reindex_preserves_baseline(self, project: Path, db_path: Path) -> None:
        """After a full reindex, the old symbols_hash is preserved so that
        sync-check can detect symbol drift (new/removed public symbols).
        """
        graph_dir = project / ".beadloom" / "_graph"
        docs = project / "docs"
        src = project / "src"

        # Set up a node with linked doc and annotated code.
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: F1\n"
            "    kind: feature\n"
            '    summary: "Feature"\n'
            "    docs:\n"
            "      - docs/spec.md\n"
        )
        (docs / "spec.md").write_text("## Spec\n\nFeature spec.\n")
        (src / "api.py").write_text("# beadloom:feature=F1\ndef handler():\n    pass\n")

        # First reindex: establishes baseline.
        reindex(project)

        conn = open_db(db_path)
        row = conn.execute(
            "SELECT symbols_hash FROM sync_state WHERE ref_id = 'F1'"
        ).fetchone()
        assert row is not None
        baseline_hash = row["symbols_hash"]
        assert baseline_hash != "", "First reindex should compute a baseline hash"
        conn.close()

        # Second full reindex: should PRESERVE the baseline hash, not recompute.
        reindex(project)

        conn = open_db(db_path)
        row = conn.execute(
            "SELECT symbols_hash FROM sync_state WHERE ref_id = 'F1'"
        ).fetchone()
        assert row is not None
        assert row["symbols_hash"] == baseline_hash, (
            "Full reindex should preserve the old symbols_hash baseline"
        )
        conn.close()


# ---------------------------------------------------------------------------
# old_symbols = {} (empty dict) should NOT trigger fresh baseline
# ---------------------------------------------------------------------------


class TestOldSymbolsEmptyDict:
    """old_symbols = {} must NOT be replaced by None (the `or None` bug)."""

    def test_empty_dict_does_not_compute_fresh_baseline(
        self, project: Path, db_path: Path
    ) -> None:
        """When old_symbols is an empty dict (no previously tracked symbols),
        it should be passed as-is to _build_initial_sync_state, NOT converted
        to None. If converted to None, a fresh baseline would be computed,
        resetting drift detection.
        """
        graph_dir = project / ".beadloom" / "_graph"
        docs = project / "docs"
        src = project / "src"

        # Set up linked node.
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: F1\n"
            "    kind: feature\n"
            '    summary: "Feature"\n'
            "    docs:\n"
            "      - docs/spec.md\n"
        )
        (docs / "spec.md").write_text("## Spec\n\nSpec.\n")
        (src / "api.py").write_text("# beadloom:feature=F1\ndef handler():\n    pass\n")

        # Full reindex to populate file_index + baseline.
        reindex(project)

        # Read baseline hash.
        conn = open_db(db_path)
        row = conn.execute(
            "SELECT symbols_hash FROM sync_state WHERE ref_id = 'F1'"
        ).fetchone()
        baseline_hash = row["symbols_hash"]
        conn.close()

        # Modify ONLY the doc (not code) to trigger incremental path.
        (docs / "spec.md").write_text("## Spec\n\nUpdated spec.\n")

        # Now simulate the scenario where sync_state had no symbols_hash stored
        # (all empty). The old_symbols dict will be {}, not None.
        # With the bug (`old_symbols or None`), {} is falsy → becomes None
        # → fresh baseline is computed → drift detection is reset.
        # With the fix (`old_symbols if old_symbols is not None else None`),
        # {} is kept → preserved_symbols={} → no ref_ids match → fresh hash
        # is computed for new ref_ids only (which is the correct behavior for
        # ref_ids that were NOT previously tracked).
        result = incremental_reindex(project)
        assert result.docs_indexed == 1

        # The symbols_hash should still be the baseline (code didn't change,
        # and the old baseline was preserved from the first reindex).
        conn = open_db(db_path)
        row = conn.execute(
            "SELECT symbols_hash FROM sync_state WHERE ref_id = 'F1'"
        ).fetchone()
        assert row is not None
        # The hash should be preserved from the first reindex because
        # old_symbols captured it before incremental delete+rebuild.
        assert row["symbols_hash"] == baseline_hash, (
            "Incremental reindex should preserve baseline hash"
        )
        conn.close()
