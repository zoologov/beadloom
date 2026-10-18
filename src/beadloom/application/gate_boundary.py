# beadloom:domain=application
# beadloom:feature=ci-gate
"""The Gate's per-step exception boundary: a step that raises becomes an ``ERROR`` step.

``run_ci_gate`` promises it never short-circuits, and until BDL-083 S1e that was true
of a step that FAILED and false of a step that raised. The steps ran in a row with no
boundary, so an exception in the fourth ended the run: the seven after it never ran,
and ``beadloom ci`` printed nothing and exited through a traceback (BDL-UX #318,
measured at 3e95a208). Two instances of the class had each been fixed at their own site
(#226 a full pipe, #287 an unreadable configuration), which closes the instance and
leaves the class.

The boundary is held apart from the orchestrator because it is the one part of the
Gate that decides nothing about a project: it turns what a checker did wrong into a
report, and every step goes through it the same way.

The three reports the Gate derives after its steps — the room census, the verification
coverage and the ownership report — go through the same boundary in the form
:func:`derive_bounded` gives it. They are not steps and have no status, so one that
raises is not an ``ERROR`` step: it is a report that is absent, with a sentence saying
why, and the steps' verdict and exit code are the ones the steps produced. Until
BDL-083 S1 fix 1 they ran outside any boundary, and an exception in one of them took
the verdict of eleven steps that had all run with it (S1R Major 1).

It catches :class:`Exception` and nothing wider. ``KeyboardInterrupt`` and
``SystemExit`` are the operator and the process ending the run, not a checker failing,
and a boundary that swallowed them would make a Gate that cannot be stopped.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from beadloom.application.gate_step import Finding, GateStep

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

logger = logging.getLogger(__name__)

_Report = TypeVar("_Report")

#: What a reader does about a crashed step. The step's check did not run, so there is
#: nothing in the project to fix on its account; the defect is the checker's.
CRASH_REMEDIATION = (
    "this is a defect in the checker, not a finding about the project: report it with "
    "this line; the other steps' results in this run still stand"
)


def run_bounded(name: str, run: Callable[[], GateStep]) -> GateStep:
    """Run one step; an exception it raises becomes an ``ERROR`` step named *name*."""
    try:
        return run()
    except Exception as exc:  # the boundary exists for what no step anticipated
        logger.debug("gate step %s raised", name, exc_info=True)
        return crashed_step(name, exc)


def derive_bounded(
    report: str, derive: Callable[[], _Report]
) -> tuple[_Report | None, str | None]:
    """Derive the report *report*; an exception it raises becomes the reason it is absent.

    Returns the report and ``None``, or ``None`` and :func:`report_raised`'s sentence —
    exactly one of the two, so a caller cannot hold a report and a reason for its
    absence at once.
    """
    try:
        return derive(), None
    except Exception as exc:  # the boundary exists for what no report anticipated
        logger.debug("gate report %s raised", report, exc_info=True)
        return None, report_raised(report, exc)


def report_raised(report: str, exc: Exception) -> str:
    """``the <report> raised <class>: <message>`` — the reason a report is absent."""
    return f"the {report} raised {_exception_text(exc)}"


def crashed_step(name: str, exc: Exception) -> GateStep:
    """The step *name* as it is reported when it raised *exc* instead of returning."""
    error = _exception_text(exc)
    why = (
        f"the {name} step raised {error}{_raised_at(exc)}; "
        "what it checks was not checked in this run"
    )
    finding: Finding = {
        "kind": name,
        "rule": name,
        "severity": "error",
        "locations": [],
        "why": why,
        "remediation": CRASH_REMEDIATION,
    }
    return GateStep(
        name, passed=False, error=error, findings=[finding], summary=f"crashed — {error}"
    )


def crashed_clause(steps: Sequence[GateStep]) -> str:
    """``N step(s) crashed: a, b`` over the steps that raised, or ``""`` when none did."""
    crashed = [step.name for step in steps if step.error is not None]
    if not crashed:
        return ""
    return f"{len(crashed)} step(s) crashed: {', '.join(crashed)}"


def _exception_text(exc: Exception) -> str:
    """``<class>: <message>``, or the class alone for an exception with no message."""
    message = str(exc)
    name = type(exc).__name__
    return f"{name}: {message}" if message else name


def _raised_at(exc: Exception) -> str:
    """Where the exception was raised: the innermost frame, by function, file and line."""
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return ""
    frame = frames[-1]
    return f" (raised in {frame.name}, {Path(frame.filename).name}:{frame.lineno})"
