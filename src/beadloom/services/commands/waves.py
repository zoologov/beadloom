"""The ``waves`` command — decide which of these beads may run at the same time.

Presentation and wiring only. The decision is
:func:`beadloom.application.waves.plan_waves`, which takes bead records as data;
this module is where those records are read out of the tracker through the ``bd``
seam, where the declared overrides are read out of ``flow.yml``, and where a plan
becomes lines on a stream and one exit code.

Codes (the contract a caller may rely on):

* ``0`` — a shape was decided and it rests on nothing unstated.
* ``1`` — a shape was decided and carries findings: a bead that did not declare
  its scope, an override past its exit condition, an override that changed
  nothing. Visible, never blocking — the shape is still usable.
* ``2`` — no shape could be decided: no index, no answer from the tracker, a
  bead the tracker does not have, or a ``waves:`` block that would not parse.

**Every fact is printed in both shapes.** The human output and ``--json`` carry
the same counts and the same verdict, and neither depends on whether stdout is a
terminal — a monitoring surface whose shape depends on whether a human is
watching will be sampled by a program and silently give it a different answer
(BDL-UX #148). Nothing here asks a caller to count lines.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.application.waves import BeadRecord, WaveEnvironment, WavePlan

#: Exit codes, named so the renderer and the docstring cannot drift apart.
_EXIT_CLEAN = 0
_EXIT_FINDINGS = 1
_EXIT_UNDECIDABLE = 2

#: The tracker's own word for a dependency that is a parent link rather than an
#: ordering constraint. A parent never blocks its child.
_PARENT_CHILD = "parent-child"


def _declaration(record: dict[str, Any]) -> str:
    """Everything the bead says about itself, in one string for the scope parser."""
    return "\n".join(
        str(record.get(key, "")) for key in ("title", "description", "design", "notes")
    )


def _blocked_by(record: dict[str, Any]) -> frozenset[str]:
    """The OPEN, non-parent dependencies of *record* — beads that must land first."""
    deps = record.get("dependencies")
    if not isinstance(deps, list):
        return frozenset()
    return frozenset(
        str(dep.get("id"))
        for dep in deps
        if isinstance(dep, dict)
        and dep.get("dependency_type") != _PARENT_CHILD
        and dep.get("status") != "closed"
        and dep.get("id")
    )


def _read_beads(bead_ids: tuple[str, ...], project_root: Path) -> list[BeadRecord]:
    """One :class:`BeadRecord` per id, read through the ``bd`` seam.

    A bead the tracker cannot answer for is an error rather than a bead with an
    empty declaration: an absent answer that reads as "declares nothing" would be
    serialised with a finding pointing at the author, when the thing to fix is the
    id or the tracker.
    """
    from beadloom.application.waves import BeadRecord
    from beadloom.services.bd_seam import run_bd

    records: list[BeadRecord] = []
    for bead_id in bead_ids:
        result = run_bd(["show", bead_id, "--json"], cwd=str(project_root))
        if not result.ok or not result.stdout.strip():
            msg = f"the tracker has no bead {bead_id!r} ({result.stderr.strip()})"
            raise LookupError(msg)
        parsed = json.loads(result.stdout)
        record = parsed[0] if isinstance(parsed, list) and parsed else parsed
        if not isinstance(record, dict):
            msg = f"the tracker's answer for {bead_id!r} was not a bead record"
            raise LookupError(msg)
        records.append(
            BeadRecord(
                bead_id=bead_id,
                declaration=_declaration(record),
                blocked_by=_blocked_by(record),
                title=str(record.get("title", "")),
            )
        )
    return records


def _commit_gate(project_root: Path) -> str | None:
    """What the installed pre-commit hook judges, read where the installer writes.

    The same path ``install-hooks`` writes to, deliberately: a check that looked
    somewhere else would be a second opinion about one fact. ``None`` means the
    hook could not be read — no ``.git`` directory, or a hook whose bytes are not
    text — and it is reported as unmeasured rather than as a missing gate.
    """
    from beadloom.application.waves import GATE_ABSENT, GATE_COMMIT_SCOPED, GATE_WHOLE_TREE
    from beadloom.services.commands.docsync import _HOOK_SCOPE_MARKER

    hooks_dir = project_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        return None
    hook = hooks_dir / "pre-commit"
    if not hook.exists():
        return GATE_ABSENT
    try:
        content = hook.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # An unreadable hook is not an absent one and not a scoped one. Naming
        # the third answer is the whole reason `unmeasured` is a status.
        return None
    return GATE_COMMIT_SCOPED if _HOOK_SCOPE_MARKER in content else GATE_WHOLE_TREE


def _stale_pairs(db_path: Path, project_root: Path) -> int | None:
    """How many doc pairs are stale before the wave starts, or ``None`` if unknown."""
    from beadloom.doc_sync.engine import check_sync
    from beadloom.infrastructure.db import open_db

    conn = open_db(db_path)
    try:
        return sum(1 for row in check_sync(conn, project_root=project_root)
                   if row.get("status") == "stale")
    except sqlite3.Error:
        # A doc baseline that cannot be read is not a reconciled one.
        return None
    finally:
        conn.close()


def _environment(project_root: Path, db_path: Path) -> WaveEnvironment:
    """Measure the three media the graph cannot see, here at the services edge.

    Gathered here rather than inside the planner so the application layer keeps
    taking its input as data: the decision stays runnable without git, without a
    repository and without a hook, and every one of those absences arrives as a
    ``None`` that the checks report rather than as a silent zero.
    """
    from beadloom.application.waves import WaveEnvironment
    from beadloom.doc_sync.git_baseline import changed_paths

    changed = changed_paths(project_root)
    return WaveEnvironment(
        tree_changed_paths=None if changed is None else tuple(sorted(changed)),
        commit_gate=_commit_gate(project_root),
        doc_baseline_stale_pairs=_stale_pairs(db_path, project_root),
    )


def _plan_as_dict(plan: WavePlan) -> dict[str, Any]:
    """The whole plan as data — the same facts the human shape prints."""
    return {
        "beads": len(plan.scopes),
        "waves": [
            {
                "index": wave.index,
                "beads": list(wave.beads),
                "gate_owner": wave.gate_owner,
            }
            for wave in plan.waves
        ],
        "scopes": [
            {
                "bead": scope.bead_id,
                "refs": sorted(scope.refs),
                "files": len(scope.files),
                "unresolved": scope.unresolved,
                "unknown_refs": list(scope.unknown_refs),
            }
            for scope in plan.scopes
        ],
        "conflicts": [
            {
                "left": c.left,
                "right": c.right,
                "reason": c.reason,
                "detail": c.detail,
            }
            for c in plan.conflicts
        ],
        "overrides": [
            {
                "beads": list(o.override.beads),
                "decision": o.override.decision,
                "reason": o.override.reason,
                "until": o.override.until,
                "changed": o.changed,
                "inert": o.inert,
                "expired": o.expired,
            }
            for o in plan.overrides
        ],
        "shared_media": [
            {"name": m.name, "statement": m.statement, "evidence": m.evidence}
            for m in plan.shared_media
        ],
        "media_checks": [
            {"medium": c.medium, "status": c.status, "detail": c.detail}
            for c in plan.media_checks
        ],
        "findings": list(plan.findings),
        "exit_code": plan.exit_code,
    }


def _render(plan: WavePlan) -> None:
    """Print the decided shape, its reasons, and what it did not decide."""
    click.echo(
        f"{len(plan.waves)} wave(s) for {len(plan.scopes)} bead(s), "
        f"{len(plan.conflicts)} serialisation(s), {len(plan.findings)} finding(s)."
    )
    click.echo("")
    for wave in plan.waves:
        click.echo(f"Wave {wave.index}: {', '.join(wave.beads)}")
        if len(wave.beads) > 1:
            click.echo(f"  combined-tree gate: {wave.gate_owner}")
    if plan.conflicts:
        click.echo("")
        click.echo("Serialised because:")
        for conflict in plan.conflicts:
            click.echo(
                f"  {conflict.left} | {conflict.right} — "
                f"{conflict.reason}: {conflict.detail}"
            )
    click.echo("")
    click.echo(f"{len(plan.overrides)} declared override(s).")
    for outcome in plan.overrides:
        state = "inert" if outcome.inert else f"changed {outcome.changed} decision(s)"
        expiry = " — EXPIRED" if outcome.expired else ""
        click.echo(
            f"  [{', '.join(outcome.override.beads)}] {outcome.override.decision}: "
            f"{outcome.override.reason} (until {outcome.override.until}{expiry}) "
            f"— {state}"
        )
    click.echo("")
    if plan.shared_media:
        click.echo(
            "Shared by every wave of more than one bead, and NOT decided by code "
            "independence:"
        )
        for medium in plan.shared_media:
            click.echo(f"  {medium.name} ({medium.evidence}) — {medium.statement}")
    else:
        click.echo(
            "No wave runs more than one bead, so nothing is shared concurrently."
        )
    if plan.media_checks:
        click.echo("")
        click.echo("Plan-time precondition of each shared medium:")
        for check in plan.media_checks:
            click.echo(f"  {check.medium}: {check.status} — {check.detail}")
    if plan.findings:
        click.echo("")
        for finding in plan.findings:
            click.echo(f"FINDING: {finding}", err=True)


# beadloom:domain=application
@main.command("waves")
@click.argument("beads", nargs=-1, required=True)
@click.option("--json", "output_json", is_flag=True, help="Structured JSON output.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def waves(*, beads: tuple[str, ...], output_json: bool, project: Path | None) -> None:
    """Decide which of these beads may run at the same time.

    Parallelism is decided from the code-level independence of the beads' node
    scopes: independent subgraphs share a wave, a shared node serialises, and a
    bead that has not declared what it occupies is serialised against everything
    rather than assumed independent.
    """
    from beadloom.application.waves import WaveConfigError, load_overrides, plan_waves
    from beadloom.infrastructure.db import open_db
    from beadloom.services.bd_seam import BdUnavailableError

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(_EXIT_UNDECIDABLE)

    try:
        overrides = load_overrides(project_root)
        records = _read_beads(beads, project_root)
    except (WaveConfigError, LookupError, BdUnavailableError, json.JSONDecodeError) as exc:
        click.echo(f"Error: no wave shape could be decided — {exc}", err=True)
        sys.exit(_EXIT_UNDECIDABLE)

    environment = _environment(project_root, db_path)
    conn = open_db(db_path)
    try:
        plan = plan_waves(
            records, conn=conn, overrides=overrides, environment=environment
        )
    finally:
        conn.close()

    if output_json:
        click.echo(json.dumps(_plan_as_dict(plan), indent=2))
    else:
        _render(plan)
    sys.exit(_EXIT_FINDINGS if plan.findings else _EXIT_CLEAN)
