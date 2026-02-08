"""Tests for beadloom reindex — full pipeline: YAML + docs + code → SQLite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.db import get_meta, open_db
from beadloom.reindex import reindex

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
