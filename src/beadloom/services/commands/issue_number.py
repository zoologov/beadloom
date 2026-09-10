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

* ``0`` — the number was allocated, or the check found nothing.
* ``1`` — ``check`` found at least one finding.
* ``2`` — nothing was allocated: the project declares no ``issue_log:`` block.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
from pathlib import Path

import click

from beadloom.doc_sync.issue_numbers import (
    CHECK_NAMES,
    IssueNumberReport,
    allocate_number,
    check_issue_numbers,
)
from beadloom.services.commands._root import main

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
    if as_json:
        click.echo(json.dumps(_payload(report), indent=2))
    else:
        for line in _lines(report):
            click.echo(line)
    raise SystemExit(_EXIT_FINDINGS if report.findings else _EXIT_CLEAN)


def _payload(report: IssueNumberReport) -> dict[str, object]:
    return {
        "declared": report.declared,
        "entries": report.entries,
        "claims": report.claims,
        "floor": report.floor,
        "log_missing": report.log_missing,
        "not_verified": report.not_verified,
        "unaccounted": list(report.unaccounted),
        "entries_below_floor": report.entries_below_floor,
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


def _lines(report: IssueNumberReport) -> list[str]:
    """The report as a reader sees it, stating what each leg could not read."""
    if not report.declared:
        return [
            "No issue log is declared — no leg ran.",
            "  add an `issue_log:` block with `path:` and `ledger:` to .beadloom/config.yml",
        ]
    if report.log_missing:
        return ["The declared issue log is missing or unreadable — no leg ran."]
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
