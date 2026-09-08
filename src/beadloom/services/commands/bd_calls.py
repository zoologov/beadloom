"""The ``bd-calls`` command — every place this project reaches ``bd``, and what it assumes.

Presentation and wiring only. The derivation is
:func:`beadloom.services.bd_seam.population.project_report`; this module turns a
report into lines on a stream and one exit code.

The command exists because CONTEXT Q4 decided that External ``bd`` findings are
answered by deriving our own call sites, never by a wrapper: a wrapper is a
second thing to keep in step with upstream, and a derived population fails on a
call site added later. What it prints is therefore a REPORT and not a guard —
naming a site, the assumption its call form makes about bd's answer, and whether
anything settles that assumption.

Codes (the contract a caller may rely on):

* ``0`` — the population was derived. Unsettled sites are the normal state and
  are not a failure: most of them are instructions to a person, and the fix for
  an instruction is a role duty rather than an exit code.
* ``1`` — with ``--strict``, at least one site's assumption is unsettled.
* ``2`` — the invocation cannot be answered: ``--assumption`` names one this
  derivation does not judge. An empty answer would read as "no site makes that
  assumption", which is the clean list an agent trusts and stops at.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.services.bd_seam.assumptions import BdCallSite, CallSiteReport

_EXIT_CLEAN = 0
_EXIT_UNSETTLED = 1
_EXIT_UNANSWERABLE = 2

#: How many sites the human report names in full before it counts the rest. A
#: population of 278 printed whole is a wall nobody reads, and a report nobody
#: reads is the clean list this epic exists to stop producing.
_NAMED_LIMIT = 15


@main.command("bd-calls")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--assumption",
    default=None,
    help="Report only the sites making one named assumption.",
)
@click.option(
    "--unsettled",
    is_flag=True,
    default=False,
    help="Report only the sites whose assumption nothing settles.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit 1 when any site's assumption is unsettled (default: report, exit 0).",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON output.")
def bd_calls(
    *,
    project: Path | None,
    assumption: str | None,
    unsettled: bool,
    strict: bool,
    as_json: bool,
) -> None:
    """Derive every ``bd`` call site and state what each assumes about the answer."""
    import json as json_module

    from beadloom.services.bd_seam.assumptions import ASSUMPTIONS
    from beadloom.services.bd_seam.population import project_report

    if assumption is not None and assumption not in ASSUMPTIONS:
        click.echo(
            f"bd-calls: `{assumption}` is not an assumption this derivation judges. "
            f"It judges: {', '.join(ASSUMPTIONS)}.",
            err=True,
        )
        sys.exit(_EXIT_UNANSWERABLE)

    report = project_report(project or Path.cwd())
    shown = _selected(report, assumption=assumption, unsettled_only=unsettled)

    if as_json:
        click.echo(json_module.dumps(_as_dict(report, shown), indent=2))
    else:
        _render(report, shown)

    sys.exit(_EXIT_UNSETTLED if strict and report.unsettled else _EXIT_CLEAN)


def _selected(
    report: CallSiteReport, *, assumption: str | None, unsettled_only: bool
) -> tuple[BdCallSite, ...]:
    """The sites this invocation asked for, in the order they were derived."""
    sites = report.unsettled if unsettled_only else report.sites
    if assumption is None:
        return sites
    return tuple(site for site in sites if any(a.name == assumption for a in site.assumptions))


def _render(report: CallSiteReport, shown: tuple[BdCallSite, ...]) -> None:
    """The human report: the shape first, then the worst sites, then the gaps."""
    channels = Counter(site.channel for site in report.sites)
    click.echo(
        f"{len(report.sites)} `bd` call site(s), measured against bd "
        f"{report.measured_against}: "
        + ", ".join(f"{count} {name}" for name, count in sorted(channels.items()))
    )
    verdicts: Counter[tuple[str, str]] = Counter()
    for site in report.sites:
        for held in site.assumptions:
            verdicts[held.name, held.verdict] += 1
    click.echo("")
    for (name, verdict), count in sorted(verdicts.items(), key=lambda item: -item[1]):
        click.echo(f"  {count:4d}  {name:26s} {verdict}")

    click.echo("")
    click.echo(f"{len(shown)} site(s) selected:")
    for site in shown[:_NAMED_LIMIT]:
        made = ", ".join(f"{a.name}={a.verdict}" for a in site.assumptions) or "no assumption"
        click.echo(f"  {site.source}:{site.line}  `{site.text}`  [{made}]")
    if len(shown) > _NAMED_LIMIT:
        click.echo(f"  ... and {len(shown) - _NAMED_LIMIT} more")

    click.echo("")
    click.echo(f"{len(report.unreached)} region(s) this derivation did not reach:")
    for region, why in report.unreached:
        click.echo(f"  {region} — {why}")


def _as_dict(report: CallSiteReport, shown: tuple[BdCallSite, ...]) -> dict[str, object]:
    """The same facts the human shape prints, as data."""
    return {
        "measured_against": report.measured_against,
        "sites": len(report.sites),
        "unsettled": len(report.unsettled),
        "selected": [
            {
                "source": site.source,
                "line": site.line,
                "channel": site.channel,
                "invocation": site.text,
                "subcommand": site.subcommand,
                "unresolved_arguments": site.unresolved_arguments,
                "assumptions": [
                    {"name": a.name, "verdict": a.verdict, "detail": a.detail}
                    for a in site.assumptions
                ],
            }
            for site in shown
        ],
        "unreached": [{"region": region, "why": why} for region, why in report.unreached],
    }
