# beadloom:domain=application
# beadloom:feature=ci-gate
"""The shape one gate step reports in, and the one line the Gate prints about it.

Held apart from the orchestrator for a reason the orchestrator's own size made
concrete. ``gate.py`` composes the legs AND rendered every one of them, so a leg
lifted into a module of its own could not name the type it returns without
importing the module that imports it. The shape is what every leg shares and the
composition is not, so the shape is what moves (BDL-069, ``beadloom-rqma.8``,
the first slice of ``beadloom-oew7``).

Nothing here decides a verdict or runs a check. :class:`GateStep` records what a
leg found; ``GateResult.ok`` in :mod:`beadloom.application.gate` folds the steps
into one answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# A single finding in the shared, agent-actionable shape (see linter._finding).
Finding = dict[str, object]


@dataclass
class GateStep:
    """One step of the gate and its honest outcome.

    - ``name``     — the step identity (``reindex`` / ``lint`` / ``sync-check`` /
      ``config-check`` / ``federate``).
    - ``passed``   — True when the step did not fail the gate. A *skipped* step
      counts as passed (it cannot block the build).
    - ``skipped``  — True when the step did not run (e.g. ``--no-reindex``).
    - ``not_verified`` — True when the step ran, found nothing wrong, and could
      not actually check part of what it reports on. It stays ``passed`` (a
      project that cannot supply a baseline is not thereby broken) but it prints
      ``WARN``, because *unverifiable is not clean*: a green that describes the
      checker's own ignorance is the defect BDL-UX #174/#175/#178 are all made
      of, and the honest word costs nothing.
    - ``findings`` — the step's findings in the shared shape (empty on PASS/SKIP).
    - ``summary``  — a short human line for the ``rich`` report.

    **A number the summary states about the findings is the length of THIS
    list.** The ``readme-pair`` leg counted its comparison's findings instead and
    printed ``0 finding(s)`` in a run whose ``findings`` held one, so the Gate
    contradicted its own leg in two lines of one output (``beadloom-qae9``,
    re-review MAJOR 3). A leg that renders its line from a second computation of
    what it found is how the two come to disagree.
    """

    name: str
    passed: bool = True
    skipped: bool = False
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    not_verified: bool = False
    pairs_excused: int | None = None
    """Sync pairs a declaration excused, for the step that MEASURED it.

    Carried on the step rather than recomputed by the later step that also
    prints it: one run said ``exempt: 0`` and ``55 WORKING document(s) exempt``
    about one tree, and a second implementation of "how many were excused" is
    exactly how two adjacent lines came to contradict. ``None`` means no step in
    this run measured it, and a surface that was not told makes no pair claim.
    """

    @property
    def status(self) -> str:
        """``PASS`` / ``WARN`` / ``FAIL`` / ``SKIP`` — never an ambiguous green."""
        if self.skipped:
            return "SKIP"
        if not self.passed:
            return "FAIL"
        return "WARN" if self.not_verified else "PASS"


def gate_step_line(step: GateStep) -> str:
    """The one line the Gate prints about a step: ``[STATUS] name: summary``.

    Lives here rather than in the renderer because two commands quote it and one
    of them is not the Gate: ``init`` tells the adopter what ``beadloom ci`` will
    say about the graph it just judged, and it said ``lint - <summary>``, which
    nothing prints (BDL-067 `.14`, the review of `.13`'s minor 3). A line that
    pre-empts another command's output has to be produced by that command's own
    formatter, or it drifts the first time either is reworded.
    """
    return f"[{step.status}] {step.name}: {step.summary}"
