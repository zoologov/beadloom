# Import Resolver

Import analysis and `depends_on` edge generation via tree-sitter-based source code parsing.

**Source:** `src/beadloom/graph/import_resolver.py`, with the manifest readers
`src/beadloom/graph/go_modules.py`, `src/beadloom/graph/jvm_packages.py` and
`src/beadloom/graph/swift_packages.py`

---

## Specification

### Purpose

Extract import statements from source files using tree-sitter grammars, resolve each import to an architecture graph node, store the results in the `code_imports` table, and generate `depends_on` edges between graph nodes. This forms the foundation for automated dependency detection and architectural rule enforcement.

### Supported Languages

| Language              | File Extensions            | Import Syntax Handled                      | Skipped Imports                                 |
|-----------------------|----------------------------|--------------------------------------------|-------------------------------------------------|
| Python                | `.py`                      | `import X`, `from X import Y`              | Relative imports (`from . import`, `from ..`)   |
| TypeScript/JavaScript | `.ts`, `.tsx`, `.js`, `.jsx`| `import ... from 'path'`, `export ... from 'path'`, `import('literal')` | None at extraction; npm packages resolve to no node |
| Vue component         | `.vue`                     | The TS/JS forms, inside each `<script>` / `<script setup>` block | As TypeScript/JavaScript                        |
| Go                    | `.go`                      | `import "path"`, `import (...)` blocks     | Nothing skipped: every import is recorded, the standard library's resolved to none (BDL-078 `beadloom-jcng`); resolved through `go.mod` (see below) |
| Rust                  | `.rs`                      | `use path::to::module`                     | Built-in crates (`std`, `core`, `alloc`), `self`, `super` |

