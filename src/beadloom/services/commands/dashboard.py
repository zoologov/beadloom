"""Interactive dashboard + file-watch commands: tui, ui, watch."""
# beadloom:component=cli-commands

from __future__ import annotations

import sys
from pathlib import Path

import click

from beadloom.services.commands._root import main


# beadloom:domain=tui
def _launch_tui(*, project: Path | None, no_watch: bool) -> None:
    """Shared implementation for tui/ui commands."""
    try:
        from beadloom.tui import launch
    except ImportError:
        click.echo(
            "Error: TUI requires 'textual'. Install with: pip install beadloom[tui]",
            err=True,
        )
        sys.exit(1)

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    try:
        launch(db_path=db_path, project_root=project_root, no_watch=no_watch)
    except ImportError:
        click.echo(
            "Error: TUI requires 'textual'. Install with: pip install beadloom[tui]",
            err=True,
        )
        sys.exit(1)


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--no-watch",
    is_flag=True,
    default=False,
    help="Disable file watcher.",
)
def tui(*, project: Path | None, no_watch: bool) -> None:
    """Launch interactive terminal dashboard.

    Multi-screen architecture workstation with graph explorer,
    debt gauge, lint panel, doc status, and keyboard actions.
    Requires textual: pip install beadloom[tui]
    """
    _launch_tui(project=project, no_watch=no_watch)


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--no-watch",
    is_flag=True,
    default=False,
    help="Disable file watcher.",
)
def ui(*, project: Path | None, no_watch: bool) -> None:
    """Launch interactive terminal dashboard (alias for 'tui').

    Browse domains, nodes, edges, and documentation coverage.
    Requires textual: pip install beadloom[tui]
    """
    _launch_tui(project=project, no_watch=no_watch)


# beadloom:domain=watcher
@main.command("watch")
@click.option("--debounce", default=500, type=int, help="Debounce delay in ms.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def watch_cmd(*, debounce: int, project: Path | None) -> None:
    """Watch files and auto-reindex on changes.

    Monitors graph YAML, documentation, and source files.
    Graph changes trigger full reindex; other changes trigger incremental.
    Requires watchfiles: pip install beadloom[watch]
    """
    try:
        from beadloom.application.watcher import watch
    except ImportError:
        click.echo(
            "Error: watch requires 'watchfiles'. Install with: pip install beadloom[watch]",
            err=True,
        )
        sys.exit(1)

    project_root = project or Path.cwd()
    graph_dir = project_root / ".beadloom" / "_graph"

    if not graph_dir.is_dir():
        click.echo("Error: graph directory not found. Run `beadloom init` first.", err=True)
        sys.exit(1)

    try:
        watch(project_root, debounce_ms=debounce)
    except ImportError:
        click.echo(
            "Error: watch requires 'watchfiles'. Install with: pip install beadloom[watch]",
            err=True,
        )
        sys.exit(1)
