"""The platform dimension: priced by BDL-061.39, declined by the owner in .64.

WHAT THIS FILE USED TO BE. BDL-061.39 added a ``tests-windows`` leg to
``ci.yml`` and this module asserted that the leg could not go vacuously green:
it executed the workflow's own probe script against injected platforms and an
injected ``WinError 1314`` so that a runner which was not Windows, or which
could not create a symbolic link, failed the leg instead of carrying it on
~6000 tests that never needed Windows.

WHY IT IS THIS INSTEAD. The owner declined the leg on 2026-08-24 (bead
``beadloom-mr2l.64``), and the reason is cost rather than doubt: .39 measured
~8-14 minutes at GitHub's 2x Windows multiplier, i.e. ~16-28 runner-minutes per
PR against ~8 for both locale rows, and — unlike those rows — the leg becomes
the pipeline's critical path, so PR-to-merge latency roughly triples. Windows is
not in the target audience. The probe, its four injection rows and the whole leg
are recoverable verbatim from commit ``98bcb0d``; nothing was learned that had
to be unlearned.

WHAT SURVIVES THE WITHDRAWAL, and it is most of what .39 was worth: the six
guard tests that carried ``skipif(sys.platform == "win32")`` are gated on a
MEASURED symlink capability and run on every runner that holds it (see
:mod:`tests.symlink_capability` and :mod:`tests.test_windows_dimension`), which
is true with or without a Windows leg. This file keeps the withdrawal coherent
across the three places the leg was declared — the workflow, the vendored
template an adopter gets, and the required-context constant — because a required
context whose check-run nothing produces is the lockout .38 paid for once
already, and it would arrive here by deleting a job and forgetting a tuple.

WHAT THE PROJECT IS THEREFORE NOT CLAIMING. Nothing in this repository has ever
executed on Windows, and by this decision nothing will. That is *unverified by
decision* — a third state next to verified and broken, and the one this epic
exists to keep visible: the platform rules in ``application/guards/paths.py``
answer for Windows harnesses and have never run under one. What CAN be settled
without a runner is settled by making the platform an argument rather than an
ambient fact (``beadloom-0mdo.33``, which closed ``beadloom-mr2l.60``'s residue);
what cannot is a residual in ``flow-guards/SPEC.md``, never a mark no runner can
flip.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TEMPLATE = (
    REPO_ROOT
    / "src"
    / "beadloom"
    / "onboarding"
    / "templates"
    / "ai_techwriter"
    / "github-workflow.yml"
)

#: The job name the withdrawn leg carried, and the check-run name it produced.
WINDOWS_JOB = "tests-windows"

#: The commit that holds the leg, its anti-vacuity probe and the sixteen rows
#: that exercised the probe. Named so a future re-add restores the lock with the
#: leg rather than reinventing a weaker one.
LEG_COMMIT = "98bcb0d"


def _jobs(path: Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    jobs = doc["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _windows_jobs(path: Path) -> list[str]:
    """Job keys that would run on a Windows image, by ``runs-on`` and not by name.

    Reading ``runs-on`` rather than the key is the difference between a check of
    the decision and a check of a string: a leg re-added as ``tests-platform``
    or as a matrix row costs the same runner-minutes and would slip a name test.
    """
    found: list[str] = []
    for key, job in _jobs(path).items():
        if not isinstance(job, dict):
            continue
        if "windows" in yaml.safe_dump(job.get("runs-on", "")).lower():
            found.append(str(key))
        strategy = job.get("strategy")
        matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
        if isinstance(matrix, dict) and "windows" in yaml.safe_dump(matrix).lower():
            found.append(str(key))
    return sorted(set(found))


# --------------------------------------------------------------------------- #
# 1. The decision, at each of the three places the leg was declared
# --------------------------------------------------------------------------- #


def test_the_pipeline_runs_no_windows_leg() -> None:
    """The owner declined the platform dimension; the workflow says the same thing.

    If this fails because a Windows leg was re-added, the leg needs its
    anti-vacuity probe back with it — a Windows runner that cannot create a
    symbolic link capability-skips the six guard rows the leg is bought for and
    reports green on the rest. Restore both from ``98bcb0d`` and re-price the
    ~16-28 runner-minutes per PR, rather than adding the job alone.
    """
    assert _windows_jobs(CI) == [], (
        f"ci.yml runs a Windows leg again; it was withdrawn in "
        f"beadloom-mr2l.64 for cost. Restore the probe from {LEG_COMMIT} with "
        "it, or the leg can go green while covering nothing it was bought for."
    )


def test_the_vendored_template_runs_no_windows_leg() -> None:
    """An adopter is scaffolded the pipeline this repository decided against.

    The template is what ``beadloom setup-agentic-flow`` writes into someone
    else's repository, and .39's own honest objection was that the platform
    dimension is not on-thesis for a Linux-only service the way a non-UTF-8
    container is. Shipping the leg there while this repository declines it would
    charge an adopter for a decision the owner took the other way.
    """
    assert _windows_jobs(TEMPLATE) == []


def test_no_required_context_names_the_withdrawn_leg() -> None:
    """Deleting a job and keeping its required context is a lockout, not a tidy-up.

    ``DEFAULT_STATUS_CHECK_CONTEXTS`` is the payload
    ``beadloom setup-branch-protection`` PUTs in ANY repository. A context whose
    check-run no pipeline produces never reports, and under ``strict: true``
    that branch is permanently unmergeable — for the adopter, not for us.
    ``test_required_contexts_match_ci_yml_check_runs`` states the general
    invariant over this repo's ci.yml; this row states the specific fact the
    withdrawal turns on, so the failure names the decision.
    """
    from beadloom.onboarding.branch_protection import DEFAULT_STATUS_CHECK_CONTEXTS

    assert WINDOWS_JOB not in DEFAULT_STATUS_CHECK_CONTEXTS
    assert len(DEFAULT_STATUS_CHECK_CONTEXTS) == 9


# --------------------------------------------------------------------------- #
# 2. The reason, where the reader meets the absence
# --------------------------------------------------------------------------- #


def test_the_workflow_states_why_there_is_no_platform_dimension() -> None:
    """An absence with a reason is a decision; an absence without one is a gap.

    The next person to ask "why does this pipeline vary the locale but not the
    platform?" reads ci.yml, not a closed bead, so the price and the bead id are
    in the file next to the dimension that WAS kept.
    """
    text = CI.read_text(encoding="utf-8")

    assert "beadloom-mr2l.64" in text, (
        "ci.yml does not say why the platform dimension is absent; the locale "
        "dimension next to it carries its own price, and this one costs more"
    )
    assert "16-28" in text, "the withdrawal drops the measured cost that justified it"
