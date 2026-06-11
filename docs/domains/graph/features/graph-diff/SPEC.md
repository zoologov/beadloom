# Graph Diff

Compare the current on-disk graph YAML against the state at a given git ref.

**Source:** `src/beadloom/graph/diff.py`

---

## Specification

### Purpose

Detect structural changes (added, removed, or modified nodes and edges) between the current `.beadloom/_graph/*.yml` files on disk and their counterparts at a specified git ref. This enables change tracking across commits and supports CI workflows that gate on graph drift.

A second entry point, `compute_diff_from_snapshot`, compares a saved database snapshot against the current live database state instead of disk-vs-git.

### Entry Point

```python
def compute_diff(project_root: Path, since: str = "HEAD") -> GraphDiff
```

| Parameter      | Type   | Default  | Description                                  |
|----------------|--------|----------|----------------------------------------------|
| `project_root` | `Path` | required | Absolute path to the project root directory. |
| `since`        | `str`  | `"HEAD"` | Git ref to compare against.                  |

**Returns:** A `GraphDiff` instance containing all detected changes.

**Raises:** `ValueError` if `since` is not a valid git ref.

### Snapshot Entry Point

```python
def compute_diff_from_snapshot(conn: sqlite3.Connection, snapshot_id: int) -> GraphDiff
```

| Parameter     | Type                 | Description                                          |
|---------------|----------------------|------------------------------------------------------|
| `conn`        | `sqlite3.Connection` | Database connection with `nodes`, `edges` tables.    |
| `snapshot_id` | `int`                | ID of a saved snapshot in the `graph_snapshots` table. |

**Returns:** A `GraphDiff` instance. The `since_ref` field is set to `"snapshot:<id>"`.

**Raises:** `ValueError` if the snapshot ID is not found.

Unlike `compute_diff`, this function compares a saved snapshot (loaded via `_load_snapshot_data` from `beadloom.graph.snapshot`) with the current live state in the `nodes` and `edges` database tables. The same comparison logic applies: nodes are compared by `kind`, `summary`, `source`, and `tags`; edges by `(src, dst, kind)` set difference.

### Data Structures

All dataclasses are frozen (immutable).

#### `NodeChange`

| Field            | Type                | Description                                                  |
|------------------|---------------------|--------------------------------------------------------------|
| `ref_id`         | `str`               | Node identifier.                                             |
| `kind`           | `str`               | Node kind (e.g. `domain`, `service`).                        |
| `change_type`    | `str`               | One of `"added"`, `"removed"`, `"changed"`.                  |
| `old_summary`    | `str \| None`       | Previous summary text (only for `"changed"` type).           |
| `new_summary`    | `str \| None`       | Current summary text (only for `"changed"` type).            |
| `old_source`     | `str \| None`       | Previous `source` path (only for `"changed"` type).          |
| `new_source`     | `str \| None`       | Current `source` path (only for `"changed"` type).           |
| `old_tags`       | `tuple[str, ...]`   | Previous sorted tags (defaults to `()`).                     |
| `new_tags`       | `tuple[str, ...]`   | Current sorted tags (defaults to `()`).                      |
| `symbols_added`  | `int`               | Number of code symbols added (defaults to `0`).              |
| `symbols_removed`| `int`               | Number of code symbols removed (defaults to `0`).            |

#### `EdgeChange`

| Field         | Type  | Description                                 |
|---------------|-------|---------------------------------------------|
| `src`         | `str` | Source node ref_id.                         |
| `dst`         | `str` | Destination node ref_id.                    |
| `kind`        | `str` | Edge kind (e.g. `depends_on`, `part_of`).   |
| `change_type` | `str` | One of `"added"`, `"removed"`.              |

#### `GraphDiff`

| Field       | Type                    | Description                           |
|-------------|-------------------------|---------------------------------------|
| `since_ref` | `str`                   | The git ref compared against (or `"snapshot:<id>"` for snapshot diffs). |
| `nodes`     | `tuple[NodeChange, ...]`| All detected node changes.            |
| `edges`     | `tuple[EdgeChange, ...]`| All detected edge changes.            |

**Property:** `has_changes -> bool` -- `True` when `nodes` or `edges` is non-empty.

### Algorithm

