"""Tests for `beadloom install-hooks` CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_git_project(tmp_path: Path) -> Path:
    """Create a project with .git/hooks directory."""
    project = tmp_path / "proj"
    project.mkdir()
    hooks_dir = project / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    (project / ".beadloom").mkdir()
    return project


class TestInstallHooksCommand:
    def test_creates_pre_commit_hook(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["install-hooks", "--project", str(project)])
        assert result.exit_code == 0, result.output
        hook_path = project / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()
        content = hook_path.read_text()
        assert "beadloom" in content
        assert "sync-check" in content

    def test_hook_is_executable(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        hook_path = project / ".git" / "hooks" / "pre-commit"
        import stat

        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR  # Owner execute bit set.

    def test_warn_mode_default(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        hook_path = project / ".git" / "hooks" / "pre-commit"
        content = hook_path.read_text()
        # Warn mode should NOT have "exit 1" in the stale section.
        assert "# exit 1" in content or "exit 1" not in content.split("block")[0]

    def test_block_mode(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["install-hooks", "--mode", "block", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        hook_path = project / ".git" / "hooks" / "pre-commit"
        content = hook_path.read_text()
        assert "exit 1" in content

    def test_no_git_dir(self, tmp_path: Path) -> None:
        project = tmp_path / "no-git"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["install-hooks", "--project", str(project)])
        assert result.exit_code != 0

    def test_remove_flag(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        # Install first.
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        hook_path = project / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()
        # Remove.
        result = runner.invoke(main, ["install-hooks", "--remove", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert not hook_path.exists()
