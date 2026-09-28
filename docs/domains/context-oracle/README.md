# Context Oracle

Context Oracle is the core domain of beadloom, responsible for building context bundles via BFS traversal of the architecture graph, code symbol indexing, caching, full-text search, API route extraction, test mapping, and impact analysis.

## Features and components

Features (each with a `SPEC.md`):

- **[Code Indexer](features/code-indexer/SPEC.md)** — tree-sitter symbol + `beadloom:` annotation extraction.
- **[Route Extraction](features/route-extraction/SPEC.md)** — API route discovery across web frameworks.
- **[Test Mapping](features/test-mapping/SPEC.md)** — test-to-node binding by the mirror of a test file's path, by its place beside the code, or by a `tests:` declaration, over a test layout `.beadloom/config.yml` can declare; `ctx` and the debt report read it.
- **[Search](features/search/SPEC.md)** — FTS5 full-text search over nodes + docs.
- **[Cache](features/cache/SPEC.md)** — two-tier context-bundle cache.
- **[Why](features/why/SPEC.md)** — bidirectional impact analysis.

Components (internal building blocks, each with a `DOC.md`):

- **[Context Builder](components/context-builder/DOC.md)** — the BFS bundle assembler behind `ctx` / `prime`.

Two components of Test Mapping are nodes of their own, `part_of` `test-mapping`, and have no
`DOC.md`: each declares `docs_absent`, because the loader keeps a document for one node only
and the [Test Mapping SPEC](features/test-mapping/SPEC.md) documents both (`beadloom-2mj3.15`):

- **`test-layout`** (`test_layout.py`) — where a project keeps its tests and which paths are
  tests, read from `tests:` in `.beadloom/config.yml`.
- **`test-file-reader`** (`test_file_reader.py`) — the test functions and absolute imports one
  test file holds.

## Specification

### Purpose

When an AI agent or developer requests context for a `ref_id`, Context Oracle:

1. Validates the requested ref_id(s) (with Levenshtein + prefix suggestions on error)
2. Performs BFS traversal of the graph from focus nodes
3. Collects text chunks of documentation for subgraph nodes
4. Collects code symbols via `# beadloom:key=value` annotations
5. Checks sync_state for stale doc-code pairs
6. Collects architecture constraints (deny/require rules) relevant to the subgraph
7. Extracts external links, test mapping, git activity, and API routes from focus node extra data
8. Returns a versioned JSON bundle (version 2)

### Modules

| Module | Source | Description |
|--------|--------|-------------|
| `builder` | `builder.py` | BFS subgraph traversal, chunk collection, context bundle assembly |
| `cache` | `cache.py` | L1 in-memory and L2 SQLite-backed context bundle caching |
| `intent` | `intent.py` | Which recorded intent a node's bundle carries, and the three answers absence can have |
| `code_indexer` | `code_indexer.py` | Tree-sitter parsing and `beadloom:` annotation extraction for every extension in `_EXTENSION_LOADERS` |
| `search` | `search.py` | FTS5 full-text search over architecture graph nodes and documentation |
| `route_extractor` | `route_extractor.py` | API route extraction via regex for 12 frameworks, with self-exclusion and display formatting |
| `test_binding` | `test_binding.py` | Which node a test file binds to: a `tests:` declaration, else the mirror of its path under a mirrored kind folder or a build tool's test tree, else its place inside a node's source; placements, the four-key `extra["tests"]` summary, and the unplaced-files sentence `ctx` and the debt report print |
| `test_file_reader` | `test_file_reader.py` | One `ast` parse of a Python test file (its test-function count and absolute imports); a file in another language counted by the line its tests are written in |
| `test_layout` | `test_layout.py` | The project's test layout, from the `tests:` block of `.beadloom/config.yml`: roots, kind folders, patterns by framework (a file name, or the end of a path), build-tool test trees and `beside_code`, each with a default (BDL-074 G2, `beadloom-2mj3.15`) |
| `why` | `why.py` | Impact analysis via bidirectional BFS (upstream deps + downstream dependents) |

### BFS Algorithm

BFS traverses the graph bidirectionally (outgoing + incoming edges), sorting neighbors by edge priority:

| Priority | Edge type | Description |
|-----------|-----------|----------|
| 1 | part_of | Component is part of |
| 2 | touches_entity | Touches entity |
| 3 | uses / implements | Uses / implements |
| 4 | depends_on | Depends on |
| 5 | touches_code | Touches code |

Parameters: `depth` (default 2), `max_nodes` (node limit, default 20).

### Context Bundle Format

