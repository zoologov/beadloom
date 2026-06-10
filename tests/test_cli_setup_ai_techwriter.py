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
