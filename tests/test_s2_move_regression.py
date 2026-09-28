"""S2 move-regression hardening (BDL-051 / S2, BEAD-05).

S2 dev moved ``tools/ai_techwriter/`` -> ``src/beadloom/ai_agents/ai_techwriter/``,
declared the ``ai_agents`` domain + ``ai-techwriter`` feature, retired the
BDL-047/048 vendoring (the recipe + provisioner now ride as **package data** read
via :mod:`importlib.resources`; the scaffold no longer copies ``*.py.txt``),
added a ``beadloom-ai-techwriter`` console entry, and 2 char-class
``forbid_import`` boundary rules.

These tests HARDEN the move without re-testing the (already-passing) moved
harness unit tests. They focus on the seams the move actually touched:

* **Packaging/resources** — recipe + provisioner resolve from the *installed
  package* (not a relative ``tools/`` path), independent of CWD.
* **Invocation** — ``python -m beadloom.ai_agents.ai_techwriter`` resolves; the
  ``beadloom-ai-techwriter`` console entry points at the real callable.
* **No-vendoring scaffold** — the emitted CI workflow references the installed
  module; no vendored harness Python is produced; the vendoring symbols are gone.
* **CI configs** — root + template CI reference ``beadloom.ai_agents.ai_techwriter``
  (not ``tools.ai_techwriter``); the BDL-049/050 markers survive; YAML is valid.
* **Boundary rule (the fnmatch char-class hack)** — a synthetic core->ai_agents
  import IS flagged; an ai_agents->application import and an ai_agents self-import
  are NOT. Every core source dir is covered; ai_agents excludes itself.
* **Graph** — the ``ai_agents`` domain + ``ai-techwriter`` feature resolve.
* **Behavior** — the moved provider/scope logic behaves at the new path.
"""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from importlib import resources
from typing import TYPE_CHECKING

import pytest
import yaml

from tests.support import ci_pipeline_properties as properties
from tests.support.package_under_test import PACKAGE_ROOT

if TYPE_CHECKING:
    from pathlib import Path


_HARNESS_PKG = "beadloom.ai_agents.ai_techwriter"
#: Derived from the IMPORTED package rather than from this file: under
#: `mutmut run` the suite is copied beside the mutated sources, so a root built
#: from `__file__` answers about the copy (BDL-UX #289). This walk reads
#: `*.py.txt`, which mutmut copies rather than mutates, so the move keeps the
#: population identical and removes the shape.
_TPL = PACKAGE_ROOT / "onboarding" / "templates" / "ai_techwriter"


# ---------------------------------------------------------------------------
# Packaging / importlib.resources — recipe + provisioner ride in the package
# ---------------------------------------------------------------------------


