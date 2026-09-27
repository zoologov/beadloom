"""The vendored workflow template carries the locale dimension too (BDL-074 A3).

This repository's own ci.yml is checked in tests/self_check/config/test_ci_locale_dimension.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


#: The job that carries the dimension.
LOCALE_JOB = "tests-locale"


TEMPLATE = (
    REPO_ROOT
    / "src"
    / "beadloom"
    / "onboarding"
    / "templates"
    / "ai_techwriter"
    / "github-workflow.yml"
)


def _template_jobs() -> dict[str, Any]:
    doc = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    jobs = doc["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def test_the_vendored_template_runs_the_locale_dimension_too() -> None:
    """A scaffolded repo gets the dimension, not just this one.

    Adopters running in a container are who .36's defect would have shipped to,
    so the template carrying the dimension is the point rather than a courtesy.
    """
    assert LOCALE_JOB in _template_jobs(), (
        f"the vendored template declares no {LOCALE_JOB!r} job, but "
        "DEFAULT_STATUS_CHECK_CONTEXTS names its check-runs as REQUIRED — a "
        "scaffolded repo would have required checks that never report"
    )


def test_every_default_required_context_is_a_check_the_template_runs() -> None:
    """The lockout guard, stated over the TEMPLATE rather than over this repo.

    tests/self_check/config/test_ci_consolidated_structure.py already pins
    ``derived(ci.yml) == DEFAULT_STATUS_CHECK_CONTEXTS`` for this repo. That is
    not enough on its own: the same constant is applied to repos whose pipeline
    is the template, so both must render the same check-run names.
    """
    from beadloom.onboarding.branch_protection import DEFAULT_STATUS_CHECK_CONTEXTS

    rendered: set[str] = set()
    for key, job in _template_jobs().items():
        base = str(job.get("name", key))
        strategy = job.get("strategy")
        matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
        axes = (
            [v for v in matrix.values() if isinstance(v, list)]
            if isinstance(matrix, dict)
            else []
        )
        if axes:
            assert len(axes) == 1, f"{key}: multi-axis matrix is not modelled"
            rendered.update(f"{base} ({value})" for value in axes[0])
        else:
            rendered.add(base)

    missing = set(DEFAULT_STATUS_CHECK_CONTEXTS) - rendered
    assert not missing, (
        "required-by-default contexts the vendored template never produces "
        f"(a scaffolded repo would be permanently unmergeable): {sorted(missing)}"
    )
