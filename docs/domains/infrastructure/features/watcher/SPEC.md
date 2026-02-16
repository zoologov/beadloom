# Watcher

File watcher for automatic reindex on file system changes.

Source: `src/beadloom/infrastructure/watcher.py`

## Specification

### Purpose

The watcher module monitors project directories for file changes and automatically triggers reindex operations. It uses the `watchfiles` library for efficient file system monitoring with configurable debounce. Graph YAML changes trigger a full reindex; all other changes (docs, code) trigger an incremental reindex. A callback mechanism supports programmatic consumers beyond the default Rich console output.

### Data Structures

#### WatchEvent (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `files_changed` | `int` | Number of relevant files in the debounced batch |
| `is_graph_change` | `bool` | `True` if any changed file is inside `.beadloom/_graph/` |
| `reindex_type` | `str` | Either `"full"` or `"incremental"` |

### Constants

#### `DEFAULT_DEBOUNCE_MS`

```python
DEFAULT_DEBOUNCE_MS = 500
```

Default debounce interval in milliseconds. Changes within this window are batched into a single reindex.

#### `_WATCH_EXTENSIONS`

Frozen set of file extensions that the watcher considers relevant:

```python
_WATCH_EXTENSIONS = frozenset({
    ".yml", ".yaml",           # graph
    ".md",                     # docs
    ".py", ".ts", ".tsx",      # code
    ".js", ".jsx",             # code
    ".go", ".rs",              # code
})
```

### Watched Directories

`_get_watch_paths(project_root)` builds the list of directories to monitor:

| Directory | Condition | Purpose |
|-----------|-----------|---------|
| `.beadloom/_graph/` | Always (if exists) | Graph YAML definitions |
| `docs/` | If exists | Markdown documentation |
| `src/` | If exists | Source code |
| `lib/` | If exists | Source code |
| `app/` | If exists | Source code |

If no directories exist, the watcher prints an error and returns immediately.

### Change Classification

Changes are classified by path to determine reindex type:

- **Graph change**: File path starts with `<project_root>/.beadloom/_graph/` (checked by `_is_graph_file`).
- **Non-graph change**: All other relevant files.

If any file in a debounced batch is a graph change, the entire batch triggers a **full reindex**. Otherwise, an **incremental reindex** is triggered.

### Filtering Logic

`_filter_relevant(changes, project_root)` applies the following filters to raw file system events:

1. **Temp file exclusion**: Skip files whose name starts with `~` or ends with `.tmp`.
2. **Extension filter**: Skip files whose suffix is not in `_WATCH_EXTENSIONS`.
3. **Relative path check**: Skip files that are not relative to `project_root`.
4. **Hidden directory exclusion**: Skip files inside hidden directories (name starts with `.`), with the explicit exception of `.beadloom`. Only directory components are checked, not the filename itself.

### Watch Loop

`watch(project_root, debounce_ms, callback)` operates as follows:

1. Resolve watch paths via `_get_watch_paths`.
2. If no paths, print error and return.
3. Print monitored paths and debounce configuration via Rich console.
4. Enter `watchfiles.watch()` loop with configured debounce.
5. For each batch:
   a. Filter to relevant changes via `_filter_relevant`.
   b. If no relevant changes remain, skip.
   c. Determine if any graph file changed.
   d. Execute full or incremental reindex accordingly.
   e. Print timestamped summary (UTC `HH:MM:SS` format) with reindex type and file count.
   f. If `callback` is provided, invoke it with a `WatchEvent`.
6. On `KeyboardInterrupt`, print stop message and return.

### CLI Interface

```
beadloom watch [--debounce MS] [--project DIR]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--debounce` | `int` | `500` | Debounce interval in milliseconds |
| `--project` | `Path` | `.` | Path to the project root |

The CLI command (`watch_cmd` in `cli.py`) performs two pre-flight checks before invoking `watch()`:
1. Verifies that `watchfiles` is importable; exits with error and install instructions if missing.
2. Verifies that the `.beadloom/_graph/` directory exists; exits with error suggesting `beadloom init` if missing.

## API

### Public Functions

