"""Tests for beadloom reindex — full pipeline: YAML + docs + code → SQLite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.db import get_meta, open_db
from beadloom.reindex import incremental_reindex, reindex

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
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "nodes" in tables
        assert "edges" in tables
        conn.close()

    def test_loads_graph(self, project: Path, db_path: Path) -> None:
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "domains.yml").write_text(
            "nodes:\n"
            "  - ref_id: routing\n"
            "    kind: domain\n"
            '    summary: "Routing"\n'
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
            "nodes:\n"
            "  - ref_id: old\n"
            "    kind: domain\n"
            '    summary: "Old"\n'
        )
        reindex(project)

        # Change graph.
        (graph_dir / "d.yml").write_text(
            "nodes:\n"
            "  - ref_id: new\n"
            "    kind: domain\n"
            '    summary: "New"\n'
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
            "nodes:\n"
            "  - ref_id: FEAT-1\n"
            "    kind: feature\n"
            '    summary: "Feature"\n'
        )
        src = project / "src"
        (src / "handler.py").write_text(
            "# beadloom:feature=FEAT-1\n"
            "def do_thing():\n"
            "    pass\n"
        )
        reindex(project)
        conn = open_db(db_path)
        edges = conn.execute(
            "SELECT * FROM edges WHERE kind = 'touches_code'"
        ).fetchall()
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
        from beadloom.reindex import ReindexResult

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
        conflict_warnings = [
            w for w in result.warnings if "architecture.md" in w
        ]
        assert len(conflict_warnings) == 1
        assert "beadloom" in conflict_warnings[0]
        assert "context-oracle" in conflict_warnings[0]

    def test_doc_ref_map_conflict_keeps_first(
        self, project: Path, db_path: Path
    ) -> None:
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
        conflict_warnings = [
            w for w in result.warnings if "referenced by both" in w
        ]
        assert len(conflict_warnings) == 0


class TestReindexDocsDir:
    """Tests for configurable docs_dir in reindex."""

    def test_default_docs_dir_when_no_config(
        self, project: Path, db_path: Path
    ) -> None:
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

    def test_docs_dir_from_config_yml(
        self, project: Path, db_path: Path
    ) -> None:
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

    def test_explicit_docs_dir_overrides_config(
        self, project: Path, db_path: Path
    ) -> None:
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

    def test_config_yml_without_docs_dir_falls_back(
        self, project: Path, db_path: Path
    ) -> None:
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

    def test_custom_docs_dir_with_graph_ref_linking(
        self, project: Path, db_path: Path
    ) -> None:
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
        row = conn.execute(
            "SELECT ref_id FROM docs WHERE path = ?", ("spec.md",)
        ).fetchone()
        assert row is not None
        assert row["ref_id"] == "F1"
        conn.close()


class TestFullReindexPopulatesFileIndex:
    """Full reindex should populate file_index for subsequent incremental runs."""

    def test_file_index_populated_after_full_reindex(
        self, project: Path, db_path: Path,
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
        self, project: Path, db_path: Path,
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
        self, project: Path, db_path: Path,
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
        self, project: Path, db_path: Path,
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
        chunk = conn.execute(
            "SELECT content FROM chunks ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert chunk is not None
        assert "Updated" in chunk["content"]
        conn.close()

    def test_added_code_file_indexed(
        self, project: Path, db_path: Path,
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
        self, project: Path, db_path: Path,
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
        assert conn.execute(
            "SELECT count(*) FROM docs WHERE path = ?", ("gone.md",)
        ).fetchone()[0] == 1
        conn.close()

        # Delete the doc.
        doc.unlink()
        incremental_reindex(project)

        conn = open_db(db_path)
        assert conn.execute(
            "SELECT count(*) FROM docs WHERE path = ?", ("gone.md",)
        ).fetchone()[0] == 0
        conn.close()

    def test_deleted_code_file_removed(
        self, project: Path, db_path: Path,
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
        assert conn.execute(
            "SELECT count(*) FROM code_symbols WHERE file_path = ?",
            ("src/old.py",),
        ).fetchone()[0] >= 1
        conn.close()

        # Delete code file.
        code.unlink()
        incremental_reindex(project)

        conn = open_db(db_path)
        assert conn.execute(
            "SELECT count(*) FROM code_symbols WHERE file_path = ?",
            ("src/old.py",),
        ).fetchone()[0] == 0
        conn.close()

    def test_graph_change_triggers_full_reindex(
        self, project: Path, db_path: Path,
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
        refs = {
            r["ref_id"]
            for r in conn.execute("SELECT ref_id FROM nodes").fetchall()
        }
        assert "NEW" in refs
        assert "OLD" not in refs
        conn.close()

    def test_file_index_updated_after_incremental(
        self, project: Path, db_path: Path,
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
        paths = {
            r["path"]
            for r in conn.execute("SELECT path FROM file_index").fetchall()
        }
        assert "src/b.py" in paths
        assert "src/a.py" in paths
        conn.close()
