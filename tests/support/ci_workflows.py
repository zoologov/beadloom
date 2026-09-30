"""This repository's CI pipelines and the ai-techwriter templates the package ships.

Where each file is, the facts several tests hold them to, and how a test reads
one. The live pipelines are this repository's own; the templates are what an
adopter receives, so a test of a template is a product test and a test of a
live pipeline is a self-check (BDL-074 A3).

BDL-050 folded the ai-techwriter job into the consolidated ``ci.yml`` (the three
old PR workflows, ``beadloom-gate.yml`` / ``tests.yml`` / ``ai-techwriter.yml``,
were retired), so the BDL-049 structural checks run over its ``ai-techwriter``
job.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: This repository's own pipelines.
GH_CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
GL_CI = REPO_ROOT / ".gitlab-ci.yml"

#: The ai-techwriter templates the package ships to adopters.
TEMPLATES = REPO_ROOT / "src" / "beadloom" / "onboarding" / "templates" / "ai_techwriter"
GH_TEMPLATE = TEMPLATES / "github-workflow.yml"
GL_TEMPLATE = TEMPLATES / "gitlab-ci-job.yml"

GITHUB_FILES = (GH_CI, GH_TEMPLATE)
GITLAB_FILES = (GL_CI, GL_TEMPLATE)

#: The three verify jobs every consolidated GitHub workflow must declare, and
#: the exact ``needs`` of the ai-techwriter job (RFC §"ci.yml shape").
VERIFY_JOBS = ("gate", "tests", "site-build")

#: The job that carries the locale dimension.
LOCALE_JOB = "tests-locale"

#: Jobs ``ci.yml`` runs that are deliberately NOT required status checks, each
#: with its reason and the exit that makes it required. The self-check that
#: compares ``ci.yml`` with the required contexts leaves these out, and fails on
#: an entry whose job no longer exists or that is also required, so the map only
#: shrinks and never hides a lockout.
ADVISORY_JOBS: dict[str, str] = {
    "site-e2e": (
        "the portal's browser tests (BDL-076 A5) stay non-required until they have "
        "run clean on ten pull requests; the exit is to add 'site-e2e' to "
        "DEFAULT_STATUS_CHECK_CONTEXTS in the change that removes this entry"
    ),
}

#: The fallback expression the checkout token + GH_TOKEN must use on the PR path.
PAT_FALLBACK_CHECKOUT = "secrets.AI_TW_PAT || github.token"
PAT_FALLBACK_GH_TOKEN = "secrets.AI_TW_PAT || secrets.GITHUB_TOKEN"  # noqa: S105 - GH expression, not a secret


def load_yaml(path: Path) -> dict[str, object]:
    """*path* parsed, required to be a mapping."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def jobs_of(path: Path) -> dict[str, Any]:
    """The ``jobs`` mapping of the workflow at *path*."""
    jobs = load_yaml(path)["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def windows_jobs(path: Path) -> list[str]:
    """Job keys that would run on a Windows image, by ``runs-on`` and not by name.

    Reading ``runs-on`` rather than the key is the difference between a check of
    the decision and a check of a string: a leg re-added as ``tests-platform``
    or as a matrix row costs the same runner-minutes and would slip a name test.
    """
    found: list[str] = []
    for key, job in jobs_of(path).items():
        if not isinstance(job, dict):
            continue
        if "windows" in yaml.safe_dump(job.get("runs-on", "")).lower():
            found.append(str(key))
        strategy = job.get("strategy")
        matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
        if isinstance(matrix, dict) and "windows" in yaml.safe_dump(matrix).lower():
            found.append(str(key))
    return sorted(set(found))
