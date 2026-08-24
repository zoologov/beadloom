# Reindex

Full and incremental reindex pipeline for rebuilding the architecture graph database.

Source: `src/beadloom/application/reindex/` (package; decomposed by cohesion in BDL-059 S4 into `models`, `rules_loader`, `indexing`, `enrichment`, `sync_state`, `change_detection`, `full`, `incremental`, with the package `__init__` re-exporting the stable public + back-compat surface)

## Specification

### Purpose

The reindex module orchestrates the complete data pipeline that transforms YAML graph definitions, Markdown documentation, and source code into a queryable SQLite database. It provides two modes: a full reindex that drops all tables and rebuilds from scratch, and an incremental reindex that processes only changed files. The incremental path uses SHA-256 file hashes stored in a `file_index` table to detect changes, and falls back to full reindex when graph YAML files change or no prior file index exists.

### Data Structures

#### ReindexResult (dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `nodes_loaded` | `int` | `0` | Number of graph nodes loaded from YAML (full reindex) or live-DB total (incremental) |
| `edges_loaded` | `int` | `0` | Number of graph edges loaded from YAML (full reindex) or live-DB total (incremental) |
| `docs_indexed` | `int` | `0` | Number of Markdown documents indexed |
| `chunks_indexed` | `int` | `0` | Number of document chunks created |
| `symbols_indexed` | `int` | `0` | Number of code symbols extracted (full reindex) or live-DB total (incremental) |
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
| 0 | Snapshot sync baselines (`symbols_hash`, `file_symbols_hash`, two-phase hashes and baseline PROVENANCE from `sync_state`) | `_snapshot_sync_baselines` |
| 1 | Drop all tables (`_TABLES_TO_DROP`) | `_drop_all_tables` |
| 2 | Create schema | `infrastructure.db.create_schema` |
| 3 | Load YAML graph from `.beadloom/_graph/*.yml` | `graph.loader.load_graph` |
| 3b | Store deep config in root node's `extra` | `onboarding.config_reader.read_deep_config` |
| 4 | Index Markdown documents from docs directory | `doc_sync.doc_indexer.index_docs` |
| 4b | Cache the DECLARED doc surface (every `docs:` entry, existing or not) | `read_declared_docs` / `store_declared_docs` |
| 4c | Index the TO-BE space in place, from the configured `doc_roots` | `index_to_be_space` → `doc_sync.doc_indexer.index_space_documents` |

