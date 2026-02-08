"""Tests for `beadloom sync-update` CLI command."""

from __future__ import annotations

import os
import unittest.mock
from typing import TYPE_CHECKING

import yaml
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
        with unittest.mock.patch("beadloom.cli.click.edit") as mock_edit:
            runner = CliRunner()
            result = runner.invoke(
                main, ["sync-update", "F1", "--project", str(project)],
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

        with unittest.mock.patch("beadloom.cli.click.edit") as mock_edit:
            runner = CliRunner()
            result = runner.invoke(
                main, ["sync-update", "F1", "--project", str(project)],
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

        with unittest.mock.patch("beadloom.cli.click.edit"):
            runner = CliRunner()
            runner.invoke(
                main, ["sync-update", "F1", "--project", str(project)],
                input="y\n",
            )

        # Verify sync_state is now 'ok'.
        from beadloom.db import open_db

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        rows = conn.execute(
            "SELECT status FROM sync_state WHERE ref_id = 'F1'"
        ).fetchall()
        conn.close()
        assert all(r["status"] == "ok" for r in rows)


def _setup_project_with_llm_config(tmp_path: Path) -> Path:
    """Create project with sync_state and LLM config."""
    project = _setup_project_with_sync(tmp_path)

    # Write config with LLM section.
    config_path = project / ".beadloom" / "config.yml"
    config = {
        "languages": [".py"],
        "llm": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key_env": "TEST_ANTHROPIC_KEY",
        },
    }
    config_path.write_text(yaml.dump(config), encoding="utf-8")

    # Make it stale.
    (project / "src" / "api.py").write_text(
        "# beadloom:feature=F1\ndef handler():\n    return 'updated'\n"
    )

    return project


class TestSyncUpdateAuto:
    """Tests for sync-update --auto (LLM integration)."""

    def test_auto_no_llm_config(self, tmp_path: Path) -> None:
        """--auto without llm config shows error."""
        project = _setup_project_with_sync(tmp_path)
        # Write config without llm section.
        config_path = project / ".beadloom" / "config.yml"
        config_path.write_text(yaml.dump({"languages": [".py"]}), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-update", "F1", "--auto", "--project", str(project)]
        )
        assert result.exit_code != 0
        assert "LLM not configured" in result.output

    def test_auto_applies_llm_changes(self, tmp_path: Path) -> None:
        """--auto with accept should apply LLM-proposed changes and mark synced."""
        project = _setup_project_with_llm_config(tmp_path)

        proposed_doc = "## Spec\n\nUpdated feature spec for handler returning 'updated'.\n"

        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": proposed_doc}],
        }

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "sk-test-123"}),
            unittest.mock.patch("beadloom.llm_updater.httpx") as mock_httpx,
        ):
            mock_httpx.post.return_value = mock_response
            runner = CliRunner()
            result = runner.invoke(
                main, ["sync-update", "F1", "--auto", "--project", str(project)],
                input="yes\n",
            )

        assert result.exit_code == 0, result.output
        assert "Applied and synced" in result.output

        # Verify doc was updated.
        doc_content = (project / "docs" / "spec.md").read_text(encoding="utf-8")
        assert "Updated feature spec" in doc_content

        # Verify sync_state is ok.
        from beadloom.db import open_db

        conn = open_db(project / ".beadloom" / "beadloom.db")
        rows = conn.execute(
            "SELECT status FROM sync_state WHERE ref_id = 'F1'"
        ).fetchall()
        conn.close()
        assert all(r["status"] == "ok" for r in rows)

    def test_auto_rejects_changes(self, tmp_path: Path) -> None:
        """--auto with reject should not modify doc."""
        project = _setup_project_with_llm_config(tmp_path)

        original_doc = (project / "docs" / "spec.md").read_text(encoding="utf-8")
        proposed_doc = "## Spec\n\nDifferent content.\n"

        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": proposed_doc}],
        }

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "sk-test-123"}),
            unittest.mock.patch("beadloom.llm_updater.httpx") as mock_httpx,
        ):
            mock_httpx.post.return_value = mock_response
            runner = CliRunner()
            result = runner.invoke(
                main, ["sync-update", "F1", "--auto", "--project", str(project)],
                input="no\n",
            )

        assert result.exit_code == 0
        assert "Skipped" in result.output

        # Doc should not be changed.
        current_doc = (project / "docs" / "spec.md").read_text(encoding="utf-8")
        assert current_doc == original_doc

    def test_auto_all_synced(self, tmp_path: Path) -> None:
        """--auto when nothing is stale should report up to date."""
        project = _setup_project_with_sync(tmp_path)

        # Write config with LLM section but don't make anything stale.
        config_path = project / ".beadloom" / "config.yml"
        config = {
            "languages": [".py"],
            "llm": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "api_key_env": "TEST_ANTHROPIC_KEY",
            },
        }
        config_path.write_text(yaml.dump(config), encoding="utf-8")

        with unittest.mock.patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "sk-test"}):
            runner = CliRunner()
            result = runner.invoke(
                main, ["sync-update", "F1", "--auto", "--project", str(project)]
            )

        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_auto_llm_api_error(self, tmp_path: Path) -> None:
        """--auto should handle LLM API errors gracefully."""
        project = _setup_project_with_llm_config(tmp_path)

        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "sk-test-123"}),
            unittest.mock.patch("beadloom.llm_updater.httpx") as mock_httpx,
        ):
            mock_httpx.post.return_value = mock_response
            runner = CliRunner()
            result = runner.invoke(
                main, ["sync-update", "F1", "--auto", "--project", str(project)]
            )

        # Should not crash — error is printed per-doc.
        assert result.exit_code == 0
        assert "Error" in result.output
