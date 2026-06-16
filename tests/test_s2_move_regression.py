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

from beadloom.graph.rule_engine import (
    ImportBoundaryRule,
    evaluate_import_boundary_rules,
    load_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path

_HARNESS_PKG = "beadloom.ai_agents.ai_techwriter"
_REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
_GITLAB_YML = _REPO_ROOT / ".gitlab-ci.yml"
_TPL = _REPO_ROOT / "src" / "beadloom" / "onboarding" / "templates" / "ai_techwriter"


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
            text=True,
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
            text=True,
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
    return [
        _CI_YML,
        _GITLAB_YML,
        _TPL / "github-workflow.yml",
        _TPL / "gitlab-ci-job.yml",
    ]


class TestCiConfigsModulePath:
    @pytest.mark.parametrize("cfg", _ci_configs(), ids=lambda p: p.name)
    def test_references_new_module_not_tools(self, cfg: Path) -> None:
        text = cfg.read_text(encoding="utf-8")
        assert "beadloom.ai_agents.ai_techwriter" in text
        assert "tools.ai_techwriter" not in text

    @pytest.mark.parametrize("cfg", _ci_configs(), ids=lambda p: p.name)
    def test_is_valid_yaml(self, cfg: Path) -> None:
        # GitHub Actions reuses the bare word `on:` which PyYAML loads as the
        # boolean True key; that is still valid YAML — just assert it parses to
        # a mapping.
        loaded = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)

    @pytest.mark.parametrize(
        "marker",
        [
            "--target pr-branch",
            "merge-base",
            "--since",
            "AI_TW_PAT",
        ],
    )
    def test_root_github_ci_keeps_bdl049_050_markers(self, marker: str) -> None:
        text = _CI_YML.read_text(encoding="utf-8")
        assert marker in text

    def test_root_github_ci_keeps_loop_guard_and_verdict(self) -> None:
        text = _CI_YML.read_text(encoding="utf-8")
        # loop-guard: the workflow must not re-trigger itself on its own push.
        assert "loop-guard" in text or "loop guard" in text.lower()
        # verdict classification survives (ok/flagged/infra).
        assert "verdict" in text.lower()

    @pytest.mark.parametrize(
        "marker",
        ["--target pr-branch", "merge-base", "--since", "AI_TW_PAT"],
    )
    def test_gitlab_ci_keeps_bdl049_050_markers(self, marker: str) -> None:
        text = _GITLAB_YML.read_text(encoding="utf-8")
        assert marker in text


class TestCiConfigNoRetiredToolsPath:
    """REGRESSION pin for the BUG documented on beadloom-mukc.5: after the S2
    move, repo-root ``tools/`` no longer exists, so the CI lint/type steps that
    pass ``tools/`` to ruff + mypy fail hard (ruff E902 / mypy can't-read-file).
    These tests pin that the retired path is dropped from the CI invocations.

    Fixed in S2 (the coordinator dropped ``tools/`` from both CI invocations);
    these are now live assertions that the retired path stays gone.
    """

    def test_github_ci_does_not_lint_retired_tools_path(self) -> None:
        text = _CI_YML.read_text(encoding="utf-8")
        assert "ruff check src/ tests/ tools/" not in text
        assert "mypy src/ tools/" not in text

    def test_gitlab_ci_does_not_lint_retired_tools_path(self) -> None:
        text = _GITLAB_YML.read_text(encoding="utf-8")
        assert "ruff check src/ tests/ tools/" not in text
        assert "mypy src/ tools/" not in text


# ---------------------------------------------------------------------------
# Boundary rule — the fnmatch char-class hack (the riskiest part of S2)
# ---------------------------------------------------------------------------


def _insert_import(
    conn: sqlite3.Connection, file_path: str, import_path: str
) -> None:
    conn.execute(
        "INSERT INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        (file_path, 1, import_path, None, "h"),
    )


@pytest.fixture()
def boundary_rules() -> list[ImportBoundaryRule]:
    """Load the two real ai_agents char-class forbid_import rules from the live
    project rules.yml so the test exercises the SHIPPED patterns, not a copy."""
    rules = load_rules(_REPO_ROOT / ".beadloom" / "_graph" / "rules.yml")
    ai = [
        r
        for r in rules
        if isinstance(r, ImportBoundaryRule)
        and r.name in {"core-no-import-ai-agents", "application-no-import-ai-agents"}
    ]
    assert len(ai) == 2, f"expected the 2 ai_agents boundary rules, got {ai}"
    return ai


# Every core source dir that the char-class globs are meant to cover.
_CORE_DIRS = [
    "application",
    "context_oracle",
    "doc_sync",
    "graph",
    "infrastructure",
    "onboarding",
    "services",
    "tui",
]


