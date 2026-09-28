"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_ci_consolidated_structure.py``;
the product tests of the same code stay there.
The live rows of that module's properties -- the same assertion over this
repository's own ``ci.yml`` and ``.gitlab-ci.yml`` -- moved here in BDL-074 F3
under their ids; the body each runs is in :mod:`tests.support.ci_pipeline_properties`.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support import ci_pipeline_properties as properties
from tests.support.ci_pipeline_properties import held_to
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

#: The rows the properties below run over: this repository's own pipelines.
GH_LIVE = (GH_CI,)
GL_LIVE = (GL_CI,)

test_github_has_all_consolidated_jobs = held_to(
    properties.github_has_all_consolidated_jobs, GH_LIVE
)
test_github_tests_matrix_covers_3_10_to_3_13 = held_to(
    properties.github_tests_matrix_covers_3_10_to_3_13, GH_LIVE
)
test_github_ai_techwriter_needs_the_three_verify_jobs = held_to(
    properties.github_ai_techwriter_needs_the_three_verify_jobs, GH_LIVE
)
test_gitlab_declares_verify_and_docs_stages = held_to(
    properties.gitlab_declares_verify_and_docs_stages, GL_LIVE
)
test_gitlab_verify_stage_jobs = held_to(properties.gitlab_verify_stage_jobs, GL_LIVE)
test_gitlab_tests_matrix_covers_3_10_to_3_13 = held_to(
    properties.gitlab_tests_matrix_covers_3_10_to_3_13, GL_LIVE
)
test_gitlab_ai_techwriter_in_docs_stage_needs_verify_jobs = held_to(
    properties.gitlab_ai_techwriter_in_docs_stage_needs_verify_jobs, GL_LIVE
)
test_gitlab_ai_techwriter_runs_on_merge_request = held_to(
    properties.gitlab_ai_techwriter_runs_on_merge_request, GL_LIVE
)


def _derive_required_check_names(ci_path: Path) -> set[str]:
    """Render the set of GitHub check-run names produced by ``ci.yml`` jobs.

    GitHub convention: a job's check-run name is its ``name:`` field when
    present, else the job key. A ``strategy.matrix`` job fans out to one
    check-run per matrix combination, named ``"<base> (<value>)"`` — for the
    single-axis ``tests`` matrix that is one leg per ``python-version``. The
    matrix legs are derived dynamically from the file, so adding python 3.14
    (and the matching context) stays consistent and forgetting one fails.
    """
    jobs = load_yaml(ci_path)["jobs"]
    assert isinstance(jobs, dict)

    names: set[str] = set()
    for job_key, job in jobs.items():
        assert isinstance(job, dict)
        base = str(job.get("name", job_key))
        matrix = job.get("strategy", {}).get("matrix") if isinstance(
            job.get("strategy"), dict
        ) else None
        if isinstance(matrix, dict) and matrix:
            # Single-axis matrix (the `tests` job): one leg per value. Guard
            # the single-axis assumption so a future multi-axis matrix can't
            # silently mis-derive the leg names.
            axes = [v for v in matrix.values() if isinstance(v, list)]
            assert len(axes) == 1, (
                f"{ci_path.name}: job {job_key!r} has a multi-axis matrix; the "
                "check-run-name derivation only models single-axis matrices"
            )
            for value in axes[0]:
                names.add(f"{base} ({value})")
        else:
            names.add(base)
    return names


def test_github_template_mirrors_live_consolidated_jobs() -> None:
    """The vendored GitHub template declares the same consolidated job set."""
    live = set(load_yaml(GH_CI)["jobs"])  # type: ignore[arg-type]
    tmpl = set(load_yaml(GH_TEMPLATE)["jobs"])  # type: ignore[arg-type]
    assert {*VERIFY_JOBS, "ai-techwriter"} <= live
    assert {*VERIFY_JOBS, "ai-techwriter"} <= tmpl


def test_gitlab_template_mirrors_live_consolidated_stages() -> None:
    """The vendored GitLab template declares the same verify -> docs stages."""
    assert load_yaml(GL_CI)["stages"] == ["verify", "docs"]
    assert load_yaml(GL_TEMPLATE)["stages"] == ["verify", "docs"]


def test_required_contexts_match_ci_yml_check_runs() -> None:
    """branch_protection's required contexts == the real ci.yml check-run names.

    Lockout-regression guard: derive every check-run name ci.yml produces and
    assert it equals ``DEFAULT_STATUS_CHECK_CONTEXTS``. If a ci.yml job/check
    name drifts from the protection set (either side), a required check would
    never report and ``main`` would be unmergeable.
    """
    from beadloom.onboarding.branch_protection import DEFAULT_STATUS_CHECK_CONTEXTS

    derived = _derive_required_check_names(GH_CI)
    required = set(DEFAULT_STATUS_CHECK_CONTEXTS)

    missing = required - derived  # required but no such check-run -> lockout
    extra = derived - required  # a real check ci.yml runs but is not required
    assert derived == required, (
        "ci.yml job/check names drifted from branch-protection required "
        "contexts -> main would be unmergeable.\n"
        f"  required but absent from ci.yml (LOCKOUT): {sorted(missing)}\n"
        f"  in ci.yml but not required:               {sorted(extra)}"
    )
