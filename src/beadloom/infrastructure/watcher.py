"""File watcher: auto-reindex on file changes."""

# beadloom:domain=infrastructure

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

DEFAULT_DEBOUNCE_MS = 500

_WATCH_EXTENSIONS = frozenset(
    {
        ".yml",
        ".yaml",  # graph
        ".md",  # docs
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",  # code
        ".go",
        ".rs",  # code
    }
)


def _get_watch_paths(project_root: Path) -> list[Path]:
    """Build list of directories to watch.

    Always includes the graph dir; optionally includes docs, src, lib, app
    if they exist.
    """
    paths: list[Path] = []

    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        paths.append(graph_dir)

    for name in ("docs", "src", "lib", "app"):
        candidate = project_root / name
        if candidate.is_dir():
            paths.append(candidate)

    return paths


def _is_graph_file(path_str: str, project_root: Path) -> bool:
    """Check if *path_str* is inside the ``.beadloom/_graph/`` directory."""
    graph_prefix = str(project_root / ".beadloom" / "_graph") + "/"
    return path_str.startswith(graph_prefix)


def _filter_relevant(
    changes: Iterable[tuple[object, str]],
    project_root: Path,
) -> list[tuple[object, str]]:
    """Keep only changes with watched extensions, ignoring hidden/temp files."""
    result: list[tuple[object, str]] = []

    for change_type, path_str in changes:
        p = Path(path_str)

        # Ignore temp files (name starts with ~ or ends with .tmp).
        if p.name.startswith("~") or p.name.endswith(".tmp"):
            continue

        # Ignore files without a watched extension.
        if p.suffix not in _WATCH_EXTENSIONS:
            continue

        # Compute the relative path from project root to check for hidden dirs.
        try:
            rel = p.relative_to(project_root)
        except ValueError:
            # Path is not relative to project root -- skip.
            continue

        # Check for hidden directories in the relative path, but allow .beadloom.
        skip = False
        for part in rel.parts[:-1]:  # check directory parts, not filename
            if part.startswith(".") and part != ".beadloom":
                skip = True
                break
        if skip:
            continue

        result.append((change_type, path_str))

    return result


def _format_time() -> str:
    """Return current time as ``HH:MM:SS`` string."""
    return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


@dataclass(frozen=True)
class WatchEvent:
    """A single watch event after filtering and debounce."""

    files_changed: int
    is_graph_change: bool
    reindex_type: str  # "full" | "incremental"


def watch(
    project_root: Path,
    debounce_ms: int = DEFAULT_DEBOUNCE_MS,
    callback: Callable[[WatchEvent], None] | None = None,
) -> None:
    """Watch project files and auto-reindex on changes.

    Monitors graph YAML, documentation, and source files.
    Graph changes trigger full reindex; other changes trigger incremental.

    Requires ``watchfiles`` (optional dependency).
    """
    from rich.console import Console
    from watchfiles import watch as fs_watch

    console = Console()

    watch_paths = _get_watch_paths(project_root)
    if not watch_paths:
        console.print("[red]No directories to watch.[/red]")
        return

    path_names = ", ".join(str(p.relative_to(project_root)) for p in watch_paths)
    console.print(f"[bold blue]Watching:[/bold blue] {path_names}")
    console.print(f"[dim]Debounce: {debounce_ms}ms  |  Press Ctrl+C to stop[/dim]")
    console.print()

    try:
        for batch in fs_watch(
            *watch_paths,
            debounce=debounce_ms,
        ):
            relevant = _filter_relevant(batch, project_root)
            if not relevant:
                continue

            graph_changed = any(_is_graph_file(path_str, project_root) for _, path_str in relevant)

            if graph_changed:
                from beadloom.infrastructure.reindex import reindex as do_reindex

                do_reindex(project_root)
                reindex_type = "full"
            else:
                from beadloom.infrastructure.reindex import incremental_reindex

                incremental_reindex(project_root)
                reindex_type = "incremental"

            timestamp = _format_time()
            console.print(
                f"[dim]{timestamp}[/dim] "
                f"[green]{reindex_type} reindex[/green] "
                f"({len(relevant)} file{'s' if len(relevant) != 1 else ''} changed)"
            )

            if callback is not None:
                event = WatchEvent(
                    files_changed=len(relevant),
                    is_graph_change=graph_changed,
                    reindex_type=reindex_type,
                )
                callback(event)

    except KeyboardInterrupt:
        console.print("\n[yellow]Watch stopped.[/yellow]")