The table details four languages. The resolver also extracts Kotlin, Java, Swift, Objective-C
and C/C++ imports (`_extract_kotlin_imports`, `_extract_java_imports`, `_extract_swift_imports`,
`_extract_objc_imports`, `_extract_c_cpp_imports`); their extraction is not described here.
`.java` and `.kt` files share one import language (`_IMPORT_LANGUAGE['.java'] = '.kt'`), so a
Java file and a Kotlin file are given the same scan paths. How Go, Java/Kotlin and Swift imports
are resolved is described in [Imports resolved through a manifest](#imports-resolved-through-a-manifest).

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

0. A `.vue` file goes to `_extract_component_imports` (see below) and skips the steps that follow.
1. Detect language via file extension using `get_lang_config(suffix)`. Return empty list if unsupported.
2. Read file content as UTF-8. Return empty list on `OSError`, `UnicodeDecodeError`, or empty content.
3. Parse content with `tree_sitter.Parser` using the detected language grammar.
4. Dispatch to language-specific extractor based on extension.

#### AST traversal

Every extractor iterates `_walk(root)` — the **whole** tree in document order —
not just the root's children. Extraction used to consider only a file's
top-level statements, so an import inside a function, a class body, an
`if TYPE_CHECKING:` guard or a `try:` block was invisible to the dependency
graph. Those are exactly the places an import is put to defer cost or to break a
cycle, so the graph was blind to the very edges the cycle and boundary rules
exist to judge (BDL-UX #159). Measured on Beadloom when the walk was introduced:
460 nested imports, 231 of them first-party — about a third of all imports; the
`depends_on` edge count went from 51 to 146, and six real boundary violations
surfaced that had been hidden behind nested imports.

The statement types the extractors match never nest inside themselves, so a full
walk cannot double-count a single statement.

#### Language-Specific Extractors

**Python** (`_extract_python_imports`):
- Walks every `import_statement` / `import_from_statement` in the tree.
- `import_statement`: extracts the `dotted_name` child as the import path.
- `import_from_statement`: checks for `relative_import` child; if present, skips. Otherwise extracts the first `dotted_name` as the module path.

**TypeScript/JavaScript** (`_extract_ts_imports`):
- Walks every `import_statement` and `export_statement` node in the tree and
  extracts the string source via `_get_ts_import_source` (looks for `string` ->
  `string_fragment` children). A re-export (`export { X } from './x'`,
  `export * from '../y'`) is read as an import, because that is how an
  `index.js` facade exposes its folder. An `export` without `from` yields
  nothing.
- Walks every `call_expression` whose callee is the `import` keyword
  (`_dynamic_import_source`, BDL-076 J2). The import is read only when the
  first argument is a literal: a string, or a template string with no `${...}`.
  A computed specifier (`import(name)`, `import('./' + a)`, a template with a
  substitution) names nothing knowable and is not read.
- Keeps every specifier as written, relative ones included. Until BDL-076 J1
  relative specifiers were dropped here, so a JS/TS project got no `depends_on`
  edge between its own modules.

**Vue component** (`_extract_component_imports`, BDL-076 J2):
- Finds the `<script>` and `<script setup>` blocks with `script_blocks`, the
  same finder the symbol indexer uses, reached through `code_indexer`'s
  re-export so the resolver keeps its one declared crossing into code-indexer.
- Parses each block with the grammar its `lang` names (`ts`, `tsx`, `jsx`,
  otherwise JavaScript) and runs `_extract_ts_imports` on it.
- Moves each import's `line_number` to its line in the `.vue` file.
- The `<template>` and `<style>` are not read.

**Go** (`_extract_go_imports`):
- Walks `import_declaration` nodes.
- Handles both single `import_spec` and grouped `import_spec_list`.
- Extracts `interpreted_string_literal_content` from each spec.
- Records every import, the standard library's too (BDL-078 `beadloom-jcng`). The shortcut that
  skipped a path with no `/` is gone: it also dropped a project whose module path has no `/`
  (`module tidewater` imported as `"tidewater"`). Whether an import is the standard library is
  decided in one place, `resolve_go_import`, which resolves it to `None`. Visible effects: a
  `code_imports` row per standard-library import, lint's `files scanned` counts a Go file that
  imports only the standard library, and a `forbid_import` rule sees Go standard-library paths
  as it already saw Python's.

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
    source_files: Collection[str],
    is_ts: bool = False,
) -> str | None
```

| Parameter     | Type               | Default                    | Description                                          |
|---------------|--------------------|----------------------------|------------------------------------------------------|
| `import_path` | `str`              | required                   | Raw import path to resolve.                          |
| `file_path`   | `Path`             | required                   | Path of the file containing the import.              |
| `conn`        | `sqlite3.Connection` | required                 | Database connection.                                 |
| `scan_paths`  | `list[str] \| None`| `None` (defaults to `["src", "lib", "app"]`) | Source directories to search. |
| `source_files` | `Collection[str]` | required (keyword-only)    | Project-relative POSIX paths of the tree's source files; a candidate exists only if it is one of them (BDL-078 `beadloom-nh7h`). Required, not defaulted: a default falling back to the index would be the order-dependent read the bead removed. |
| `is_ts`       | `bool`             | `False`                    | Whether the import is from a TS/JS file.             |

**Resolution strategies (tried in order):**

Candidate files come from `_import_path_to_file_paths` (replaces `.` with `/`, prepends each
scan_path prefix, generates both `.py` and `__init__.py` variants).

**Strategy 1 -- Ownership of the imported file:**
1. For each candidate present in `source_files`, return its owner
   (`infrastructure/repository.get_owning_ref_id`, most specific `source` wins) when it has one.
   This is the rule the importing side is attributed by, so an edge connects the two nodes that
   own the two files. Existence is read from the tree, not from an index table (BDL-078
   `beadloom-nh7h`): it used to be read from `code_symbols` or `file_index`, a module of
   re-exports holds no symbol, and a full reindex filled `file_index` only after it resolved
   the imports, so a fresh index resolved `tui`'s import of `graph_reads` to `application` and
   a second reindex of the same tree to `graph-reads`.

**Strategy 2 -- Code-symbols annotation lookup:**
1. For each candidate, query `code_symbols` for `annotations` JSON.
2. Parse the annotations and look for keys `domain`, `service`, or `feature` whose values match a `nodes.ref_id` (constructed as `"{kind}:{value}"`).
3. Return the first matching `ref_id`.

**Strategy 3 -- Hierarchical source-prefix matching:**
1. For TypeScript/JavaScript (`is_ts=True`): normalize the import path via `_normalize_ts_import`. Returns `None` for npm packages (non-aliased, non-relative paths), terminating resolution.
2. For other languages: convert the dotted path to a directory path (replace `.` with `/`).
3. Call `_find_node_by_source_prefix(dir_path, scan_paths, conn)`:
   - Prepend each scan_path root (trailing `/` normalised), plus the bare path.
   - Split into path segments, walk from deepest to shallowest, and **stop below the scan
     path's root**: neither the root nor anything above it is tried (BDL-076 J2). The bare
     reading walks down to its first segment, as before.
   - For each segment level, query `nodes.source` with and without trailing `/`.
   - Return the first matching `ref_id`.

The floor exists because of a measurement. With `site/.vitepress/theme` as a scan path, every
Python import no file answered (`typing`, `pathlib`, 1,318 of them) walked up to `site/` and
became one of 103 false edges into the node owning it (A0, BDL-076). A node whose source IS a
scan root would catch every such import the same way.

### Relative JS/TS Imports

```python
def is_relative_specifier(specifier: str) -> bool
def relative_import_candidates(specifier: str, importer: str) -> list[str]
def resolve_relative_import(
    specifier: str, importer: str, project_root: Path, conn: sqlite3.Connection
) -> str | None
```

A specifier is relative when it is `.`, `..`, or starts with `./` or `../`. In a `.ts`, `.tsx`,
`.js`, `.jsx` or `.vue` importer it is resolved by `resolve_relative_import`, never by
`resolve_import_to_node` (BDL-076 J1). `relative_import_candidates` joins the specifier to the
importer's directory, normalises it, and yields, in order:

1. the path as written;
2. for a written `.js`, the `.ts` then `.tsx` source; for a written `.jsx`, the `.tsx` source
   (TypeScript's ESM convention writes the extension the file has after compilation);
3. the path plus `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.vue`;
4. `<path>/index` plus the same extensions.

A file therefore beats a folder of the same name. A specifier that climbs above the project root
yields no candidate. The first candidate that is a file on disk is the target, and its node is
`get_owning_ref_id` of that file. A `.mjs`, `.cjs` or `.vue` target only has to exist: it need
not be parseable.

A specifier that names no file, or names a file no node owns, is written to `code_imports` with
`resolved_ref_id` NULL, like any unresolved import. It is never dropped.

**Not handled** (each is a decision, named in the docstring):

- `tsconfig` `paths`/`baseUrl` beyond the `@/` and `~/` aliases of `_TS_ALIAS_MAP`;
- a folder's `package.json` `main`/`exports`;
- `.mts`, `.cts` and `.d.ts` targets;
- query suffixes (`./x.vue?raw`);
- CommonJS `require()`;
- `.mjs` and `.cjs` files as importers: they are not in `supported_extensions()`, so they are
  resolution targets only and their own imports are not read.

A `forbid_import` rule matches `code_imports.import_path`, so for a relative import it sees the
raw specifier, not the resolved file.

### Scan Paths per Import Language

```python
def scan_path_languages(
    project_root: Path, scan_paths: Sequence[str], files: Sequence[Path]
) -> dict[str, frozenset[str]]
```

`index_imports` and `reindex_file_imports` pass each file only the scan paths that hold files of
its import language (`_scan_paths_for`, BDL-076 J2). `_IMPORT_LANGUAGE` groups extensions into
one language: `.ts`/`.tsx`/`.js`/`.jsx`/`.mjs`/`.cjs`/`.vue`; `.kt`/`.kts`; `.m`/`.mm`;
`.c`/`.h`/`.cpp`/`.hpp`. Every other extension is its own language. So a Python import is never
prefixed with a scan path that holds no Python. An importer whose language no scan path holds (a
file outside every scan path) keeps the full list.

Limits: a scan path holding both languages is read for both, because the grouping is by
extension. The test index still calls `resolve_import_to_node` with every scan path, memoised
per import path and given the code files the run indexed as `source_files`: it gets the walk-up
floor, not the per-language filter. The onboarding scan no longer calls it.

### Imports resolved through a manifest

Three languages name a module, not a folder, so a dotted-path reading finds nothing or the wrong
node. Each is resolved through what the project declares (BDL-076 B5, B7 and R2 finding 6):

| Language | Function | Read from | Unresolved |
|----------|----------|-----------|------------|
| Go | `resolve_go_import(import_path, importer, project_root, conn, modules)` | `GoModules` (`go_modules.py`): the nearest `go.mod` at or above the importer; the longest module path among the project's modules, the importer's local `replace` directives and those of the `go.work` that uses it; the rest of the path is a directory under that module | The standard library and every module the project does not hold |
| Java, Kotlin | `resolve_jvm_import(import_path, file_path, conn, scan_paths, packages, *, source_files)` | `JvmPackages` (`jvm_packages.py`): the longest dotted prefix of the import that some file declares as its `package`, mapped to the folders of the files declaring it; where several folders declare the package, the import reaches those holding a file named after the imported class (`B.kt`, `B.java`), else all of them | A package no file declares (the JDK, a library), whose dotted folder reading stays the fallback; an import whose folders different nodes own (a wildcard or a top-level Kotlin function of a package split across nodes) |
| Swift | `resolve_swift_import(import_path, importer, project_root, conn, packages)` | `SwiftPackages` (`swift_packages.py`): the target of that name in the nearest `Package.swift`, else the one other package declaring it | An Apple framework, a product of a package the project does not hold, a test, plugin, binary or system-library target |

The owner of the folder found is decided by the one ownership rule (`get_owning_ref_id`). A Go
import never goes through `resolve_import_to_node`, whose dotted reading turned `net/http` into a
node sourced at `net/`. A Swift import goes through `resolve_swift_import` only when some manifest
declares its module; a project with no `Package.swift` keeps the folder-path reading of
`resolve_import_to_node`. The Kotlin layout that omits the common root package from the folders
(`package org.example.network` in `src/main/kotlin/network/`) resolves because the package is
read from the declaration, not from the folder.

A JVM package declared in several folders — split across a Java and a Kotlin root, across
modules, or across folders of Kotlin's recommended layout — is not given to the folder read
first (BDL-076 `beadloom-ujzb.24`, re-review finding m5). That choice drew a false edge to the
first folder for every import of a class the other folder holds. The segment after the package
is read as the class the import names: Java requires a public class's file to carry its name,
and Kotlin's conventions ask it of a file holding one class. `resolve_jvm_import` resolves only
when one node owns every folder the import reaches, so an import naming no such file draws no
edge rather than a guessed one. `init`'s quick import scan applies the same rule to clusters.

### Internal Resolution Helpers

| Function                      | Description                                                                                                 |
|-------------------------------|-------------------------------------------------------------------------------------------------------------|
| `_import_path_to_file_paths`  | Convert dotted import path to candidate file paths with scan_path prefixes. Generates `.py` and `__init__.py` variants. |
| `_normalize_ts_import`        | Resolve `@/` and `~/` aliases to `src/`. Returns `None` for npm packages.                                  |
| `_find_node_by_source_prefix` | Walk path hierarchy from deepest to shallowest, query `nodes.source` with and without trailing `/`.         |
| `_find_node_for_file`         | The node that OWNS a file — delegates to `infrastructure/repository.get_owning_ref_id` (most specific `source` wins). Used by `create_import_edges`. Previously walked up from the file's PARENT directory, so a node whose source IS a file never owned that file and its imports were credited to the enclosing directory's node. |
| `_walk`                       | Pre-order traversal of the whole AST in document order; every extractor iterates it so imports below the top level are seen. |
| `_part_of_ancestors`          | Each node mapped to the set of nodes it is transitively `part_of`, for the containment skip in `create_import_edges`. Reads the direct `part_of` edges and delegates the climb to `graph/rules/layers.py::part_of_ancestors`, which is the one ancestry walk in the codebase (BDL-070 A1). |

### Edge Generation

```python
def create_import_edges(conn: sqlite3.Connection) -> int
```

1. Query all distinct `(file_path, resolved_ref_id)` from `code_imports` where `resolved_ref_id IS NOT NULL`.
2. For each row, determine the source node via `_find_node_for_file(rel_path, conn)` (file ownership).
3. Skip if no source node is found or if `source_ref_id == target_ref_id` (self-reference).
4. Skip **containment in one direction only** — an edge from a node to a node it
   is `part_of` (a container depending on its own part). A package façade
   re-exporting its children says nothing the `part_of` edge did not, and paired
   with a child's ordinary upward import it manufactures a node-level cycle with
   no module-level counterpart. The reverse is KEPT: a child reaching into
   shared code that lives in its container but belongs to no other node is a
   real dependency, and dropping it made such a node report "depends on
   nothing" — false, and worse than a coarse answer.
5. Deduplicate `(source, target)` pairs via a `seen` set.
6. Insert `depends_on` edge with `INSERT OR IGNORE`, stamping
   `extra = {"derived": "imports"}`. The marker is the provenance that lets an
   incremental refresh delete the derived set without touching a graph-declared
   edge; `INSERT OR IGNORE` means a pair also declared in YAML keeps the YAML
   row and stays unmarked.
7. Commit and return the count of edges created.

### Derived-Edge Refresh

```python
def delete_derived_import_edges(conn: sqlite3.Connection) -> int
def refresh_import_edges(conn: sqlite3.Connection) -> int
```

The derived edge set is a pure function of `code_imports`, so a refresh is
delete-then-recreate. Doing only the recreate half kept a dependency edge alive
after its import was removed, for the cycle and layer rules to trip over.

### Incremental Indexing

```python
def reindex_file_imports(
    project_root: Path,
    conn: sqlite3.Connection,
    *,
    touched: Sequence[str],
    removed: Sequence[str],
) -> int
```

Deletes `code_imports` rows for the touched and removed paths, re-extracts the touched ones,
then resolves every other stored import again against the same tree, without parsing it
(`_reresolve_stored_imports`), records the manifest fingerprint and calls
`refresh_import_edges`. A touched or removed file can change what an untouched file's import
names (BDL-078 `beadloom-nh7h`), and so can a manifest: the incremental reindex asks
`import_manifests.manifests_changed()` and, when only a `go.mod`, `go.work` or `Package.swift`
changed, calls this with both lists empty (`beadloom-jcng`). The JVM package declarations are
read on every run. The result equals a fresh index of the same tree. This is what an incremental
reindex calls; without it every import rule read an index frozen at the last
FULL rebuild, so `reindex && lint` passed a real boundary break (BDL-UX #142).

### Full Indexing Pipeline

```python
def index_imports(project_root: Path, conn: sqlite3.Connection) -> int
```

1. Resolve scan paths via `resolve_scan_paths(project_root)` from config.
2. Collect source files via `_collect_source_files(project_root)`, which uses `resolve_scan_paths` and `supported_extensions()` to enumerate files under each scan directory, then `scan_path_languages` over them.
3. For each file:
   a. Call `extract_imports(file_path)`. Skip if empty.
   b. Read file content, compute SHA-256 hash, compute relative path.
   c. Determine `is_ts` flag from file extension (`.ts`, `.tsx`, `.js`, `.jsx`, `.vue`).
   d. For each `ImportInfo`: a relative specifier from a TS/JS/Vue importer goes to
      `resolve_relative_import`; a Go import to `resolve_go_import`; a Java or Kotlin import to
      `resolve_jvm_import`; a Swift import whose module a manifest declares to
      `resolve_swift_import`; every other import goes to `resolve_import_to_node` with the
      scan paths of the file's import language. One dispatch (`_resolve_import`) serves the
      full and the incremental path. The Go modules, the declared JVM packages, the Swift
      packages and the source files are read once per run, as one `_ImportTree`.
   e. Upsert into `code_imports` with `ON CONFLICT(file_path, line_number, import_path) DO UPDATE SET resolved_ref_id, file_hash`.
4. Commit.
5. Record the manifest fingerprint (`import_manifests.record_manifests`) and call
   `refresh_import_edges(conn)` to regenerate `depends_on` edges.
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
def is_relative_specifier(specifier: str) -> bool: ...
def relative_import_candidates(specifier: str, importer: str) -> list[str]: ...
def resolve_relative_import(
    specifier: str,
    importer: str,
    project_root: Path,
    conn: sqlite3.Connection,
) -> str | None: ...
def scan_path_languages(
    project_root: Path, scan_paths: Sequence[str], files: Sequence[Path]
) -> dict[str, frozenset[str]]: ...
def resolve_import_to_node(
    import_path: str,
    file_path: Path,
    conn: sqlite3.Connection,
    scan_paths: list[str] | None = None,
    *,
    source_files: Collection[str],
    is_ts: bool = False,
) -> str | None: ...
def resolve_go_import(
    import_path: str, importer: str, project_root: Path, conn: sqlite3.Connection,
    modules: GoModules,
) -> str | None: ...
def resolve_jvm_import(
    import_path: str, file_path: Path, conn: sqlite3.Connection, scan_paths: list[str],
    packages: JvmPackages, *, source_files: Collection[str],
) -> str | None: ...
def resolve_swift_import(
    import_path: str, importer: str, project_root: Path, conn: sqlite3.Connection,
    packages: SwiftPackages,
) -> str | None: ...
def create_import_edges(conn: sqlite3.Connection) -> int: ...
def delete_derived_import_edges(conn: sqlite3.Connection) -> int: ...
def refresh_import_edges(conn: sqlite3.Connection) -> int: ...
def index_imports(project_root: Path, conn: sqlite3.Connection) -> int: ...
def reindex_file_imports(
    project_root: Path,
    conn: sqlite3.Connection,
    *,
    touched: Sequence[str],
    removed: Sequence[str],
) -> int: ...
```

The manifest readers' public API, and that of `import_manifests.py` (BDL-078 `beadloom-jcng`:
`manifests_fingerprint`, `resolves_through_manifests`, `record_manifests`, `manifests_changed`,
`MANIFESTS_META_KEY`), is listed in the [graph domain README](../../README.md), under each
module.

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
- Resolution strategies are tried in strict order: file ownership, then annotation lookup, then source-prefix matching.
- The source-prefix walk never tries a scan path's root or anything above it.
- A relative JS/TS specifier is never dropped: it resolves to the owner of an existing file or is stored with `resolved_ref_id` NULL.
- A `.vue` import's `line_number` is a line of the `.vue` file.
- `_import_path_to_file_paths` always includes the bare (no-prefix) variant as the last set of candidates.
- An import resolves to the same node however the index was built: fresh, a second full
  reindex, or incrementally after a file or a manifest changed (BDL-078 `beadloom-nh7h`,
  `beadloom-jcng`).

