"""Tests for `beadloom setup-ai-techwriter` (BDL-047 / F4.1, G8).

The command scaffolds the AI tech-writer into ANY target repo: it vendors the
deterministic harness package + Goose recipe, drops the chosen platform's CI
wrapper, and writes the 3-step getting-started guide. It is idempotent (a
re-run cleanly overwrites the generated copy) and rejects unknown platforms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.onboarding.ai_techwriter_setup import (
    HARNESS_MODULES,
    vendored_harness_root,
)
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _run(project: Path, platform: str) -> object:
    runner = CliRunner()
    return runner.invoke(
        main,
        ["setup-ai-techwriter", "--platform", platform, "--project", str(project)],
    )


class TestVendoredHarnessAsset:
    def test_vendored_root_exists_and_has_all_modules(self) -> None:
        root = vendored_harness_root()
        assert root.is_dir()
        for module in HARNESS_MODULES:
            assert (root / f"{module}.py.txt").is_file(), module
        assert (root / "recipe.yaml").is_file()

    def test_vendored_harness_matches_live_source(self) -> None:
        """No hand-maintained drift (principle 5): the packaged harness must
        byte-match the live ``tools/ai_techwriter`` source."""
        from pathlib import Path

        live = Path(__file__).resolve().parents[1] / "tools" / "ai_techwriter"
        root = vendored_harness_root()
        for module in HARNESS_MODULES:
            assert (root / f"{module}.py.txt").read_text(encoding="utf-8") == (
                live / f"{module}.py"
            ).read_text(encoding="utf-8"), module
        assert (root / "recipe.yaml").read_text(encoding="utf-8") == (
            live / "recipe.yaml"
        ).read_text(encoding="utf-8")
        # The vendored parent tools/__init__.py asset byte-matches the live file.
        assert (root / "tools_init.py.txt").read_text(encoding="utf-8") == (
            live.parent / "__init__.py"
        ).read_text(encoding="utf-8")


class TestSyncVendoredHarness:
    def test_sync_round_trips_live_source(self, tmp_path: Path) -> None:
        from pathlib import Path

        from beadloom.onboarding.ai_techwriter_setup import sync_vendored_harness

        live = Path(__file__).resolve().parents[1] / "tools" / "ai_techwriter"
        written = sync_vendored_harness(live)
        # Every module + the recipe is (re)written; idempotent against the
        # packaged copy (this is the drift guard run as code).
        assert "runner.py.txt" in written
        assert "recipe.yaml" in written


class TestSetupAiTechwriterGithub:
    def test_creates_github_workflow(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        result = _run(project, "github")
        assert result.exit_code == 0, result.output
        wf = project / ".github" / "workflows" / "ai-techwriter.yml"
        assert wf.exists()
        text = wf.read_text(encoding="utf-8")
        assert "name: AI tech-writer" in text
        assert "python -m tools.ai_techwriter --platform github" in text
        assert "QWEN_API_KEY" in text

    def test_github_workflow_triggers_on_push_main_master(self, tmp_path: Path) -> None:
        """G10: trigger on push to main/master (+ manual dispatch), not nightly cron."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        text = (project / ".github" / "workflows" / "ai-techwriter.yml").read_text(
            encoding="utf-8"
        )
        assert "push:" in text
        assert "branches: [main, master]" in text
        assert "workflow_dispatch: {}" in text
        # No nightly schedule — on-push closes the staleness window.
        assert "schedule:" not in text
        assert "cron:" not in text

    def test_vendors_harness_package(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        harness = project / "tools" / "ai_techwriter"
        assert (harness / "__main__.py").exists()
        assert (harness / "runner.py").exists()
        assert (harness / "recipe.yaml").exists()
        # Vendored python is real .py (not the .py.txt asset form).
        assert not (harness / "runner.py.txt").exists()

    def test_vendors_tools_package_init(self, tmp_path: Path) -> None:
        """The parent ``tools/__init__.py`` is vendored too, so the target does
        not rely on implicit namespace-package behavior for the
        ``python -m tools.ai_techwriter`` invocation (BEAD-11 hardening)."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        tools_init = project / "tools" / "__init__.py"
        assert tools_init.is_file()

    def test_writes_getting_started_guide(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        guide = project / "docs" / "guides" / "ai-techwriter.md"
        assert guide.exists()
        text = guide.read_text(encoding="utf-8")
        assert "QWEN_API_KEY" in text
        assert "setup-ai-techwriter" in text
        # 3-step checklist markers.
        assert "runner" in text.lower()

    def test_does_not_create_gitlab_file(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        assert not (project / ".gitlab-ci.yml").exists()


class TestSetupAiTechwriterGitlab:
    def test_creates_gitlab_job(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        result = _run(project, "gitlab")
        assert result.exit_code == 0, result.output
        ci = project / ".gitlab-ci.yml"
        assert ci.exists()
        text = ci.read_text(encoding="utf-8")
        assert "ai-techwriter:" in text
        assert "python -m tools.ai_techwriter --platform gitlab" in text

    def test_gitlab_job_triggers_on_push_main_master(self, tmp_path: Path) -> None:
        """G10: trigger on push to main/master (+ manual web), not scheduled pipelines."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "gitlab")
        text = (project / ".gitlab-ci.yml").read_text(encoding="utf-8")
        assert '$CI_COMMIT_BRANCH == "main" || $CI_COMMIT_BRANCH == "master"' in text
        assert '$CI_PIPELINE_SOURCE == "web"' in text
        # No schedule-only gating.
        assert '$CI_PIPELINE_SOURCE == "schedule"' not in text

    def test_vendors_harness_for_gitlab_too(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "gitlab")
        assert (project / "tools" / "ai_techwriter" / "runner.py").exists()

    def test_does_not_create_github_workflow(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "gitlab")
        assert not (project / ".github" / "workflows" / "ai-techwriter.yml").exists()


class TestProvisionRunnerScript:
    """BEAD-14 (G11): setup-ai-techwriter also drops a hardened, idempotent
    ``provision-runner.sh`` so any project gets a first-class easy start at
    standing up the self-hosted VPS runner the AI tech-writer needs."""

    def _provision_path(self, project: Path) -> Path:
        return project / "tools" / "ai_techwriter" / "provision-runner.sh"

    def test_github_scaffold_drops_provision_runner(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        result = _run(project, "github")
        assert result.exit_code == 0, result.output
        script = self._provision_path(project)
        assert script.exists()

    def test_gitlab_scaffold_drops_provision_runner(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        result = _run(project, "gitlab")
        assert result.exit_code == 0, result.output
        assert self._provision_path(project).exists()

    def test_provision_runner_is_executable(self, tmp_path: Path) -> None:
        import os

        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        script = self._provision_path(project)
        assert os.access(script, os.X_OK), "provision-runner.sh must be executable"

    def test_provision_runner_fail_hard_and_hardening_markers(
        self, tmp_path: Path
    ) -> None:
        """The lessons we lived: fail-hard shell, RAM/swap/disk guards."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        text = self._provision_path(project).read_text(encoding="utf-8")
        # fail-hard on critical steps.
        assert "set -euo pipefail" in text
        # RAM precheck (refuse/warn under ~2 GB, recommend >=4 GB).
        assert "MIN_RAM" in text or "min_ram" in text
        assert "MemTotal" in text or "/proc/meminfo" in text
        # Swap guaranteed BEFORE apt, fail hard if it can't be created.
        assert "swapon" in text
        assert "swapfile" in text.lower()
        # Disk precheck (fail under a sane threshold ~5 GB).
        assert "MIN_DISK" in text or "min_disk" in text or "df " in text

    def test_provision_runner_parameterized_both_platforms(
        self, tmp_path: Path
    ) -> None:
        """Parameterized, not repo-hardcoded: takes repo URL + token + platform,
        and registers a GitHub Actions runner OR a GitLab Runner accordingly."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        text = self._provision_path(project).read_text(encoding="utf-8")
        # Clean CLI: flags for repo / token / platform.
        assert "--platform" in text
        assert "--repo" in text
        assert "--token" in text
        # GitHub registration step (Actions runner config).
        assert "config.sh" in text
        assert "self-hosted,ai-techwriter" in text or "self-hosted" in text
        # GitLab registration step (GitLab Runner).
        assert "gitlab-runner" in text and "register" in text

    def test_provision_runner_goose_best_effort_verified(self, tmp_path: Path) -> None:
        """Goose/beadloom/bd are best-effort + verified (warn + report
        ``goose --version`` at the end), not fail-hard."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        text = self._provision_path(project).read_text(encoding="utf-8")
        assert "goose --version" in text
        assert "beadloom" in text

    def test_provision_runner_no_inlined_secret(self, tmp_path: Path) -> None:
        """No secrets inlined: token comes via arg/env, never written to repo."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        text = self._provision_path(project).read_text(encoding="utf-8")
        # The QWEN key lives only on the runner / CI secret, not in this script.
        assert "QWEN_API_KEY=" not in text

    def test_provision_runner_bash_parses(self, tmp_path: Path) -> None:
        """``bash -n`` must parse the emitted script (shellcheck-clean where
        available; at minimum valid bash syntax)."""
        import shutil
        import subprocess

        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        script = self._provision_path(project)
        bash = shutil.which("bash")
        assert bash is not None
        proc = subprocess.run(  # noqa: S603 - fixed argv
            [bash, "-n", str(script)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        shellcheck = shutil.which("shellcheck")
        if shellcheck is not None:
            sc = subprocess.run(  # noqa: S603 - fixed argv
                [shellcheck, "-S", "warning", str(script)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert sc.returncode == 0, sc.stdout + sc.stderr

    def test_provision_runner_rerun_idempotent(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        script = self._provision_path(project)
        before = script.read_text(encoding="utf-8")
        script.write_text("# stale\n", encoding="utf-8")
        _run(project, "github")
        assert script.read_text(encoding="utf-8") == before

    def test_guide_documents_provision_runner_flow(self, tmp_path: Path) -> None:
        """The guide documents the <=3-step flow including the provision-runner
        invocation with --platform/--repo/--token."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        guide = (project / "docs" / "guides" / "ai-techwriter.md").read_text(
            encoding="utf-8"
        )
        assert "provision-runner.sh" in guide
        assert "--platform" in guide
        assert "--repo" in guide
        assert "--token" in guide


class TestVendoredHarnessIsRunnable:
    def test_vendored_harness_runs_dry_run(self, tmp_path: Path) -> None:
        """The whole point of vendoring: ``python -m tools.ai_techwriter``
        resolves + runs from a fresh target repo with only the scaffolded
        files present (no Beadloom source tree)."""
        import subprocess
        import sys

        from beadloom.onboarding.ai_techwriter_setup import scaffold

        project = tmp_path / "fresh-repo"
        project.mkdir()
        scaffold(project, platform="github")
        proc = subprocess.run(  # noqa: S603 - fixed argv (no untrusted input)
            [sys.executable, "-m", "tools.ai_techwriter", "--platform", "github", "--dry-run"],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert "dry-run" in proc.stdout


class TestIdempotenceAndErrors:
    def test_rerun_is_idempotent(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        first = _run(project, "github")
        assert first.exit_code == 0, first.output
        runner_py = project / "tools" / "ai_techwriter" / "runner.py"
        before = runner_py.read_text(encoding="utf-8")
        # Mutate the vendored copy; a re-run must restore (clean overwrite).
        runner_py.write_text("# stale\n", encoding="utf-8")
        second = _run(project, "github")
        assert second.exit_code == 0, second.output
        assert runner_py.read_text(encoding="utf-8") == before

    def test_unknown_platform_errors(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        result = _run(project, "bitbucket")
        assert result.exit_code != 0
        assert "bitbucket" in result.output or "Invalid value" in result.output

    def test_scaffold_rejects_unknown_platform_directly(self, tmp_path: Path) -> None:
        import pytest

        from beadloom.onboarding.ai_techwriter_setup import scaffold

        with pytest.raises(ValueError, match="unknown platform"):
            scaffold(tmp_path, platform="bitbucket")

    def test_rerun_gitlab_does_not_duplicate_job(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "gitlab")
        first = (project / ".gitlab-ci.yml").read_text(encoding="utf-8")
        _run(project, "gitlab")
        second = (project / ".gitlab-ci.yml").read_text(encoding="utf-8")
        # Already-wired marker → file left as-is, no duplicate job.
        assert first == second
        assert second.count("ai-techwriter:") == 1

    def test_existing_gitlab_ci_is_not_clobbered_blindly(self, tmp_path: Path) -> None:
        """If a .gitlab-ci.yml already exists, the command must not silently
        destroy the user's other stages."""
        project = tmp_path / "proj"
        project.mkdir()
        (project / ".gitlab-ci.yml").write_text(
            "stages:\n  - build\nbuild:\n  script:\n    - make\n",
            encoding="utf-8",
        )
        result = _run(project, "gitlab")
        # Either it merges/appends or it skips with a clear message — never a
        # silent total overwrite that loses the build job.
        text = (project / ".gitlab-ci.yml").read_text(encoding="utf-8")
        assert result.exit_code == 0, result.output
        assert "build" in text
