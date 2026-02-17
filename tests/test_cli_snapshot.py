"""Tests for `beadloom snapshot` CLI commands (save, list, compare)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
    """Create a project with a populated beadloom DB."""
    project = tmp_path / "proj"
    beadloom_dir = project / ".beadloom"
    beadloom_dir.mkdir(parents=True)

    db_path = beadloom_dir / "beadloom.db"
    conn = open_db(db_path)
    create_schema(conn)

    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("auth-login", "feature", "User authentication"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("user-service", "service", "User management"),
    )
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("auth-login", "user-service", "uses"),
    )
    conn.commit()
    conn.close()

    return project


class TestCliSnapshotSave:
    def test_save_basic(self, tmp_path: Path) -> None:
        """beadloom snapshot save creates a snapshot."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["snapshot", "save", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "Snapshot #" in result.output
        assert "saved" in result.output

    def test_save_with_label(self, tmp_path: Path) -> None:
        """beadloom snapshot save --label stores the label."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["snapshot", "save", "--label", "v1.6.0", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert "v1.6.0" in result.output

    def test_save_no_db(self, tmp_path: Path) -> None:
        """beadloom snapshot save with no DB prints error."""
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["snapshot", "save", "--project", str(project)])
        assert result.exit_code != 0
        assert "database not found" in result.output


class TestCliSnapshotList:
    def test_list_empty(self, tmp_path: Path) -> None:
        """beadloom snapshot list with no snapshots shows message."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["snapshot", "list", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "No snapshots found" in result.output

    def test_list_after_save(self, tmp_path: Path) -> None:
        """beadloom snapshot list shows saved snapshots."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["snapshot", "save", "--label", "test", "--project", str(project)])
        result = runner.invoke(main, ["snapshot", "list", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "#1" in result.output
        assert "[test]" in result.output
        assert "nodes=2" in result.output
        assert "edges=1" in result.output

    def test_list_json(self, tmp_path: Path) -> None:
        """beadloom snapshot list --json outputs valid JSON."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["snapshot", "save", "--label", "j", "--project", str(project)])
        result = runner.invoke(main, ["snapshot", "list", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["label"] == "j"


class TestCliSnapshotCompare:
    def test_compare_no_changes(self, tmp_path: Path) -> None:
        """Comparing identical snapshots shows no changes."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["snapshot", "save", "--project", str(project)])
        runner.invoke(main, ["snapshot", "save", "--project", str(project)])
        result = runner.invoke(main, ["snapshot", "compare", "1", "2", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "No changes" in result.output

    def test_compare_json(self, tmp_path: Path) -> None:
        """beadloom snapshot compare --json outputs valid JSON."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["snapshot", "save", "--project", str(project)])
        runner.invoke(main, ["snapshot", "save", "--project", str(project)])
        result = runner.invoke(
            main, ["snapshot", "compare", "1", "2", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["has_changes"] is False

    def test_compare_with_changes(self, tmp_path: Path) -> None:
        """Comparing snapshots with changes shows diff."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["snapshot", "save", "--project", str(project)])

        # Modify DB directly
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("billing", "domain", "Billing domain"),
        )
        conn.commit()
        conn.close()

        runner.invoke(main, ["snapshot", "save", "--project", str(project)])
        result = runner.invoke(main, ["snapshot", "compare", "1", "2", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "billing" in result.output
        assert "Added nodes" in result.output

    def test_compare_nonexistent(self, tmp_path: Path) -> None:
        """Comparing with nonexistent snapshot ID prints error."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["snapshot", "save", "--project", str(project)])
        result = runner.invoke(
            main, ["snapshot", "compare", "1", "999", "--project", str(project)]
        )
        assert result.exit_code != 0
        assert "not found" in result.output
