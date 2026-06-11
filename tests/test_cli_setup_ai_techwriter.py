"""Tests for `beadloom setup-ai-techwriter` (BDL-047 / F4.1, G8; BDL-051 / S2).

The command scaffolds the AI tech-writer into ANY target repo. Since BDL-051 / S2
the harness ships INSIDE the installed ``beadloom`` package
(:mod:`beadloom.ai_agents.ai_techwriter`), so the scaffold no longer vendors any
Python: it drops the chosen platform's CI wrapper (which invokes
``python -m beadloom.ai_agents.ai_techwriter``), the operator artifacts
``tools/ai_techwriter/{recipe.yaml,provision-runner.sh}`` copied from the harness
package data, and the getting-started guide. It is idempotent (a re-run cleanly
overwrites the generated copy) and rejects unknown platforms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _run(project: Path, platform: str) -> object:
    runner = CliRunner()
    return runner.invoke(
        main,
        ["setup-ai-techwriter", "--platform", platform, "--project", str(project)],
    )


class TestNoVendoring:
    """BDL-051 / S2: the harness ships in the installed package — the scaffold
    must NOT copy any harness Python, and the vendoring machinery is gone."""

    def test_does_not_vendor_harness_python(self, tmp_path: Path) -> None:
        from beadloom.onboarding.ai_techwriter_setup import scaffold

        project = tmp_path / "proj"
        project.mkdir()
        scaffold(project, platform="github")
        # No harness .py is copied into the target (it ships in the wheel).
        assert not (project / "tools" / "ai_techwriter" / "runner.py").exists()
        assert not (project / "tools" / "ai_techwriter" / "cli.py").exists()
        assert not (project / "tools" / "__init__.py").exists()

    def test_vendoring_api_retired(self) -> None:
        """The BDL-047/048 vendoring symbols are removed from the module."""
        import beadloom.onboarding.ai_techwriter_setup as setup

        assert not hasattr(setup, "HARNESS_MODULES")
        assert not hasattr(setup, "sync_vendored_harness")
        assert not hasattr(setup, "vendored_harness_root")
        assert not hasattr(setup, "vendor_harness")

    def test_recipe_copied_from_package_data(self, tmp_path: Path) -> None:
        """The recipe lands as an operator reference, byte-identical to the
        harness package-data recipe (read via importlib.resources)."""
        from beadloom.ai_agents.ai_techwriter.provider import default_recipe_path
        from beadloom.onboarding.ai_techwriter_setup import scaffold

        project = tmp_path / "proj"
        project.mkdir()
        scaffold(project, platform="github")
        recipe = project / "tools" / "ai_techwriter" / "recipe.yaml"
        assert recipe.is_file()
        assert recipe.read_text(encoding="utf-8") == default_recipe_path().read_text(
            encoding="utf-8"
        )


class TestSetupAiTechwriterGithub:
    def test_creates_github_workflow(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        result = _run(project, "github")
        assert result.exit_code == 0, result.output
        wf = project / ".github" / "workflows" / "ai-techwriter.yml"
        assert wf.exists()
        text = wf.read_text(encoding="utf-8")
        # BDL-050: the scaffolded workflow is now the consolidated CI pipeline
        # (gate / tests / site-build / ai-techwriter) rather than a single
        # ai-techwriter job — its top-level name is `CI`.
        assert "name: CI" in text
        assert "ai-techwriter:" in text
        assert "python -m beadloom.ai_agents.ai_techwriter" in text
        assert "--platform github" in text
        assert "QWEN_API_KEY" in text

    def test_github_workflow_triggers_on_pull_request(self, tmp_path: Path) -> None:
        """BDL-049: trunk-based — trigger on pull_request (+ manual dispatch),
        not push:main, not nightly cron."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        text = (project / ".github" / "workflows" / "ai-techwriter.yml").read_text(
            encoding="utf-8"
        )
        assert "pull_request:" in text
        assert "branches: [main, master]" in text
        assert "workflow_dispatch:" in text
        assert "--target pr-branch" in text
        # push:main removed (trunk-based replaces per-push refresh).
        assert "\n  push:" not in text
        # No nightly schedule.
        assert "schedule:" not in text
        assert "cron:" not in text

    def test_drops_operator_recipe_no_harness_python(self, tmp_path: Path) -> None:
        """BDL-051 / S2: the scaffold drops the operator recipe (package-data
        reference) but never the harness Python — the harness ships in the
        installed ``beadloom`` package."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "github")
        harness = project / "tools" / "ai_techwriter"
        assert (harness / "recipe.yaml").exists()
        # No vendored harness Python (it ships in the wheel) and no parent init.
        assert not (harness / "runner.py").exists()
        assert not (harness / "__main__.py").exists()
        assert not (project / "tools" / "__init__.py").exists()

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
        assert "python -m beadloom.ai_agents.ai_techwriter --platform gitlab" in text

    def test_gitlab_job_triggers_on_merge_request(self, tmp_path: Path) -> None:
        """BDL-049: trunk-based — trigger on merge_request_event (+ manual web),
        not push-to-main, not scheduled pipelines."""
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "gitlab")
        text = (project / ".gitlab-ci.yml").read_text(encoding="utf-8")
        assert '$CI_PIPELINE_SOURCE == "merge_request_event"' in text
        assert '$CI_PIPELINE_SOURCE == "web"' in text
        assert "--target pr-branch" in text
        # The old push-to-main gate is gone.
        assert '$CI_COMMIT_BRANCH == "main"' not in text
        # No schedule-only gating.
        assert '$CI_PIPELINE_SOURCE == "schedule"' not in text

    def test_drops_operator_recipe_for_gitlab_too(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        _run(project, "gitlab")
        assert (project / "tools" / "ai_techwriter" / "recipe.yaml").exists()
        # No vendored harness Python (ships in the wheel).
        assert not (project / "tools" / "ai_techwriter" / "runner.py").exists()

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


class TestInstalledHarnessIsRunnable:
    def test_installed_harness_runs_dry_run(self, tmp_path: Path) -> None:
        """BDL-051 / S2: the harness ships in the installed ``beadloom`` package,
        so ``python -m beadloom.ai_agents.ai_techwriter`` resolves + runs from a
        scaffolded target repo (no vendored Python copied into the repo)."""
        import subprocess
        import sys

        from beadloom.onboarding.ai_techwriter_setup import scaffold

        project = tmp_path / "fresh-repo"
        project.mkdir()
        scaffold(project, platform="github")
        proc = subprocess.run(  # noqa: S603 - fixed argv (no untrusted input)
            [
                sys.executable,
                "-m",
                "beadloom.ai_agents.ai_techwriter",
                "--platform",
                "github",
                "--dry-run",
            ],
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
        recipe = project / "tools" / "ai_techwriter" / "recipe.yaml"
        before = recipe.read_text(encoding="utf-8")
        # Mutate the scaffolded operator copy; a re-run must restore (clean overwrite).
        recipe.write_text("# stale\n", encoding="utf-8")
        second = _run(project, "github")
        assert second.exit_code == 0, second.output
        assert recipe.read_text(encoding="utf-8") == before

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
