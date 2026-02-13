"""Tests for `beadloom sync-check` CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
    """Create a project with linked doc + code for sync testing."""
    import yaml

    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {
                        "ref_id": "F1",
                        "kind": "feature",
                        "summary": "Feature 1",
                        "docs": ["docs/spec.md"],
                    },
                ],
            }
        )
    )

    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Spec\n\nContent.\n")

    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text("# beadloom:feature=F1\ndef handler():\n    pass\n")

    from beadloom.infrastructure.reindex import reindex

    reindex(project)

    # Populate sync_state.
    from beadloom.doc_sync.engine import build_sync_state
    from beadloom.infrastructure.db import open_db

    db_path = project / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    pairs = build_sync_state(conn)
    for pair in pairs:
        conn.execute(
            "INSERT OR REPLACE INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                pair.doc_path,
                pair.code_path,
                pair.ref_id,
                pair.code_hash,
                pair.doc_hash,
                "2025-01-01",
                "ok",
            ),
        )
    conn.commit()
    conn.close()

    return project


class TestSyncCheckCommand:
    def test_all_ok(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_porcelain_output(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--porcelain", "--project", str(project)])
        assert result.exit_code == 0, result.output
        # Porcelain uses TAB-separated format.
        if result.output.strip():
            assert "\t" in result.output

    def test_stale_exit_code(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)

        # Make sync_state stale by changing code hash.
        from beadloom.infrastructure.db import open_db

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        conn.execute("UPDATE sync_state SET code_hash_at_sync = 'OLD_HASH'")
        conn.commit()
        conn.close()

        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--project", str(project)])
        assert result.exit_code == 2  # stale found

    def test_ref_filter(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--ref", "F1", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_ref_filter_nonexistent(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--ref", "NOPE", "--project", str(project)])
        # Should still succeed (no pairs matched).
        assert result.exit_code == 0

    def test_no_db(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--project", str(project)])
        assert result.exit_code != 0
