"""The ``waves`` command — decide which of these beads may run at the same time.

Presentation and wiring only. The decision is
:func:`beadloom.application.waves.plan_waves`, which takes bead records as data;
this module is where those records are read out of the tracker through the ``bd``
seam, where the declared overrides are read out of ``flow.yml``, and where a plan
becomes lines on a stream and one exit code.

Codes (the contract a caller may rely on):

* ``0`` — a shape was decided and it rests on nothing unstated.
* ``1`` — a shape was decided and carries findings: a bead whose declared scope
  could not be read (it declared none, named a ref the graph does not have, wrote
  the declaration inside a sentence, or wrote a second ref the parser had to drop),
  an override past its exit condition, an override that changed nothing, a shared
  medium whose precondition failed (including a bead the document every route
  writes carries no row for), a shared medium nobody measured, a bead declaring a
  node its work item rules out of scope, a concurrent wave whose beads leave
  part of that work item's approved scope undeclared, a ready list the
  tracker capped, which makes the population this plan was held against a part
  of one, and a bead in progress under the same work item that the tracker could
  not show, so the plan was not compared against it. Visible, never blocking —
  the shape is still usable.
* ``2`` — no shape could be decided: no index, no answer from the tracker, a
  bead the tracker does not have, a ``--parent`` whose beads could not be
  derived, neither a bead nor a ``--parent``, or a ``waves:`` block that would
  not parse.

**How many ready beads this plan was NOT asked about is printed and is never a
finding** (BDL-UX #274). The bead list was the one thing here a human typed, and
this project's own coordinator lost three beads of a slice that way. Narrowing a
wave deliberately stays legitimate — measured over BDL-068's S6, 15 of 15
launches were subsets — so the count is a notice, and ``--parent`` is the half
that removes the typing instead of reporting on it.

**Every plan is compared against the beads already in progress under its work
item** (BDL-UX #283). The plan's beads are ready ones and a bead in progress is
not ready, so a running bead used to be compared against nothing and the plan
printed ``0 serialisation(s)`` beside it. A conflict with running work is printed
apart from the plan's own serialisations, on the first line and in a block of its
own, because it is acted on differently: it does not order the plan's waves, it
holds a bead back until work nobody is launching lands.

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
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.application.waves import (
        BeadRecord,
        FocusDocument,
        GraphInput,
        TrackerBead,
        TrackerCensus,
        WaveEnvironment,
        WavePlan,
        WorkItemAxes,
    )

#: Exit codes, named so the renderer and the docstring cannot drift apart.
_EXIT_CLEAN = 0
_EXIT_FINDINGS = 1
_EXIT_UNDECIDABLE = 2

#: The tracker's own word for a dependency that is a parent link rather than an
#: ordering constraint. A parent never blocks its child.
_PARENT_CHILD = "parent-child"


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


def _read_bead(bead_id: str, project_root: Path) -> BeadRecord:
    """One :class:`BeadRecord`, read through the ``bd`` seam.

    A bead the tracker cannot answer for is an error rather than a bead with an
    empty declaration: an absent answer that reads as "declares nothing" would be
    serialised with a finding pointing at the author, when the thing to fix is the
    id or the tracker.
    """
    from beadloom.application.waves import BeadRecord, compose_declaration
    from beadloom.services.bd_seam import run_bd

    result = run_bd(["show", bead_id, "--json"], cwd=str(project_root))
    if not result.ok or not result.stdout.strip():
        msg = f"the tracker has no bead {bead_id!r} ({result.stderr.strip()})"
        raise LookupError(msg)
    parsed = json.loads(result.stdout)
    record = parsed[0] if isinstance(parsed, list) and parsed else parsed
    if not isinstance(record, dict):
        msg = f"the tracker's answer for {bead_id!r} was not a bead record"
        raise LookupError(msg)
    return BeadRecord(
        bead_id=bead_id,
        declaration=compose_declaration(record),
        blocked_by=_blocked_by(record),
        title=str(record.get("title", "")),
    )


def _read_beads(bead_ids: tuple[str, ...], project_root: Path) -> list[BeadRecord]:
    """One :class:`BeadRecord` per id; the first bead the tracker cannot show raises."""
    return [_read_bead(bead_id, project_root) for bead_id in bead_ids]


def _running_records(
    census: TrackerCensus, asked: tuple[str, ...], project_root: Path
) -> list[BeadRecord]:
    """The records of the beads in progress that this plan does not hold (BDL-UX #283).

    Every bead the census lists as in progress, not only those under the plan's
    work item: which item that is gets derived by the planner, and a bead in
    progress is claimed work, so the population stays small — 2 of 897 beads on
    this repository on 2026-09-11. The planner ignores a record outside the item.

    Tolerant where :func:`_read_beads` is strict, because these beads are not the
    plan. A bead the tracker cannot show is left out, and the planner reports an
    in-progress bead with no record as not compared, which is a finding rather
    than a refusal to decide the shape.
    """
    from beadloom.application.waves import TRACKER_IN_PROGRESS
    from beadloom.services.bd_seam import BdUnavailableError

    planned = frozenset(asked)
    records: list[BeadRecord] = []
    for bead in census.beads or ():
        if bead.status != TRACKER_IN_PROGRESS or bead.bead_id in planned:
            continue
        try:
            records.append(_read_bead(bead.bead_id, project_root))
        except (LookupError, json.JSONDecodeError):
            continue
        except BdUnavailableError:
            break
    return records


def _bead_ids(
    beads: tuple[str, ...], parent: str | None, census: TrackerCensus
) -> tuple[str, ...]:
    """The beads to plan: the ones named, plus the ones *parent* derives.

    Without ``--parent`` this is the caller's list unchanged — passing a subset
    stays legitimate and is reported rather than refused. With it, the list is
    derived from the tracker, which is the half of BDL-UX #274 that removes the
    typing rather than reporting on it.

    A ``--parent`` the census cannot answer for is an error and not an empty
    plan: the caller asked this command to derive a list, and a plan of no beads
    would read as "nothing is ready under it", which is a different fact.
    """
    from beadloom.application.waves import ready_under

    if not parent:
        return beads
    derived = ready_under(parent, census)
    if derived is None:
        msg = (
            f"the tracker could not be read, so the beads ready under {parent!r} "
            f"could not be derived"
        )
        raise LookupError(msg)
    return tuple(sorted(set(beads) | set(derived)))


def _tracker_census(project_root: Path) -> TrackerCensus:
    """What the tracker holds beyond the beads this call names.

    Two call forms and one purpose: the whole tracker, so a work item's
    population can be walked, and the ready list, so the population can be cut
    down to beads that could actually have been planned. Both name the
    population they want — ``--all`` lifts a status filter bd does not announce
    at all, and ``--limit 0`` lifts a cap bd announces on stderr only (BDL-UX
    #187) — and the ready answer is then held against
    :func:`~beadloom.services.bd_seam.coverage_of`, so a cap applied anyway is
    reported rather than silently narrowing the count.

    Fail-safe by construction: every failure leaves the corresponding field
    ``None``, and a plan whose census could not be read says so instead of
    reporting that nothing was left out. A tracker that cannot answer must not
    stop a shape being decided — the population is a notice beside the plan, not
    an input to it.
    """
    from beadloom.application.waves import TrackerCensus
    from beadloom.services.bd_seam import BdUnavailableError, run_bd
    from beadloom.services.bd_seam.answers import coverage_of, ready_ids

    try:
        listed = run_bd(["list", "--all", "--json"], cwd=str(project_root))
        ready = run_bd(["ready", "--json", "--limit", "0"], cwd=str(project_root))
    except BdUnavailableError:
        return TrackerCensus()
    beads = _census_beads(listed.stdout) if listed.ok else None
    ids = ready_ids(ready.stdout) if ready.ok else None
    coverage = coverage_of(("ready", "--json", "--limit", "0"), ready.stderr)
    return TrackerCensus(
        beads=beads,
        ready=ids,
        ready_whole=coverage.as_asked,
        ready_note=coverage.stated,
    )


def _census_beads(stdout: str) -> tuple[TrackerBead, ...] | None:
    """One :class:`TrackerBead` per row of a ``bd list --json`` answer.

    ``None`` when the answer could not be read: an unreadable tracker is not a
    tracker holding no bead, and reporting it as one would say every bead of
    every work item was planned.

    The dependency rows are read in ``bd list``'s own spelling — ``type`` and
    ``depends_on_id``, where ``bd show`` writes ``dependency_type`` and ``id``
    for the same edge. Two spellings of one fact in one tracker, so the reader
    of each answer owns its own.
    """
    from beadloom.application.waves import TrackerBead

    try:
        rows = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(rows, list):
        return None
    found: list[TrackerBead] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            return None
        deps = row.get("dependencies")
        status = row.get("status")
        found.append(
            TrackerBead(
                bead_id=row["id"],
                parent=str(row.get("parent") or ""),
                status=status if isinstance(status, str) else None,
                depends_on=frozenset(
                    str(dep["depends_on_id"])
                    for dep in (deps if isinstance(deps, list) else [])
                    if isinstance(dep, dict)
                    and dep.get("type") != _PARENT_CHILD
                    and dep.get("depends_on_id")
                ),
            )
        )
    return tuple(found)


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


def _graph_input(project_root: Path, db_path: Path) -> GraphInput | None:
    """The graph this plan is derived from, read from both of the homes it has.

    Read through :func:`~beadloom.onboarding.graph_files.each_graph_file`, which
    is the one policy every reader of that directory holds — a second reader
    with a skip policy of its own is how two readers of one directory come to
    disagree about what a node is, which is what that module exists to stop.

    ``None`` when there is no graph directory or the index will not answer:
    neither is a project whose graph declares nothing, and an unknown population
    must not print like an empty one.
    """
    from beadloom.application.waves import GraphFile, GraphInput
    from beadloom.infrastructure.db import open_db
    from beadloom.infrastructure.repository import get_all_nodes
    from beadloom.onboarding.graph_files import each_graph_file

    graph_dir = project_root / ".beadloom" / "_graph"
    if not graph_dir.is_dir():
        return None
    files = tuple(
        GraphFile(
            path=_relative(yml, project_root),
            nodes=tuple(
                sorted(
                    str(node["ref_id"])
                    for node in data.get("nodes") or []
                    if isinstance(node, dict) and node.get("ref_id")
                )
            ),
        )
        for yml, data in each_graph_file(graph_dir)
    )
    conn = open_db(db_path)
    try:
        indexed = frozenset(node.ref_id for node in get_all_nodes(conn))
    except sqlite3.Error:
        # An index that will not answer is not an index holding no node.
        return None
    finally:
        conn.close()
    return GraphInput(files=files, indexed=indexed)


def _focus_documents(
    project_root: Path, axes: WorkItemAxes
) -> tuple[FocusDocument, ...] | None:
    """The documents every work-item type writes, and the rows each carries.

    Two derivations already in the codebase, joined and read once. WHICH kind
    every route writes is
    :attr:`~beadloom.application.work_item_routing.Routing.shared_kinds`, off the
    composed ``/task-init`` command. WHICH work item this plan belongs to is
    *axes*, the same read the commit gate makes, and its document names the
    folder the work item's own files live in — so no path is spelled here and a
    project with another convention is not measured against this one.

    **Scoped to ONE work item, and the reason is a measurement.** The first
    version read every focus document in the project and asked whether any row
    named the bead. Run on this repository it reported ``passed`` for all three
    beads of BDL-068's S6 wave over 58 documents, none of which carries a row for
    any of them: an ACTIVE table abbreviates ``beadloom-0mdo.75`` to ``.75``, and
    BDL-061's table has a ``.75`` row of its own. That is the ambiguity
    :func:`~beadloom.application.active_table.row_ids.resolve_row_bead_id`
    already refuses to guess at, met from the other side — this project holds
    eight beads numbered ``.17`` in eight epics.

    ``None`` when the routing could not be read, or when the branch names no work
    item: neither is a flow whose routes write nothing, and an unknown population
    must not print like an empty one.
    """
    from beadloom.application.doc_shape import planning_document_globs
    from beadloom.application.waves import FocusDocument
    from beadloom.application.work_item_routing import task_init_routing
    from beadloom.doc_sync.tables import cells_of

    routing = task_init_routing(project_root=project_root)
    if not routing.routes or not axes.readable or not axes.document:
        return None
    kinds = routing.shared_kinds
    if not kinds:
        return ()
    folder = (project_root / axes.document).parent
    found: list[FocusDocument] = []
    for pattern in planning_document_globs(project_root):
        for path in sorted(project_root.glob(pattern)):
            kind = path.stem.upper()
            if kind not in kinds or path.parent != folder:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                # A focus document nobody could read is not one with no rows.
                return None
            found.append(
                FocusDocument(
                    path=_relative(path, project_root),
                    kind=kind,
                    row_cells=tuple(
                        cells[0]
                        for line in text.splitlines()
                        if (cells := cells_of(line))
                    ),
                )
            )
    return tuple(found)


def _relative(path: Path, project_root: Path) -> str:
    """*path* as the project writes it, whether the root was absolute or not."""
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _environment(
    project_root: Path, db_path: Path, axes: WorkItemAxes
) -> WaveEnvironment:
    """Measure the media the graph cannot see, here at the services edge.

    Gathered here rather than inside the planner so the application layer keeps
    taking its input as data: the decision stays runnable without git, without a
    repository and without a hook, and every one of those absences arrives as a
    ``None`` that the checks report rather than as a silent zero.
    """
    from beadloom.application.waves import WaveEnvironment, lock_sites
    from beadloom.doc_sync.git_baseline import changed_paths
    from beadloom.services.bd_seam.assumptions import lock_invocations
    from beadloom.services.bd_seam.invocations import text_invocations
    from beadloom.services.bd_seam.population import flow_artifacts

    changed = changed_paths(project_root)
    return WaveEnvironment(
        tree_changed_paths=None if changed is None else tuple(sorted(changed)),
        commit_gate=_commit_gate(project_root),
        doc_baseline_stale_pairs=_stale_pairs(db_path, project_root),
        landing_lock_sites=lock_sites(
            lock_invocations(text_invocations(flow_artifacts(project_root)))
        ),
        focus_documents=_focus_documents(project_root, axes),
        graph_input=_graph_input(project_root, db_path),
    )


def _plan_as_dict(plan: WavePlan) -> dict[str, Any]:
    """The whole plan as data — the same facts the human shape prints."""
    from beadloom.application.waves import room_for

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
        "axes": {
            "work_item": plan.axes.work_item,
            "document": plan.axes.document,
            "seed": plan.axes.seed,
            "unresolved": plan.axes.unresolved,
            "approved": sorted(plan.axes.approved),
            "reason": plan.axes.reason,
        },
        "agreements": [
            {
                "bead": a.bead_id,
                "ref": a.ref,
                "verdict": a.verdict,
                "detail": a.detail,
            }
            for a in plan.agreements
        ],
        "population": {
            "work_item": plan.population.work_item,
            "asked": list(plan.population.asked),
            "under": len(plan.population.under),
            "ready_under": list(plan.population.ready_under),
            "unasked": list(plan.population.unasked),
            "reason": plan.population.reason,
            "ready_whole": plan.population.ready_whole,
            "ready_note": plan.population.ready_note,
        },
        "running": {
            "work_item": plan.running.work_item,
            "in_progress": list(plan.running.in_progress),
            "compared": list(plan.running.compared),
            "not_compared": list(plan.running.not_compared),
            "conflicts": [
                {
                    "planned": c.planned,
                    "running": c.running,
                    "reason": c.reason,
                    "detail": c.detail,
                }
                for c in plan.running.conflicts
            ],
            "reason": plan.running.reason,
        },
        "unguarded_axes": [
            {"wave": g.wave, "beads": list(g.beads), "nodes": list(g.nodes)}
            for g in plan.unguarded_axes
        ],
        "scopes": [
            {
                "bead": scope.bead_id,
                "declared": list(scope.declared),
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
        "rooms": {
            bead: room_for(bead) for wave in plan.waves for bead in wave.beads
        },
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
    from beadloom.application.waves import (
        population_lines,
        room_for,
        running_lines,
        running_summary,
    )

    click.echo(
        f"{len(plan.waves)} wave(s) for {len(plan.scopes)} bead(s), "
        f"{len(plan.conflicts)} serialisation(s), {running_summary(plan.running)}, "
        f"{len(plan.findings)} finding(s)."
    )
    click.echo("")
    for wave in plan.waves:
        click.echo(f"Wave {wave.index}: {', '.join(wave.beads)}")
        click.echo(f"  combined-tree gate: {wave.gate_owner}")
        rooms = "; ".join(f"{bead} -> {room_for(bead)}" for bead in wave.beads)
        click.echo(f"  clean room: {rooms}")
        waiting = "; ".join(
            f"{bead} behind {', '.join(plan.running.waits_for(bead))}"
            for bead in wave.beads
            if plan.running.waits_for(bead)
        )
        if waiting:
            click.echo(f"  waits for running work: {waiting}")
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
    _render_axes(plan)
    click.echo("")
    for line in population_lines(plan.population):
        click.echo(line)
    click.echo("")
    for line in running_lines(plan.running):
        click.echo(line)
    click.echo("")
    click.echo("Shared by every wave, and NOT decided by code independence:")
    for medium in plan.shared_media:
        click.echo(f"  {medium.name} ({medium.evidence}) — {medium.statement}")
    if plan.media_checks:
        click.echo("")
        click.echo("Plan-time precondition of each shared medium:")
        for check in plan.media_checks:
            click.echo(f"  {check.medium}: {check.status} — {check.detail}")
    if plan.findings:
        click.echo("")
        for finding in plan.findings:
            click.echo(f"FINDING: {finding}", err=True)


def _render_axes(plan: WavePlan) -> None:
    """What the declarations above were held against, and what could not be.

    Printed for every plan, including one the comparison produced no finding
    for: the counts are how a reader tells a plan whose declarations agreed from
    one whose declarations nothing could be compared against (BDL-UX #232).
    """
    from beadloom.application.waves import (
        AXIS_AGREES,
        AXIS_NOT_ATTRIBUTED,
        AXIS_NOT_DERIVED,
        AXIS_SWEPT_UNDECIDED,
    )

    axes = plan.axes
    click.echo("")
    if not axes.readable:
        click.echo(f"Declared axes: NOT COMPARED — {axes.reason}")
        return
    counts = Counter(agreement.verdict for agreement in plan.agreements)
    click.echo(
        f"Declared axes ({axes.work_item}, {axes.document}): "
        f"{len(axes.approved)} node(s) approved, "
        f"{counts[AXIS_AGREES]} declared ref(s) agree, "
        f"{counts[AXIS_NOT_DERIVED]} the derivation did not reach, "
        f"{counts[AXIS_SWEPT_UNDECIDED]} swept and not ruled on, "
        f"{counts[AXIS_NOT_ATTRIBUTED]} axis row(s) name no node."
    )
    click.echo(f"  seed: {axes.seed or 'not stated'}")
    if axes.unresolved:
        click.echo(f"  the derivation could not reach: {axes.unresolved}")
    for agreement in plan.agreements:
        if agreement.verdict == AXIS_AGREES:
            continue
        subject = f"{agreement.bead_id} " if agreement.bead_id else ""
        click.echo(f"  {subject}{agreement.ref}: {agreement.verdict} — {agreement.detail}")


# beadloom:domain=application
@main.command("waves")
@click.argument("beads", nargs=-1)
@click.option(
    "--parent",
    "parent",
    default=None,
    help=(
        "Plan every bead the tracker lists as ready under this work item, "
        "instead of a list typed on the command line. The plan is compared "
        "against the beads already in progress under it either way."
    ),
)
@click.option("--json", "output_json", is_flag=True, help="Structured JSON output.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def waves(
    *,
    beads: tuple[str, ...],
    parent: str | None,
    output_json: bool,
    project: Path | None,
) -> None:
    """Decide which of these beads may run at the same time.

    Parallelism is decided from the code-level independence of the beads' node
    scopes: independent subgraphs share a wave, a shared node serialises, and a
    bead that has not declared what it occupies is serialised against everything
    rather than assumed independent.

    ``--parent`` derives the bead list from the tracker instead of taking it from
    the command line, and without it every plan still reports how many ready
    beads under the same work item it was not asked about (BDL-UX #274). Either
    way the plan is compared against the beads already in progress under that
    work item, and a conflict with one is printed apart from the plan's own
    serialisations (BDL-UX #283).
    """
    from beadloom.application.declared_scope import work_item_axes
    from beadloom.application.waves import WaveConfigError, load_overrides, plan_waves
    from beadloom.infrastructure.db import open_db
    from beadloom.services.bd_seam import BdUnavailableError

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(_EXIT_UNDECIDABLE)
    if not beads and not parent:
        click.echo(
            "Error: name the beads to plan, or the work item to derive them from "
            "with `--parent`.",
            err=True,
        )
        sys.exit(_EXIT_UNDECIDABLE)

    census = _tracker_census(project_root)
    try:
        asked = _bead_ids(beads, parent, census)
        overrides = load_overrides(project_root)
        records = _read_beads(asked, project_root)
    except (WaveConfigError, LookupError, BdUnavailableError, json.JSONDecodeError) as exc:
        click.echo(f"Error: no wave shape could be decided — {exc}", err=True)
        sys.exit(_EXIT_UNDECIDABLE)
    running = _running_records(census, asked, project_root)

    axes = work_item_axes(project_root)
    environment = _environment(project_root, db_path, axes)
    conn = open_db(db_path)
    try:
        plan = plan_waves(
            records,
            conn=conn,
            overrides=overrides,
            environment=environment,
            axes=axes,
            census=census,
            work_item=parent or "",
            running=running,
        )
    finally:
        conn.close()

    if output_json:
        click.echo(json.dumps(_plan_as_dict(plan), indent=2))
    else:
        _render(plan)
    sys.exit(_EXIT_FINDINGS if plan.findings else _EXIT_CLEAN)
