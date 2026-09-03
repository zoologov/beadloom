"""The ``mutation`` command — the score a run produced, over the declared scope.

Presentation and wiring only. The decision is
:func:`beadloom.application.mutation_scope.report_mutation_score`; this module is
where a runner's counters file becomes a report, where the room is named, and
where a report becomes lines on a stream and one exit code.

Beadloom owns no mutation runner — the tool is the project's choice (BDL-061
CONTEXT Q5). What it owns is the declared scope, this report over whatever
counters a run wrote, and the refusal to turn an absence into a number.

Codes (the contract a caller may rely on):

* ``0`` — every declared target was measured by a run that produced mutants,
  and the score clears the floor if one was declared. A project declaring no
  mutation scope also exits 0: not opting in is not a violation.
* ``1`` — findings: a declared target no run covered, a run that produced no
  mutants, counters the score cannot be computed from, or a score under the
  declared floor.
* ``2`` — the invocation cannot be answered: counters were named without the
  scope they cover, so what the run measured is unstated.

**Every fact is printed in both shapes.** The human output and ``--json`` carry
the same score, the same room and the same findings, so a monitoring surface and
a reader are told the same thing (BDL-UX #148).
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.application.mutation_scope import MutationReport

#: Exit codes, named so the renderer and the docstring cannot drift apart.
_EXIT_CLEAN = 0
_EXIT_FINDINGS = 1
_EXIT_UNANSWERABLE = 2

#: What the tool is called when the caller does not say. Printed rather than
#: omitted: a score whose producer is unnamed is a weaker claim, and the report
#: should look weaker.
_UNNAMED_TOOL = "an unnamed runner"


@main.command("mutation")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root holding .beadloom/flow.yml (default: current directory).",
)
@click.option(
    "--stats",
    type=click.Path(path_type=Path),
    default=None,
    help="JSON object of counters a mutation run wrote (killed, survived, …).",
)
@click.option(
    "--target",
    "targets",
    multiple=True,
    help="A path the run covered. Repeatable. Required whenever --stats is given.",
)
@click.option(
    "--only",
    "only",
    multiple=True,
    help=(
        "Judge only these declared targets. Repeatable. The rest are printed as "
        "not judged by this run rather than reported as findings."
    ),
)
@click.option("--tool", default=None, help="The runner that produced the counters.")
@click.option(
    "--min-score",
    type=float,
    default=None,
    help="Floor the score must clear, as a fraction (0.85 is 85%).",
)
@click.option("--json", "output_json", is_flag=True, help="Structured JSON output.")
def mutation(
    *,
    project: Path | None,
    stats: Path | None,
    targets: tuple[str, ...],
    only: tuple[str, ...],
    tool: str | None,
    min_score: float | None,
    output_json: bool,
) -> None:
    """Report the mutation score a run produced over the declared scope.

    The counters come from whatever tool the project runs; this command reads
    them by NAME and reports a counter it did not find rather than reading it as
    zero, because a missing `killed` read as zero produces "0%" and a number is
    what gets pasted into a bead comment.
    """
    from beadloom.application.mutation_scope import (
        MutationRun,
        describe_room,
        read_run_counters,
        report_mutation_score,
    )

    project_root = project or Path.cwd()
    if stats is not None and not targets:
        click.echo(
            "Error: --stats needs --target: a run that does not say what it "
            "covered cannot be held against a declared scope.",
            err=True,
        )
        sys.exit(_EXIT_UNANSWERABLE)

    run = (
        MutationRun(
            tool=tool or _UNNAMED_TOOL,
            room=describe_room(),
            covered=tuple(targets),
            counters=read_run_counters(stats),
        )
        if stats is not None
        else None
    )
    report = report_mutation_score(project_root, run, only=only or None)
    below_floor = _below_floor(report.score, min_score)

    if output_json:
        click.echo(json.dumps(_payload(report, min_score, below_floor), indent=2))
    else:
        _render(report, min_score, below_floor)

    if report.findings or below_floor:
        sys.exit(_EXIT_FINDINGS)
    sys.exit(_EXIT_CLEAN)


def _below_floor(score: float | None, min_score: float | None) -> bool:
    """Whether a declared floor was missed.

    A floor declared against a score that does not exist is MISSED, not passed:
    an absent number clearing a threshold is how a run that measured nothing
    reports success.
    """
    if min_score is None:
        return False
    return score is None or score < min_score


def _payload(
    report: MutationReport, min_score: float | None, below_floor: bool
) -> dict[str, object]:
    run = report.run
    return {
        "declared": list(report.declared),
        "not_judged": list(report.not_judged),
        "covered": list(run.covered) if run else [],
        "tool": run.tool if run else None,
        "room": run.room if run else None,
        "score": report.score,
        "counters": dict(run.counters.values) if run else {},
        "missing_counters": list(run.counters.missing) if run else [],
        "min_score": min_score,
        "below_floor": below_floor,
        "findings": [
            {
                "check": finding.check,
                "target": finding.target,
                "severity": finding.severity,
                "why": finding.why,
                "remediation": finding.remediation,
            }
            for finding in report.findings
        ],
    }


def _render(report: MutationReport, min_score: float | None, below_floor: bool) -> None:
    """Print the score, the room it was measured in, and what was not measured."""
    if not report.declared:
        click.echo(
            "No mutation scope declared — `mutation.targets` in "
            ".beadloom/flow.yml is empty, so there is nothing to measure."
        )
        return

    click.echo(f"Declared scope: {', '.join(report.declared)}")
    if report.not_judged:
        click.echo(f"Not judged by this run: {', '.join(report.not_judged)}")
    run = report.run
    if run is None:
        click.echo("No run was reported.")
    else:
        click.echo(f"Measured: {', '.join(run.covered)}")
        click.echo(f"Tool: {run.tool}")
        click.echo(f"Room: {run.room}")
        counters = ", ".join(
            f"{name} {value}" for name, value in sorted(run.counters.values.items())
        )
        click.echo(f"Counters: {counters or 'none'}")
    if report.score is None:
        click.echo("Score: none — see the findings below.")
    else:
        scored = run.counters.scored if run else 0
        click.echo(f"Score: {report.score * 100:.1f}% of {scored} scored mutants")
    if min_score is not None:
        verdict = "under" if below_floor else "at or over"
        click.echo(f"Floor: {min_score} — the score is {verdict} it.")
    for finding in report.findings:
        click.echo(
            f"{finding.severity.upper()} [{finding.check}] "
            f"{finding.target}: {finding.why}"
        )
        click.echo(f"  fix: {finding.remediation}")
