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
  scope they cover, so what the run measured is unstated; or a change, a
  survivor list or a sample was named and cannot be read.

**A run can cover a change or a sample instead of the declared scope**
(BDL-074 D1). ``--changed-since REF`` states the population of a change — the
functions it touched in the declared scope, the node owning each, and the tests
the binding ties to that node — and, with ``--stats``, scores the run over it;
the declared targets are then printed as not judged by this run, because a
change covers functions, not targets. ``--sample-of N`` reads the counters as a
random sample drawn from a population of N mutants — the sample's own size is
what the counters scored — and prints the interval the sample supports.
``--survivors FILE`` lists the surviving mutants under the node owning their
file. The last two read the index, and so does the first.

**Every fact is printed in both shapes.** The human output and ``--json`` carry
the same score, the same room and the same findings, so a monitoring surface and
a reader are told the same thing (BDL-UX #148).

**The room is named on every report, not only on the ones carrying a run**
(BDL-068 S3.3). A report over declared targets no run covered is still a verdict
— it exits 1 — and it was printing no room at all, which is the shape BDL-067
produced nine times. The room is a property of the process, so it is stated
wherever the process states anything.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    import sqlite3

    from beadloom.application.mutation_scope import (
        ChangePlan,
        MutationReport,
        SampleInterval,
        Survivor,
    )

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
@click.option(
    "--changed-since",
    "changed_since",
    default=None,
    help=(
        "Cover the change since the merge base with this ref: the functions it "
        "touched in the declared scope, by node, with the tests bound to each."
    ),
)
@click.option(
    "--survivors",
    type=click.Path(path_type=Path),
    default=None,
    help="JSON list of surviving mutants ({path, mutant}) to list by node.",
)
@click.option(
    "--sample-of",
    "sample_of",
    type=click.IntRange(min=1),
    default=None,
    help=(
        "The counters are a random sample drawn from a population of this many "
        "mutants; print the interval the sample supports."
    ),
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
    changed_since: str | None,
    survivors: Path | None,
    sample_of: int | None,
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
    if stats is not None and not targets and changed_since is None:
        _unanswerable(
            "--stats needs --target: a run that does not say what it "
            "covered cannot be held against a declared scope."
        )
    if sample_of is not None and stats is None:
        _unanswerable("--sample-of needs --stats: there is no sample without counters.")

    change = _read_change(project_root, changed_since) if changed_since else None
    room = describe_room()
    covered = targets or (change.mutated_files if change is not None else ())
    run = (
        MutationRun(
            tool=tool or _UNNAMED_TOOL,
            room=room,
            covered=tuple(covered),
            counters=read_run_counters(stats),
        )
        if stats is not None
        else None
    )
    judged_only = change.mutated_files if change is not None else (only or None)
    report = report_mutation_score(project_root, run, only=judged_only)
    extras = _Extras(
        change=change,
        survivors=_read_survivors(project_root, survivors) if survivors else None,
        sample=_read_sample(report, sample_of),
    )
    below_floor = _below_floor(report.score, min_score, extras.sample)

    if output_json:
        payload = _payload(report, room, min_score, below_floor)
        payload.update(_extras_payload(extras))
        click.echo(json.dumps(payload, indent=2))
    else:
        _render(report, room, min_score, below_floor, extras)

    if report.findings or below_floor:
        sys.exit(_EXIT_FINDINGS)
    sys.exit(_EXIT_CLEAN)


@dataclass(frozen=True)
class _Extras:
    """What a run over a change or a sample adds to the report, when it is one."""

    change: ChangePlan | None = None
    survivors: dict[str | None, tuple[Survivor, ...]] | None = None
    sample: SampleInterval | None = None


def _unanswerable(message: str) -> NoReturn:
    click.echo(f"Error: {message}", err=True)
    sys.exit(_EXIT_UNANSWERABLE)


def _index(project_root: Path, needed_for: str) -> sqlite3.Connection:
    from beadloom.infrastructure.db import open_db_readonly

    try:
        return open_db_readonly(project_root / ".beadloom" / "beadloom.db")
    except FileNotFoundError:
        _unanswerable(
            f"{needed_for} reads the index, and there is none — run `beadloom reindex`."
        )


def _read_change(project_root: Path, base: str) -> ChangePlan:
    from beadloom.application.mutation_scope import (
        MutationChangeError,
        diff_since,
        plan_change,
    )

    try:
        diff = diff_since(project_root, base)
    except MutationChangeError as error:
        _unanswerable(f"--changed-since {base}: {error}")
    with closing(_index(project_root, "--changed-since")) as conn:
        return plan_change(project_root, conn, diff, base=base)


def _read_survivors(
    project_root: Path, path: Path
) -> dict[str | None, tuple[Survivor, ...]]:
    from beadloom.application.mutation_scope import read_survivors, survivors_by_node

    listed = read_survivors(path)
    if listed is None:
        _unanswerable(
            f"--survivors {path} holds no survivor list: a JSON list of "
            f"{{path, mutant}} objects is expected."
        )
    with closing(_index(project_root, "--survivors")) as conn:
        return survivors_by_node(conn, listed)


def _read_sample(report: MutationReport, sample_of: int | None) -> SampleInterval | None:
    from beadloom.application.mutation_scope import sample_interval

    if sample_of is None or report.run is None:
        return None
    try:
        return sample_interval(report.run.counters, population=sample_of)
    except ValueError as error:
        _unanswerable(f"--sample-of {sample_of}: {error}.")


def _extras_payload(extras: _Extras) -> dict[str, object]:
    from beadloom.application.mutation_scope import (
        change_payload,
        sample_payload,
        survivors_payload,
    )

    return {
        "change": change_payload(extras.change) if extras.change else None,
        "survivors_by_node": (
            survivors_payload(extras.survivors) if extras.survivors is not None else None
        ),
        "sample": sample_payload(extras.sample) if extras.sample else None,
    }


def _below_floor(
    score: float | None, min_score: float | None, sample: SampleInterval | None = None
) -> bool:
    """Whether a declared floor was missed.

    A floor declared against a score that does not exist is MISSED, not passed:
    an absent number clearing a threshold is how a run that measured nothing
    reports success.

    A score measured on a sample misses the floor only when its WHOLE interval
    lies under it (BDL-074 D1): a sample of 150 from a scope at 0.89 reads under
    0.88 about a third of the time, and a floor that fails on that is a coin.
    """
    if min_score is None:
        return False
    if sample is not None:
        return sample.high < min_score
    return score is None or score < min_score


def _score_line(report: MutationReport, extras: _Extras) -> str | None:
    """The score, or why there is none; nothing for a change no run was given."""
    run = report.run
    if run is None and extras.change is not None:
        return None
    if report.score is None:
        return "Score: none — see the findings below."
    scored = run.counters.scored if run else 0
    return f"Score: {report.score * 100:.1f}% of {scored} scored mutants"


def _floor_verdict(below_floor: bool, sample: SampleInterval | None) -> str:
    if sample is not None:
        return (
            "the sample's interval lies wholly under it."
            if below_floor
            else "the sample's interval reaches it."
        )
    return f"the score is {'under' if below_floor else 'at or over'} it."


def _payload(
    report: MutationReport,
    room: str,
    min_score: float | None,
    below_floor: bool,
) -> dict[str, object]:
    run = report.run
    return {
        "declared": list(report.declared),
        "not_judged": list(report.not_judged),
        "covered": list(run.covered) if run else [],
        "tool": run.tool if run else None,
        "room": room,
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


def _render(
    report: MutationReport,
    room: str,
    min_score: float | None,
    below_floor: bool,
    extras: _Extras,
) -> None:
    """Print the score, the room it was measured in, and what was not measured."""
    from beadloom.application.mutation_scope import (
        describe_change,
        describe_sample,
        describe_survivors,
    )

    click.echo(f"Room: {room}")
    if extras.change is not None:
        for line in describe_change(extras.change):
            click.echo(line)
    if not report.declared:
        click.echo(
            "No mutation scope declared — `mutation.targets` in "
            ".beadloom/flow.yml is empty, so there is nothing to measure."
        )
        return

    click.echo(f"Declared scope: {', '.join(report.declared)}")
    if extras.change is not None:
        click.echo(
            "Judged by this run: the functions above — a change covers functions, "
            "not declared targets"
        )
    elif report.not_judged:
        click.echo(f"Not judged by this run: {', '.join(report.not_judged)}")
    run = report.run
    if run is None and extras.change is not None:
        click.echo("No run was reported: the population above is what a runner is given.")
    elif run is None:
        click.echo("No run was reported.")
    else:
        click.echo(f"Measured: {', '.join(run.covered)}")
        click.echo(f"Tool: {run.tool}")
        counters = ", ".join(
            f"{name} {value}" for name, value in sorted(run.counters.values.items())
        )
        click.echo(f"Counters: {counters or 'none'}")
    score = _score_line(report, extras)
    if score is not None:
        click.echo(score)
    if extras.sample is not None:
        click.echo(describe_sample(extras.sample))
    if extras.survivors is not None:
        for line in describe_survivors(extras.survivors):
            click.echo(line)
    if min_score is not None:
        click.echo(f"Floor: {min_score} — {_floor_verdict(below_floor, extras.sample)}")
    for finding in report.findings:
        click.echo(
            f"{finding.severity.upper()} [{finding.check}] "
            f"{finding.target}: {finding.why}"
        )
        click.echo(f"  fix: {finding.remediation}")
