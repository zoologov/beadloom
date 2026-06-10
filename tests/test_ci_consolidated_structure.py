"""BDL-050 BEAD-03: the consolidated CI structure mirrors across GitHub + GitLab.

These are static, network-free YAML checks asserting the consolidated pipeline
shape introduced in BDL-050:

* ``.github/workflows/ci.yml`` — jobs ``gate`` / ``tests`` (3.10-3.13 matrix) /
  ``site-build`` / ``ai-techwriter`` (``needs: [gate, tests, site-build]``).
* ``.gitlab-ci.yml`` — stage ``verify`` (``gate`` / ``tests`` matrix /
  ``site-build``) + stage ``docs`` (``ai-techwriter`` with
  ``needs: [gate, tests, site-build]`` and the merge_request_event rule).
* the vendored ``ai_techwriter`` templates — restructured to the SAME
  consolidated model so a scaffolded repo gets the consolidated pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

GH_CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
GL_CI = REPO_ROOT / ".gitlab-ci.yml"
TEMPLATES = REPO_ROOT / "src" / "beadloom" / "onboarding" / "templates" / "ai_techwriter"
GH_TEMPLATE = TEMPLATES / "github-workflow.yml"
GL_TEMPLATE = TEMPLATES / "gitlab-ci-job.yml"

#: The three verify jobs every consolidated GitHub workflow must declare, and
#: the exact ``needs`` of the ai-techwriter job (RFC §"ci.yml shape").
VERIFY_JOBS = ("gate", "tests", "site-build")
MATRIX_LEGS = ["3.10", "3.11", "3.12", "3.13"]


def _load(path: Path) -> dict[str, object]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


# --------------------------------------------------------------------------- #
# GitHub: ci.yml + the vendored github-workflow.yml template
# --------------------------------------------------------------------------- #

GH_FILES = (GH_CI, GH_TEMPLATE)


@pytest.mark.parametrize("path", GH_FILES, ids=lambda p: p.name)
def test_github_has_all_consolidated_jobs(path: Path) -> None:
    """gate / tests / site-build / ai-techwriter are all declared as jobs."""
    jobs = _load(path)["jobs"]
    assert isinstance(jobs, dict)
    for name in (*VERIFY_JOBS, "ai-techwriter"):
        assert name in jobs, f"{path.name} missing job {name}"


@pytest.mark.parametrize("path", GH_FILES, ids=lambda p: p.name)
def test_github_tests_matrix_covers_3_10_to_3_13(path: Path) -> None:
    """The ``tests`` job runs the un-filtered 3.10-3.13 matrix (no paths filter)."""
    jobs = _load(path)["jobs"]
    assert isinstance(jobs, dict)
    tests = jobs["tests"]
    assert isinstance(tests, dict)
    versions = tests["strategy"]["matrix"]["python-version"]
    assert [str(v) for v in versions] == MATRIX_LEGS
    assert "paths" not in tests


@pytest.mark.parametrize("path", GH_FILES, ids=lambda p: p.name)
def test_github_ai_techwriter_needs_the_three_verify_jobs(path: Path) -> None:
    """ai-techwriter is gated on gate + tests + site-build (no tokens on red)."""
    jobs = _load(path)["jobs"]
    assert isinstance(jobs, dict)
    atw = jobs["ai-techwriter"]
    assert isinstance(atw, dict)
    assert set(atw["needs"]) == set(VERIFY_JOBS)


# --------------------------------------------------------------------------- #
# GitLab: .gitlab-ci.yml + the vendored gitlab-ci-job.yml template
# --------------------------------------------------------------------------- #

GL_FILES = (GL_CI, GL_TEMPLATE)


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_declares_verify_and_docs_stages(path: Path) -> None:
    """The consolidated GitLab pipeline declares the verify -> docs stages."""
    doc = _load(path)
    assert doc["stages"] == ["verify", "docs"]


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_verify_stage_jobs(path: Path) -> None:
    """gate / tests / site-build all sit in the verify stage."""
    doc = _load(path)
    for name in VERIFY_JOBS:
        job = doc[name]
        assert isinstance(job, dict)
        assert job["stage"] == "verify"


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_tests_matrix_covers_3_10_to_3_13(path: Path) -> None:
    """The GitLab ``tests`` job mirrors the 3.10-3.13 matrix via parallel:matrix."""
    doc = _load(path)
    tests = doc["tests"]
    assert isinstance(tests, dict)
    versions = tests["parallel"]["matrix"][0]["PYTHON_VERSION"]
    assert [str(v) for v in versions] == MATRIX_LEGS


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_ai_techwriter_in_docs_stage_needs_verify_jobs(path: Path) -> None:
    """ai-techwriter sits in docs stage and ``needs`` the three verify jobs."""
    doc = _load(path)
    atw = doc["ai-techwriter"]
    assert isinstance(atw, dict)
    assert atw["stage"] == "docs"
    assert set(atw["needs"]) == set(VERIFY_JOBS)


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_ai_techwriter_runs_on_merge_request(path: Path) -> None:
    """The ai-techwriter MR rule fires on a merge_request_event (verdict gates)."""
    doc = _load(path)
    atw = doc["ai-techwriter"]
    assert isinstance(atw, dict)
    rules_text = yaml.safe_dump(atw["rules"])
    assert 'merge_request_event' in rules_text


# --------------------------------------------------------------------------- #
# Live <-> template parity (so a scaffolded repo gets the consolidated pipeline)
# --------------------------------------------------------------------------- #


def test_github_template_mirrors_live_consolidated_jobs() -> None:
    """The vendored GitHub template declares the same consolidated job set."""
    live = set(_load(GH_CI)["jobs"])  # type: ignore[arg-type]
    tmpl = set(_load(GH_TEMPLATE)["jobs"])  # type: ignore[arg-type]
    assert {*VERIFY_JOBS, "ai-techwriter"} <= live
    assert {*VERIFY_JOBS, "ai-techwriter"} <= tmpl


def test_gitlab_template_mirrors_live_consolidated_stages() -> None:
    """The vendored GitLab template declares the same verify -> docs stages."""
    assert _load(GL_CI)["stages"] == ["verify", "docs"]
    assert _load(GL_TEMPLATE)["stages"] == ["verify", "docs"]
