# Reindex

Full and incremental reindex pipeline for rebuilding the architecture graph database.

Source: `src/beadloom/infrastructure/reindex.py`

## Specification

### Purpose

The reindex module orchestrates the complete data pipeline that transforms YAML graph definitions, Markdown documentation, and source code into a queryable SQLite database. It provides two modes: a full reindex that drops all tables and rebuilds from scratch, and an incremental reindex that processes only changed files. The incremental path uses SHA-256 file hashes stored in a `file_index` table to detect changes, and falls back to full reindex when graph YAML files change or no prior file index exists.

### Data Structures

#### ReindexResult (dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `nodes_loaded` | `int` | `0` | Number of graph nodes loaded from YAML |
| `edges_loaded` | `int` | `0` | Number of graph edges loaded from YAML |
| `docs_indexed` | `int` | `0` | Number of Markdown documents indexed |
| `chunks_indexed` | `int` | `0` | Number of document chunks created |
| `symbols_indexed` | `int` | `0` | Number of code symbols extracted |
| `imports_indexed` | `int` | `0` | Number of code imports resolved |
| `rules_loaded` | `int` | `0` | Number of architecture rules loaded from `rules.yml` |
| `nothing_changed` | `bool` | `False` | `True` when incremental reindex detects no file changes |
| `errors` | `list[str]` | `[]` | Fatal errors encountered during reindex |
| `warnings` | `list[str]` | `[]` | Non-fatal warnings (e.g., duplicate doc references) |

### Constants

#### `_TABLES_TO_DROP`

Ordered list of tables dropped during full reindex. Order matters for foreign key constraints:

```python
_TABLES_TO_DROP = [
    "search_index", "sync_state", "code_imports", "rules",
    "code_symbols", "chunks", "docs", "edges", "nodes", "meta",
]
```

#### `_CODE_EXTENSIONS`

Frozen set of file extensions scanned for code symbols:

```python
_CODE_EXTENSIONS = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".go", ".rs",
    ".kt", ".kts", ".java", ".swift", ".m", ".mm", ".c", ".h", ".cpp", ".hpp",
})
```

#### `_EXT_TO_LANG`

Mapping of file extensions to language labels for route extraction:

```python
_EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".go": "go",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".graphql": "graphql", ".gql": "graphql", ".proto": "protobuf",
}
```

#### `_DEFAULT_SCAN_DIRS`

Default source directories when `config.yml` has no `scan_paths`:

```python
_DEFAULT_SCAN_DIRS = ("src", "lib", "app")
```

### Full Reindex Pipeline

`reindex(project_root, *, docs_dir=None)` executes the following steps in order:

| Step | Action | Module |
|------|--------|--------|
| 0 | Snapshot sync baselines (`symbols_hash` from `sync_state`) | `_snapshot_sync_baselines` |
| 1 | Drop all tables (`_TABLES_TO_DROP`) | `_drop_all_tables` |
| 2 | Create schema | `infrastructure.db.create_schema` |
| 3 | Load YAML graph from `.beadloom/_graph/*.yml` | `graph.loader.load_graph` |
| 3b | Store deep config in root node's `extra` | `onboarding.config_reader.read_deep_config` |
| 4 | Index Markdown documents from docs directory | `doc_sync.doc_indexer.index_docs` |
| 5 | Extract and index code symbols from source files | `context_oracle.code_indexer.extract_symbols` |
| 5b | Extract code imports and create `depends_on` edges | `graph.import_resolver.index_imports` |
| 5c | Load architecture rules from `.beadloom/_graph/rules.yml` | `graph.rule_engine.load_rules` |
| 5d | Map test files to source nodes and store in `nodes.extra` | `_store_test_mappings` |
| 5e | Analyze git activity and store in `nodes.extra` | `_store_git_activity` |
| 5f | Extract API routes and store in `nodes.extra` | `_extract_and_store_routes` |
| 6 | Build `sync_state` with preserved symbol hashes for drift detection | `_build_initial_sync_state` |
| 7 | Populate FTS5 search index | `context_oracle.search.populate_search_index` |
| 8 | Clear `bundle_cache`, set meta, take health snapshot | Multiple internal functions |
| 9 | Populate `file_index` for subsequent incremental runs | `_populate_file_index` |
| 10 | Store parser fingerprint | `_store_parser_fingerprint` |

