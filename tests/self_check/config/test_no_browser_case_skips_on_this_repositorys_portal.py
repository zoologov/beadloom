"""No case of the portal's browser tests may skip on this repository's own portal.

BDL-076 (``beadloom-ujzb.17``). A shipped case whose shape a portal lacks skips and
names the shape, so the suite passes on an adopter's portal that is correct. This
repository's graph holds every shape the suite is written about, so a skip on its
portal would be a check that stopped running without anyone deciding it should.
The ``site-e2e`` job therefore runs the suite under the switch with which a missing
shape fails the case. ``site-adopters`` runs the fixtures' portals without it,
because a fixture lacks shapes by design.
"""

from __future__ import annotations

from typing import Any

from tests.support.ci_workflows import GH_CI, jobs_of
from tests.support.portal_browser_suite import shape_constant


def _steps(job: str) -> list[dict[str, Any]]:
    return [step for step in jobs_of(GH_CI)[job]["steps"] if isinstance(step, dict)]


def test_the_portal_job_runs_the_browser_tests_with_skips_forbidden() -> None:
    (step,) = [s for s in _steps("site-e2e") if "npm run test:e2e" in str(s.get("run", ""))]

    assert (step.get("env") or {}).get(shape_constant("NO_SKIP")) == "1"


def test_no_job_but_the_portal_job_forbids_a_skip() -> None:
    """A fixture lacks shapes by design, so forbidding its skips would fail a correct portal."""
    switch = shape_constant("NO_SKIP")
    forbidding = sorted(
        name
        for name, job in jobs_of(GH_CI).items()
        if isinstance(job, dict)
        for step in job.get("steps", [])
        if isinstance(step, dict) and switch in (step.get("env") or {})
    )

    assert forbidding == ["site-e2e"]
