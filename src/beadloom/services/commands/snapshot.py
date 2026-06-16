"""The ``snapshot`` command group: save, list, compare."""
# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from beadloom.services.commands._root import main


# beadloom:domain=graph-snapshot
@main.group()
def snapshot() -> None:
    """Architecture snapshot management."""


@snapshot.command("save")
@click.option("--label", default=None, help="Optional label for the snapshot (e.g. v1.6.0).")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def snapshot_save(*, label: str | None, project: Path | None) -> None:
    """Save the current graph state as a snapshot."""
    from beadloom.graph.snapshot import save_snapshot
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    snap_id = save_snapshot(conn, label=label)
    conn.close()

    label_str = f" ({label})" if label else ""
    click.echo(f"Snapshot #{snap_id} saved{label_str}.")


@snapshot.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def snapshot_list(*, output_json: bool, project: Path | None) -> None:
    """List all saved architecture snapshots."""
    from beadloom.graph.snapshot import list_snapshots
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    snapshots = list_snapshots(conn)
    conn.close()

    if not snapshots:
        click.echo("No snapshots found.")
        return

    if output_json:
        data = [
            {
                "id": s.id,
                "label": s.label,
                "created_at": s.created_at,
                "node_count": s.node_count,
                "edge_count": s.edge_count,
                "symbols_count": s.symbols_count,
            }
            for s in snapshots
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for s in snapshots:
            label_str = f" [{s.label}]" if s.label else ""
            click.echo(
                f"  #{s.id}{label_str}  {s.created_at}  "
                f"nodes={s.node_count} edges={s.edge_count} symbols={s.symbols_count}"
            )


@snapshot.command("compare")
@click.argument("old_id", type=int)
@click.argument("new_id", type=int)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def snapshot_compare(
    old_id: int,
    new_id: int,
    *,
    output_json: bool,
    project: Path | None,
) -> None:
    """Compare two architecture snapshots."""
    from beadloom.graph.snapshot import compare_snapshots
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    try:
        diff = compare_snapshots(conn, old_id, new_id)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        conn.close()
        sys.exit(1)

    conn.close()

    if output_json:
        data = {
            "old_id": diff.old_id,
            "new_id": diff.new_id,
            "has_changes": diff.has_changes,
            "added_nodes": diff.added_nodes,
            "removed_nodes": diff.removed_nodes,
            "changed_nodes": diff.changed_nodes,
            "added_edges": diff.added_edges,
            "removed_edges": diff.removed_edges,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not diff.has_changes:
        click.echo(f"No changes between snapshot #{old_id} and #{new_id}.")
        return

    click.echo(f"Snapshot diff: #{old_id} -> #{new_id}")
    click.echo()

    if diff.added_nodes:
        click.echo("Added nodes:")
        for n in diff.added_nodes:
            click.echo(f"  + {n['ref_id']} ({n.get('kind', '')}): {n.get('summary', '')}")

    if diff.removed_nodes:
        click.echo("Removed nodes:")
        for n in diff.removed_nodes:
            click.echo(f"  - {n['ref_id']} ({n.get('kind', '')}): {n.get('summary', '')}")

    if diff.changed_nodes:
        click.echo("Changed nodes:")
        for n in diff.changed_nodes:
            click.echo(f"  ~ {n['ref_id']} ({n.get('kind', '')})")
            click.echo(f"    was: {n.get('old_summary', '')}")
            click.echo(f"    now: {n.get('new_summary', '')}")

    if diff.added_edges:
        click.echo("Added edges:")
        for e in diff.added_edges:
            click.echo(f"  + {e['src_ref_id']} --[{e['kind']}]--> {e['dst_ref_id']}")

    if diff.removed_edges:
        click.echo("Removed edges:")
        for e in diff.removed_edges:
            click.echo(f"  - {e['src_ref_id']} --[{e['kind']}]--> {e['dst_ref_id']}")