### Incremental Reindex Pipeline

`incremental_reindex(project_root, *, docs_dir=None)` follows this decision tree:

1. Scan current project files and compute SHA-256 hashes.
2. Read stored file hashes from `file_index` table.
3. **Fallback to full reindex** if:
   - `file_index` is empty (first run or post-upgrade).
   - Parser fingerprint changed (new tree-sitter grammar installed).
   - Any graph YAML file changed, detected via `_graph_yaml_changed()` which directly compares hashes for files with `kind == "graph"` (belt-and-suspenders check that catches changes even when `file_index` is stale).
4. **Early return** if no files changed (sets `nothing_changed=True`, updates meta timestamp, takes health snapshot).
5. **True incremental path**:
   - Snapshot `symbols_hash` from `sync_state` before modifications for drift preservation.
   - Delete old data for changed and deleted files (from `docs`, `code_symbols`, `sync_state`).
   - Re-index changed and added files individually.
   - Re-extract API routes and update `nodes.extra`.
   - Rebuild `sync_state` from scratch (full table delete + rebuild) with preserved `symbols_hash`.
   - Rebuild FTS5 search index.
   - Clear `bundle_cache` (conservative invalidation).
   - Update `file_index` incrementally.
   - Update meta timestamps and take health snapshot.

### Configuration

Configuration is read from `.beadloom/config.yml`:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `docs_dir` | `str` | `"docs"` | Relative path to documentation directory from project root |
| `scan_paths` | `list[str]` | `["src", "lib", "app"]` | Directories to scan for source code |

### File Hashing

Files are classified into three kinds in the `file_index`:

| Kind | Source | Extensions |
|------|--------|------------|
| `"graph"` | `.beadloom/_graph/*.yml` | `.yml` |
| `"doc"` | `<docs_dir>/**/*.md` | `.md` |
| `"code"` | `<scan_paths>/**/*` | `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.vue`, `.go`, `.rs`, `.kt`, `.kts`, `.java`, `.swift`, `.m`, `.mm`, `.c`, `.h`, `.cpp`, `.hpp` |

Hashes are computed as: `hashlib.sha256(file_bytes).hexdigest()`

### Doc-to-Node Reference Map

`_build_doc_ref_map` scans YAML graph files for nodes with `docs` lists and builds a `{relative_doc_path: ref_id}` mapping. When a doc path is referenced by multiple nodes, the first reference wins and a warning is emitted.

### CLI Interface

```
beadloom reindex [--project DIR] [--docs-dir DIR] [--full]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project` | `Path` | `.` | Path to the project root |
| `--docs-dir` | `Path` | from config | Documentation directory |
| `--full` | flag | `False` | Force full rebuild (drop all tables and re-create) |

By default, performs an incremental reindex (only changed files). Use `--full` to force a complete rebuild. When `nothing_changed` is detected, displays current DB totals instead of reindex counts. Warns about missing language parsers when `symbols_indexed == 0`.

## API

### Public Functions

```python
def reindex(project_root: Path, *, docs_dir: Path | None = None) -> ReindexResult
```

Full reindex: drop all tables, recreate schema, and reload everything from disk. Returns a `ReindexResult` with counts and diagnostics.

```python
def incremental_reindex(project_root: Path, *, docs_dir: Path | None = None) -> ReindexResult
```

Incremental reindex: only process files that changed since the last reindex. Falls back to `reindex()` when graph YAML changed or no prior file index exists.

```python
def resolve_scan_paths(project_root: Path) -> list[str]
```

Resolve source scan directories from `.beadloom/config.yml`. Returns `["src", "lib", "app"]` when config is absent or has no `scan_paths` key.

### Internal Functions

```python
def _snapshot_sync_baselines(conn: sqlite3.Connection) -> dict[str, str]
```

Snapshot `symbols_hash` from `sync_state` before table drop. Returns `{ref_id: symbols_hash}` for entries with non-empty hash. Returns empty dict if the table does not exist yet (first run).

```python
def _drop_all_tables(conn: sqlite3.Connection) -> None
```

Drop all application tables to allow a clean re-create. Iterates `_TABLES_TO_DROP` in order.

