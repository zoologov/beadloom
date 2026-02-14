# Import Resolver

Import analysis and `depends_on` edge generation via tree-sitter-based source code parsing.

**Source:** `src/beadloom/graph/import_resolver.py`

---

## Specification

### Purpose

Extract import statements from source files using tree-sitter grammars, resolve each import to an architecture graph node, store the results in the `code_imports` table, and generate `depends_on` edges between graph nodes. This forms the foundation for automated dependency detection and architectural rule enforcement.

### Supported Languages

| Language              | File Extensions            | Import Syntax Handled                      | Skipped Imports                                 |
|-----------------------|----------------------------|--------------------------------------------|-------------------------------------------------|
| Python                | `.py`                      | `import X`, `from X import Y`              | Relative imports (`from . import`, `from ..`)   |
| TypeScript/JavaScript | `.ts`, `.tsx`, `.js`, `.jsx`| `import ... from 'path'`                   | Relative (`./`, `../`), npm packages            |
| Go                    | `.go`                      | `import "path"`, `import (...)` blocks     | Standard library (no `/` in path)               |
| Rust                  | `.rs`                      | `use path::to::module`                     | Built-in crates (`std`, `core`, `alloc`), `self`, `super` |

### Constants

```python
_RUST_BUILTIN_CRATES: frozenset[str] = frozenset({"std", "core", "alloc"})

_TS_ALIAS_MAP: dict[str, str] = {
    "@/": "src/",
    "~/": "src/",
}
```

### Data Structures

#### `ImportInfo`

Frozen dataclass representing a single extracted import.

| Field             | Type           | Description                                      |
|-------------------|----------------|--------------------------------------------------|
| `file_path`       | `str`          | Path to the source file containing the import.   |
| `line_number`     | `int`          | 1-based line number of the import statement.     |
| `import_path`     | `str`          | Raw import path (e.g. `"beadloom.auth.tokens"`). |
| `resolved_ref_id` | `str \| None`  | Resolved graph node `ref_id`, or `None`.         |

### Import Extraction

```python
def extract_imports(file_path: Path) -> list[ImportInfo]
```

1. Detect language via file extension using `get_lang_config(suffix)`. Return empty list if unsupported.
2. Read file content as UTF-8. Return empty list on `OSError`, `UnicodeDecodeError`, or empty content.
3. Parse content with `tree_sitter.Parser` using the detected language grammar.
4. Dispatch to language-specific extractor based on extension.

#### Language-Specific Extractors

**Python** (`_extract_python_imports`):
- Walks top-level children of the AST root.
- `import_statement`: extracts the `dotted_name` child as the import path.
- `import_from_statement`: checks for `relative_import` child; if present, skips. Otherwise extracts the first `dotted_name` as the module path.

**TypeScript/JavaScript** (`_extract_ts_imports`):
- Walks top-level `import_statement` nodes.
- Extracts the string source via `_get_ts_import_source` (looks for `string` -> `string_fragment` children).
- Skips imports starting with `"."` or `".."` (relative).

**Go** (`_extract_go_imports`):
- Walks `import_declaration` nodes.
- Handles both single `import_spec` and grouped `import_spec_list`.
- Extracts `interpreted_string_literal_content` from each spec.
- Skips standard library packages (heuristic: no `/` in the path).

**Rust** (`_extract_rust_imports`):
- Walks `use_declaration` nodes.
- Extracts the path via `_get_rust_use_path`, handling `scoped_identifier`, `identifier`, `scoped_use_list`, and `use_wildcard` node types.
- Determines root crate from the first `::` segment.
- Skips built-in crates (`std`, `core`, `alloc`) and relative imports (`self`, `super`).
- Emits at most one `ImportInfo` per `use_declaration`.

### Import Resolution

```python
def resolve_import_to_node(
    import_path: str,
    file_path: Path,
    conn: sqlite3.Connection,
    scan_paths: list[str] | None = None,
    *,
    is_ts: bool = False,
) -> str | None
```

| Parameter     | Type               | Default                    | Description                                          |
|---------------|--------------------|----------------------------|------------------------------------------------------|
| `import_path` | `str`              | required                   | Raw import path to resolve.                          |
| `file_path`   | `Path`             | required                   | Path of the file containing the import.              |
| `conn`        | `sqlite3.Connection` | required                 | Database connection.                                 |
| `scan_paths`  | `list[str] \| None`| `None` (defaults to `["src", "lib", "app"]`) | Source directories to search. |
| `is_ts`       | `bool`             | `False`                    | Whether the import is from a TS/JS file.             |