---

## Constraints

- Requires tree-sitter grammar packages for each supported language (e.g. `tree-sitter-python`, `tree-sitter-typescript`). Returns empty list if the grammar is not installed.
- Only processes files located under directories listed in `scan_paths`.
- Relative and standard-library imports are skipped (language-specific detection):
  - Python: `relative_import` AST node presence.
  - Rust: root identifier is `self` or `super`.
- TypeScript/JavaScript relative imports are NOT skipped since BDL-076 J1; see Relative JS/TS Imports.
- npm packages (non-aliased, non-relative TypeScript/JavaScript imports) are skipped by `_normalize_ts_import` returning `None`.
- The `code_symbols` table must be populated for annotation-based resolution to work (Strategy 2).
- The `nodes` table must be populated for source-prefix resolution to work (Strategy 3).
- File content is read as UTF-8; files that raise `UnicodeDecodeError` are silently skipped.

---

## Testing

### Extraction Tests

- **Python imports.** Parse a file with `import foo`, `from bar import baz`, and `from . import relative`. Assert the first two yield `ImportInfo` entries; the relative import is skipped.
- **TypeScript imports.** Relative specifiers are kept as written (`tests/test_import_resolver.py`, `tests/unit/graph/test_import_resolver.py`): candidate order, specifier classification, re-exports, six dynamic `import()` cases, two `.vue` cases.
- **Go imports.** Parse `import ("fmt"; "github.com/org/pkg")`. Assert both imports are extracted (the standard library's too, since BDL-078 `beadloom-jcng`).
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

- **Relative resolution** (`tests/integration/graph/test_import_resolver.py`). Owner resolution, order preference, file beats folder index, a `.vue` target, a missing file, an unowned file, full and incremental reindex.
- **Walk-up floor and per-language scan paths** (same file). A node above the scan path, a node at the scan root, a trailing slash, a package below the root still resolving, a mixed project, `scan_path_languages`.

### Acceptance Scenarios

`tests/acceptance/graph/import-resolver/`:
- `relative_js_ts_imports.feature` (5 scenarios): a TS package and a JS package with `index.js`/`index.mjs` facades get exactly their real edges, and `beadloom why` lists the dependents.
- `a_foreign_scan_path_adds_no_false_edges.feature` (3 scenarios): a Python service beside a JS theme scan path owned by a node above it gets no false edge.
- `vue_and_dynamic_imports.feature` (2 scenarios): `why` on a composable lists the component, the import is on its `.vue` line, a lazy `import('../charts/bar')` is an edge.
- `go_module_imports.feature`: Go imports resolve through `go.mod`, and a deny rule fires on a Go import.
- `an_import_resolves_the_same_however_the_index_was_built.feature` (3 scenarios, BDL-078
  `beadloom-nh7h`): a fresh index, a second full reindex and an incremental one resolve every
  import identically, a removed target included.
- `a_manifest_is_an_input_of_the_files_it_governs.feature` (4 scenarios, BDL-078
  `beadloom-jcng`): a `go.mod` rename, a `go.work` replace, a `Package.swift` target path and a
  Go root package re-resolve on an incremental reindex.
- `one_jvm_package_in_two_folders.feature` (2 scenarios, `beadloom-ujzb.24`): an import of a class
  of a package declared in two folders draws its edge to the node holding the class's file, from
  `init` and from `reindex`, and a wildcard import of that package resolves to no folder.

The manifest readers have unit tests of their own: `tests/unit/graph/test_go_modules.py`,
`tests/unit/graph/test_jvm_packages.py` (with `TestAPackageDeclaredInTwoFolders`),
`tests/unit/graph/test_swift_packages.py`. `tests/integration/graph/test_import_resolver.py`
covers a package in two folders on a full and an incremental reindex.

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