1. **Validate git ref.** Call `_validate_git_ref` which runs `git rev-parse --verify <ref>`. Raise `ValueError` on failure.
2. **Read current state from disk.** Glob `*.yml` files in `<project_root>/.beadloom/_graph/`. For each file, parse YAML content via `_parse_yaml_content` to extract a `nodes_dict` (keyed by `ref_id`) and an `edges_set` of `(src, dst, kind)` tuples. Merge all files into combined `current_nodes` and `current_edges`.
3. **Read previous state from git ref.** Call `_list_graph_files_at_ref` (runs `git ls-tree -r --name-only <ref> .beadloom/_graph/`) to enumerate files. For each, call `_read_yaml_at_ref` (runs `git show <ref>:<path>`) and parse the content. Merge into `prev_nodes` and `prev_edges`.
4. **Compare nodes.** Union all `ref_id` keys from both maps. Classify each:
   - Present in current only: `"added"`.
   - Present in previous only: `"removed"`.
   - Present in both with different `kind`, `summary`, `source`, or `tags`: `"changed"` (captures `old_summary`/`new_summary`, `old_source`/`new_source`, `old_tags`/`new_tags`).
5. **Compare edges.** Set difference on `(src, dst, kind)` tuples:
   - `current_edges - prev_edges` = added edges.
   - `prev_edges - current_edges` = removed edges.
6. **Assemble result.** Node changes sorted by `ref_id`, edge changes sorted by `(src, dst, kind)`.

### Internal Helpers

| Function                   | Git Command                                     | Purpose                                         |
|----------------------------|--------------------------------------------------|-------------------------------------------------|
| `_validate_git_ref`        | `git rev-parse --verify <ref>`                   | Verify the ref exists. Returns `bool`.          |
| `_read_yaml_at_ref`        | `git show <ref>:<path>`                          | Read file content at ref; returns `None` if absent. |
| `_list_graph_files_at_ref` | `git ls-tree -r --name-only <ref> .beadloom/_graph/` | List `.yml` files at the ref. Returns `list[str]` of relative paths. |
| `_parse_yaml_content`      | (none)                                           | Parse YAML string into `(nodes_dict, edges_set)` where `nodes_dict: dict[str, dict[str, object]]` (keys: `kind`, `summary`, `source`, `tags`) and `edges_set: set[tuple[str, str, str]]`. |

### Rendering and Serialization

```python
def render_diff(diff: GraphDiff, console: Console) -> None
```

Renders a Rich-formatted diff to the console:
- Header: `"Graph diff (since {ref}):"` (bold).
- No-change case: prints `"No graph changes since {ref}."`.
- Nodes section: `+` (green) for added, `~` (yellow) for changed, `-` (red) for removed. Each entry shows `ref_id (kind)`. Changed nodes additionally display:
  - Old summary (dim) and new summary (bold) when summaries differ.
  - Source path change: `"source: <old> → <new>"` when source paths differ.
  - Tags change: `"tags: <old_list> → <new_list>"` when tags differ.
  - Symbols change: `"symbols: +<N> -<N>"` when `symbols_added` or `symbols_removed` are non-zero.
- Edges section: `+` (green) for added, `-` (red) for removed, formatted as `src --[kind]--> dst`.
- Summary line: `"{N} added, {N} changed, {N} removed nodes; {N} added, {N} removed edges"`.

```python
def diff_to_dict(diff: GraphDiff) -> dict[str, object]
```

Serializes a `GraphDiff` to a JSON-compatible dictionary. Produces a dict with keys: `since_ref`, `has_changes`, `nodes` (list of `asdict(NodeChange)`), `edges` (list of `asdict(EdgeChange)`).

---

## API

### Public Functions

```python
def compute_diff(project_root: Path, since: str = "HEAD") -> GraphDiff: ...
def compute_diff_from_snapshot(conn: sqlite3.Connection, snapshot_id: int) -> GraphDiff: ...
def render_diff(diff: GraphDiff, console: Console) -> None: ...
def diff_to_dict(diff: GraphDiff) -> dict[str, object]: ...
```

All functions are defined in `src/beadloom/graph/diff.py`. `Console` is from `rich.console`.

### Public Classes