**Resolution strategies (tried in order):**

**Strategy 1 -- Code-symbols annotation lookup:**
1. Convert the import path to candidate file paths via `_import_path_to_file_paths` (replaces `.` with `/`, prepends each scan_path prefix, generates both `.py` and `__init__.py` variants).
2. For each candidate, query `code_symbols` for `annotations` JSON.
3. Parse the annotations and look for keys `domain`, `service`, or `feature` whose values match a `nodes.ref_id` (constructed as `"{kind}:{value}"`).
4. Return the first matching `ref_id`.

**Strategy 2 -- Hierarchical source-prefix matching:**
1. For TypeScript/JavaScript (`is_ts=True`): normalize the import path via `_normalize_ts_import`. Returns `None` for npm packages (non-aliased, non-relative paths), terminating resolution.
2. For other languages: convert the dotted path to a directory path (replace `.` with `/`).
3. Call `_find_node_by_source_prefix(dir_path, scan_paths, conn)`:
   - Prepend each scan_path prefix (plus bare path).
   - Split into path segments, walk from deepest to shallowest.
   - For each segment level, query `nodes.source` with and without trailing `/`.
   - Return the first matching `ref_id`.

### Internal Resolution Helpers

| Function                      | Description                                                                                                 |
|-------------------------------|-------------------------------------------------------------------------------------------------------------|
| `_import_path_to_file_paths`  | Convert dotted import path to candidate file paths with scan_path prefixes. Generates `.py` and `__init__.py` variants. |
| `_normalize_ts_import`        | Resolve `@/` and `~/` aliases to `src/`. Returns `None` for npm packages.                                  |
| `_find_node_by_source_prefix` | Walk path hierarchy from deepest to shallowest, query `nodes.source` with and without trailing `/`.         |
| `_find_node_for_file`         | Walk up directory hierarchy of a relative file path, matching against `nodes.source`. Used by `create_import_edges`. |

### Edge Generation

```python
def create_import_edges(conn: sqlite3.Connection) -> int
```

1. Query all distinct `(file_path, resolved_ref_id)` from `code_imports` where `resolved_ref_id IS NOT NULL`.
2. For each row, determine the source node via `_find_node_for_file(rel_path, conn)`.
3. Skip if no source node is found or if `source_ref_id == target_ref_id` (self-reference).
4. Deduplicate `(source, target)` pairs via a `seen` set.
5. Insert `depends_on` edge with `INSERT OR IGNORE`.
6. Commit and return the count of edges created.

### Full Indexing Pipeline

```python
def index_imports(project_root: Path, conn: sqlite3.Connection) -> int
```

1. Resolve scan paths via `resolve_scan_paths(project_root)` from config.
2. Collect source files via `_collect_source_files(project_root)`, which uses `resolve_scan_paths` and `supported_extensions()` to enumerate files under each scan directory.
3. For each file:
   a. Call `extract_imports(file_path)`. Skip if empty.
   b. Read file content, compute SHA-256 hash, compute relative path.
   c. Determine `is_ts` flag from file extension (`.ts`, `.tsx`, `.js`, `.jsx`, `.vue`).
   d. For each `ImportInfo`, call `resolve_import_to_node` to resolve it.
   e. Upsert into `code_imports` with `ON CONFLICT(file_path, line_number, import_path) DO UPDATE SET resolved_ref_id, file_hash`.
4. Commit.
5. Call `create_import_edges(conn)` to generate `depends_on` edges.
6. Return the total count of imports indexed.

### Configuration

Scan paths are configurable via `.beadloom/config.yml`:

```yaml
scan_paths:
  - src
  - lib
  - app
```

Default: `["src", "lib", "app"]`.

---

## API

### Public Functions

```python
def extract_imports(file_path: Path) -> list[ImportInfo]: ...
def resolve_import_to_node(
    import_path: str,
    file_path: Path,
    conn: sqlite3.Connection,
    scan_paths: list[str] | None = None,
    *,
    is_ts: bool = False,
) -> str | None: ...
def create_import_edges(conn: sqlite3.Connection) -> int: ...
def index_imports(project_root: Path, conn: sqlite3.Connection) -> int: ...
```

