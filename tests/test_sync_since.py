"""Tests for ref-baseline sync detection: ``check_sync_since`` + CLI ``--since``.

The ref-baseline path answers a different question than the stored-state path:
*relative to the code state at a git ref, did the code drift without the doc
being correspondingly updated?* This is what a fresh CI checkout needs (a
from-scratch reindex re-baselines every pair to the current code, so the
stored-state path reports 0 stale even when a push left a doc behind).
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.doc_sync.engine import check_sync_since
from beadloom.infrastructure.db import open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _git(project: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )


def _build_project(tmp_path: Path) -> Path:
    """Create a git repo with a linked doc + code pair and one baseline commit.

    Returns the project root. After this, HEAD is the baseline ref and the
    sync_state is populated (baselined to the committed code).
    """
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
    (docs_dir / "spec.md").write_text("## Spec\n\nDocuments handler().\n")

    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text("# beadloom:feature=F1\ndef handler():\n    pass\n")

    _git(project, "init")
    _git(project, "config", "user.email", "t@t.t")
    _git(project, "config", "user.name", "t")
    _git(project, "add", "-A")
    _git(project, "commit", "-m", "baseline")

    from beadloom.application.reindex import reindex
    from beadloom.doc_sync.engine import build_sync_state

    reindex(project)
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


class TestCheckSyncSinceEngine:
    def test_nothing_changed_is_zero_stale(self, tmp_path: Path) -> None:
        project = _build_project(tmp_path)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        results = check_sync_since(conn, project_root=project, since="HEAD")
        conn.close()
        assert all(r["status"] == "ok" for r in results), results

    def test_code_changed_doc_not_updated_is_stale(self, tmp_path: Path) -> None:
        project = _build_project(tmp_path)
        # Code drifts from the ref baseline; doc untouched.
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler(x):\n    return x\n"
        )
        conn = open_db(project / ".beadloom" / "beadloom.db")
        results = check_sync_since(conn, project_root=project, since="HEAD")
        conn.close()
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) == 1, results
        assert stale[0]["ref_id"] == "F1"

    def test_code_and_doc_both_changed_is_not_stale(self, tmp_path: Path) -> None:
        project = _build_project(tmp_path)
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler(x):\n    return x\n"
        )
        # Dev also updated the doc since the ref → must NOT re-flag.
        (project / "docs" / "spec.md").write_text("## Spec\n\nDocuments handler(x).\n")
        conn = open_db(project / ".beadloom" / "beadloom.db")
        results = check_sync_since(conn, project_root=project, since="HEAD")
        conn.close()
        assert all(r["status"] == "ok" for r in results), results

    def test_doc_changed_code_unchanged_is_not_stale(self, tmp_path: Path) -> None:
        project = _build_project(tmp_path)
        (project / "docs" / "spec.md").write_text("## Spec\n\nMore docs, same code.\n")
        conn = open_db(project / ".beadloom" / "beadloom.db")
        results = check_sync_since(conn, project_root=project, since="HEAD")
        conn.close()
        assert all(r["status"] == "ok" for r in results), results


class TestSyncCheckSinceCli:
    def test_since_invalid_ref_errors(self, tmp_path: Path) -> None:
        project = _build_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-check", "--since", "nope-not-a-ref", "--project", str(project)]
        )
        assert result.exit_code == 1
        assert "Invalid git ref" in result.output

    def test_since_zero_sha_errors(self, tmp_path: Path) -> None:
        project = _build_project(tmp_path)
        runner = CliRunner()
        zero = "0" * 40
        result = runner.invoke(
            main, ["sync-check", "--since", zero, "--project", str(project)]
        )
        assert result.exit_code == 1

    def test_since_code_changed_is_stale_exit_2(self, tmp_path: Path) -> None:
        project = _build_project(tmp_path)
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler(x):\n    return x\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-check", "--since", "HEAD", "--project", str(project)]
        )
        assert result.exit_code == 2, result.output

    def test_since_json_shape_parity(self, tmp_path: Path) -> None:
        import json

        project = _build_project(tmp_path)
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler(x):\n    return x\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-check", "--since", "HEAD", "--json", "--project", str(project)]
        )
        assert result.exit_code == 2, result.output
        data = json.loads(result.output)
        assert set(data.keys()) == {"summary", "pairs"}
        assert set(data["summary"].keys()) == {"total", "ok", "stale"}
        assert data["summary"]["stale"] == 1
        pair = data["pairs"][0]
        assert set(pair.keys()) >= {"status", "ref_id", "doc_path", "code_path", "reason"}

    def test_since_clean_exit_0(self, tmp_path: Path) -> None:
        project = _build_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-check", "--since", "HEAD", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
