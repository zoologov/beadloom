"""The ``clean-room`` command — build the room this bead measures in, exactly once.

Presentation and wiring only. The build is
:func:`beadloom.application.waves.build_room`; this module is where the bead is
looked up through the ``bd`` seam, where a refusal becomes one exit code, and
where the room's own limits are printed beside its path.

**Why a command and not a paragraph.** The convention it replaces was three
shell lines in every role core, and following it exactly produced a room holding
a neighbour's work (BDL-UX #235) and a room whose second occupancy manufactured
a failure shaped like a real one (BDL-UX #243). Both are answered by deriving
the path from the bead and creating the directory rather than entering it —
which is a thing a command can do and a paragraph cannot.

Codes (the contract a caller may rely on):

* ``0`` — the room was built and the tracker says the bead is in progress.
* ``1`` — the room was built, and something about its OWNERSHIP is unconfirmed:
  the bead is not in progress, or the tracker could not be reached. The room is
  usable; who claimed the bead is a fact about the tracker, not about the room.
* ``2`` — no room was built. The directory exists, the tracker has no such bead,
  the path is inside the project, a carried file is not a file of it, or git has
  no commit to archive.

Nothing here writes into an existing directory, so a run that exits 2 leaves the
room it declined to enter exactly as it found it.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.application.waves import RoomBuild

_EXIT_CLEAN = 0
_EXIT_FINDINGS = 1
_EXIT_REFUSED = 2

#: The refusal reported when the tracker answers and has no such bead. It is a
#: refusal rather than a finding because a room named after a bead nobody holds
#: cannot say whose it is, which is the whole property this command adds.
_REFUSAL_UNKNOWN_BEAD = "unknown_bead"

#: The tracker status that means "this bead is mine right now".
_CLAIMED = "in_progress"


def _claim(bead_id: str, project_root: Path) -> tuple[str | None, str | None]:
    """The bead's tracker status, and the finding that its absence produces.

    Three answers, deliberately kept apart: a status, ``None`` for *the tracker
    could not answer*, and the empty string for *the tracker answered and has no
    such bead*. Collapsing the last two would either refuse every project without
    ``bd`` or build a room for a bead id somebody mistyped.
    """
    from beadloom.services.bd_seam import BdUnavailableError, run_bd

    try:
        result = run_bd(["show", bead_id, "--json"], cwd=str(project_root))
    except BdUnavailableError as exc:
        return None, f"the tracker could not be asked who holds {bead_id} ({exc})"
    if not result.ok or not result.stdout.strip():
        return "", f"the tracker has no bead {bead_id!r} ({result.stderr.strip()})"
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f"the tracker's answer for {bead_id} was not JSON ({exc})"
    record = parsed[0] if isinstance(parsed, list) and parsed else parsed
    if not isinstance(record, dict):
        return None, f"the tracker's answer for {bead_id} was not a bead record"
    status = str(record.get("status", ""))
    if status != _CLAIMED:
        return status, (
            f"{bead_id} is {status or 'of no stated status'} rather than "
            f"{_CLAIMED}: build the room for the bead you claimed, because the "
            "room is the only thing that says which bead a measurement is about"
        )
    return status, None


def _payload(
    build: RoomBuild, status: str | None, findings: list[str], code: int
) -> dict[str, Any]:
    """The whole answer as data — the same facts the human shape prints."""
    return {
        "bead": build.bead_id,
        "room": str(build.path),
        "built": build.built,
        "refusal": build.refusal,
        "detail": build.detail,
        "commit": build.commit,
        "carried": list(build.carried),
        "invocation": list(build.invocation),
        "extras": build.extras,
        "claim": status or None,
        "findings": findings,
        "exit_code": code,
    }


def _render(build: RoomBuild, status: str | None, findings: list[str]) -> None:
    """Print the room, how to measure in it, and what it cannot answer."""
    if not build.built:
        click.echo(f"No room was built — {build.refusal}: {build.detail}", err=True)
        click.echo(f"  room: {build.path}", err=True)
        return
    click.echo(f"{build.path.name} built at {build.path}")
    click.echo(f"  from commit {build.commit}, holder recorded as {build.bead_id}")
    carried = ", ".join(build.carried) if build.carried else "none"
    click.echo(f"  carried from the working tree: {carried}")
    click.echo(
        "  extras the invocation's interpreter has: "
        + (build.extras or "not resolved — no verdict here can state them")
    )
    click.echo(f"  tracker status: {status or 'not answered'}")
    click.echo("")
    click.echo("Measure in the room, not in the tree:")
    for line in build.invocation:
        click.echo(f"  {line}")
    click.echo("")
    click.echo(
        "What this room cannot answer: it carries no .git, so a freshness check "
        "inside it has no baseline; and its verdict is a claim about these files "
        "only, never about the combined tree — that measurement belongs to the "
        "wave's gate owner. Report it in those words, with the extras above: on "
        "this project one code base gave 0 mypy errors under `[all,dev]` and 82 "
        "under `[dev]` (BDL-UX #236)."
    )
    for finding in findings:
        click.echo(f"FINDING: {finding}", err=True)


# beadloom:domain=application
@main.command("clean-room")
@click.argument("bead")
@click.option(
    "--at",
    "at",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Directory to build the room under (default: the system temp directory).",
)
@click.option(
    "--carry",
    "carry",
    multiple=True,
    help=(
        "A project file to copy into the room, repeatable. Only what you name: "
        "on a shared tree, everything that differs from HEAD includes your "
        "neighbour's work."
    ),
)
@click.option(
    "--rebuild",
    is_flag=True,
    default=False,
    help="Replace a room this command built for this bead, rather than refusing it.",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option("--json", "output_json", is_flag=True, help="Structured JSON output.")
def clean_room(
    *,
    bead: str,
    at: Path | None,
    carry: tuple[str, ...],
    rebuild: bool,
    project: Path | None,
    output_json: bool,
) -> None:
    """Build BEAD's clean room from HEAD plus the files you name.

    The room's directory is derived from the bead, so two agents of one wave
    cannot be handed the same one, and an existing directory is refused rather
    than entered, so nothing in a room postdates the room.
    """
    from beadloom.application.waves import RoomBuild, build_room, room_path

    project_root = project or Path.cwd()
    parent = at or Path(tempfile.gettempdir())

    status, finding = _claim(bead, project_root)
    if status == "":
        refused = RoomBuild(
            bead_id=bead,
            path=room_path(parent, bead),
            built=False,
            detail=finding or "",
            refusal=_REFUSAL_UNKNOWN_BEAD,
        )
        _finish(refused, status, [], _EXIT_REFUSED, output_json=output_json)

    build = build_room(
        bead_id=bead,
        project_root=project_root,
        parent=parent,
        carry=tuple(carry),
        rebuild=rebuild,
    )
    findings = [finding] if finding else []
    code = _EXIT_REFUSED if not build.built else (_EXIT_FINDINGS if findings else _EXIT_CLEAN)
    _finish(build, status, findings, code, output_json=output_json)


def _finish(
    build: RoomBuild,
    status: str | None,
    findings: list[str],
    code: int,
    *,
    output_json: bool,
) -> None:
    """Print one shape and exit — the single place the two shapes agree."""
    if output_json:
        click.echo(json.dumps(_payload(build, status, findings, code), indent=2))
    else:
        _render(build, status, findings)
    sys.exit(code)
