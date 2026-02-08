"""Tests for `beadloom sync-update` CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project_with_sync(tmp_path: Path) -> Path:
    """Create a project with sync_state populated."""
    import yaml

    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump({
            "nodes": [
                {
                    "ref_id": "F1",
                    "kind": "feature",
                    "summary": "Feature 1",
                    "docs": ["docs/spec.md"],
                },
            ],
        })
    )

    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Spec\n\nFeature spec.\n")

    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text(
        "# beadloom:feature=F1\ndef handler():\n    pass\n"
    )

    from beadloom.reindex import reindex

    reindex(project)

    # Populate sync_state.
    from beadloom.db import open_db
    from beadloom.sync_engine import build_sync_state

    db_path = project / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    pairs = build_sync_state(conn)
    for pair in pairs:
        conn.execute(
            "INSERT OR REPLACE INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pair.doc_path, pair.code_path, pair.ref_id,
             pair.code_hash, pair.doc_hash, "2025-01-01", "ok"),
        )
    conn.commit()
    conn.close()

    return project


class TestSyncUpdateCommand:
    def test_shows_stale_info(self, tmp_path: Path) -> None:
        """sync-update with --check should show sync status."""
        project = _setup_project_with_sync(tmp_path)

        # Make it stale.
        from beadloom.db import open_db

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        conn.execute("UPDATE sync_state SET code_hash_at_sync = 'OLD'")
        conn.commit()
        conn.close()

        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-update", "F1", "--check", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert "stale" in result.output.lower() or "F1" in result.output

    def test_no_stale(self, tmp_path: Path) -> None:
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-update", "F1", "--check", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output

    def test_no_db(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-update", "F1", "--project", str(project)]
        )
        assert result.exit_code != 0

    def test_unknown_ref(self, tmp_path: Path) -> None:
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-update", "NOPE", "--check", "--project", str(project)]
        )
        assert result.exit_code == 0  # No stale pairs, just empty output.