```python
def _resolve_docs_dir(project_root: Path) -> Path
```

Resolve docs directory from `.beadloom/config.yml` key `docs_dir`, defaulting to `<project_root>/docs`.

```python
def _build_doc_ref_map(
    graph_dir: Path,
    project_root: Path,
    docs_dir: Path,
) -> tuple[dict[str, str], list[str]]
```

Build a mapping of `{relative_doc_path: ref_id}` from YAML graph nodes. Returns `(ref_map, warnings)`.

```python
def _index_code_files(
    project_root: Path,
    conn: sqlite3.Connection,
    seen_ref_ids: set[str],
) -> tuple[int, list[str]]
```

Scan source files, extract symbols, insert into SQLite, and create `touches_code` edges for annotated symbols. Returns `(symbols_indexed, warnings)`.

```python
def _build_initial_sync_state(
    conn: sqlite3.Connection,
    *,
    preserved_symbols: dict[str, str] | None = None,
) -> None
```

Populate `sync_state` table from docs and code_symbols with shared ref_ids. When `preserved_symbols` is provided, keeps old `symbols_hash` for drift detection; otherwise computes a fresh baseline.

```python
def _load_rules_into_db(
    rules_path: Path,
    conn: sqlite3.Connection,
    result: ReindexResult,
) -> None
```

Load architecture rules from `rules.yml` into the `rules` table. Supports `DenyRule` and `RequireRule` types.

```python
def _store_test_mappings(project_root: Path, conn: sqlite3.Connection) -> None
```

Run test mapper and merge results into `nodes.extra["tests"]`. Builds `source_dirs` from nodes with a `source` field.

```python
def _update_node_extra(conn: sqlite3.Connection, ref_id: str, key: str, value: object) -> None
```

Merge a key/value into a node's `extra` JSON column. Does nothing if `ref_id` does not exist.

```python
def _extract_and_store_routes(project_root: Path, conn: sqlite3.Connection) -> None
```

Scan source files for API routes using `_EXT_TO_LANG` for language detection and store aggregated results in `nodes.extra["routes"]`.

```python
def _store_git_activity(conn: sqlite3.Connection, project_root: Path) -> None
```

Analyze git activity via `analyze_git_activity()` and store results in `nodes.extra["activity"]` (level, commits_30d, commits_90d, last_commit, top_contributors).

```python
def _compute_file_hash(path: Path) -> str
```

Compute SHA-256 hex digest of a file's contents.

```python
def _scan_project_files(
    project_root: Path,
    docs_dir: Path,
) -> dict[str, tuple[str, str]]
```

Scan all project files and return `{relative_path: (sha256_hex, kind)}`.

```python
def _get_stored_file_index(conn: sqlite3.Connection) -> dict[str, tuple[str, str]]
```

Read file_index from DB. Returns `{path: (hash, kind)}`. Filters out sentinel rows (paths starting with `__`).

```python
def _diff_files(
    current: dict[str, tuple[str, str]],
    stored: dict[str, tuple[str, str]],
) -> tuple[set[str], set[str], set[str]]
```

Compare current vs stored file index. Returns `(changed, added, deleted)` sets of relative paths.

```python
def _graph_yaml_changed(
    current_files: dict[str, tuple[str, str]],
    stored_files: dict[str, tuple[str, str]],
) -> bool
```

Check whether any graph YAML file was added, removed, or modified by directly comparing hashes for files with `kind == "graph"`. This belt-and-suspenders check catches changes even when `file_index` is stale.

```python
def _populate_file_index(conn: sqlite3.Connection, current_files: dict[str, tuple[str, str]]) -> None
```

Replace the entire `file_index` with current files (used after full reindex).

```python
def _update_file_index(
    conn: sqlite3.Connection,
    current_files: dict[str, tuple[str, str]],
    changed: set[str],
    added: set[str],
    deleted: set[str],
) -> None
```

Incrementally update `file_index` for affected paths (used after incremental reindex).

```python
def _index_single_doc(conn, md_path, docs_dir, ref_map) -> tuple[int, int]
```

Index one doc file. Returns `(docs_count, chunks_count)`.

```python
def _index_single_code_file(conn, file_path, project_root, seen_ref_ids) -> int
```

Index one code file. Returns symbol count.