```json
{
  "version": 2,
  "focus": {
    "ref_id": "...",
    "kind": "...",
    "summary": "...",
    "links": [{"url": "...", "label": "..."}],
    "activity": {"level": "hot|warm|cold|dormant", "commits_30d": 8}
  },
  "graph": { "nodes": [...], "edges": [...] },
  "text_chunks": [
    { "doc_path": "...", "section": "spec", "heading": "...", "content": "..." }
  ],
  "code_symbols": [
    { "file_path": "...", "symbol_name": "...", "kind": "function", "line_start": 10, "line_end": 80 }
  ],
  "sync_status": { "stale_docs": [...], "last_reindex": "..." },
  "constraints": [
    { "rule": "...", "description": "...", "type": "deny|require", "definition": {...} }
  ],
  "routes": [
    { "method": "GET", "path": "/api/...", "handler": "...", "file": "...", "line": 1 }
  ],
  "tests": {
    "framework": "pytest",
    "test_files": ["..."],
    "test_count": 10,
    "coverage_estimate": "high|medium|low|none"
  },
  "test_placements": { "unplaced": 3, "other_kind": 1, "mirror": 12 },
  "test_unplaced": "3 of 16 test file(s) are unplaced (not under tests/integration/ or tests/unit/) and bind to no node",
  "test_recognition": "a test file is read when its path matches a pattern of pytest (test_*.py, *_test.py) under the root tests",
  "warning": null
}
```

The `focus.links` and `focus.activity` fields are optional and only present when the focus node's `extra` JSON contains them. The `constraints`, `routes`, and `tests` fields are always present (may be empty list/null).
`test_placements` (BDL-074 C2) counts the project's indexed test files by placement, read by
`infrastructure.repository.count_test_files_by_placement`; it is `{}` for an index older than
the test tables. `test_unplaced` (BDL-074 G2) is the `describe_unplaced()` sentence stated
against the test layout the index recorded, or `null` when no file is unplaced.
`test_recognition` (`beadloom-2mj3.15`) is the `describe_test_file_recognition()` clause —
which paths a test file is read under — or `null` for an index with no recorded layout. The
three keys are additive and the bundle version stays `2`.

### Chunk Priority

Chunks are sorted by section:

| Priority | Section | Description |
|-----------|--------|----------|
| 1 | spec | Specification |
| 2 | invariants | Invariants |
| 3 | constraints | Constraints |
| 4 | api | API |
| 5 | tests | Tests |
| 6 | other | Other |

### Token Estimation

The `estimate_tokens` function provides a rough token count approximation using a chars/4 heuristic. It is used by the `status` CLI command to measure context bundle sizes across all nodes.

### suggest_ref_id

When a non-existent ref_id is requested, the system suggests similar ones using two strategies:

1. **Prefix matching** (case-insensitive) -- `mcp` will find `mcp-server`
2. **Levenshtein distance** -- `PROJ-125` will find `PROJ-123`, `PROJ-124`

Maximum 5 suggestions, prefix matches take priority.

### Code Indexer

Tree-sitter-based code symbol extraction. `_EXTENSION_LOADERS` is the authority and the table
below is its transcription — eleven languages over seventeen extensions. The count is
deliberately not written as a digit: `language_count` in the audit's fact vocabulary means the
languages the audited project is WRITTEN in, so a digit beside the word `languages` here is read
as a claim about that and has to be suppressed to stay green.

| Extension(s) | Language | Symbol types |
|-------------|----------|-------------|
| `.py` | Python | function, class |
| `.ts`, `.tsx` | TypeScript | function, class, type |
| `.js`, `.jsx` | JavaScript | function, class, type (via TS parser) |
| `.go` | Go | function, type |
| `.rs` | Rust | function, class (struct), type (enum, trait) |
| `.kt`, `.kts` | Kotlin | class, function |
| `.java` | Java | class, function, type (interface, annotation) |
| `.swift` | Swift | class, type (protocol), function |
| `.m`, `.mm` | Objective-C | class, type (protocol), function |
| `.c`, `.h` | C | function, class (struct, enum), type |
| `.cpp`, `.hpp` | C++ | function, class (struct, enum, namespace), type |

Annotations are parsed from comments matching the pattern `# beadloom:<key>=<value>`. Module-level annotations (before the first symbol) apply to all symbols in the file; symbol-specific annotations (immediately before a definition) take precedence.

A **module docstring** is read too (BDL-061.50): tree-sitter sees a docstring as a string node rather than a comment, so an annotation written there was invisible to the extractor and to every annotation-keyed reader downstream. Inside a docstring the form is strict — the comment marker at **column 0**, one declaration per line, every line considered — so that an indented code sample, or the in-doc `<!-- beadloom:watches=... -->` form, is read as the EXAMPLE it is and does not silently claim a node. See the [code-indexer SPEC](features/code-indexer/SPEC.md).

### Route Extractor

