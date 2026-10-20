"""The ``landing-check`` command — a push that would land its own bead's hold is refused.

Presentation and wiring only. The judgement is
:func:`beadloom.application.landing_slot.check_push`; this module reads the refs a push
names and turns the verdict into lines on standard output and one exit code.

The pre-push hook runs it before the Gate, with git's own input: one line per pushed ref,
``<local ref> <local oid> <remote ref> <remote oid>`` (``--stdin``). Without ``--stdin``
the current ``HEAD`` is judged as a branch no remote holds yet, which is the form a person
types before pushing (BDL-083 S2g, BDL-UX #354, RFC D12).

The first line is always the verdict, led by
:data:`~beadloom.application.landing_slot.VERDICT_LEAD`, so a hook written in ``sh`` reads
the verdict on a shape rather than on the exit code alone.

Codes (the contract a caller may rely on):

* ``0`` — no ref of the push lands an export holding the slot for a bead it carries.
* ``1`` — one does; the lines after the verdict name the release and the sequence.
* ``2`` — the push could not be judged: no repository, a commit git does not know, or
  input git would not write. Never ``0``: a push nobody judged is not a clean one.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import sys
from pathlib import Path

import click

from beadloom.services.commands._root import main

_EXIT_CLEAN = 0
_EXIT_REFUSED = 1
_EXIT_NOT_CHECKED = 2

#: The remote side of a ref the remote does not hold, as git writes it to the hook.
_NO_REMOTE_TIP = "0" * 40


@main.command("landing-check")
@click.option(
    "--stdin",
    "from_stdin",
    is_flag=True,
    default=False,
    help=(
        "Read the pushed refs from standard input, as git hands them to a pre-push "
        "hook (default: judge HEAD as a branch no remote holds yet)."
    ),
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def landing_check(*, from_stdin: bool, project: Path | None) -> None:
    """Refuse a push whose exported tracker holds the landing slot for a bead it lands.

    The slot is tracker state exported to .beads/issues.jsonl, so the trunk says what the
    last landed export says. A push whose export still holds the slot for one of the
    beads its commits carry (by their Bead: trailer) leaves every later clone refused
    by a closed bead. The sequence that lands the release with the work is printed.
    """
    from beadloom.application.landing_slot import (
        VERDICT_CLEAN,
        VERDICT_LEAD,
        VERDICT_NOT_CHECKED,
        VERDICT_REFUSED,
        PushedRef,
        check_push,
        pushed_refs,
    )

    project_root = project or Path.cwd()
    if from_stdin:
        try:
            pushes = pushed_refs(sys.stdin.read())
        except ValueError as exc:
            click.echo(f"{VERDICT_LEAD}{VERDICT_NOT_CHECKED} -- {exc}")
            sys.exit(_EXIT_NOT_CHECKED)
    else:
        # A branch no remote holds yet: every commit no remote-tracking ref holds is
        # carried. git resolves `HEAD` wherever an object id is read.
        pushes = (PushedRef("HEAD", "HEAD", "HEAD", _NO_REMOTE_TIP),)
    verdict = check_push(project_root, pushes)
    for line in verdict.lines:
        click.echo(line)
    codes = {
        VERDICT_CLEAN: _EXIT_CLEAN,
        VERDICT_REFUSED: _EXIT_REFUSED,
        VERDICT_NOT_CHECKED: _EXIT_NOT_CHECKED,
    }
    sys.exit(codes[verdict.status])