Step 4c runs on BOTH paths. The incremental path rebuilds the TO-BE space
wholesale rather than tracking it in `file_index`: the planning tree is
small, and the two reindex paths disagreeing about what is in the index is a
defect class this project has already paid for twice (BDL-UX #142, #146).
| 5 | Extract and index code symbols from source files | `context_oracle.code_indexer.extract_symbols` |
| 5b | Extract code imports and create `depends_on` edges | `graph.import_resolver.index_imports` |
| 5c | Load architecture rules from `.beadloom/_graph/rules.yml` | `graph.rule_engine.load_rules` |
| 5d | Map test files to source nodes and store in `nodes.extra` | `_store_test_mappings` |
| 5e | Analyze git activity and store in `nodes.extra` | `_store_git_activity` |
| 5f | Extract API routes and store in `nodes.extra` | `_extract_and_store_routes` |
| 5g | Populate `file_index` — BEFORE anything derives ownership from it | `_populate_file_index` |
| 6 | Build `sync_state` with preserved symbol hashes for drift detection | `_build_initial_sync_state` |
| 7 | Populate FTS5 search index | `context_oracle.search.populate_search_index` |
| 8 | Clear `bundle_cache`, set meta, take health snapshot | Multiple internal functions |
| 9 | Store parser fingerprint | `_store_parser_fingerprint` |

Step **5g** moved ahead of step 6 in BDL-061.50, and the ordering is now load
bearing rather than incidental. A node's owned files are read from `file_index`
(so a module with no top-level symbol is still paired with its doc), and a full
reindex drops every table first — so populating `file_index` at the END left the
very first build of a fresh index with an empty table, and those pairs appeared
only on the SECOND reindex. A checker whose input arrives after it runs reports
clean because there was nothing there.

`load_graph` (step 3) also STATs each node's declared `source`: a directory
written without a trailing slash is normalised to carry one, and a `source` that
names no path on disk becomes a `ReindexResult` warning naming the `ref_id` —
see the [graph-loader component doc](../../../graph/components/graph-loader/DOC.md).

### Incremental Reindex Pipeline

`incremental_reindex(project_root, *, docs_dir=None)` follows this decision tree:

1. Scan current project files and compute SHA-256 hashes.
2. Read stored file hashes from `file_index` table.
3. **Fallback to full reindex** if:
   - `file_index` is empty (first run or post-upgrade).
   - Parser fingerprint changed (new tree-sitter grammar installed).
   - The index predates derived-edge provenance (`meta.import_edge_provenance` absent or older). One rebuild is required because a derived `depends_on` edge is otherwise indistinguishable from a graph-declared one, so refreshing the first would delete the second.
   - Any graph YAML file changed, detected via `_graph_yaml_changed()` which directly compares hashes for files with `kind == "graph"` (belt-and-suspenders check that catches changes even when `file_index` is stale).
4. **Early return** if no files changed (sets `nothing_changed=True`, updates meta timestamp, takes health snapshot).
5. **True incremental path**:
   - Snapshot `symbols_hash` from `sync_state` before modifications for drift preservation.
   - Delete old data for changed and deleted files (from `docs`, `code_symbols`, `sync_state`).
   - Re-index changed and added files individually.
   - **Re-extract imports** for the code files touched, forget those deleted, then rebuild the derived `depends_on` edge set (`reindex_file_imports`). Without this step `code_imports` — and therefore every `forbid_import`, cycle and layer rule — described the tree as it was at the last FULL rebuild, so the documented `reindex && lint` loop reported a clean boundary over a real violation (BDL-UX #142).
   - Re-extract API routes and update `nodes.extra`.
   - Rebuild `sync_state` from scratch (full table delete + rebuild) with preserved `symbols_hash`.
   - Rebuild FTS5 search index.
   - Clear `bundle_cache` (conservative invalidation).
   - Update `file_index` incrementally.
   - Update meta timestamps and take health snapshot.
   - **Backfill result counts**: Populate `nodes_loaded`, `edges_loaded`, and `symbols_indexed` with live-DB totals (not per-run deltas), matching the behavior of the `nothing_changed` path.

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

Incremental reindex: only process files that changed since the last reindex. Falls back to `reindex()` when graph YAML changed or no prior file index exists. The returned `ReindexResult` has `nodes_loaded`, `edges_loaded`, and `symbols_indexed` populated with live-DB totals (not per-run deltas), ensuring accurate reporting even when the incremental path does not touch the graph.

```python
def resolve_scan_paths(project_root: Path) -> list[str]
```

Resolve source scan directories from `.beadloom/config.yml`. Returns `["src", "lib", "app"]` when config is absent or has no `scan_paths` key.

### Internal Functions

```python
def _snapshot_sync_baselines(
    conn: sqlite3.Connection,
) -> tuple[dict[str, str], dict[tuple[str, str], _SyncPairSnapshot]]
```

Snapshot `sync_state` before the table drop. Returns `({ref_id: symbols_hash} for entries with a non-empty hash, {(doc_path, code_path): _SyncPairSnapshot})`, or two empty dicts if the table does not exist yet (first run). **Every pair is snapshotted**, not only those carrying two-phase data: the snapshot also carries `baseline_source`, and a baseline that comes back without its provenance is indistinguishable from one that was earned (BDL-UX #175). It also carries `file_symbols_hash`, the pair's own file surface. `_build_initial_sync_state` carries it rather than recomputing it, and where there is none to carry it computes one only when `_node_in_drift` says the node's carried hash still matches the tree — a file fact invented against a node ALREADY in drift would contradict it and silently win, and recomputing a carried one would re-baseline against the tree just indexed, which is how integrating a parallel wave erased the drift it brought in (BDL-UX #133 / #175). Both reindex paths call this one function, so they cannot disagree about what survives a rebuild.

```python
def _drop_all_tables(conn: sqlite3.Connection) -> None
```

Drop all application tables to allow a clean re-create. Iterates `_TABLES_TO_DROP` in order.

```python
def _resolve_docs_dir(project_root: Path) -> Path
```

Resolve docs directory from `.beadloom/config.yml` key `docs_dir`, defaulting to `<project_root>/docs`. Delegates to `infrastructure.doc_roots.resolve_docs_dir`, the single reader of the key: it was read in three places before, so a project keeping its documentation elsewhere had one reader looking where the others had not (`beadloom-mr2l.75`).

```python
def _build_doc_ref_map(
    graph_dir: Path,
    project_root: Path,
    docs_dir: Path,
) -> tuple[dict[str, str], list[str]]
```

Build a mapping of `{relative_doc_path: ref_id}` from YAML graph nodes. Returns `(ref_map, warnings)`. Built on `read_declared_docs`, so the doc→ref map and the declared surface are parsed once, from one place.

```python
def read_declared_docs(
    graph_dir: Path,
    project_root: Path,
    docs_dir: Path,
) -> list[tuple[str, str, str]]

def store_declared_docs(
    conn: sqlite3.Connection,
    declared: list[tuple[str, str, str]],
) -> None
```

Read every doc a node DECLARES in its `docs:` list as `(declared_path, doc_path, ref_id)` — *declared_path* resolved project-relative (both spellings, `docs/domains/x/README.md` and `domains/x/README.md`, land on the same file) and *doc_path* docs-dir-relative, the key of the `docs` table — and cache them in `declared_docs`. The `docs` table only holds files found on disk, so without this a deleted doc simply stopped being indexed and the gate had nothing to miss (BDL-UX #174). Both reindex paths write it; a graph-YAML change already forces a full reindex.

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
    preserved_pairs: dict[tuple[str, str], _SyncPairSnapshot] | None = None,
) -> None
```

Populate `sync_state` table from docs and code_symbols with shared ref_ids. When `preserved_symbols` is provided, keeps old `symbols_hash` for drift detection; otherwise computes a fresh baseline. `preserved_pairs` carries the two-phase hashes and, through `_baseline_provenance`, each pair's `baseline_source`:

- no snapshot -> `index_build` — this pair had no baseline before the build, so the hashes just written ARE the current tree and prove nothing on their own;
- a snapshot -> its own value, verbatim. `index_build` that survives a reindex is still `index_build`: a fabricated baseline does not become earned by being copied. A pre-provenance row (`''`) reads as `carried`, since it genuinely came from an earlier generation.

`check_sync` corroborates an `index_build` pair against git rather than reporting it fresh.

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

- Full reindex always snapshots `symbols_hash` baselines via `_snapshot_sync_baselines()` before dropping tables, preserving drift detection state. The incremental path takes the SAME snapshot (it used to re-derive one inline, which silently dropped baseline provenance).
- A baseline's provenance is never promoted by a reindex: only an attestation (`sync-update`) or an observed doc edit upgrades it.
- Full reindex always drops ALL tables before recreating them (clean slate guarantee).
- WAL mode is enabled on every database connection opened by `open_db`.
- Foreign keys are enabled per-connection via `open_db`.
- File hashes are SHA-256 hex digests.
- Incremental reindex always rebuilds `sync_state` from scratch (full delete + rebuild) even though only some files changed, using preserved `symbols_hash` values.
- Incremental reindex always clears `bundle_cache` (conservative invalidation).
- Incremental reindex re-extracts API routes after code changes.
- Incremental reindex re-extracts imports for changed/added code files and deletes those of removed files, then rebuilds the derived `depends_on` edges, so the incremental import graph is identical to the one a full rebuild produces. Measured on Beadloom's own tree (67 nodes, 1255 symbols, 1322 imports): +29 ms for one changed file, +42 ms for five, against 755 ms for a full rebuild.
- Only `depends_on` edges carrying `extra.derived = "imports"` are deleted by that refresh; an edge declared in the graph YAML is never touched.
- Incremental reindex backfills `nodes_loaded`, `edges_loaded`, and `symbols_indexed` with live-DB totals (not per-run deltas), ensuring accurate reporting even when the incremental path does not touch the graph or code symbols.
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
- **Incremental doc change**: Modify a Markdown file, run incremental reindex, verify the doc is re-indexed and chunks updated. Verify `nodes_loaded`, `edges_loaded`, and `symbols_indexed` are populated with live-DB totals.
- **Incremental code change**: Modify a source file, run incremental reindex, verify symbols are re-indexed. Verify `symbols_indexed` reflects the live-DB total.
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