class TestPackageDataResources:
    """The recipe + provisioner load from the installed package via
    importlib.resources — NOT a relative ``tools/`` path — and resolve even
    when the CWD is not the repo root."""

    @pytest.mark.parametrize("name", ["recipe.yaml", "provision-runner.sh"])
    def test_package_data_resolves_to_real_content(self, name: str) -> None:
        resource = resources.files(_HARNESS_PKG) / name
        text = resource.read_text(encoding="utf-8")
        assert text.strip(), f"{name} resolved to empty content"

    def test_recipe_is_valid_yaml_via_resources(self) -> None:
        text = (resources.files(_HARNESS_PKG) / "recipe.yaml").read_text(
            encoding="utf-8"
        )
        loaded = yaml.safe_load(text)
        assert isinstance(loaded, dict)

    def test_default_recipe_path_returns_real_content(self) -> None:
        from beadloom.ai_agents.ai_techwriter.provider import default_recipe_path

        path = default_recipe_path()
        assert path.is_file()
        assert "version" in path.read_text(encoding="utf-8").lower()

    def test_default_recipe_path_matches_resources(self) -> None:
        """The provider's recipe path returns the same bytes resources serves."""
        from beadloom.ai_agents.ai_techwriter.provider import default_recipe_path

        via_provider = default_recipe_path().read_text(encoding="utf-8")
        via_resources = (resources.files(_HARNESS_PKG) / "recipe.yaml").read_text(
            encoding="utf-8"
        )
        assert via_provider == via_resources

    def test_recipe_resolves_when_cwd_not_repo_root(self, tmp_path: Path) -> None:
        """A subprocess started OUTSIDE the repo root still resolves the recipe
        from the installed package (proves no reliance on a relative tools/ path)."""
        code = (
            "from beadloom.ai_agents.ai_techwriter.provider import default_recipe_path;"
            "p = default_recipe_path();"
            "assert p.is_file(), p;"
            "print('OK')"
        )
        proc = subprocess.run(  # noqa: S603 - fixed argv, no untrusted input
            [sys.executable, "-c", code],
            cwd=tmp_path,
            capture_output=True,
            # The child speaks UTF-8 by contract (our own CLI, a JSON payload, a shell
            # block from a YAML file); `text=True` would have decoded it with the
            # image's locale instead (BDL-061.42).
            encoding="utf-8",
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert "OK" in proc.stdout

    def test_provisioner_package_data_is_fail_hard_bash(self) -> None:
        """The provisioner shipped as package data is the hardened script
        (sanity that the right file rode along, not a stub)."""
        text = (resources.files(_HARNESS_PKG) / "provision-runner.sh").read_text(
            encoding="utf-8"
        )
        assert "set -euo pipefail" in text


# ---------------------------------------------------------------------------
# Invocation — python -m ... + the console entry point
# ---------------------------------------------------------------------------


class TestInvocation:
    def test_module_invocation_resolves(self, tmp_path: Path) -> None:
        """``python -m beadloom.ai_agents.ai_techwriter --help`` resolves from
        any CWD (the module + its __main__ are importable)."""
        proc = subprocess.run(  # noqa: S603 - fixed argv
            [sys.executable, "-m", _HARNESS_PKG, "--help"],
            cwd=tmp_path,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert "--platform" in proc.stdout

    def test_console_entry_points_at_real_callable(self) -> None:
        """The ``beadloom-ai-techwriter`` console script is registered and
        resolves to the harness Click command."""
        eps = importlib.metadata.entry_points(group="console_scripts")
        match = {e.name: e.value for e in eps if e.name == "beadloom-ai-techwriter"}
        assert match == {
            "beadloom-ai-techwriter": "beadloom.ai_agents.ai_techwriter.cli:main"
        }
        # The referenced callable is importable and is a Click command.
        ep = next(e for e in eps if e.name == "beadloom-ai-techwriter")
        loaded = ep.load()
        from beadloom.ai_agents.ai_techwriter.cli import main as cli_main

        assert loaded is cli_main

    def test_main_export_matches_cli_main(self) -> None:
        """The package's top-level ``main`` re-export is the CLI command."""
        import beadloom.ai_agents.ai_techwriter as pkg
        from beadloom.ai_agents.ai_techwriter.cli import main as cli_main

        assert pkg.main is cli_main


# ---------------------------------------------------------------------------
# No-vendoring scaffold — installed module, no harness Python copied
# ---------------------------------------------------------------------------


class TestNoVendoringScaffold:
    def _scaffold(self, tmp_path: Path, platform: str = "github") -> Path:
        from beadloom.onboarding.ai_techwriter_setup import scaffold

        project = tmp_path / "proj"
        project.mkdir()
        scaffold(project, platform=platform)
        return project

    def test_workflow_references_installed_module(self, tmp_path: Path) -> None:
        project = self._scaffold(tmp_path)
        wf = (project / ".github" / "workflows" / "ai-techwriter.yml").read_text(
            encoding="utf-8"
        )
        assert "python -m beadloom.ai_agents.ai_techwriter" in wf
        # The retired vendored path must not be referenced.
        assert "tools.ai_techwriter" not in wf
        assert "python -m tools" not in wf

    def test_scaffold_writes_no_harness_py_txt(self, tmp_path: Path) -> None:
        """The scaffold must NOT emit any vendored ``*.py.txt`` harness module."""
        project = self._scaffold(tmp_path)
        py_txt = list(project.rglob("*.py.txt"))
        assert py_txt == [], f"unexpected vendored modules: {py_txt}"
        # And no harness .py landed in the target tools/ dir either.
        harness = project / "tools" / "ai_techwriter"
        assert not (harness / "runner.py").exists()
        assert not (harness / "seams.py").exists()
        assert not (harness / "__init__.py").exists()

    def test_vendoring_symbols_retired(self) -> None:
        """No lingering HARNESS_MODULES / sync_vendored_harness drift-guard."""
        import beadloom.onboarding.ai_techwriter_setup as setup

        for sym in (
            "HARNESS_MODULES",
            "sync_vendored_harness",
            "vendored_harness_root",
            "vendor_harness",
            "_HARNESS_MODULES",
        ):
            assert not hasattr(setup, sym), f"vendoring symbol survived: {sym}"

    def test_no_harness_template_dir_survives(self) -> None:
        """The old ``templates/ai_techwriter/harness/`` (the ``*.py.txt`` store)
        is gone — the scaffold has nothing to vendor from."""
        assert not (_TPL / "harness").exists()
        assert list(_TPL.glob("**/*.py.txt")) == []


# ---------------------------------------------------------------------------
# CI configs — new module path + BDL-049/050 markers + valid YAML
# ---------------------------------------------------------------------------


def _ci_configs() -> list[Path]:
    """The two CI templates the package ships.

    This repository's own two pipelines are held to the same properties as
    self-checks, in
    ``tests/self_check/config/test_the_ci_configurations_survive_the_harness_move.py``
    (BDL-074 F3). Both run the bodies in :mod:`tests.support.ci_pipeline_properties`.
    """
    return [_TPL / "github-workflow.yml", _TPL / "gitlab-ci-job.yml"]


class TestCiConfigsModulePath:
    @pytest.mark.parametrize("cfg", _ci_configs(), ids=lambda p: p.name)
    def test_references_new_module_not_tools(self, cfg: Path) -> None:
        properties.references_new_module_not_tools(cfg)

    @pytest.mark.parametrize("cfg", _ci_configs(), ids=lambda p: p.name)
    def test_is_valid_yaml(self, cfg: Path) -> None:
        # GitHub Actions reuses the bare word `on:` which PyYAML loads as the
        # boolean True key; that is still valid YAML — the property asserts it
        # parses to a mapping.
        properties.ci_config_is_valid_yaml(cfg)


# ---------------------------------------------------------------------------
# Boundary rule — the fnmatch char-class hack (the riskiest part of S2)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Graph — ai_agents domain + ai-techwriter feature resolve
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Behavior unchanged — provider/scope logic at the new path
# ---------------------------------------------------------------------------


class TestBehaviorUnchangedAtNewPath:
    def test_provider_resolves_base_url_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beadloom.ai_agents.ai_techwriter.provider import (
            DASHSCOPE_OPENAI_BASE_URL,
            qwen_provider,
        )

        monkeypatch.delenv("QWEN_BASE_URL", raising=False)
        assert qwen_provider().base_url == DASHSCOPE_OPENAI_BASE_URL
        monkeypatch.setenv("QWEN_BASE_URL", "https://maas.example/v1")
        assert qwen_provider().base_url == "https://maas.example/v1"

    def test_provider_omits_key_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beadloom.ai_agents.ai_techwriter.provider import qwen_provider

        monkeypatch.delenv("QWEN_API_KEY", raising=False)
        cfg = qwen_provider()
        assert cfg.resolve_api_key() is None
        assert "OPENAI_API_KEY" not in cfg.goose_env(api_key=None)

    def test_dry_run_smoke_at_new_path(self, tmp_path: Path) -> None:
        """The harness entrypoint runs a no-network dry-run from the new path."""
        proc = subprocess.run(  # noqa: S603 - fixed argv
            [
                sys.executable,
                "-m",
                _HARNESS_PKG,
                "--platform",
                "github",
                "--dry-run",
            ],
            cwd=tmp_path,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert "dry-run" in proc.stdout
