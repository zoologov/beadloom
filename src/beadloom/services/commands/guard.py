"""The ``guard`` command — evaluate one flow guard, or report guard liveness.

Presentation only, and now literally so: the whole decision — locating the
project, parsing the arguments, reading the harness payload, evaluating, and
recording the firing — happens inside
:func:`beadloom.application.guards.invocation.run_invocation`, which returns a
result and never raises and never exits. This module turns that result into
lines on a stream and calls :func:`sys.exit` **once** — with the render inside a
``try`` and that one exit outside it, so a failure while printing cannot hand
the exit code to Click (exit 1, the non-blocking *warn* code) for a reason that
has nothing to do with the edit.

That shape is the fix for a defect three cycles could not close by patching:
each entry path (argument parsing, the stdin read, project discovery, the
evaluation) used to decide for itself whether to record a firing, and each new
one was a fresh place to forget. There is now one boundary, so "does this exit
path leave a record" is a question about one function rather than about every
branch of this one.

Streams and codes (the adapter contract):

* ``pass`` / ``skip`` -> stdout, exit 0
* ``warn`` -> stderr, exit 1 (visible, never blocking)
* ``block`` / ``error`` -> stderr, exit 2
* configuration or command-line error -> stderr, exit 3 **from a shell**, exit 2
  when ``--hook`` names a harness

``warn``/``block``/``error`` go to **stderr** because that is the stream a hook
harness shows to the agent. ``3`` is kept for a defect in the project's declared
configuration and for a command line that could not be used at all, so a genuine
``block`` stays distinguishable from Click's own usage exit code (2); which
failures earn ``3`` rather than ``2`` is decided — with the reason — in the
boundary module.

That distinction is worth something to a person at a terminal and nothing to a
hook, where ``3`` means only that the edit went through unguarded — which is how
a ``flow.yml`` that would not parse switched every bound guard off (BDL-061.33).
So the same class exits the blocking code when the invocation names a harness.
The choice is made in the application layer, not in the emitted adapter: an
adapter that maps codes carries logic, and logic in an adapter is behaviour that
exists inside one tool only.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.application.guards.contract import GuardProbes
    from beadloom.application.guards.invocation import InvocationResult
    from beadloom.application.guards.liveness import GuardLiveness
    from beadloom.application.guards.models import GuardVerdict


#: Why a ``--hook`` read failed when the caller left this process no stdin at all.
_NO_STDIN = (
    "this process has no standard input to read the payload from (the caller "
    "closed it)"
)

#: Reported when the verdict itself could not be printed. The exit code does not move.
_RENDER_FAILED = (
    "the verdict could not be printed ({detail}); the guard's exit code is "
    "unchanged, and the firing record — if one was due — was already written"
)


def _probes(project_root: Path) -> GuardProbes:
    """Seam over the real bd/git probes (patched in tests, wired for real here)."""
    from beadloom.services.guard_probes import build_probes

    return build_probes(project_root)


def _read_stdin() -> bytes:
    """The harness payload as the BYTES the harness wrote — never as decoded text.

    Read lazily, so a failure happens inside the boundary: a non-UTF-8 byte on
    the hook's stdin used to raise ``UnicodeDecodeError`` here, before anything
    could turn it into a verdict — exit 1, the *warn* code a harness reads as
    non-blocking, a raw traceback, and no firing record (BDL-061.28, F7).

    Returning **bytes** is BDL-061.36. ``sys.stdin.read()`` decodes with
    whatever error handler the interpreter was started with: ``strict`` under a
    UTF-8 locale, ``surrogateescape`` under ``LC_ALL=C`` or ``PYTHONUTF8=1``
    (measured on 3.10.1 and 3.13.7), which is the default of most container
    images. Under the second the refusal one layer up never fired — the bad
    bytes became lone surrogates, the JSON parsed, and the guard evaluated a
    file name this process had invented. The decode now happens inside the
    boundary with a stated error handler, so this function hands over the byte
    sequence the writer produced and decides nothing.

    The binary layer is used when the stream has one — the real ``sys.stdin``
    always does. A stream without one (an in-process double) is re-encoded with
    ``surrogateescape``, the exact inverse of the decoding that would otherwise
    hide the bad bytes: what the stream's decoder escaped comes back as the
    original bytes, and text that decoded cleanly re-encodes to itself.

    A CLOSED stdin is stated rather than left to speak for itself: ``sys.stdin``
    is ``None`` when the caller ran the guard with ``0<&-``, and the resulting
    ``AttributeError: 'NoneType' object has no attribute 'read'`` reached the
    reader as the reason the edit was blocked — an internal repr where a cause
    belongs (BDL-061.30, section 4). The raise happens inside the boundary's
    ``try`` because the invocation calls this function, not the other way round.
    """
    stream = sys.stdin
    if stream is None:
        raise OSError(_NO_STDIN)
    binary = getattr(stream, "buffer", None)
    if isinstance(binary, io.BufferedIOBase):
        return binary.read()
    return stream.read().encode("utf-8", "surrogateescape")


def _emit_liveness(rows: tuple[GuardLiveness, ...], *, output_json: bool) -> None:
    """Print the liveness report for every registered guard."""
    if output_json:
        click.echo(json.dumps([row.to_dict() for row in rows], indent=2))
        return
    for row in rows:
        flags = []
        if row.never_fired:
            flags.append("never-fired")
        if row.excluded_everywhere:
            flags.append("excluded-everywhere")
        for pattern in row.dead_exclusions:
            flags.append(f"matches no file in the project: {pattern!r}")
        for pattern in row.expired_exclusions:
            flags.append(f"exit condition has passed: {pattern!r}")
        source = "flow.yml" if row.declared else "default"
        suffix = f" [{', '.join(flags)}]" if flags else ""
        last = f", last {row.last_outcome} at {row.last_fired_at}" if row.last_fired_at else ""
        click.echo(
            f"{row.guard}: strictness={row.strictness} ({source}), "
            f"fired={row.fired_count}{last}{suffix}"
        )


def _emit_verdict(result: InvocationResult, verdict: GuardVerdict, *, output_json: bool) -> None:
    """Print *verdict* on the stream its outcome dictates, and say if it went unrecorded."""
    from beadloom.application.guards.models import GuardOutcome

    if output_json:
        payload: dict[str, object] = {
            **verdict.to_dict(),
            "recorded": result.recorded,
            "not_recorded_because": result.not_recorded_because,
        }
        click.echo(json.dumps(payload, indent=2))
        return
    to_stderr = verdict.outcome in (
        GuardOutcome.WARN,
        GuardOutcome.BLOCK,
        GuardOutcome.ERROR,
    )
    click.echo(
        f"{verdict.guard}: {verdict.outcome.value.upper()} — {verdict.why}", err=to_stderr
    )
    for item in verdict.not_covered:
        click.echo(f"  not checked: {item}", err=to_stderr)
    if verdict.remediation:
        click.echo(f"  fix: {verdict.remediation}", err=to_stderr)
    if not result.recorded:
        click.echo(f"  not recorded: {result.not_recorded_because}", err=True)


def _emit(result: InvocationResult, *, output_json: bool) -> None:
    """Render whatever the invocation produced: a verdict, or the report it asked for."""
    if result.verdict is None:
        _emit_liveness(result.liveness, output_json=output_json)
        return
    _emit_verdict(result, result.verdict, output_json=output_json)


@main.command()
@click.argument("name", required=False)
@click.option(
    "--project",
    # `readable=False` because `click.Path` defaults it to True, and that check
    # runs in Click, before the callback: a directory this process may not read
    # was a usage error at exit 2 with no verdict and no record (BDL-061.32).
    # The conversion here must refuse nothing, so that every reason a declared
    # project cannot be used is answered by the boundary as a verdict.
    type=click.Path(path_type=Path, readable=False),
    default=None,
    help="Project root (default: the nearest directory above with .beadloom/).",
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
    this same command, so the hook and the shell can never disagree about the
    *verdict*. They differ in one code and only one: a defect in the declared
    configuration, or a command line that could not be used, exits ``3`` here
    and ``2`` under ``--hook``, because ``3`` does not stop a tool call and a
    guard that cannot answer must never read as one that passed.

    With no ``--project``, the project root is the nearest directory at or above
    the working directory that contains ``.beadloom/`` — the firing record
    belongs to the project, not to wherever the process was started.
    ``--project`` is honoured verbatim, and must name a directory that carries
    ``.beadloom/``: the flag names a project, and a guard manufactures none.

    ``--project`` is deliberately not validated by Click: an option Click
    rejects exits before this callback, and therefore before the boundary that
    guarantees a verdict and a record. That covers the keywords nobody typed as
    well — ``click.Path`` defaults ``readable=True``, so a directory this
    process may not read was a usage error with no verdict until BDL-061.32.
    """
    from beadloom.application.guards.invocation import GuardInvocation, run_invocation

    result = run_invocation(
        GuardInvocation(
            name=name,
            declared_project=project,
            context_pairs=context_pairs,
            harness=harness,
            liveness=liveness,
            read_payload=_read_stdin,
            probes_for=_probes,
        )
    )
    try:
        _emit(result, output_json=output_json)
    except BaseException as exc:  # rendering must not get a say in the verdict
        # The boundary has already decided and already recorded; everything left
        # is presentation. Letting a failure here propagate would hand the exit
        # code to Click — exit 1, the non-blocking *warn* code — for a reason
        # that has nothing to do with the edit (BDL-061.30, section 5). The
        # note is best-effort by design: if the streams are broken badly enough
        # that even this cannot be said, the code is still the verdict's.
        with contextlib.suppress(BaseException):
            click.echo(_RENDER_FAILED.format(detail=exc), err=True)
    sys.exit(result.exit_code)