class TestAiAgentsBoundaryRule:
    @pytest.fixture()
    def conn(self, tmp_path: Path) -> Iterator[sqlite3.Connection]:
        db = open_db(tmp_path / "b.db")
        create_schema(db)
        yield db
        db.close()

    @pytest.mark.parametrize("core_dir", _CORE_DIRS)
    def test_core_importing_ai_agents_is_forbidden(
        self,
        conn: sqlite3.Connection,
        boundary_rules: list[ImportBoundaryRule],
        core_dir: str,
    ) -> None:
        """Every core domain/service importing ai_agents IS flagged — the two
        char-class globs together cover every core source dir."""
        _insert_import(
            conn,
            f"src/beadloom/{core_dir}/foo.py",
            "beadloom.ai_agents.ai_techwriter.runner",
        )
        conn.commit()
        violations = evaluate_import_boundary_rules(conn, boundary_rules)
        assert len(violations) >= 1, f"{core_dir} -> ai_agents not flagged"
        assert violations[0].severity == "error"

    def test_ai_agents_importing_itself_is_allowed(
        self, conn: sqlite3.Connection, boundary_rules: list[ImportBoundaryRule]
    ) -> None:
        """ai_agents internal imports must NOT false-positive (the a[!i]* and
        [!a]* classes both exclude the ``ai_agents`` dir)."""
        _insert_import(
            conn,
            "src/beadloom/ai_agents/ai_techwriter/runner.py",
            "beadloom.ai_agents.ai_techwriter.seams",
        )
        conn.commit()
        violations = evaluate_import_boundary_rules(conn, boundary_rules)
        assert violations == []

    def test_ai_agents_importing_application_is_allowed(
        self, conn: sqlite3.Connection, boundary_rules: list[ImportBoundaryRule]
    ) -> None:
        """ai_agents is a leaf CONSUMER — it MAY import the core read-APIs
        (e.g. application). The rule only forbids the reverse direction."""
        _insert_import(
            conn,
            "src/beadloom/ai_agents/ai_techwriter/packet.py",
            "beadloom.application.reindex",
        )
        _insert_import(
            conn,
            "src/beadloom/ai_agents/ai_techwriter/scope.py",
            "beadloom.context_oracle.builder",
        )
        conn.commit()
        violations = evaluate_import_boundary_rules(conn, boundary_rules)
        assert violations == []

    def test_core_importing_core_is_not_flagged(
        self, conn: sqlite3.Connection, boundary_rules: list[ImportBoundaryRule]
    ) -> None:
        """The rule only fires on a ``to`` of ai_agents — ordinary core->core
        imports are untouched."""
        _insert_import(
            conn,
            "src/beadloom/application/reindex.py",
            "beadloom.graph.loader",
        )
        conn.commit()
        assert evaluate_import_boundary_rules(conn, boundary_rules) == []

    def test_exactly_one_rule_fires_per_core_dir(
        self,
        conn: sqlite3.Connection,
        boundary_rules: list[ImportBoundaryRule],
    ) -> None:
        """The two char-class globs are DISJOINT (application matched only by
        a[!i]*, everything-else only by [!a]*) — no core->ai_agents import is
        double-counted."""
        _insert_import(
            conn,
            "src/beadloom/application/reindex.py",
            "beadloom.ai_agents.ai_techwriter.runner",
        )
        _insert_import(
            conn,
            "src/beadloom/graph/loader.py",
            "beadloom.ai_agents.ai_techwriter.runner",
        )
        conn.commit()
        violations = evaluate_import_boundary_rules(conn, boundary_rules)
        # one per import, never doubled by overlapping patterns.
        assert len(violations) == 2
        by_file = {v.file_path for v in violations}
        assert by_file == {
            "src/beadloom/application/reindex.py",
            "src/beadloom/graph/loader.py",
        }


# ---------------------------------------------------------------------------
# Graph — ai_agents domain + ai-techwriter feature resolve
# ---------------------------------------------------------------------------


def _beadloom_ctx_json(ref_id: str) -> dict[str, object]:
    """Resolve the ``beadloom`` console script to an absolute path (no partial
    path -> no S607) and return the parsed ``ctx --json`` bundle."""
    import json
    import shutil

    exe = shutil.which("beadloom")
    assert exe is not None, "beadloom console script not on PATH"
    proc = subprocess.run(  # noqa: S603 - resolved absolute path, fixed argv
        [exe, "ctx", ref_id, "--json"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    parsed: dict[str, object] = json.loads(proc.stdout)
    return parsed


class TestGraphResolution:
    def test_ai_techwriter_feature_resolves(self, live_repo_reindexed: Path) -> None:
        bundle = _beadloom_ctx_json("ai-techwriter")
        focus = bundle["focus"]
        assert isinstance(focus, dict)
        assert focus["ref_id"] == "ai-techwriter"
        graph = bundle["graph"]
        assert isinstance(graph, dict)
        node_ids = {n["ref_id"] for n in graph["nodes"]}
        assert "ai_agents" in node_ids
        assert "ai-techwriter" in node_ids

    def test_feature_is_part_of_ai_agents_domain(self, live_repo_reindexed: Path) -> None:
        graph = _beadloom_ctx_json("ai-techwriter")["graph"]
        assert isinstance(graph, dict)
        edges = graph["edges"]
        assert any(
            e["src"] == "ai-techwriter"
            and e["dst"] == "ai_agents"
            and e["kind"] == "part_of"
            for e in edges
        )


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
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert "dry-run" in proc.stdout
