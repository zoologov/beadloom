"""The ``guard`` command — evaluate one flow guard, or report guard liveness.

Presentation only: the decision lives in
:mod:`beadloom.application.guards.evaluation`, which is what makes a harness
hook and a human shell produce the same verdict. This module maps the verdict
onto a stream and an exit code, and records the firing.

Streams and codes (the adapter contract):

* ``pass`` / ``skip`` -> stdout, exit 0
* ``warn`` -> stderr, exit 1 (visible, never blocking)
* ``block`` -> stderr, exit 2
* usage / configuration error -> stderr, exit 3

``warn``/``block`` go to **stderr** because that is the stream a hook harness
shows to the agent; ``3`` is used for errors so a genuine ``block`` stays
distinguishable from Click's own usage exit code (2).
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
    from beadloom.application.guards.contract import GuardProbes
    from beadloom.application.guards.models import GuardVerdict


def _probes(project_root: Path) -> GuardProbes:
    """Seam over the real bd/git probes (patched in tests, wired for real here)."""
    from beadloom.services.guard_probes import build_probes

    return build_probes(project_root)


def _fail(message: str) -> None:
    """Report a usage/configuration error on the reserved exit code."""
    from beadloom.application.guards.models import EXIT_CODE_CONFIG_ERROR

    click.echo(f"guard: {message}", err=True)
    sys.exit(EXIT_CODE_CONFIG_ERROR)


def _parse_context(pairs: tuple[str, ...]) -> dict[str, str]:
    """Parse repeated ``--context k=v`` flags into a mapping."""
    context: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key.strip():
            _fail(f"--context expects KEY=VALUE, got {pair!r}")
        context[key.strip()] = value
    return context


def _emit_liveness(project_root: Path, *, output_json: bool) -> None:
    """Print the liveness report for every registered guard."""
    from beadloom.application.guards.liveness import build_liveness

    rows = build_liveness(project_root)
    if output_json:
        click.echo(json.dumps([row.to_dict() for row in rows], indent=2))
        return
    for row in rows:
        flags = []
        if row.never_fired:
            flags.append("never-fired")
        if row.excluded_everywhere:
            flags.append("excluded-everywhere")
        source = "flow.yml" if row.declared else "default"
        suffix = f" [{', '.join(flags)}]" if flags else ""
        last = f", last {row.last_outcome} at {row.last_fired_at}" if row.last_fired_at else ""
        click.echo(
            f"{row.guard}: strictness={row.strictness} ({source}), "
            f"fired={row.fired_count}{last}{suffix}"
        )


def _emit_verdict(verdict: GuardVerdict, *, output_json: bool) -> None:
    """Print *verdict* on the stream its outcome dictates."""
    from beadloom.application.guards.models import GuardOutcome

    if output_json:
        click.echo(json.dumps(verdict.to_dict(), indent=2))
        return
    to_stderr = verdict.outcome in (GuardOutcome.WARN, GuardOutcome.BLOCK)
    click.echo(
        f"{verdict.guard}: {verdict.outcome.value.upper()} — {verdict.why}", err=to_stderr
    )
    for item in verdict.not_covered:
        click.echo(f"  not checked: {item}", err=to_stderr)
    if verdict.remediation:
        click.echo(f"  fix: {verdict.remediation}", err=to_stderr)


@main.command()
@click.argument("name", required=False)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--context",
    "context_pairs",
    multiple=True,
    metavar="KEY=VALUE",
    help="Evaluation context (repeatable): path=..., tool=..., work_kind=...",
)
@click.option(
    "--hook",
    "harness",
    default=None,
    metavar="HARNESS",
    help="Read the harness hook event as JSON on stdin (e.g. claude-code).",
)
@click.option(
    "--liveness",
    is_flag=True,
    help="Report which guards have fired, and which protect nothing.",
)
def guard(
    *,
    name: str | None,
    project: Path | None,
    output_json: bool,
    context_pairs: tuple[str, ...],
    harness: str | None,
    liveness: bool,
) -> None:
    """Evaluate a flow guard and return its verdict (exit 0 pass/skip, 1 warn, 2 block).

    Guards are declared in ``.beadloom/flow.yml`` (strictness per work kind,
    exclusions that must carry a reason and an expiry). A harness hook calls
    this same command, so the hook and the shell can never disagree.
    """
    from beadloom.application.guards.config import GuardConfigError
    from beadloom.application.guards.evaluation import evaluate_guard
    from beadloom.application.guards.firing import record_firing
    from beadloom.application.guards.hook_payload import (
        HookPayloadError,
        context_from_hook_payload,
    )

    project_root = project or Path.cwd()

    if liveness:
        if name is not None:
            _fail("--liveness reports every guard; do not name one")
        try:
            _emit_liveness(project_root, output_json=output_json)
        except GuardConfigError as exc:
            _fail(str(exc))
        return

    if name is None:
        _fail("name a guard to evaluate, or pass --liveness")
        return

    context = _parse_context(context_pairs)
    if harness is not None:
        try:
            hook_context = context_from_hook_payload(harness, sys.stdin.read())
        except HookPayloadError as exc:
            _fail(str(exc))
            return
        context = {**hook_context, **context}

    try:
        verdict = evaluate_guard(
            name,
            project_root=project_root,
            context=context,
            probes=_probes(project_root),
        )
    except GuardConfigError as exc:
        _fail(str(exc))
        return

    record_firing(project_root, verdict)
    _emit_verdict(verdict, output_json=output_json)
    sys.exit(verdict.exit_code)
