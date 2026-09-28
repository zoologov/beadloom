"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/integration/ai_agents/ai_techwriter/test_bdl050_hardening.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import yaml

from tests.support.repository_root import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"


PYPI = WORKFLOWS / "pypi-publish.yml"


GITLAB_CI = REPO_ROOT / ".gitlab-ci.yml"


def test_pypi_publish_parses_clean() -> None:
    """pypi-publish.yml still ``yaml.safe_load``s after tests.yml was folded away."""
    doc = yaml.safe_load(PYPI.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert isinstance(doc["jobs"], dict)


def test_pypi_publish_has_inlined_test_job_not_workflow_call() -> None:
    """tests.yml was deleted, so the release pipeline must run pytest INLINE (no
    ``uses: ./.github/workflows/tests.yml`` workflow_call that would now 404)."""
    text = PYPI.read_text(encoding="utf-8")
    assert "workflows/tests.yml" not in text
    jobs = yaml.safe_load(text)["jobs"]
    assert "tests" in jobs
    steps = jobs["tests"]["steps"]
    runs = "\n".join(str(s.get("run", "")) for s in steps if isinstance(s, dict))
    assert "pytest" in runs


def test_gitlab_ci_parses_clean() -> None:
    """The GitLab mirror ``yaml.safe_load``s clean (no YAML-anchor breakage)."""
    doc = yaml.safe_load(GITLAB_CI.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert doc["stages"] == ["verify", "docs"]