```python
def watch(
    project_root: Path,
    debounce_ms: int = DEFAULT_DEBOUNCE_MS,
    callback: Callable[[WatchEvent], None] | None = None,
) -> None
```

Watch project files and auto-reindex on changes. This function blocks until interrupted by `KeyboardInterrupt`. The `callback` parameter enables programmatic consumers to receive `WatchEvent` notifications after each reindex.

### Internal Functions

```python
def _get_watch_paths(project_root: Path) -> list[Path]
```

Build the list of directories to watch. Always includes `.beadloom/_graph/` (if it exists); conditionally includes `docs/`, `src/`, `lib/`, `app/`.

```python
def _is_graph_file(path_str: str, project_root: Path) -> bool
```

Check if a file path string is inside the `.beadloom/_graph/` directory by comparing against the directory prefix string.

```python
def _filter_relevant(
    changes: Iterable[tuple[object, str]],
    project_root: Path,
) -> list[tuple[object, str]]
```

Filter raw `watchfiles` change events to only relevant changes. Each change is a `(change_type, path_str)` tuple.

```python
def _format_time() -> str
```

Return current UTC time as `HH:MM:SS` string.

### Public Classes

```python
@dataclass(frozen=True)
class WatchEvent:
    files_changed: int
    is_graph_change: bool
    reindex_type: str  # "full" | "incremental"
```

### Public Constants

```python
DEFAULT_DEBOUNCE_MS: int = 500
```

## Invariants

- Graph YAML changes (files inside `.beadloom/_graph/`) always trigger a full reindex, never incremental.
- Only one reindex executes per debounced batch. Multiple file changes within the debounce window are coalesced.
- The `callback` is invoked after the reindex completes, not before.
- `WatchEvent.reindex_type` is always either `"full"` or `"incremental"` -- no other values.
- `_filter_relevant` never passes through temp files or files with non-watched extensions.

## Constraints

- Requires the `watchfiles` optional dependency. It is not installed by default; install via `beadloom[watch]` extra (or `pip install beadloom[watch]`). The CLI command catches `ImportError` at two points (import and invocation) and provides install instructions.
- The CLI command also requires `.beadloom/_graph/` to exist; it exits with an error suggesting `beadloom init` if the directory is missing.
- `KeyboardInterrupt` is the only supported mechanism to stop the watch loop. There is no programmatic stop/cancel API.
- The watcher does not recurse into hidden directories except `.beadloom`. Files in `.git/`, `.venv/`, or other dotdirs are never watched.
- Watch paths are resolved once at startup. New directories created after the watcher starts (e.g., a new `lib/` directory) are not automatically picked up; the watcher must be restarted.
- The watcher uses `watchfiles.watch()` which internally uses the `notify` Rust crate for platform-native file system events. Behavior on network file systems may be unreliable.
- Console output uses Rich formatting. In non-TTY environments the formatting degrades gracefully but timestamps and messages are still emitted.

## Testing

Test files: `tests/test_watcher.py`

Tests should cover the following scenarios:

- **`_get_watch_paths`**: Verify correct paths are returned based on which directories exist. Verify empty list when no relevant directories exist.
- **`_is_graph_file`**: Verify `True` for paths inside `.beadloom/_graph/` and `False` for all other paths.
- **`_filter_relevant` -- temp files**: Verify files starting with `~` or ending with `.tmp` are excluded.
- **`_filter_relevant` -- extension filter**: Verify files with non-watched extensions (e.g., `.pyc`, `.log`) are excluded.
- **`_filter_relevant` -- hidden directories**: Verify files in `.git/` or `.venv/` are excluded, but files in `.beadloom/_graph/` are included.
- **`_filter_relevant` -- outside project root**: Verify files not relative to `project_root` are excluded.
- **`WatchEvent` construction**: Verify correct field values for graph changes (full reindex) and non-graph changes (incremental reindex).
- **`_format_time`**: Verify output format matches `HH:MM:SS`.
- **Watch loop integration**: Mock `watchfiles.watch` to yield controlled batches, verify correct reindex functions are called and callback receives expected `WatchEvent` values.
- **No watch paths**: Verify `watch()` returns immediately when no directories to watch exist.
