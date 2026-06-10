"""Tests for `beadloom sync-update` CLI command."""

from __future__ import annotations

import unittest.mock
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project_with_sync(tmp_path: Path) -> Path:
    """Create a project with sync_state populated."""
    import yaml as _yaml

    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        _yaml.dump(
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
    (docs_dir / "spec.md").write_text("## Spec\n\nFeature spec.\n")

    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text("# beadloom:feature=F1\ndef handler():\n    pass\n")

    from beadloom.application.reindex import reindex

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


class TestSyncUpdateCommand:
    def test_shows_stale_info(self, tmp_path: Path) -> None:
        """sync-update with --check should show sync status."""
        project = _setup_project_with_sync(tmp_path)

        # Make it stale.
        from beadloom.infrastructure.db import open_db

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        conn.execute("UPDATE sync_state SET code_hash_at_sync = 'OLD'")
        conn.commit()
        conn.close()

        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "F1", "--check", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "stale" in result.output.lower() or "F1" in result.output

    def test_no_stale(self, tmp_path: Path) -> None:
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "F1", "--check", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_no_db(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "F1", "--project", str(project)])
        assert result.exit_code != 0

    def test_unknown_ref(self, tmp_path: Path) -> None:
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "NOPE", "--check", "--project", str(project)])
        assert result.exit_code == 0  # No stale pairs, just empty output.


class TestSyncUpdateInteractive:
    """Tests for interactive sync-update (opening $EDITOR)."""

    def test_opens_editor_on_stale(self, tmp_path: Path) -> None:
        """When stale, should call click.edit() with doc path."""
        project = _setup_project_with_sync(tmp_path)

        # Make it stale by modifying code.
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler():\n    return 'changed'\n"
        )

        # Mock click.edit to not actually open editor.
        with unittest.mock.patch("beadloom.services.cli.click.edit") as mock_edit:
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["sync-update", "F1", "--project", str(project)],
                input="y\n",
            )
        assert result.exit_code == 0, result.output
        assert mock_edit.called
        assert "Synced" in result.output

    def test_skips_when_user_declines(self, tmp_path: Path) -> None:
        """When user says no, should not open editor."""
        project = _setup_project_with_sync(tmp_path)
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler():\n    return 'changed'\n"
        )

        with unittest.mock.patch("beadloom.services.cli.click.edit") as mock_edit:
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["sync-update", "F1", "--project", str(project)],
                input="n\n",
            )
        assert result.exit_code == 0
        assert not mock_edit.called

    def test_updates_sync_state_after_edit(self, tmp_path: Path) -> None:
        """After editing, sync_state should be updated to 'ok'."""
        project = _setup_project_with_sync(tmp_path)
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler():\n    return 'changed'\n"
        )

        with unittest.mock.patch("beadloom.services.cli.click.edit"):
            runner = CliRunner()
            runner.invoke(
                main,
                ["sync-update", "F1", "--project", str(project)],
                input="y\n",
            )

        # Verify sync_state is now 'ok'.
        from beadloom.infrastructure.db import open_db

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        rows = conn.execute("SELECT status FROM sync_state WHERE ref_id = 'F1'").fetchall()
        conn.close()
        assert all(r["status"] == "ok" for r in rows)


class TestSyncUpdateAutoRemoved:
    """--auto flag was removed in v0.6.0."""

    def test_auto_flag_rejected(self, tmp_path: Path) -> None:
        """--auto should be rejected as unknown option."""
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "F1", "--auto", "--project", str(project)])
        assert result.exit_code != 0


def _make_stale(project: Path) -> None:
    """Mutate code so the F1 ref becomes stale."""
    from beadloom.infrastructure.db import open_db

    db_path = project / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    conn.execute("UPDATE sync_state SET code_hash_at_sync = 'OLD'")
    conn.commit()
    conn.close()


def _stale_refs(project: Path) -> list[str]:
    """Return the ref_ids that sync-check currently flags as stale."""
    from beadloom.doc_sync.engine import check_sync
    from beadloom.infrastructure.db import open_db

    db_path = project / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    results = check_sync(conn, project_root=project)
    conn.close()
    return sorted({r["ref_id"] for r in results if r["status"] == "stale"})


class TestSyncUpdateNonInteractive:
    """`sync-update <ref> --yes` re-baselines a ref without an editor/prompt."""

    def test_yes_marks_ref_synced(self, tmp_path: Path) -> None:
        """--yes should re-baseline the ref non-interactively and exit 0."""
        project = _setup_project_with_sync(tmp_path)
        _make_stale(project)
        assert _stale_refs(project) == ["F1"]

        # Editor must NOT be opened in non-interactive mode.
        with unittest.mock.patch("beadloom.services.cli.click.edit") as mock_edit:
            runner = CliRunner()
            result = runner.invoke(
                main, ["sync-update", "F1", "--yes", "--project", str(project)]
            )
        assert result.exit_code == 0, result.output
        assert not mock_edit.called
        assert "F1" in result.output
        # After re-baselining, sync-check reports it fresh.
        assert _stale_refs(project) == []

    def test_short_flag_y(self, tmp_path: Path) -> None:
        """-y is the short alias for --yes."""
        project = _setup_project_with_sync(tmp_path)
        _make_stale(project)
        with unittest.mock.patch("beadloom.services.cli.click.edit"):
            runner = CliRunner()
            result = runner.invoke(main, ["sync-update", "F1", "-y", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert _stale_refs(project) == []

    def test_yes_reports_rows_rebaselined(self, tmp_path: Path) -> None:
        """Output names the ref and how many pairs were re-baselined."""
        project = _setup_project_with_sync(tmp_path)
        _make_stale(project)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "F1", "--yes", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "1" in result.output  # one pair re-baselined

    def test_yes_unknown_ref(self, tmp_path: Path) -> None:
        """--yes with an unknown ref exits 0 with a clear no-op message."""
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "NOPE", "--yes", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "NOPE" in result.output

    def test_check_still_status_only(self, tmp_path: Path) -> None:
        """--check must remain status-only and never re-baseline."""
        project = _setup_project_with_sync(tmp_path)
        _make_stale(project)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "F1", "--check", "--project", str(project)])
        assert result.exit_code == 0, result.output
        # Still stale: --check did not touch the baseline.
        assert _stale_refs(project) == ["F1"]


class TestSyncUpdateAll:
    """`sync-update --all --yes` re-baselines every stale ref in one call."""

    def test_all_rebaselines_every_stale_ref(self, tmp_path: Path) -> None:
        project = _setup_project_with_sync(tmp_path)
        _make_stale(project)
        assert _stale_refs(project) == ["F1"]
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "--all", "--yes", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "F1" in result.output
        assert _stale_refs(project) == []

    def test_all_no_stale_is_noop(self, tmp_path: Path) -> None:
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "--all", "--yes", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_all_requires_yes(self, tmp_path: Path) -> None:
        """--all without --yes is rejected (non-interactive only)."""
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["sync-update", "--all", "--project", str(project)])
        assert result.exit_code != 0

    def test_all_rejects_ref_argument(self, tmp_path: Path) -> None:
        """--all and an explicit ref_id are mutually exclusive."""
        project = _setup_project_with_sync(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-update", "F1", "--all", "--yes", "--project", str(project)]
        )
        assert result.exit_code != 0
