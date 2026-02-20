# beadloom:service=tui
"""File watcher Worker for the TUI — detects source changes and posts ReindexNeeded.

Uses ``watchfiles`` (optional) to monitor source directories discovered from the
graph.  Falls back gracefully when the library is not installed.
"""

from __future__ import annotations

import importlib.util
import logging
import threading
from pathlib import Path as _Path
from typing import TYPE_CHECKING

from textual.message import Message
from textual.worker import Worker, WorkerCancelled, get_current_worker

if TYPE_CHECKING:
    from pathlib import Path

    from textual.app import App

logger = logging.getLogger(__name__)

# Default debounce window (milliseconds) — matches infrastructure watcher.
DEFAULT_DEBOUNCE_MS: int = 500

# Extensions we care about (reused from infrastructure.watcher concept).
_WATCH_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".yml",
        ".yaml",
        ".md",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".rs",
    }
)


# ---------------------------------------------------------------------------
# Custom messages
# ---------------------------------------------------------------------------


class ReindexNeeded(Message):
    """Posted when source files change and reindex is recommended."""

    def __init__(self, changed_paths: list[str]) -> None:
        self.changed_paths = changed_paths
        super().__init__()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_watchfiles() -> bool:
    """Return True if the ``watchfiles`` package is importable."""
    return importlib.util.find_spec("watchfiles") is not None


def _collect_watch_dirs(
    project_root: Path,
    source_paths: list[str],
) -> list[Path]:
    """Build a de-duplicated list of directories to watch.

    Resolves each *source_paths* entry relative to *project_root*, keeps only
    those that actually exist, and always includes the graph YAML directory.
    """
    dirs: dict[str, Path] = {}

    # Always watch the graph dir when it exists.
    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        dirs[str(graph_dir)] = graph_dir

    for src in source_paths:
        candidate = project_root / src
        if candidate.is_dir():
            dirs[str(candidate)] = candidate
        elif candidate.is_file():
            parent = candidate.parent
            dirs[str(parent)] = parent

    return list(dirs.values())


def _filter_paths(
    raw_changes: set[tuple[object, str]],
    project_root: Path,
) -> list[str]:
    """Keep only changed paths with watched extensions, skipping hidden dirs."""
    result: list[str] = []
    for _change_type, path_str in raw_changes:
        p = _Path(path_str)
        if p.name.startswith("~") or p.name.endswith(".tmp"):
            continue
        if p.suffix not in _WATCH_EXTENSIONS:
            continue
        try:
            rel = p.relative_to(project_root)
        except ValueError:
            continue
        skip = False
        for part in rel.parts[:-1]:
            if part.startswith(".") and part != ".beadloom":
                skip = True
                break
        if skip:
            continue
        result.append(path_str)
    return result


# ---------------------------------------------------------------------------
# Worker entry-point (run in a thread via Textual Worker)
# ---------------------------------------------------------------------------


def _watch_loop(
    app: App[None],
    project_root: Path,
    watch_dirs: list[Path],
    debounce_ms: int,
    stop_event: threading.Event,
) -> None:
    """Blocking watch loop executed inside a Textual Worker thread.

    Posts :class:`ReindexNeeded` to *app* whenever relevant files change.
    Exits cleanly when *stop_event* is set or the worker is cancelled.
    """
    from watchfiles import watch

    worker = get_current_worker()

    try:
        for batch in watch(
            *watch_dirs,
            debounce=debounce_ms,
            step=100,
            stop_event=stop_event,
        ):
            if worker.is_cancelled or stop_event.is_set():
                return

            # watchfiles returns set[tuple[Change, str]]; Change is an enum subclass
            # of int, so we cast to satisfy our generic object-based signature.
            changed = _filter_paths(batch, project_root)  # type: ignore[arg-type]
            if not changed:
                continue

            logger.info(
                "File watcher detected %d change(s): %s",
                len(changed),
                ", ".join(changed[:5]),
            )
            try:
                app.post_message(ReindexNeeded(changed))
            except RuntimeError:
                logger.debug(
                    "File watcher: RuntimeError posting message (interpreter shutdown)"
                )
                return
    except WorkerCancelled:
        return


# ---------------------------------------------------------------------------
# Public API — called from BeadloomApp
# ---------------------------------------------------------------------------


def start_file_watcher(
    app: App[None],
    project_root: Path,
    source_paths: list[str],
    *,
    debounce_ms: int = DEFAULT_DEBOUNCE_MS,
) -> Worker[None] | None:
    """Start the file-watcher Worker, or return ``None`` if watchfiles is missing.

    Parameters
    ----------
    app:
        The Textual application instance (used to post messages and run workers).
    project_root:
        Project root directory.
    source_paths:
        List of source path strings (relative to *project_root*) obtained from
        ``GraphDataProvider``.
    debounce_ms:
        Debounce window in milliseconds.

    Returns
    -------
    The ``Worker`` instance if started, or ``None`` on graceful fallback.
    """
    if not _has_watchfiles():
        logger.warning(
            "watchfiles is not installed — file watcher disabled. "
            "Install with: pip install beadloom[tui]"
        )
        return None

    watch_dirs = _collect_watch_dirs(project_root, source_paths)
    if not watch_dirs:
        logger.warning("No directories to watch — file watcher disabled.")
        return None

    logger.info(
        "Starting file watcher on %d dir(s): %s",
        len(watch_dirs),
        ", ".join(str(d) for d in watch_dirs),
    )

    stop_event = threading.Event()

    def _run() -> None:
        _watch_loop(app, project_root, watch_dirs, debounce_ms, stop_event)

    worker: Worker[None] = app.run_worker(
        _run,
        name="file-watcher",
        exclusive=True,
        thread=True,
    )
    # Attach stop_event to worker so app can signal clean shutdown
    worker._stop_event = stop_event  # type: ignore[attr-defined]
    return worker