```python
@dataclass(frozen=True)
class NodeChange:
    ref_id: str
    kind: str
    change_type: str          # "added" | "removed" | "changed"
    old_summary: str | None = None  # only for "changed"
    new_summary: str | None = None  # only for "changed"
    old_source: str | None = None
    new_source: str | None = None
    old_tags: tuple[str, ...] = ()
    new_tags: tuple[str, ...] = ()
    symbols_added: int = 0
    symbols_removed: int = 0

@dataclass(frozen=True)
class EdgeChange:
    src: str
    dst: str
    kind: str
    change_type: str          # "added" | "removed"

@dataclass(frozen=True)
class GraphDiff:
    since_ref: str
    nodes: tuple[NodeChange, ...]
    edges: tuple[EdgeChange, ...]

    @property
    def has_changes(self) -> bool: ...
```

### CLI

```
beadloom diff [--since REF] [--json] [--project DIR]
```

| Flag       | Default  | Description                                |
|------------|----------|--------------------------------------------|
| `--since`  | `HEAD`   | Git ref to compare against.                |
| `--json`   | `False`  | Output as JSON (via `diff_to_dict`).       |
| `--project`| Current directory | Project root directory.            |

**Exit codes:**

| Code | Meaning              |
|------|----------------------|
| `0`  | No changes detected. |
| `1`  | Changes detected, or graph directory not found, or invalid git ref. |

---

## Invariants

- `GraphDiff.nodes` and `GraphDiff.edges` are immutable tuples.
- Node changes are sorted lexicographically by `ref_id`.
- Edge changes are sorted lexicographically by `(src, dst, kind)`.
- `has_changes` returns `True` if and only if at least one `NodeChange` or `EdgeChange` exists.
- `diff_to_dict` output is deterministic for a given `GraphDiff` input.
- `NodeChange.old_tags` and `NodeChange.new_tags` are always sorted tuples.

---

## Constraints

- Requires a git repository at `project_root` (all git commands run with `cwd=project_root`).
- Default comparison is against `HEAD`.
- Raises `ValueError` on an invalid git ref (determined by `git rev-parse --verify`).
- Only considers `.yml` files inside `.beadloom/_graph/`.
- Files that do not exist at the given ref are treated as absent (contributing zero nodes and edges for that ref).
- YAML files are parsed with `yaml.safe_load`; `None` content is treated as empty.
- `compute_diff_from_snapshot` requires a database with `nodes`, `edges`, and `graph_snapshots` tables.

---

## Testing

Test files: `tests/test_diff.py`, `tests/test_diff_enhanced.py`, `tests/test_cli_diff.py`, `tests/test_symbol_diff_polish.py`, `tests/test_snapshot.py`

### Unit Tests

- **No changes.** Create identical YAML at HEAD and on disk. Assert `has_changes is False`, empty `nodes` and `edges`, exit code `0`.
- **Node added.** Add a new node YAML on disk not present at HEAD. Assert a single `NodeChange` with `change_type="added"`.
- **Node removed.** Remove a node YAML from disk that exists at HEAD. Assert `change_type="removed"`.
- **Node changed.** Modify `summary`, `kind`, `source`, or `tags` of a node between HEAD and disk. Assert `change_type="changed"` with correct `old_summary`/`new_summary`, `old_source`/`new_source`, and `old_tags`/`new_tags`.
- **Edge added/removed.** Add or remove edges between refs. Assert corresponding `EdgeChange` entries with correct `change_type`.
- **Invalid ref.** Pass a non-existent ref string. Assert `ValueError` is raised.
- **Empty graph directory.** Both current and previous graphs are empty. Assert `has_changes is False`.

### Serialization Tests

- **`diff_to_dict` round-trip.** Verify the dict contains keys `since_ref`, `has_changes`, `nodes`, `edges` and that nested entries match `dataclasses.asdict` output.

### Rendering Tests

- **Rich output.** Capture console output with `Console(file=StringIO())`. Assert presence of `+`, `~`, `-` markers and summary line with correct counts.
- **No-change output.** Assert the "No graph changes" message is printed.
- **Changed-node rendering.** Assert that source path changes, tag changes, and symbol counts are rendered when present.

### Integration Tests

- **Git-backed comparison.** Create a temporary git repo, commit graph YAML, modify on disk, run `compute_diff`. Assert all change types are correctly detected against actual git state.
