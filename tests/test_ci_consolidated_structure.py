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

from typing import TYPE_CHECKING

import pytest
import yaml

from tests.support.ci_workflows import (
    GH_CI,
    GH_TEMPLATE,
    GL_CI,
    GL_TEMPLATE,
    VERIFY_JOBS,
    load_yaml,
)

if TYPE_CHECKING:
    from pathlib import Path

MATRIX_LEGS = ["3.10", "3.11", "3.12", "3.13"]


# --------------------------------------------------------------------------- #
# GitHub: ci.yml + the vendored github-workflow.yml template
# --------------------------------------------------------------------------- #

#: The rows the parametrized tests below run over. The live file's row is a
#: self-check of this repository and carries the ``self_check`` marker; its twin
#: row is the product test of the shipped template (BDL-074 A3).
GH_FILES = (pytest.param(GH_CI, marks=pytest.mark.self_check), GH_TEMPLATE)


@pytest.mark.parametrize("path", GH_FILES, ids=lambda p: p.name)
def test_github_has_all_consolidated_jobs(path: Path) -> None:
    """gate / tests / site-build / ai-techwriter are all declared as jobs."""
    jobs = load_yaml(path)["jobs"]
    assert isinstance(jobs, dict)
    for name in (*VERIFY_JOBS, "ai-techwriter"):
        assert name in jobs, f"{path.name} missing job {name}"


@pytest.mark.parametrize("path", GH_FILES, ids=lambda p: p.name)
def test_github_tests_matrix_covers_3_10_to_3_13(path: Path) -> None:
    """The ``tests`` job runs the un-filtered 3.10-3.13 matrix (no paths filter)."""
    jobs = load_yaml(path)["jobs"]
    assert isinstance(jobs, dict)
    tests = jobs["tests"]
    assert isinstance(tests, dict)
    versions = tests["strategy"]["matrix"]["python-version"]
    assert [str(v) for v in versions] == MATRIX_LEGS
    assert "paths" not in tests


@pytest.mark.parametrize("path", GH_FILES, ids=lambda p: p.name)
def test_github_ai_techwriter_needs_the_three_verify_jobs(path: Path) -> None:
    """ai-techwriter is gated on gate + tests + site-build (no tokens on red)."""
    jobs = load_yaml(path)["jobs"]
    assert isinstance(jobs, dict)
    atw = jobs["ai-techwriter"]
    assert isinstance(atw, dict)
    assert set(atw["needs"]) == set(VERIFY_JOBS)


# --------------------------------------------------------------------------- #
# GitLab: .gitlab-ci.yml + the vendored gitlab-ci-job.yml template
# --------------------------------------------------------------------------- #

#: The rows the parametrized tests below run over. The live file's row is a
#: self-check of this repository and carries the ``self_check`` marker; its twin
#: row is the product test of the shipped template (BDL-074 A3).
GL_FILES = (pytest.param(GL_CI, marks=pytest.mark.self_check), GL_TEMPLATE)


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_declares_verify_and_docs_stages(path: Path) -> None:
    """The consolidated GitLab pipeline declares the verify -> docs stages."""
    doc = load_yaml(path)
    assert doc["stages"] == ["verify", "docs"]


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_verify_stage_jobs(path: Path) -> None:
    """gate / tests / site-build all sit in the verify stage."""
    doc = load_yaml(path)
    for name in VERIFY_JOBS:
        job = doc[name]
        assert isinstance(job, dict)
        assert job["stage"] == "verify"


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_tests_matrix_covers_3_10_to_3_13(path: Path) -> None:
    """The GitLab ``tests`` job mirrors the 3.10-3.13 matrix via parallel:matrix."""
    doc = load_yaml(path)
    tests = doc["tests"]
    assert isinstance(tests, dict)
    versions = tests["parallel"]["matrix"][0]["PYTHON_VERSION"]
    assert [str(v) for v in versions] == MATRIX_LEGS


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_ai_techwriter_in_docs_stage_needs_verify_jobs(path: Path) -> None:
    """ai-techwriter sits in docs stage and ``needs`` the three verify jobs."""
    doc = load_yaml(path)
    atw = doc["ai-techwriter"]
    assert isinstance(atw, dict)
    assert atw["stage"] == "docs"
    assert set(atw["needs"]) == set(VERIFY_JOBS)


@pytest.mark.parametrize("path", GL_FILES, ids=lambda p: p.name)
def test_gitlab_ai_techwriter_runs_on_merge_request(path: Path) -> None:
    """The ai-techwriter MR rule fires on a merge_request_event (verdict gates)."""
    doc = load_yaml(path)
    atw = doc["ai-techwriter"]
    assert isinstance(atw, dict)
    rules_text = yaml.safe_dump(atw["rules"])
    assert 'merge_request_event' in rules_text


# --------------------------------------------------------------------------- #
# Live <-> template parity (so a scaffolded repo gets the consolidated pipeline)
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# Lockout-regression guard (BDL-050 BEAD-08 / review MINOR-1)
#
# branch_protection.DEFAULT_STATUS_CHECK_CONTEXTS lists the REQUIRED GitHub
# status checks for `main`. Each must match a real ci.yml check-run name
# EXACTLY; a required check that never reports leaves `main` permanently
# unmergeable (lockout). Until now the workflow-shape tests and the
# branch-protection tests asserted these as INDEPENDENT literals, so renaming a
# ci.yml job (e.g. gate -> beadloom-gate) without updating the protection set
# (or vice-versa) slipped through. This guard DERIVES the expected check-run
# names FROM ci.yml and asserts they equal the protection contract.
# --------------------------------------------------------------------------- #