### Public Classes

```python
@dataclass(frozen=True)
class ImportInfo:
    file_path: str
    line_number: int
    import_path: str
    resolved_ref_id: str | None
```

---

## Invariants

- Self-references (source node == target node) never generate `depends_on` edges.
- Each `(source_ref_id, target_ref_id)` pair generates at most one `depends_on` edge (deduplicated via `seen` set in `create_import_edges` and `INSERT OR IGNORE`).
- Imports are upserted with `ON CONFLICT(file_path, line_number, import_path) DO UPDATE`, ensuring idempotent reindexing.
- `extract_imports` returns an empty list (never raises) for unsupported languages, unreadable files, or empty files.
- Resolution strategies are tried in strict order: annotation lookup first, then source-prefix matching.
- `_import_path_to_file_paths` always includes the bare (no-prefix) variant as the last set of candidates.

---

## Constraints

- Requires tree-sitter grammar packages for each supported language (e.g. `tree-sitter-python`, `tree-sitter-typescript`). Returns empty list if the grammar is not installed.
- Only processes files located under directories listed in `scan_paths`.
- Relative imports are always skipped (language-specific detection):
  - Python: `relative_import` AST node presence.
  - TypeScript/JavaScript: path starts with `"."` or `".."`.
  - Go: no `/` in path (stdlib heuristic).
  - Rust: root identifier is `self` or `super`.
- npm packages (non-aliased, non-relative TypeScript/JavaScript imports) are skipped by `_normalize_ts_import` returning `None`.
- The `code_symbols` table must be populated for annotation-based resolution to work (Strategy 1).
- The `nodes` table must be populated for source-prefix resolution to work (Strategy 2).
- File content is read as UTF-8; files that raise `UnicodeDecodeError` are silently skipped.

---

## Testing

### Extraction Tests

- **Python imports.** Parse a file with `import foo`, `from bar import baz`, and `from . import relative`. Assert the first two yield `ImportInfo` entries; the relative import is skipped.
- **TypeScript imports.** Parse `import X from '@/components/Button'` and `import Y from './local'` and `import Z from 'react'`. Assert only the aliased import is extracted; relative and npm are skipped.
- **Go imports.** Parse `import ("fmt"; "github.com/org/pkg")`. Assert only the non-stdlib import is extracted.
- **Rust imports.** Parse `use std::io; use my_crate::module; use super::sibling;`. Assert only `my_crate::module` is extracted.
- **Unsupported extension.** Pass a `.txt` file. Assert empty list returned.
- **Empty file.** Assert empty list returned.
- **Unreadable file.** Assert empty list returned without exception.

### Resolution Tests

- **Annotation lookup hit.** Insert a `code_symbols` row with `annotations={"domain": "billing"}` for a candidate file path. Insert a node with `ref_id="domain:billing"`. Assert resolution returns `"domain:billing"`.
- **Source-prefix matching.** Insert a node with `source="src/beadloom/auth/"`. Resolve import path `beadloom.auth.tokens` with `scan_paths=["src"]`. Assert the correct `ref_id` is returned.
- **TS alias resolution.** Resolve `@/shared/utils` with `is_ts=True`. Assert it maps to `src/shared/utils` and matches the appropriate node.
- **TS npm package skip.** Resolve `react` with `is_ts=True`. Assert `None` is returned.
- **No match.** Resolve an import path with no corresponding annotation or node. Assert `None`.

### Edge Generation Tests

- **Edges created.** Insert two nodes and a resolved code_import. Call `create_import_edges`. Assert one `depends_on` edge is created.
- **Self-reference skipped.** Import where source and target resolve to the same node. Assert zero edges.
- **Deduplication.** Multiple imports from the same source to the same target. Assert exactly one edge.

### Pipeline Tests

- **`index_imports` end-to-end.** Set up a project with source files, nodes, and code_symbols. Call `index_imports`. Assert:
  - `code_imports` table is populated with correct `file_path`, `line_number`, `import_path`, `resolved_ref_id`.
  - `depends_on` edges are created in the `edges` table.
  - Return count matches the number of imports processed.
- **Idempotent reindex.** Call `index_imports` twice. Assert the same results with no duplicates (upsert behavior).