### Public Classes

```python
@dataclass
class ReindexResult:
    nodes_loaded: int = 0
    edges_loaded: int = 0
    docs_indexed: int = 0
    chunks_indexed: int = 0
    symbols_indexed: int = 0
    imports_indexed: int = 0
    rules_loaded: int = 0
    nothing_changed: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

## Invariants

- Full reindex always snapshots `symbols_hash` baselines via `_snapshot_sync_baselines()` before dropping tables, preserving drift detection state.
- Full reindex always drops ALL tables before recreating them (clean slate guarantee).
- WAL mode is enabled on every database connection opened by `open_db`.
- Foreign keys are enabled per-connection via `open_db`.
- File hashes are SHA-256 hex digests.
- Incremental reindex always rebuilds `sync_state` from scratch (full delete + rebuild) even though only some files changed, using preserved `symbols_hash` values.
- Incremental reindex always clears `bundle_cache` (conservative invalidation).
- Incremental reindex re-extracts API routes after code changes.
- `file_index` is fully replaced after full reindex and incrementally updated after incremental reindex.
- Meta key `last_reindex_at` is updated on every successful reindex (including no-change incremental runs).
- `_graph_yaml_changed()` performs a direct hash comparison on graph files by kind, independent of `_diff_files()`, to catch changes even when `file_index` is stale.

## Constraints

- Full reindex is not atomic: it drops all tables then recreates them. A crash mid-reindex leaves the database in an incomplete state. Re-running reindex resolves this.
- Incremental reindex conservatively invalidates `sync_state` and `bundle_cache` entirely, even when only a single file changed.
- Any graph YAML change (`.beadloom/_graph/*.yml`) forces a full reindex. There is no incremental graph update path.
- The `file_index` table must exist and be populated for incremental reindex to work. An empty or missing `file_index` triggers automatic fallback to full reindex.
- `_build_doc_ref_map` resolves doc path conflicts by keeping the first reference. Subsequent references to the same doc from different nodes emit warnings but do not overwrite.
- Code symbol indexing depends on `tree-sitter` being available for the target language. Missing parsers result in zero symbols for that file (not an error).

## Testing

Test files: `tests/test_reindex.py`, `tests/test_reindex_config.py`, `tests/test_reindex_tests.py`, `tests/test_reindex_activity.py`, `tests/test_reindex_routes.py`, `tests/test_cli_reindex.py`

Tests should cover the following scenarios:

- **Full reindex end-to-end**: Verify that a project with YAML graph, docs, and source code produces a populated database with correct counts in `ReindexResult`.
- **Sync baseline preservation**: Verify `_snapshot_sync_baselines()` captures `symbols_hash` before drop and that `_build_initial_sync_state()` restores them.
- **Incremental no-change**: Verify `nothing_changed=True` when no files have been modified since the last reindex.
- **Incremental doc change**: Modify a Markdown file, run incremental reindex, verify the doc is re-indexed and chunks updated.
- **Incremental code change**: Modify a source file, run incremental reindex, verify symbols are re-indexed.
- **Incremental file addition**: Add a new file, verify it appears in results.
- **Incremental file deletion**: Delete a file, verify its data is removed from the database.
- **Graph YAML change triggers full reindex**: Modify a `.beadloom/_graph/*.yml` file, verify incremental falls back to full reindex via `_graph_yaml_changed()`.
- **Parser fingerprint change triggers full reindex**: Verify that a changed parser fingerprint causes incremental to fall back to full.
- **Empty file_index triggers full reindex**: On a fresh database, verify incremental falls back to full reindex.
- **Config resolution**: Verify `resolve_scan_paths` and `_resolve_docs_dir` correctly read from `config.yml` and fall back to defaults.
- **Doc ref map conflicts**: Create YAML nodes referencing the same doc path, verify warnings are emitted and the first reference is kept.
- **`_diff_files`**: Unit test with known current/stored dicts to verify correct changed/added/deleted sets.
- **Test mapping**: Verify `_store_test_mappings()` populates `nodes.extra["tests"]`.
- **Git activity**: Verify `_store_git_activity()` populates `nodes.extra["activity"]`.
- **Route extraction**: Verify `_extract_and_store_routes()` populates `nodes.extra["routes"]`.