Extracts API routes from source files using regex pattern matching across 12 frameworks. Includes self-exclusion (skips files named `route_extractor` to avoid false positive matches from regex patterns in the extractor's own source code):

| Language | Frameworks |
|----------|-----------|
| Python | FastAPI, Flask, GraphQL (Strawberry, Ariadne) |
| TypeScript/JS | Express, NestJS, TypeGraphQL |
| Go | Gin, Echo, Fiber |
| Java/Kotlin | Spring Boot |
| Schema files | GraphQL `.graphql`/`.gql`, gRPC `.proto` |

Each extracted route is a `Route` dataclass with fields: `method`, `path`, `handler`, `file_path`, `line`, `framework`. Routes are capped at 100 per file.

### Test Mapping

Since BDL-074 C1 a test file binds to a node by where it lives
(`test_binding.bind_test_file`), and since BDL-074 G2 over the project's test layout
(`test_layout.TestLayout`), read from the `tests:` block of `.beadloom/config.yml`. A node's
`tests:` YAML declaration wins. Otherwise a file in a build tool's test tree (`src/test/java/`,
`src/test/kotlin/`, SwiftPM's `Tests/` by default) or under a root's `unit/` or
`integration/` folder binds to the node that owns the code path its path mirrors
(`tests/unit/<path>/test_<name>.py` names `<root><path>/<name>.py`), by the same
most-specific-`source` rule as code ownership. A file outside every root and test tree binds
to the node whose source holds it (placement `beside_code`), unless the layout sets
`beside_code: false`. Any other file binds to nothing and records a placement: `unowned`,
`unplaced` or `other_kind`. No file is bound by a guess — not by its name, its imports or a
folder named after a node: the path only decides whether a file is a test, by the layout's
patterns, and a file outside every root (default `tests/`, `test/`, `spec/` and a top-level
`__tests__/`, each read where it exists), test tree and node source is not read. The index
records only the roots that exist, so `ctx` and the debt report name only those
(`beadloom-2mj3.17`). The keys, their defaults per language and
the full rule are in the [Test Mapping SPEC](features/test-mapping/SPEC.md).

The reindex stores the binding in the `test_files` / `test_imports` / `test_overrides` tables,
records the layout it read as `meta.test_layout`, and rebuilds `nodes.extra["tests"]` from the
binding in the four-key shape (`framework`, `test_files`, `test_count`, `coverage_estimate`).
`framework` is named from the pattern groups the node's bound files matched (`pytest`,
`go_test`, `jest`, `junit`, `xctest`, joined by `+`). A parent's `test_files` is the union of
its own and every `part_of` descendant's. Coverage estimation is unchanged: more than 3 test
files = high, 1-3 = medium, 0 with a framework = low, no framework = none.

