"""Tests for beadloom.watcher module (unit tests for helpers)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from beadloom.watcher import (
    DEFAULT_DEBOUNCE_MS,
    WatchEvent,
    _filter_relevant,
    _format_time,
    _get_watch_paths,
    _is_graph_file,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestGetWatchPathsBasic:
    def test_get_watch_paths_basic(self, tmp_path: Path) -> None:
        """Returns only graph dir when no other dirs exist."""
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)

        paths = _get_watch_paths(tmp_path)
        assert len(paths) == 1
        assert paths[0] == graph_dir


class TestGetWatchPathsWithDocs:
    def test_get_watch_paths_with_docs(self, tmp_path: Path) -> None:
        """Returns graph dir + docs when docs/ exists."""
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        paths = _get_watch_paths(tmp_path)
        assert len(paths) == 2
        assert graph_dir in paths
        assert docs_dir in paths


class TestGetWatchPathsWithSrc:
    def test_get_watch_paths_with_src(self, tmp_path: Path) -> None:
        """Returns graph dir + src when src/ exists."""
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        paths = _get_watch_paths(tmp_path)
        assert len(paths) == 2
        assert graph_dir in paths
        assert src_dir in paths


class TestGetWatchPathsAllDirs:
    def test_get_watch_paths_all_dirs(self, tmp_path: Path) -> None:
        """Returns all directories when all exist."""
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        app_dir = tmp_path / "app"
        app_dir.mkdir()

        paths = _get_watch_paths(tmp_path)
        assert len(paths) == 5
        assert graph_dir in paths
        assert docs_dir in paths
        assert src_dir in paths
        assert lib_dir in paths
        assert app_dir in paths


class TestIsGraphFileTrue:
    def test_is_graph_file_true(self, tmp_path: Path) -> None:
        """Path inside .beadloom/_graph/ is recognized as graph file."""
        path_str = str(tmp_path / ".beadloom" / "_graph" / "nodes.yml")
        assert _is_graph_file(path_str, tmp_path) is True


class TestIsGraphFileFalse:
    def test_is_graph_file_false(self, tmp_path: Path) -> None:
        """Path outside .beadloom/_graph/ is not a graph file."""
        path_str = str(tmp_path / "src" / "main.py")
        assert _is_graph_file(path_str, tmp_path) is False


class TestFilterRelevantPyFile:
    def test_filter_relevant_py_file(self, tmp_path: Path) -> None:
        """.py file passes through the filter."""
        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / "src" / "main.py")),
        }
        result = _filter_relevant(changes, tmp_path)
        assert len(result) == 1


class TestFilterRelevantYmlFile:
    def test_filter_relevant_yml_file(self, tmp_path: Path) -> None:
        """.yml file passes through the filter."""
        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / ".beadloom" / "_graph" / "nodes.yml")),
        }
        result = _filter_relevant(changes, tmp_path)
        assert len(result) == 1


class TestFilterRelevantIgnoresHidden:
    def test_filter_relevant_ignores_hidden(self, tmp_path: Path) -> None:
        """Hidden directories (starting with .) are excluded, except .beadloom."""
        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / ".git" / "config.py")),
            (1, str(tmp_path / ".vscode" / "settings.py")),
        }
        result = _filter_relevant(changes, tmp_path)
        assert len(result) == 0


class TestFilterRelevantIgnoresTemp:
    def test_filter_relevant_ignores_temp(self, tmp_path: Path) -> None:
        """Temp files (starting with ~ or ending with .tmp) are excluded."""
        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / "~lockfile.py")),
            (1, str(tmp_path / "draft.tmp")),
        }
        result = _filter_relevant(changes, tmp_path)
        assert len(result) == 0


class TestFilterRelevantIgnoresUnknownExt:
    def test_filter_relevant_ignores_unknown_ext(self, tmp_path: Path) -> None:
        """.png, .exe files are excluded."""
        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / "image.png")),
            (1, str(tmp_path / "app.exe")),
        }
        result = _filter_relevant(changes, tmp_path)
        assert len(result) == 0


class TestFilterRelevantAllowsBeadloomDir:
    def test_filter_relevant_allows_beadloom_dir(self, tmp_path: Path) -> None:
        """.beadloom/_graph/test.yml passes through despite being in a dot-dir."""
        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / ".beadloom" / "_graph" / "test.yml")),
        }
        result = _filter_relevant(changes, tmp_path)
        assert len(result) == 1


class TestFormatTime:
    def test_format_time(self) -> None:
        """Returns a string matching HH:MM:SS pattern."""
        result = _format_time()
        assert re.match(r"^\d{2}:\d{2}:\d{2}$", result)


class TestWatchEventDataclass:
    def test_watch_event_dataclass(self) -> None:
        """WatchEvent fields are accessible and correctly typed."""
        event = WatchEvent(files_changed=3, is_graph_change=True, reindex_type="full")
        assert event.files_changed == 3
        assert event.is_graph_change is True
        assert event.reindex_type == "full"

    def test_watch_event_frozen(self) -> None:
        """WatchEvent is frozen (immutable)."""
        event = WatchEvent(files_changed=1, is_graph_change=False, reindex_type="incremental")
        try:
            event.files_changed = 99  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised, "WatchEvent should be frozen"


class TestDefaultDebounceMs:
    def test_default_debounce_ms(self) -> None:
        """DEFAULT_DEBOUNCE_MS is 500."""
        assert DEFAULT_DEBOUNCE_MS == 500
