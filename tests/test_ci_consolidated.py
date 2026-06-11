# beadloom:feature=onboarding
"""BDL-050 BEAD-01: the consolidated ``.github/workflows/ci.yml``.

The three independent PR workflows (``beadloom-gate.yml``, ``tests.yml``,
``ai-techwriter.yml``) are folded into ONE ordered pipeline:

    ci.yml (on: pull_request -> main)
      gate        (ubuntu)               beadloom ci
      tests       (ubuntu, 3.10-3.13)    pytest matrix, NO paths filter
      site-build  (ubuntu)               beadloom docs site + vitepress build
      ai-techwriter (self-hosted)        needs: [gate, tests, site-build]

``deploy-site.yml`` stays the ONLY ``push: main`` job (logic unchanged; only the
action versions + node-version bumped for Node24). All actions are bumped to
Node24-running majors.

These are static, network-free checks over the YAML.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

CI = WORKFLOWS / "ci.yml"
DEPLOY_SITE = WORKFLOWS / "deploy-site.yml"

#: The three old PR workflows folded into ci.yml — must be gone.
RETIRED = (
    WORKFLOWS / "beadloom-gate.yml",
    WORKFLOWS / "tests.yml",
    WORKFLOWS / "ai-techwriter.yml",
)


def _load(path: Path) -> dict[str, object]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def _on(doc: dict[str, object]) -> dict[str, object]:
    # YAML 1.1 parses the bare ``on`` key as boolean True.
    on = doc.get("on", doc.get(True))
    assert isinstance(on, dict)
    return on


# --------------------------------------------------------------------------- #
# ci.yml — file + triggers
# --------------------------------------------------------------------------- #


def test_ci_is_valid_yaml() -> None:
    assert isinstance(_load(CI), dict)


def test_ci_triggers_on_pull_request_to_main_not_push() -> None:
    on = _on(_load(CI))
    assert "pull_request" in on
    pr = on["pull_request"]
    assert isinstance(pr, dict)
    assert set(pr["types"]) >= {"opened", "synchronize", "reopened"}
    assert pr["branches"] == ["main", "master"]
    # Manual branch-PR fallback kept; no push:main gate/tests runs.
    assert "workflow_dispatch" in on
    assert "push" not in on


def test_ci_cancel_in_progress_concurrency() -> None:
    concurrency = _load(CI)["concurrency"]
    assert isinstance(concurrency, dict)
    assert concurrency["cancel-in-progress"] is True
    assert "pull_request.number" in str(concurrency["group"])


def test_ci_grants_contents_and_pull_request_write() -> None:
    perms = _load(CI)["permissions"]
    assert isinstance(perms, dict)
    assert perms["contents"] == "write"
    assert perms["pull-requests"] == "write"


# --------------------------------------------------------------------------- #
# ci.yml — the four jobs
# --------------------------------------------------------------------------- #


def test_ci_has_the_four_jobs() -> None:
    jobs = _load(CI)["jobs"]
    assert isinstance(jobs, dict)
    assert set(jobs) == {"gate", "tests", "site-build", "ai-techwriter"}


def test_ci_gate_tests_site_build_run_on_ubuntu() -> None:
    jobs = _load(CI)["jobs"]
    assert isinstance(jobs, dict)
    for name in ("gate", "tests", "site-build"):
        job = jobs[name]
        assert isinstance(job, dict)
        assert job["runs-on"] == "ubuntu-latest", name


def test_ai_techwriter_needs_gate_tests_site_build() -> None:
    job = _load(CI)["jobs"]["ai-techwriter"]  # type: ignore[index]
    assert isinstance(job, dict)
    assert sorted(job["needs"]) == ["gate", "site-build", "tests"]
    # Stays on the self-hosted runner (Goose + the API key live there).
    assert job["runs-on"] == ["self-hosted", "ai-techwriter"]


def test_ci_tests_job_has_full_matrix_no_paths_filter() -> None:
    doc = _load(CI)
    tests = doc["jobs"]["tests"]  # type: ignore[index]
    assert isinstance(tests, dict)
    versions = tests["strategy"]["matrix"]["python-version"]
    assert versions == ["3.10", "3.11", "3.12", "3.13"]
    # The matrix must run on EVERY PR (no paths filter) so it is a reliable
    # required check: pull_request must not carry a ``paths:`` key.
    pr = _on(doc)["pull_request"]
    assert isinstance(pr, dict)
    assert "paths" not in pr


def test_ci_tests_job_keeps_lint_mypy_coverage_steps() -> None:
    tests = _load(CI)["jobs"]["tests"]  # type: ignore[index]
    assert isinstance(tests, dict)
    runs = "\n".join(
        str(s.get("run", "")) for s in tests["steps"] if isinstance(s, dict)
    )
    assert "ruff check src/ tests/" in runs
    assert "mypy src/" in runs
    assert "--cov-fail-under=80" in runs


def test_ci_gate_job_runs_the_beadloom_gate() -> None:
    """The gate job runs the SAME composite gate beadloom-gate.yml ran."""
    gate = _load(CI)["jobs"]["gate"]  # type: ignore[index]
    assert isinstance(gate, dict)
    uses = [str(s.get("uses", "")) for s in gate["steps"] if isinstance(s, dict)]
    assert any("actions/checkout" in u for u in uses)
    assert any(".github/actions/beadloom-gate" in u for u in uses)


def test_ci_site_build_builds_vitepress_without_deploy() -> None:
    site = _load(CI)["jobs"]["site-build"]  # type: ignore[index]
    assert isinstance(site, dict)
    steps = site["steps"]
    runs = "\n".join(str(s.get("run", "")) for s in steps if isinstance(s, dict))
    uses = [str(s.get("uses", "")) for s in steps if isinstance(s, dict)]
    assert "beadloom reindex" in runs
    assert "beadloom docs site --out site" in runs
    assert "npm ci" in runs
    assert "npm run docs:build" in runs
    assert any("actions/setup-node" in u for u in uses)
    # The BUILD half only — no Pages deploy steps belong on a PR check.
    assert "configure-pages" not in "\n".join(uses)
    assert "deploy-pages" not in "\n".join(uses)


# --------------------------------------------------------------------------- #
# Old workflows retired
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("path", RETIRED, ids=lambda p: p.name)
def test_old_pr_workflows_deleted(path: Path) -> None:
    assert not path.exists(), f"{path.name} must be folded into ci.yml"


def test_no_workflow_references_deleted_tests_yml() -> None:
    """tests.yml is deleted -> nothing may ``uses:`` it via workflow_call.

    pypi-publish.yml previously called ``./.github/workflows/tests.yml`` via
    workflow_call; that path must be re-wired (inlined) so the release pipeline
    does not break on the missing file.
    """
    for wf in WORKFLOWS.glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        assert "workflows/tests.yml" not in text, wf.name


# --------------------------------------------------------------------------- #
# deploy-site.yml — stays push:main, logic unchanged, actions bumped
# --------------------------------------------------------------------------- #


def test_deploy_site_still_on_push_main() -> None:
    on = _on(_load(DEPLOY_SITE))
    assert "push" in on
    push = on["push"]
    assert isinstance(push, dict)
    assert push["branches"] == ["main"]


def test_deploy_site_keeps_deploy_job() -> None:
    jobs = _load(DEPLOY_SITE)["jobs"]
    assert isinstance(jobs, dict)
    assert "build" in jobs and "deploy" in jobs


def test_deploy_site_node_version_bumped() -> None:
    """Node24 bump: deploy-site node-version 18 -> 22 (current LTS)."""
    text = DEPLOY_SITE.read_text(encoding="utf-8")
    assert "node-version: 18" not in text
    assert "node-version: 22" in text


# --------------------------------------------------------------------------- #
# Node24 action bump across ci.yml + deploy-site.yml
# --------------------------------------------------------------------------- #

#: Action -> minimum major tag that runs on Node24.
NODE24_MAJORS = {
    "actions/checkout@": "v5",
    "astral-sh/setup-uv@": "v6",
    "actions/setup-node@": "v5",
}


@pytest.mark.parametrize("path", (CI, DEPLOY_SITE), ids=lambda p: p.name)
def test_actions_are_node24_majors(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for action, major in NODE24_MAJORS.items():
        for line in text.splitlines():
            stripped = line.strip()
            if action in stripped and stripped.startswith(("- uses:", "uses:")):
                assert f"{action}{major}" in stripped, line


def test_deploy_site_pages_actions_bumped() -> None:
    """The Pages actions bumped to current majors (Node24 via FORCE stopgap)."""
    text = DEPLOY_SITE.read_text(encoding="utf-8")
    assert "actions/configure-pages@v5" in text
    assert "actions/upload-pages-artifact@v3" in text
    assert "actions/deploy-pages@v4" in text
    # Laggard Pages actions still ship Node20 entrypoints -> documented stopgap.
    assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24" in text


# --------------------------------------------------------------------------- #
# Inline shell sanity
# --------------------------------------------------------------------------- #


def _inline_shell_blocks(doc: object) -> list[str]:
    blocks: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "run" and isinstance(value, str):
                    blocks.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    return blocks


@pytest.mark.parametrize("path", (CI, DEPLOY_SITE), ids=lambda p: p.name)
def test_inline_shell_parses_with_bash_n(path: Path) -> None:
    blocks = _inline_shell_blocks(_load(path))
    assert blocks, f"no inline shell in {path.name}"
    for block in blocks:
        result = subprocess.run(
            ["bash", "-n"],  # noqa: S607 - bash resolved on PATH in CI/dev
            input=block,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, f"{path.name}:\n{block}\n{result.stderr}"
