# Context Oracle

Context Oracle is the core domain of beadloom, responsible for building context bundles via BFS traversal of the architecture graph, code symbol indexing, caching, full-text search, API route extraction, test mapping, and impact analysis.

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
| `code_indexer` | `code_indexer.py` | Tree-sitter parsing and `beadloom:` annotation extraction for 12 languages |
| `search` | `search.py` | FTS5 full-text search over architecture graph nodes and documentation |
| `route_extractor` | `route_extractor.py` | API route extraction via tree-sitter AST + regex fallback for 12 frameworks |
| `test_mapper` | `test_mapper.py` | Test framework detection and test file to source node mapping |
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
  "warning": null
}
```

The `focus.links` and `focus.activity` fields are optional and only present when the focus node's `extra` JSON contains them. The `constraints`, `routes`, and `tests` fields are always present (may be empty list/null).

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

Tree-sitter-based code symbol extraction supporting 12 languages:

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

### Route Extractor

Extracts API routes from source files using regex pattern matching across 12 frameworks:

| Language | Frameworks |
|----------|-----------|
| Python | FastAPI, Flask, GraphQL (Strawberry, Ariadne) |
| TypeScript/JS | Express, NestJS, TypeGraphQL |
| Go | Gin, Echo, Fiber |
| Java/Kotlin | Spring Boot |
| Schema files | GraphQL `.graphql`/`.gql`, gRPC `.proto` |

Each extracted route is a `Route` dataclass with fields: `method`, `path`, `handler`, `file_path`, `line`, `framework`. Routes are capped at 100 per file.

### Test Mapper

Detects test frameworks and maps test files to source architecture nodes:

| Framework | Detection | Test patterns |
|-----------|-----------|---------------|
| pytest | `conftest.py`, `test_*.py`, `*_test.py` | `def test_*` |
| jest | `jest.config.*`, `*.test.ts`, `*.spec.ts`, `__tests__/` | `test(` / `it(` |
| go_test | `*_test.go` | `func Test*` |
| junit | `src/test/`, `*Test.java`, `*Test.kt` | `@Test` |
| xctest | `*Tests.swift`, `*Tests/` | `func test*` |

Mapping strategies (in priority order):
1. Import analysis (pytest only) -- parse `from`/`import` statements
2. Naming convention -- `test_auth.py` maps to `auth` node
3. Directory proximity -- `tests/auth/test_login.py` maps to `auth` node

Coverage estimation: >3 test files = high, 1-3 = medium, 0 with framework detected = low, no framework = none.

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
) -> dict[str, Any]
```

Build a full context bundle for the given focus ref_ids. Raises `LookupError` if any focus ref_id is not found.

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

Extract API routes from a source file. The `language` parameter accepts: `"python"`, `"typescript"`, `"javascript"`, `"go"`, `"java"`, `"kotlin"`, `"graphql"`, `"protobuf"`. Returns routes capped at 100 per file.

### test_mapper.py -- Public Classes and Functions

```python
@dataclass(frozen=True)
class TestMapping:
    framework: str          # pytest, jest, go_test, junit, xctest
    test_files: list[str]   # relative paths
    test_count: int         # number of test functions/methods
    coverage_estimate: str  # high | medium | low | none
```

```python
def map_tests(
    project_root: Path,
    source_dirs: dict[str, str],
) -> dict[str, TestMapping]
```

Map test files to source nodes. `source_dirs` maps `ref_id -> source_path` (relative). Returns a `TestMapping` for each source node.

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

Clear and rebuild the `search_index` FTS5 table from `nodes` and `chunks`. Returns row count.

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

The context-oracle domain exposes functionality through several CLI commands in `cli.py`:

- `beadloom ctx REF_IDS... [--json] [--markdown] [--depth N] [--max-nodes N] [--max-chunks N] [--project DIR]` -- Build and display context bundle
- `beadloom search QUERY [--kind KIND] [--limit N] [--json] [--project DIR]` -- FTS5 search with LIKE fallback
- `beadloom why REF_ID [--depth N] [--reverse] [--format panel|tree] [--json] [--project DIR]` -- Impact analysis
- `beadloom graph [REF_IDS...] [--json] [--depth N] [--project DIR]` -- Architecture graph (Mermaid or JSON)
- `beadloom lint [--strict] [--fail-on-warn] [--no-reindex] [--format rich|json|porcelain] [--project DIR]` -- Architecture lint rules

## Testing

Tests are located in:

| Test file | Module under test | Key scenarios |
|-----------|-------------------|---------------|
| `tests/test_context_builder.py` | `builder.py` | BFS traversal, chunk collection, bundle assembly, ref_id validation, suggestions |
| `tests/test_cache.py` | `cache.py` | L1 get/put, mtime invalidation, clear, clear_ref, stats |
| `tests/test_code_indexer.py` | `code_indexer.py` | Symbol extraction, annotation parsing, language config loading |
| `tests/test_route_extractor.py` | `route_extractor.py` | Route extraction across frameworks, safety cap, edge cases |
| `tests/test_test_mapper.py` | `test_mapper.py` | Framework detection, test file discovery, mapping strategies, coverage estimation |
| `tests/test_search.py` | `search.py` | FTS5 search, kind filtering, limit, empty query, escaping, snippets, index rebuild |
| `tests/test_why.py` | `why.py` | Impact analysis, upstream/downstream trees, reverse mode, render functions |
| `tests/test_cli_why.py` | `cli.py` (why) | CLI why command, --reverse flag, --format tree, --json output |
