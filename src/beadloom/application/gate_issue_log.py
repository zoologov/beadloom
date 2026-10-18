# beadloom:domain=application
# beadloom:feature=ci-gate
"""The ``issue-log`` leg: the verdict over one issue-number report, for both surfaces.

The three legs are :mod:`beadloom.doc_sync.issue_numbers`'; this module turns
their report into the step ``beadloom ci`` prints, and ``beadloom issue-number
check`` takes its exit code from the same step. That is the point of the module.

**Why one function serves two surfaces.** Before ``beadloom-6xdt`` the command
and the Gate each decided, in their own code, which states of the report block.
They disagreed on one: a declared log the tree does not hold was a FAIL in the
Gate and exit 0 at the command line, so an agent reading the exit code got a
green from a check that ran no leg, beside a Gate that blocked on the same tree
(BDL-UX #331, measured on 9.0.0 with this repository's own declaration and the
log absent). A second copy of the rule is how the two came apart; with one copy
they cannot disagree without the same expression disagreeing with itself.

It was lifted out of ``gate.py`` as the ``readme-pair`` leg was before it
(``beadloom-oew7``), so the orchestrator composes it and renders none of it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.gate_declarations import (
    undetermined_declaration_step,
    unusable_declaration_step,
)
from beadloom.application.gate_step import Finding, GateStep

if TYPE_CHECKING:
    from beadloom.doc_sync.issue_numbers import IssueNumberReport, NumberFinding

#: The step's name, which is also the ``kind`` of every finding it reports.
ISSUE_LOG = "issue-log"


def step_issue_log(report: IssueNumberReport) -> GateStep:
    """``issue-number check`` — the issue log's numbers; BLOCKS on a finding.

    Unlike its ``docs-quality`` neighbour this step blocks, and the difference is
    the kind of claim each makes. A writing-standard finding is an opinion about
    prose that a project may reasonably carry for a release. A duplicate number
    is a reference that resolves to two entries and to neither, and this
    repository shipped one for fifteen days across a CHANGELOG, a ROADMAP, eight
    test files and thirty-six tracker records before anyone noticed (BDL-UX
    #187). Its three legs each have a repair the author can perform in the same
    commit, which is what makes blocking fair.

    **It cannot redden a project that has not opted in.** The log is DECLARED in
    ``.beadloom/config.yml``; an adopter who declares none gets a named skip, so
    the upgrade that ships this step turns nobody's green tree red.

    **A project that opted in BADLY is a different project.** Writing
    ``issue_log:`` and misspelling ``ledger:`` is opting in, and the verdict it
    gets says how many entries were declared and how many could not be used —
    not the sentence a project that wrote nothing gets (BDL-UX #270, closed by
    ``beadloom-rqma.7`` and ``beadloom-rqma.8``). Only the third case skips: a
    config file that will not parse says nothing about whether the key is there.

    **A declared log the tree does not hold blocks**, for the same reason: the
    project opted in and no leg ran. ``issue-number check`` exits 1 on it
    because its exit code is this step's ``passed`` (BDL-UX #331).

    ``not_verified`` carries the honest half: before a project's first
    allocation the ledger has no floor, so ``unwritten-claim`` and
    ``unclaimed-number`` enter no number at all and a clean result would
    describe their ignorance rather than the log (BDL-UX #173).
    """
    if report.undetermined:
        return undetermined_declaration_step(ISSUE_LOG, "an issue log", report.refusals)
    if not report.declared:
        return GateStep(
            ISSUE_LOG,
            skipped=True,
            summary=(
                "skipped — no issue log is declared; add an `issue_log:` block with "
                "`path:` and `ledger:` to .beadloom/config.yml"
            ),
        )
    if report.refusals:
        return unusable_declaration_step(ISSUE_LOG, report.entries_declared, report.refusals)
    if report.log_missing:
        return GateStep(
            ISSUE_LOG,
            passed=False,
            findings=[_log_missing_finding()],
            summary="declared issue log missing",
        )
    return GateStep(
        ISSUE_LOG,
        passed=not report.findings,
        not_verified=report.not_verified,
        findings=[_issue_number_finding(f) for f in report.findings],
        summary=_issue_number_summary(report),
    )


def _log_missing_finding() -> Finding:
    """The declared log could not be read — a step-level error with no file to point at."""
    return {
        "kind": ISSUE_LOG,
        "rule": ISSUE_LOG,
        "severity": "error",
        "locations": [],
        "why": "the declared issue log is missing or could not be decoded",
        "remediation": "point `issue_log.path` at the log, or remove the declaration",
    }


def _issue_number_summary(report: IssueNumberReport) -> str:
    """The issue-log line, which states what it COVERED and not only what it found."""
    floor = report.floor if report.floor is not None else "none"
    head = (
        f"{len(report.findings)} finding(s)"
        if report.findings
        else f"{report.entries} entr(ies) uniquely numbered"
    )
    line = f"{head}; {report.claims} claim(s), floor {floor}"
    if report.floor is None:
        line += (
            "; NOT CHECKED: unwritten-claim, unclaimed-number "
            "(the ledger holds no claim, so neither entered a number)"
        )
    elif report.entries_below_floor:
        line += (
            f"; PARTLY CHECKED: {report.entries_below_floor} of {report.entries} "
            f"entr(ies) are below floor {report.floor}, where unclaimed-number "
            "did not enter"
        )
    if report.unaccounted:
        line += (
            f"; {len(report.unaccounted)} number(s) below the highest are stated "
            "nowhere and are unaccounted for, not free"
        )
    return line


def _issue_number_finding(finding: NumberFinding) -> Finding:
    """Project one issue-number finding onto the shared finding shape."""
    return {
        "kind": ISSUE_LOG,
        "rule": finding.check,
        "severity": "error",
        "locations": [{"file": finding.where}],
        "why": finding.why,
        "remediation": finding.remediation,
    }