On this repository 167 files are still `unplaced`, of 620 indexed (measured by `beadloom reindex`
on 2026-09-28 at `909a0098`). The placement counts and their history are in the
[Test Mapping SPEC](features/test-mapping/SPEC.md#the-transition), and `beadloom reindex`
prints the current ones on its `Tests:` line.

The count on a node is a count of BOUND files, so it can be short while files are
unplaced. `ctx` says so: when any test file is unplaced, its Markdown output prints the
bundle's `test_unplaced` sentence under the `Tests:` line, ending "so the count above can be
short". The debt report withholds its untested count for the same reason. Every time, `ctx`
also prints the bundle's `test_recognition` clause, capitalised, and the debt report ends its
population with it, because a file outside every root, test tree and node source is not read
at all: a count of test files is a count of the files that clause names.

The name-guessing heuristic this replaced, `test_mapper.py` (framework detection, then
import analysis, naming convention and directory proximity), was deleted in BDL-074 C2
once its last caller, the debt report's collector, read the binding.

### Cache

Two-tier caching system for context bundles:

- **L1 (ContextCache)**: In-memory dict keyed by `(ref_id, depth, max_nodes, max_chunks)`. Lives for the duration of the MCP server process.
- **L2 (SqliteCache)**: Persistent SQLite `bundle_cache` table. Survives MCP server restarts.

Both tiers use mtime-based invalidation (graph directory and docs directory mtimes). Full reindex clears both caches. ETag computation uses SHA-256 of the JSON-serialized bundle (truncated to 16 hex chars).

### Impact Analysis (why)

Bidirectional BFS from a target node, producing upstream dependency trees and downstream dependent trees. Returns an `ImpactSummary` with direct/transitive dependent counts, doc coverage percentage, and stale doc count for downstream nodes. Default depth: 3, max nodes per direction: 50.

Supports a `reverse` mode that emphasizes upstream dependencies: when enabled, upstream traversal uses the full `depth` while downstream traversal is reduced to `max(depth // 2, 1)`. The `render_why_tree` function provides a plain-text tree rendering suitable for CI pipelines and piped output (no Rich markup).

## Invariants

- BFS does not cycle (visited set)
- Each node in the subgraph appears exactly once
- Edges are recorded even for already visited nodes (graph completeness)
- Focus nodes are always included in the subgraph (if they exist)
- `max_nodes` is a hard limit, BFS stops when reached
- Architecture constraints are filtered to only those relevant to the subgraph nodes
- Cache invalidation is mtime-based; no TTL is involved
- Code indexer language configs are lazily loaded and cached per extension
- Route extraction is capped at 100 routes per file

## Constraints

- Maximum chunks in a bundle: 10 (default)
- Maximum nodes in a subgraph: 20 (default)
- BFS depth: 2 (default)
- Levenshtein suggestions: maximum 5
- Impact analysis max nodes per direction: 50 (default)
- Impact analysis depth: 3 (default)
- Route cap per file: 100

## API

### builder.py -- Public Functions

```python
def estimate_tokens(text: str) -> int
```

Estimate token count using chars/4 heuristic.

```python
def suggest_ref_id(conn: sqlite3.Connection, ref_id: str) -> list[str]
```

Suggest existing ref_ids similar to a missing one. Returns up to 5 suggestions.

```python
def bfs_subgraph(
    conn: sqlite3.Connection,
    focus_ref_ids: list[str],
    depth: int = 2,
    max_nodes: int = 20,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]
```

BFS traversal from focus nodes, expanding by edge priority. Returns `(nodes, edges)`.

```python
def collect_chunks(
    conn: sqlite3.Connection,
    ref_ids: set[str],
    max_chunks: int = 10,
) -> list[dict[str, str]]
```

Collect text chunks for nodes in the subgraph, ordered by section priority.

```python
def build_context(
    conn: sqlite3.Connection,
    ref_ids: list[str],
    *,
    depth: int = 2,
    max_nodes: int = 20,
    max_chunks: int = 10,
    intent: IntentReading | None = None,
) -> dict[str, Any]
```

Build a full context bundle for the given focus ref_ids. Raises `LookupError` if any focus ref_id is not found.

`intent` is a read of the project's TO-BE space, supplied by the caller. This
builder takes a connection and no project root, so it cannot read that space
itself; `None` therefore produces `intent.status = "not_checked"` rather than an
absence of intent. The bundle version stays `2` — the key is additive, no
existing key changes meaning, and a consumer asking whether a bundle carries
intent reads `intent.status`, which answers more precisely than a version bump.

### intent.py -- Public Functions

```python
def select_intent(
    reading: IntentReading | None,
    ref_ids: Sequence[str],
    *,
    limit: int = MAX_DECLARATIONS,
) -> dict[str, Any]
```

The `intent` section of a bundle: which epics declared the **focus** nodes, out
of a reading of the TO-BE space. Pure policy — it opens no file and runs no
query, which is what lets it live in the domain while the adapter that reads the
space lives in `application/intent_reader.py`.

Three statuses, and the last two are deliberately not one. `declared` names the
epics with the document and line to read them at. `none_declared` says the space
was read and nothing in it declares this node, carrying `epics_read` and
`epics_declaring_nodes` so it is a measurement rather than a claim.
`not_checked` says nobody looked, with one of four reasons —
`intent_space_not_read`, `no_intent_documents`, `no_epic_declares_any_node`,
`doc_roots_config_error`. `describe_intent_reason` renders each as prose.

At most `MAX_DECLARATIONS` (5) declarations carry their document and line; the
rest keep their names in `also_declared_by`, because a cap that truncated in
silence would be the same defect at a smaller scale. Order is descending
**natural** key, so `ORD-31` sorts above `ORD-4`.

See `components/node-intent/DOC.md`.

### cache.py -- Public Classes and Functions

```python
def compute_etag(bundle: dict[str, Any]) -> str
```

Compute `sha256:<16-char-hex>` ETag for a context bundle.

```python
class CacheEntry:
    bundle: dict[str, Any]
    created_at: float
    graph_mtime: float
    docs_mtime: float
    created_at_iso: str
```

Dataclass holding a cached context bundle with mtime metadata.

```python
class ContextCache:
    def get(self, ref_id, depth, max_nodes, max_chunks, *, graph_mtime=None, docs_mtime=None) -> dict | None
    def get_entry(self, ref_id, depth, max_nodes, max_chunks, *, graph_mtime=None, docs_mtime=None) -> CacheEntry | None
    def put(self, ref_id, depth, max_nodes, max_chunks, bundle, *, graph_mtime, docs_mtime) -> None
    def clear(self) -> None
    def clear_ref(self, ref_id: str) -> None
    def stats(self) -> dict[str, int]
```

In-memory LRU-style cache. Invalidation via graph/docs directory mtimes.

```python
class SqliteCache:
    def __init__(self, conn: sqlite3.Connection) -> None
    def get(self, cache_key, *, graph_mtime=0.0, docs_mtime=0.0) -> tuple[dict, str, str] | None
    def put(self, cache_key, bundle, *, graph_mtime, docs_mtime) -> None
    def clear(self) -> None
    def clear_ref(self, ref_id: str) -> None
```

L2 persistent cache backed by SQLite `bundle_cache` table. Returns `(bundle, etag, created_at)` on hit.

### code_indexer.py -- Public Classes and Functions

```python
class LangConfig:
    language: Language
    comment_types: frozenset[str]
    symbol_types: dict[str, str]
    wrapper_types: frozenset[str]
```

Frozen dataclass for tree-sitter language configuration.

```python
def get_lang_config(extension: str) -> LangConfig | None
```

Get language config for a file extension, or `None` if unsupported/unavailable.

```python
def supported_extensions() -> frozenset[str]
```

Return the set of file extensions with available tree-sitter grammars.

```python
def clear_cache() -> None
```

Clear the language config cache (useful for testing).

```python
def check_parser_availability(extensions: Iterable[str]) -> dict[str, bool]
```

Check whether a tree-sitter parser is available for each extension.

```python
def parse_annotations(line: str) -> dict[str, str]
```

Parse a `beadloom:key=value` annotation from a comment line.

```python
def extract_symbols(file_path: Path) -> list[dict[str, Any]]
```

Extract top-level symbols from a source file using tree-sitter. Returns list of dicts with `symbol_name`, `kind`, `line_start`, `line_end`, `annotations`, `file_hash`.

### route_extractor.py -- Public Classes and Functions

```python
@dataclass(frozen=True)
class Route:
    method: str       # GET, POST, PUT, DELETE, PATCH, * / QUERY, MUTATION, SUBSCRIPTION / RPC
    path: str         # /api/login, /users/{id}, user (GraphQL field), Auth/Login (gRPC)
    handler: str      # function name
    file_path: str    # absolute path to source file
    line: int         # 1-based line number
    framework: str    # fastapi, flask, express, nestjs, spring, gin, echo, fiber, ...
```

```python
def extract_routes(file_path: Path, language: str) -> list[Route]
```

Extract API routes from a source file. The `language` parameter accepts: `"python"`, `"typescript"`, `"javascript"`, `"go"`, `"java"`, `"kotlin"`, `"graphql"`, `"protobuf"`. Returns routes capped at 100 per file. Files named `route_extractor` are skipped (self-exclusion to prevent false positives).

```python
def format_routes_for_display(routes_data: list[dict[str, str]]) -> str
```

Format route data for human-readable display. Separates HTTP routes from GraphQL routes (QUERY/MUTATION/SUBSCRIPTION), with wider path columns and distinct section formatting. Returns a formatted multi-line string.

### test_binding.py -- Public Classes and Functions

```python
@dataclass(frozen=True)
class BoundTestFile:
    path: str
    kind: str | None        # unit | integration | acceptance | self_check | None
    ref_id: str | None
    placement: str          # mirror | beside_code | override | unowned | unplaced | other_kind
```

```python
def bind_test_file(
    path: str,
    *,
    code_files: Collection[str],
    scan_paths: Iterable[str],
    node_sources: Iterable[tuple[str, str]],
    overrides: Iterable[tuple[str, str]],
    layout: TestLayout = TestLayout(),
) -> BoundTestFile
```

Bind one test file (project-relative path) to a node. The declaration in *overrides* wins,
then the mirror of a build tool's test tree, then — outside every root — the node whose source
covers the file when the layout reads tests beside the code, then the mirror for a mirrored
kind. Everything else binds to nothing and says why.

```python
def mirrored_code_path(
    under_kind: str, *, code_files: Collection[str], scan_paths: Iterable[str]
) -> str | None
def tree_mirrored_code_path(
    code_root: str, below: str, *, code_files: Collection[str]
) -> str | None
```

`mirrored_code_path` is the code path a path beneath a kind folder names. The roots are each
scan path and each package directly beneath one. The deepest resolving root wins, and a tie
between equally deep roots resolves to `None`. `tree_mirrored_code_path` (BDL-074 G2b) is the
code path a file below a build tool's test tree names in *code_root*, with the language's test
affix taken off the name and a SwiftPM test target `<Target>Tests` read as `<Target>`; `None`
when the mirrored folder holds no code.

- `is_test_file(path: str) -> bool` -- whether a project-relative path, or a bare file name,
  is a test under the default layout's patterns.
- `name_frameworks(frameworks) -> str` -- one framework name for a set, sorted and joined by
  `+` (`go_test+pytest`), or `none`.
- `union_over_descendants(direct, parent_children) -> dict[str, frozenset[str]]` -- each node's
  files united with every descendant's, each file once.
- `estimate_coverage(file_count: int, *, framework_detected: bool) -> str` -- `high` /
  `medium` / `low` / `none`.
- `summarize_tests(files, counts, *, framework: str) -> dict[str, object]` -- one node's
  `extra["tests"]` in the four-key shape.
- `describe_unplaced(counts: Mapping[str, int], layout: RecordedTestLayout | None = None) -> str | None`
  -- `"U of N test file(s) are unplaced (not under tests/integration/ or tests/unit/) and bind
  to no node"`, or `None` when no file is unplaced. The folders are the recorded layout's
  mirrored kind folders and test trees, and `, nor inside a node's source` follows them when
  tests beside the code are read. With no folder to name it says `(inside no node's source)`
  or `(under no root)` (`beadloom-2mj3.17`); with no layout, the default folders. The one
  wording `ctx` and the debt report share.
- `describe_test_file_recognition(layout: RecordedTestLayout) -> str` (BDL-074 G2) -- what
  makes a file a test file the index reads: the clause starts `a test file is read when its
  path matches a pattern of`, then names each framework group with its patterns in
  parentheses (the group names alone for a record written before the patterns were
  recorded) and the recorded roots or test trees, and ends `or beside a node's code` when
  that is read. With none recorded it names the roots looked for: `under no root, since none
  of tests, test, spec, __tests__ exists, or beside a node's code` (`beadloom-2mj3.17`).
  `ctx` and the debt report state it every time (`beadloom-2mj3.15`).
- `describe_unbound(counts: Mapping[str, int], kinds: Mapping[str, int], layout: RecordedTestLayout | None = None) -> str | None`
  (BDL-074 F1) -- every test file bound to no node, stated by why: `describe_unplaced()`'s
  sentence over *layout*, then the unowned files, then each `other_kind` kind by its count (`A acceptance
  step and S self-check file(s) bind to no node by their kind`). `beadloom mutation
  --changed-since` prints it, so its unplaced count is the one `ctx` and the debt report state.
- Constants: `TEST_ROOT`, `MIRRORED_KINDS` (re-exported from `test_layout`), `OTHER_KINDS`
  (built from `infrastructure.repository`'s `KIND_ACCEPTANCE` and `KIND_SELF_CHECK` since
  BDL-074 F1), the six `PLACEMENT_*` values, `FRAMEWORK_NONE`. The `PLACEMENT_*` values are
  defined in `infrastructure/repository.py` since BDL-074 C3 and re-exported here under the
  same names: the rule engine's `test_binding` rule judges the placement this module assigns,
  and the vocabulary sits below both domains rather than in one of them. `TEST_FILE_PATTERNS`
  and `FRAMEWORK_PYTEST` were removed in BDL-074 G2: the patterns and the framework names are
  the layout's.

### test_file_reader.py -- Public Classes and Functions

```python
@dataclass(frozen=True)
class TestFileContents:
    test_count: int
    imports: tuple[tuple[int, str], ...]   # (line, module)
```

```python
def read_test_file(text: str, *, suffix: str = ".py") -> TestFileContents
def count_test_functions(text: str) -> int
```

For Python, one `ast` parse per file. Module-level `test*` functions and `test*` methods of
`Test*` classes count, sync or async, and a parametrised function counts once. Imports use the
code index's form, except that an aliased `import a.b as c` is recorded here. Text that does
not parse holds nothing. For another suffix (BDL-074 G2) the count is the number of lines its
tests are written in — `func Test...(` for Go, an `it(` or `test(` call for JS/TS, `@Test` for
Java and Kotlin, `func test...(` or a Swift Testing `@Test` function for Swift — and no import
is read. A suffix with no known form counts 0.

### test_layout.py -- Public Classes and Functions

```python
@dataclass(frozen=True)
class TestLayout:
    roots: tuple[str, ...] = DEFAULT_ROOTS          # ("tests", "test", "spec")
    patterns: tuple[tuple[str, tuple[str, ...]], ...] = DEFAULT_PATTERNS
    kind_folders: tuple[tuple[str, str], ...]          # each kind in its own name
    declared_kinds: frozenset[str] = frozenset()
    beside_code: bool = True
    mirrors: tuple[tuple[str, str], ...] = DEFAULT_MIRRORS
```

```python
def load_test_layout(project_root: Path) -> tuple[TestLayout, list[str]]
def layout_from_config(config: Mapping[str, object]) -> tuple[TestLayout, list[str]]
```

The layout `.beadloom/config.yml` declares under `tests:`, and a sentence for each part of it
that cannot be used; the default stands for that part. A `roots` list naming the project
itself or a folder outside it (`.`, `/`, `..`) is refused whole. `TestLayout` answers
`framework_of(path)`, `is_test_file(path)` (a project-relative path, or a bare name),
`folder_of(kind)`, `kind_prefixes(kind)`,
`locate(path)` (the kind and the path below it, or `None` under no root),
`mirror_of(path)` (the test tree, the code tree and the path below it) and
`recorded(present_mirror_roots=(), present_roots=None)`, the `RecordedTestLayout` the index
keeps, patterns included; its `roots` are *present_roots* (`None`: all of them) and
`absent_roots` the rest (`beadloom-2mj3.17`). `pattern_matches(pattern, path)` (`beadloom-2mj3.15`) says whether a pattern matches
the end of a path: the file name for a pattern without `/`, the last folders and the name for
the folder form (`__tests__/**`), where `**` is any number of folders. Constants:
`DEFAULT_ROOTS` (`tests`, `test`, `spec`, `__tests__`), `DEFAULT_PATTERNS` (`pytest`, `go_test`, `jest`, `junit`, `xctest`),
`DEFAULT_MIRRORS`, `CONFIG_PATH`, `CONFIG_KEY`, `KIND_UNIT`, `KIND_INTEGRATION`,
`MIRRORED_KINDS`, `KINDS`. The defaults per language are in the
[Test Mapping SPEC](features/test-mapping/SPEC.md#configuration-the-test-layout).

### search.py -- Public Functions

```python
def search_fts5(
    conn: sqlite3.Connection,
    query: str,
    *,
    kind: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]
```

FTS5 MATCH search. Returns list of result dicts with `ref_id`, `kind`, `summary`, `snippet`, `rank`.

```python
def populate_search_index(conn: sqlite3.Connection) -> int
```

Clear and rebuild the `search_index` FTS5 table. One row per node, plus one row per
document bound to NO node — the second half is what makes the TO-BE space searchable
(BDL-061 S5). A planning document describes intent rather than one node's code, so it
carries no `ref_id`, and a node-only index could never return it however well it was
chunked. Such a row keys `ref_id` on the document's path (the only identifier it has,
and the one a reader needs to open the file) and `kind` on its SPACE, so
`search --kind to_be` narrows to intent without a second index. Returns row count.

```python
def has_fts5(conn: sqlite3.Connection) -> bool
```

Check whether the FTS5 search index exists and contains data.

### why.py -- Public Classes and Functions

```python
class NodeInfo:
    ref_id: str
    kind: str
    summary: str

class TreeNode:
    ref_id: str
    kind: str
    summary: str
    edge_kind: str
    children: tuple[TreeNode, ...]

class ImpactSummary:
    downstream_direct: int
    downstream_transitive: int
    doc_coverage: float
    stale_count: int

class WhyResult:
    node: NodeInfo
    upstream: tuple[TreeNode, ...]
    downstream: tuple[TreeNode, ...]
    impact: ImpactSummary
```

```python
def analyze_node(
    conn: sqlite3.Connection,
    ref_id: str,
    depth: int = 3,
    max_nodes: int = 50,
    *,
    reverse: bool = False,
) -> WhyResult
```

Perform impact analysis on a node. When `reverse=True`, upstream traversal uses the full `depth` while downstream is reduced to `max(depth // 2, 1)`. Raises `LookupError` if not found.

```python
def render_why(result: WhyResult, console: Console) -> None
```

Render a WhyResult using Rich panels and trees.

```python
def render_why_tree(result: WhyResult) -> str
```

Render a WhyResult as a plain-text dependency tree with box-drawing characters. Suitable for CI/piping -- no Rich markup, no panels. Returns a multi-line string.

```python
def result_to_dict(result: WhyResult) -> dict[str, object]
```

Serialize a WhyResult to a JSON-compatible dict.

### CLI Integration

The context-oracle domain exposes functionality through CLI commands registered in the `services/commands/` package:

- **`services/commands/query.py`** — read-only context/graph query commands:
  - `beadloom ctx REF_IDS... [--json] [--markdown] [--depth N] [--max-nodes N] [--max-chunks N] [--project DIR]` -- Build and display context bundle
  - `beadloom search QUERY [--kind KIND] [--limit N] [--json] [--project DIR]` -- FTS5 search with LIKE fallback. `KIND` is a node kind or one of the three documentation spaces (`to_be`/`as_is`/`working`), because a document bound to no node is indexed under its space (BDL-061 S5)
  - `beadloom why REF_ID [--depth N] [--reverse] [--format panel|tree] [--json] [--project DIR]` -- Impact analysis
  - `beadloom graph [REF_IDS...] [--json] [--depth N] [--format mermaid|c4|c4-plantuml] [--level context|container|component] [--scope REF_ID] [--project DIR]` -- Architecture graph (Mermaid, C4-Mermaid, C4-PlantUML, or JSON). C4 formats use `--level` for diagram granularity and `--scope` to show internals of one container (only with `--level=component`).
- **`services/commands/federation.py`** — federation, gate, and lint commands:
  - `beadloom lint [--strict] [--fail-on-warn] [--no-reindex] [--format rich|json|porcelain|github] [--project DIR]` -- Architecture lint rules. The `github` format emits GitHub Actions `::error` annotations for CI integration, led by a `::notice` per layer rule stating how much of its edge set that rule judged (BDL-070 A3); `porcelain` states the same fact on a `# `-marked line ahead of its violation records.
  - The Gate renderers live here too. `_format_gate_rich` prints one line per step through `application.gate.gate_step_line` (`[STATUS] name: summary`) rather than spelling that shape itself, because `beadloom init` quotes the same line to say what `beadloom ci` will report about the graph it just judged (BDL-067 `.14`). All three renderers also print the ROOM the verdict was taken in and how many declared rooms the run did not enter (BDL-068 S3.2), from the census `GateResult.room` carries — one computation, three renderings, so the formats cannot say different things about one run. Since BDL-068 S6 they print a second qualification read from the same result — the verifications the project's pipeline declares that no step of the run performed (`GateResult.coverage`), whose block every surface quotes from `application.gate_coverage.gate_coverage_lines` for the same reason (BDL-UX #247).

## Testing

Tests are located in:

| Test file | Module under test | Key scenarios |
|-----------|-------------------|---------------|
| `tests/test_context_builder.py` | `builder.py` | BFS traversal, chunk collection, bundle assembly, ref_id validation, suggestions |
| `tests/test_cache.py` | `cache.py` | L1 get/put, mtime invalidation, clear, clear_ref, stats |
| `tests/test_code_indexer.py` | `code_indexer.py` | Symbol extraction, annotation parsing, language config loading |
| `tests/test_route_extractor.py` | `route_extractor.py` | Route extraction across frameworks, safety cap, edge cases |
| `tests/unit/context_oracle/test_binding/test_a_test_file_binds_to_the_node_its_path_mirrors.py` | `test_binding.py` | Mirror, declaration, placements, deepest root, union over descendants |
| `tests/unit/context_oracle/test_binding/test_the_unplaced_share_is_one_sentence.py` | `test_binding.py` | `describe_unplaced()` |
| `tests/unit/context_oracle/test_file_reader/test_a_test_file_is_read_for_its_tests_and_imports.py` | `test_file_reader.py` | Test counting and imports |
| `tests/unit/context_oracle/test_binding/test_a_test_beside_the_code_binds_to_the_node_covering_it.py` | `test_binding.py` | Placement `beside_code`, and `beside_code: false` |
| `tests/unit/context_oracle/test_binding/test_a_test_in_a_build_tools_test_tree_binds_by_its_mirror.py` | `test_binding.py` | Maven, Gradle and SwiftPM test trees, the test affixes |
| `tests/unit/context_oracle/test_binding/test_the_unplaced_sentence_names_the_declared_folders.py` | `test_binding.py` | `describe_unplaced()` against a recorded layout |
| `tests/unit/context_oracle/test_file_reader/test_a_test_file_in_another_language_is_counted.py` | `test_file_reader.py` | Go, JS/TS, JUnit, XCTest and Swift Testing counts |
| `tests/unit/context_oracle/test_layout/test_the_test_layout_is_read_from_config.py` | `test_layout.py` | The `tests:` block, its defaults and the unusable declarations |
| `tests/unit/context_oracle/test_layout/test_java_kotlin_and_swift_tests_are_named_by_convention.py` | `test_layout.py` | The `junit` and `xctest` default patterns |
| `tests/unit/context_oracle/test_layout/test_a_pattern_with_a_folder_matches_the_end_of_the_path.py` | `test_layout.py` | The folder form, the folder-form defaults and the refused roots |
| `tests/integration/context_oracle/builder/test_the_context_bundle_states_the_unplaced_sentence_of_the_recorded_layout.py` | `builder.py` | `test_unplaced` and `test_recognition` in the bundle |
| `tests/integration/context_oracle/builder/test_the_context_bundle_carries_the_test_placements.py` | `builder.py` | `test_placements` in the bundle |
| `tests/integration/context_oracle/builder/test_the_context_bundle_carries_a_nodes_tests.py` | `builder.py` | The focus node's `tests` in the bundle |
| `tests/unit/services/commands/test_the_ctx_markdown_states_the_tests_line.py` | `services/commands` (ctx) | The unplaced line under `Tests:` |
| `tests/unit/services/commands/test_the_ctx_markdown_prints_the_bundles_unplaced_sentence.py` | `services/commands` (ctx) | The bundle's `test_unplaced`, and the fallback for a cached bundle |
| `tests/unit/services/commands/test_the_ctx_markdown_says_which_files_count_as_tests.py` | `services/commands` (ctx) | The bundle's `test_recognition` under `Tests:`, every time |
| `tests/integration/application/debt_report/test_the_debt_report_reads_the_test_binding.py` | `application/debt_report` | The debt report's untested count |
| `tests/test_search.py` | `search.py` | FTS5 search, kind filtering, limit, empty query, escaping, snippets, index rebuild |
| `tests/test_why.py` | `why.py` | Impact analysis, upstream/downstream trees, reverse mode, render functions |
| `tests/test_cli_why.py` | `services/commands/query.py` (why) | CLI why command, --reverse flag, --format tree, --json output |
