"""The ``issue-number`` command — allocate a log number, or check the ones taken.

Presentation and wiring only. The allocation and the three legs are
:mod:`beadloom.doc_sync.issue_numbers`; this module is where a refusal becomes
an exit code and where a finding is rendered.

**Why a command and not a paragraph.** The convention it replaces was "read the
last number in the log and add one", and following it exactly produced five
collisions — BDL-UX #187, #211, #253 and, on 2026-09-09 within one hour, a
number another bead already held and a number that never reached the file. The
allocation is an exclusive create of one claim file per number, which is a thing
a command can make indivisible and a paragraph cannot.

Codes (the contract a caller may rely on):

* ``0`` — the number was allocated, or the check found nothing, or the check
  could not establish whether the project declares a log at all.
* ``1`` — ``check`` found at least one finding, or the project declared a block
  this reader could not use, or a declared log the tree does not hold. ``check``
  exits 1 exactly when the Gate's ``issue-log`` step blocks: the code is that
  step's verdict, not a second reading of the report (BDL-UX #331).
* ``2`` — nothing was allocated: the project declares no ``issue_log:`` block,
  or the declaration could not be read.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import click

from beadloom.application.gate_issue_log import step_issue_log
from beadloom.doc_sync.issue_numbers import (
    CHECK_NAMES,
    IssueNumberReport,
    allocate_number,
    check_issue_numbers,
    refusal_sentence,
)
from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.application.gate_step import GateStep

_EXIT_CLEAN = 0
_EXIT_FINDINGS = 1
_EXIT_REFUSED = 2


@main.group("issue-number")
def issue_number() -> None:
    """Allocate an issue-log number, or check the ones already taken."""


@issue_number.command("allocate")
@click.option("--holder", required=True, help="Who is taking the number (a bead id).")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd,
    help="Project root (default: current directory).",
)
@click.option("--json", "as_json", is_flag=True, help="Structured JSON output.")
def allocate(holder: str, project: Path, *, as_json: bool) -> None:
    """Take the next issue number and hold it with a claim file."""
    try:
        claim = allocate_number(project, holder=holder)
    except ValueError as exc:
        _refuse(str(exc), as_json=as_json)
        return
    if as_json:
        click.echo(
            json.dumps(
                {
                    "number": claim.number,
                    "holder": claim.holder,
                    "claim": str(claim.path),
                },
                indent=2,
            )
        )
    else:
        click.echo(f"#{claim.number} allocated to {claim.holder}")
        click.echo(f"  claim: {claim.path}")
        click.echo(f"  write the entry into the log as `{claim.number}. [date] …`")
    raise SystemExit(_EXIT_CLEAN)


def _refuse(message: str, *, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps({"refused": message}, indent=2))
    else:
        click.echo(f"Refused: {message}", err=True)
    raise SystemExit(_EXIT_REFUSED)


@issue_number.command("check")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd,
    help="Project root (default: current directory).",
)
@click.option("--json", "as_json", is_flag=True, help="Structured JSON output.")
def check(project: Path, *, as_json: bool) -> None:
    """Report duplicate, unwritten and unclaimed issue numbers."""
    report = check_issue_numbers(project)
    step = step_issue_log(report)
    if as_json:
        click.echo(json.dumps(_payload(report), indent=2))
    else:
        for line in _lines(report, step):
            click.echo(line)
    raise SystemExit(_exit_code(step))


def _exit_code(step: GateStep) -> int:
    """The Gate's verdict on this report, as an exit code — never a second reading of it.

    Before ``beadloom-6xdt`` this function decided on its own which states of the
    report block, and it disagreed with the Gate on one: a declared log the tree
    does not hold was exit 0 here and a FAIL there (BDL-UX #331). Taking the
    code from the step both surfaces share is what keeps them from disagreeing.

    A config that could not be read is still ``0``: the step skips and WARNs,
    because whether the project opted in is unknown, and any non-zero code would
    be a claim about a log nobody saw. What distinguishes it from a clean run is
    the verdict's own words and, for a machine, ``undetermined`` in the payload.
    """
    return _EXIT_CLEAN if step.passed else _EXIT_FINDINGS


def _payload(report: IssueNumberReport) -> dict[str, object]:
    return {
        # ``None`` and not ``False`` when the config could not be read: the wire
        # format carries three states and a boolean holds two, so ``false``
        # beside ``"undetermined": true`` is a statement a consumer reading one
        # key acts on. A machine asking "did this project opt out?" gets no
        # answer here, which is the true one.
        "declared": None if report.undetermined else report.declared,
        "undetermined": report.undetermined,
        "entries": report.entries,
        "claims": report.claims,
        "floor": report.floor,
        "log_missing": report.log_missing,
        "not_verified": report.not_verified,
        "unaccounted": list(report.unaccounted),
        "entries_below_floor": report.entries_below_floor,
        "entries_declared": report.entries_declared,
        "refusals": [
            {"where": refusal.where, "why": refusal.why, "remediation": refusal.remediation}
            for refusal in report.refusals
        ],
        "findings": [
            {
                "check": finding.check,
                "number": finding.number,
                "where": finding.where,
                "why": finding.why,
                "remediation": finding.remediation,
            }
            for finding in report.findings
        ],
    }


#: How many unaccounted numbers are named before the rest become a count. A
#: reader acts on a number and skips a list, and this log's gap is measured in
#: single digits — the bound exists so an adopter with a hundred does not get a
#: line they cannot read.
_NAMED_LIMIT = 12


def _named(numbers: tuple[int, ...]) -> str:
    """The numbers themselves, bounded — a count alone is not something to go and look for."""
    shown = ", ".join(f"#{number}" for number in numbers[:_NAMED_LIMIT])
    rest = len(numbers) - _NAMED_LIMIT
    return f"{shown} and {rest} more" if rest > 0 else shown


def _refused_lines(report: IssueNumberReport) -> list[str]:
    """A declaration this reader could not use, said so rather than counted as zero.

    The project opted in, so the opt-out's sentence is the wrong answer; and no
    leg opened a log, so "No duplicate, unwritten or unclaimed number." is a
    clean verdict over a population of zero. This surface printed the second and
    exited 0 — the third surface of BDL-UX #270, closed with the other two by
    ``beadloom-rqma.8``. The refusals are the ones the Gate's own leg renders,
    read off the same report through the same declaration reader.
    """
    lines = [
        f"{report.entries_declared} entr(ies) declared, {len(report.refusals)} unusable "
        "— no leg ran."
    ]
    return lines + _refusal_lines(report)


def _refusal_lines(report: IssueNumberReport) -> list[str]:
    """The refusals as ``allocate`` prints them, through the one renderer both use."""
    return [f"  {refusal_sentence(refusal)}" for refusal in report.refusals]


def _undetermined_lines(report: IssueNumberReport) -> list[str]:
    """The config itself could not be read, so the opt-out's sentence is not available.

    Absence and unreadability are different answers and this surface gave one
    of them for both: over a config it never parsed it printed, byte for byte,
    what a project that wrote no ``issue_log:`` block is told, and exited 0. A
    positive assertion about a declaration nobody read is the false green this
    epic exists to remove, and the two sibling surfaces already answered it —
    ``allocate`` refuses with the parse failure, the Gate step skips and WARNs.
    """
    return [
        "Whether this project declares an issue log is unknown — no leg ran.",
        *_refusal_lines(report),
    ]


def _unread_log_lines(step: GateStep) -> list[str]:
    """A declared log the tree does not hold, in the words the Gate's step uses for it."""
    lines = ["The declared issue log could not be read — no leg ran."]
    for finding in step.findings:
        lines.append(f"  {finding['why']}")
        lines.append(f"  -> {finding['remediation']}")
    return lines


def _lines(report: IssueNumberReport, step: GateStep) -> list[str]:
    """The report as a reader sees it, stating what each leg could not read."""
    if report.undetermined:
        return _undetermined_lines(report)
    if not report.declared:
        return [
            "No issue log is declared — no leg ran.",
            "  add an `issue_log:` block with `path:` and `ledger:` to .beadloom/config.yml",
        ]
    if report.refusals:
        return _refused_lines(report)
    if report.log_missing:
        return _unread_log_lines(step)
    lines = [
        f"{report.entries} entr(ies), {report.claims} claim(s), "
        f"floor {report.floor if report.floor is not None else 'none'}"
    ]
    if report.floor is None:
        lines.append(
            "  the ledger holds no claim, so `unwritten-claim` and `unclaimed-number` "
            "entered no number: they report nothing here rather than passing"
        )
    if report.floor is not None and report.entries_below_floor:
        lines.append(
            f"  {report.entries_below_floor} of {report.entries} entr(ies) are below "
            f"floor {report.floor}: `unclaimed-number` did not enter them, and no claim "
            "holds their numbers"
        )
    if report.unaccounted:
        lines.append(
            f"  {len(report.unaccounted)} number(s) below the highest are stated nowhere; "
            f"they are unaccounted for, not free: {_named(report.unaccounted)}"
        )
    for name in CHECK_NAMES:
        for finding in report.findings:
            if finding.check != name:
                continue
            lines.append(f"[{finding.check}] #{finding.number} at {finding.where}")
            lines.append(f"  {finding.why}")
            lines.append(f"  -> {finding.remediation}")
    if not report.findings:
        lines.append("No duplicate, unwritten or unclaimed number.")
    return lines
