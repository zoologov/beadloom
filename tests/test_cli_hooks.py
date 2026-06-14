"""Tests for `beadloom install-hooks` CLI command."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from click.testing import CliRunner

from beadloom.services.cli import main


def _path_with_git(*prefixes: str) -> str:
    """A PATH string containing git's own dir (so `git push` can re-exec git)."""
    git_bin = shutil.which("git")
    assert git_bin is not None
    git_dir = str(Path(git_bin).parent)
    return ":".join([*prefixes, git_dir, "/usr/bin", "/bin"])


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

    def test_coherence_block_present_warn(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        content = (project / ".git" / "hooks" / "pre-commit").read_text()
        assert "ACTIVE / tracker coherence" in content
        assert "command -v bd >/dev/null 2>&1" in content
        assert "active-sync --stage" in content
        # --stage stages exactly the reconciled paths; the broad `git add -u`
        # over the features subtree (which over-staged unrelated docs) is gone.
        assert "git add -u .claude/development/docs/features" not in content

    def test_coherence_block_present_block(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--mode", "block", "--project", str(project)])
        content = (project / ".git" / "hooks" / "pre-commit").read_text()
        assert "ACTIVE / tracker coherence" in content
        assert "command -v bd >/dev/null 2>&1" in content
        assert "active-sync --stage" in content
        assert "git add -u .claude/development/docs/features" not in content

    def test_coherence_block_after_sync_check(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        content = (project / ".git" / "hooks" / "pre-commit").read_text()
        assert content.index("sync-check") < content.index("ACTIVE / tracker coherence")

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


def _run_hook(hook_path: Path, cwd: Path, path_env: str) -> int:
    """Execute a POSIX-sh hook with a controlled PATH; return its exit code."""
    proc = subprocess.run(  # noqa: S603
        ["/bin/sh", str(hook_path)],
        cwd=cwd,
        env={"PATH": path_env},
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode


class TestInstallHooksPrePush:
    """The blocking pre-push Beadloom Gate hook (BDL-052 S1)."""

    def test_default_installs_both_hooks(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["install-hooks", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert (project / ".git" / "hooks" / "pre-commit").exists()
        assert (project / ".git" / "hooks" / "pre-push").exists()

    def test_pre_push_runs_beadloom_ci(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        content = (project / ".git" / "hooks" / "pre-push").read_text()
        assert "beadloom ci" in content
        # POSIX sh + guard.
        assert content.startswith("#!/bin/sh")
        assert "command -v beadloom" in content

    @staticmethod
    def _shim_beadloom(tmp_path: Path, exit_code: int) -> str:
        """Put a fake `beadloom` on PATH that exits with ``exit_code``."""
        bindir = tmp_path / "bin"
        bindir.mkdir()
        shim = bindir / "beadloom"
        shim.write_text(f"#!/bin/sh\nexit {exit_code}\n")
        shim.chmod(0o755)
        return f"{bindir}:/usr/bin:/bin"

    def test_pre_push_blocks_on_red(self, tmp_path: Path) -> None:
        """Hook exits non-zero when the Gate (beadloom ci) returns non-zero."""
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        hook_path = project / ".git" / "hooks" / "pre-push"
        path_env = self._shim_beadloom(tmp_path, exit_code=1)
        assert _run_hook(hook_path, project, path_env) != 0

    def test_pre_push_passes_on_green(self, tmp_path: Path) -> None:
        """Hook exits zero when the Gate (beadloom ci) returns zero."""
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        hook_path = project / ".git" / "hooks" / "pre-push"
        path_env = self._shim_beadloom(tmp_path, exit_code=0)
        assert _run_hook(hook_path, project, path_env) == 0

    def test_pre_push_no_op_without_beadloom(self, tmp_path: Path) -> None:
        """Outside a flow repo (beadloom absent) the hook is a safe no-op."""
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        hook_path = project / ".git" / "hooks" / "pre-push"
        # PATH with NO beadloom on it.
        assert _run_hook(hook_path, project, "/usr/bin:/bin") == 0

    def test_pre_push_is_executable(self, tmp_path: Path) -> None:
        import stat

        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        mode = (project / ".git" / "hooks" / "pre-push").stat().st_mode
        assert mode & stat.S_IXUSR

    def test_pre_push_selector_installs_only_pre_push(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["install-hooks", "--pre-push", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert (project / ".git" / "hooks" / "pre-push").exists()
        assert not (project / ".git" / "hooks" / "pre-commit").exists()

    def test_pre_commit_selector_installs_only_pre_commit(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["install-hooks", "--pre-commit", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert (project / ".git" / "hooks" / "pre-commit").exists()
        assert not (project / ".git" / "hooks" / "pre-push").exists()

    def test_remove_removes_both(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        result = runner.invoke(
            main, ["install-hooks", "--remove", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert not (project / ".git" / "hooks" / "pre-commit").exists()
        assert not (project / ".git" / "hooks" / "pre-push").exists()

    def test_remove_pre_push_only(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        result = runner.invoke(
            main, ["install-hooks", "--remove", "--pre-push", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert (project / ".git" / "hooks" / "pre-commit").exists()
        assert not (project / ".git" / "hooks" / "pre-push").exists()

    def test_pre_push_idempotent(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--pre-push", "--project", str(project)])
        first = (project / ".git" / "hooks" / "pre-push").read_text()
        runner.invoke(main, ["install-hooks", "--pre-push", "--project", str(project)])
        second = (project / ".git" / "hooks" / "pre-push").read_text()
        assert first == second

    def test_pre_push_actionable_message(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        content = (project / ".git" / "hooks" / "pre-push").read_text()
        assert "tech-writer" in content or "coordinator" in content
        assert "--no-verify" in content


def _init_real_git_repo(tmp_path: Path, name: str) -> Path:
    """Create a real working git repo with one commit + a bare origin remote."""
    repo = tmp_path / name
    repo.mkdir()
    bare = tmp_path / f"{name}.git"

    def _git(cwd: Path, *args: str) -> None:
        subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    subprocess.run(  # noqa: S603
        ["git", "init", "--quiet", "--bare", str(bare)],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "commit", "--quiet", "--allow-empty", "-m", "init")
    _git(repo, "remote", "add", "origin", str(bare))
    return repo


def _push(repo: Path, path_env: str) -> int:
    """`git push origin HEAD:main` under a controlled PATH; return the exit code."""
    env = dict(os.environ)
    env["PATH"] = path_env
    proc = subprocess.run(
        ["git", "push", "origin", "HEAD:main"],  # noqa: S607
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode


class TestPrePushEndToEndViaGit:
    """End-to-end: a REAL ``git push`` honours the installed pre-push hook's exit
    code (the dev's tests run the hook script directly; these prove git itself
    enforces it — block on red, allow on green/no-op)."""

    @staticmethod
    def _shim(tmp_path: Path, name: str, exit_code: int) -> str:
        bindir = tmp_path / f"bin-{name}"
        bindir.mkdir()
        shim = bindir / "beadloom"
        shim.write_text(f"#!/bin/sh\nexit {exit_code}\n")
        shim.chmod(0o755)
        # Include git's own dir on PATH so `git push` can re-exec git.
        return _path_with_git(str(bindir))

    def test_push_blocked_on_red_gate(self, tmp_path: Path) -> None:
        repo = _init_real_git_repo(tmp_path, "red")
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--pre-push", "--project", str(repo)])
        path_env = self._shim(tmp_path, "red", exit_code=1)
        assert _push(repo, path_env) != 0  # push rejected by the Gate.

    def test_push_allowed_on_green_gate(self, tmp_path: Path) -> None:
        repo = _init_real_git_repo(tmp_path, "green")
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--pre-push", "--project", str(repo)])
        path_env = self._shim(tmp_path, "green", exit_code=0)
        assert _push(repo, path_env) == 0  # green Gate -> push goes through.

    def test_push_allowed_when_beadloom_absent(self, tmp_path: Path) -> None:
        """A non-flow repo (beadloom not on PATH) is never blocked by the guard."""
        repo = _init_real_git_repo(tmp_path, "noflow")
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--pre-push", "--project", str(repo)])
        path_env = _path_with_git()  # no beadloom anywhere on PATH.
        assert _push(repo, path_env) == 0


class TestPrePushHookFailSafe:
    """The hook content is fail-safe: the absence guard precedes the Gate so a
    repo without beadloom never reaches (and never hangs/raises on) `beadloom ci`."""

    def _pre_push(self, tmp_path: Path) -> str:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--pre-push", "--project", str(project)])
        return (project / ".git" / "hooks" / "pre-push").read_text()

    def test_guard_precedes_gate(self, tmp_path: Path) -> None:
        content = self._pre_push(tmp_path)
        assert content.index("command -v beadloom") < content.index("beadloom ci")

    def test_guard_exits_zero_before_running_ci(self, tmp_path: Path) -> None:
        content = self._pre_push(tmp_path)
        # The guard's body is a bare `exit 0` (no-op), reached when beadloom absent.
        guard_block = content.split("beadloom ci")[0]
        assert "exit 0" in guard_block

    def test_blocks_only_via_explicit_nonzero_exit(self, tmp_path: Path) -> None:
        content = self._pre_push(tmp_path)
        # Block path is an explicit `exit 1` guarded by the ci exit code, never a
        # crash/`set -e`-style abort.
        assert "exit 1" in content
        assert "set -e" not in content

    def test_install_outside_git_repo_errors_cleanly(self, tmp_path: Path) -> None:
        """No `.git/hooks` -> clean error exit, no traceback."""
        project = tmp_path / "bare"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            main, ["install-hooks", "--pre-push", "--project", str(project)]
        )
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "git repository" in result.output


class TestPreCommitUnchangedByPrePush:
    """Installing pre-push must not regress the pre-commit hook content."""

    def _pre_commit(self, tmp_path: Path, *extra: str) -> str:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project), *extra])
        return (project / ".git" / "hooks" / "pre-commit").read_text()

    def test_pre_commit_warn_still_has_full_checks(self, tmp_path: Path) -> None:
        content = self._pre_commit(tmp_path)
        assert "ruff check" in content
        assert "mypy" in content
        assert "sync-check" in content
        assert "active-sync" in content  # BDL-053 coherence intact.
        assert "beadloom ci" not in content  # the Gate lives in pre-push only.

    def test_pre_commit_block_still_has_full_checks(self, tmp_path: Path) -> None:
        content = self._pre_commit(tmp_path, "--mode", "block")
        assert "ruff check" in content
        assert "mypy" in content
        assert "sync-check" in content
        assert "active-sync" in content
        assert "beadloom ci" not in content

    def test_default_install_pre_commit_identical_to_pre_commit_only(
        self, tmp_path: Path
    ) -> None:
        """The pre-commit written under the default (both) install is byte-identical
        to the one written with --pre-commit alone (pre-push addition is additive)."""
        second = tmp_path / "second"
        second.mkdir()
        both = self._pre_commit(tmp_path)
        only = self._pre_commit(second, "--pre-commit")
        assert both == only


class TestRemoveSelectors:
    def test_remove_pre_commit_only(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--project", str(project)])
        result = runner.invoke(
            main, ["install-hooks", "--remove", "--pre-commit", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert not (project / ".git" / "hooks" / "pre-commit").exists()
        assert (project / ".git" / "hooks" / "pre-push").exists()

    def test_remove_when_nothing_installed_is_clean_noop(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["install-hooks", "--remove", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert "No matching hook to remove" in result.output


class TestIdempotentNoDuplication:
    def test_rerun_does_not_duplicate_gate_invocation(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["install-hooks", "--pre-push", "--project", str(project)])
        first = (project / ".git" / "hooks" / "pre-push").read_text()
        runner.invoke(main, ["install-hooks", "--pre-push", "--project", str(project)])
        second = (project / ".git" / "hooks" / "pre-push").read_text()
        # Clean overwrite, not append: re-install leaves identical content with no
        # extra Gate invocation lines.
        assert first == second
        assert second.count("\nbeadloom ci\n") == 1

    def test_block_mode_with_both_hooks(self, tmp_path: Path) -> None:
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["install-hooks", "--mode", "block", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        # block pre-commit + the (always-blocking) pre-push Gate coexist.
        assert "Error: ruff" in (project / ".git" / "hooks" / "pre-commit").read_text()
        assert "beadloom ci" in (project / ".git" / "hooks" / "pre-push").read_text()
