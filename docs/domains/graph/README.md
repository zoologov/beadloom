# Graph Format

YAML format for describing the project architecture graph, with loader, diff engine, rule engine, import resolver, and linter.

## Specification

### File Location

The graph is stored in `.beadloom/_graph/*.yml`. All files with the `.yml` extension in this directory are loaded during reindex, sorted by name.

### YAML Structure

```yaml
nodes:
  - ref_id: my-service        # Unique identifier (required)
    kind: service              # Node type (required)
    summary: "Description"     # Brief description (required)
    source: src/my_service/    # Path to source code (optional)
    docs:                      # Linked documents (optional)
      - docs/my-service.md
    # Any additional fields go into extra (JSON)

edges:
  - src: my-service            # Source ref_id (required)
    dst: core                  # Destination ref_id (required)
    kind: part_of              # Edge type (required)
```

### Node Types (node kind)

| Kind | Description |
|------|----------|
| `domain` | Domain area |
| `feature` | Feature |
| `service` | Service / module |
| `entity` | Data entity |
| `adr` | Architecture Decision Record |

### Edge Types (edge kind)

| Kind | Description | BFS Priority |
|------|----------|---------------|
| `part_of` | A is part of B | 1 |
| `touches_entity` | A touches entity B | 2 |
| `uses` | A uses B | 3 |
| `implements` | A implements B | 3 |
| `depends_on` | A depends on B | 4 |
| `touches_code` | A touches code of B | 5 |

### The docs Field

An array of paths to documents linked to the node. Paths are specified relative to the project root (e.g., `docs/spec.md`). During reindex, a doc_path -> ref_id mapping is built to link chunks to graph nodes.

### Modules

- **loader.py** -- YAML graph parser and SQLite loader. Parses `.beadloom/_graph/*.yml` files and populates `nodes` and `edges` tables. Validates ref_id uniqueness and edge integrity. Supports in-place YAML node updates.
- **diff.py** -- Graph delta engine. Compares current on-disk graph YAML against state at a given git ref. Detects added, removed, and changed nodes and edges. Provides Rich rendering and JSON serialization. See [graph-diff SPEC](features/graph-diff/SPEC.md).
- **rule_engine.py** -- Architecture rule engine. Parses `rules.yml` (schema v1/v2/v3), validates rules against the graph DB, and evaluates deny/require/cycle/import-boundary rules against code imports, edges, and file paths. Supports severity levels (`error`, `warn`), tag-based node matching, and bulk tag assignments (v3).
- **import_resolver.py** -- Multi-language import analysis. Extracts imports via tree-sitter for Python, TypeScript/JavaScript, Go, Rust, Kotlin, Java, Swift, Objective-C, and C/C++. Resolves imports to graph node ref_ids. Generates `depends_on` edges from resolved imports.
- **linter.py** -- Linter orchestrator. Loads rules, optionally runs incremental reindex, evaluates all rules, and returns structured `LintResult` with violations, counts, and timing. Provides Rich, JSON, and porcelain output formatters.

## Invariants

- `ref_id` must be unique across all YAML files
- `kind` for nodes is restricted to: domain, feature, service, entity, adr
- `kind` for edges is restricted to: part_of, depends_on, uses, implements, touches_entity, touches_code
- Edges referencing non-existent nodes are skipped with a warning
- Duplicate ref_id values are skipped with an error
- Rules file supports schema versions 1, 2, and 3
- Schema v3 adds optional top-level `tags:` block for bulk tag assignments and tag-based matching in `NodeMatcher`
- Rule names must be unique within `rules.yml`
- Each rule must have exactly one of: `deny`, `require`, `forbid_cycles`, or `forbid_import`
- Rule severity must be one of: `error`, `warn`

## API

### Module `src/beadloom/graph/loader.py`

- `parse_graph_file(path: Path) -> ParsedFile` -- Parse a single YAML graph file into nodes and edges.
- `load_graph(graph_dir: Path, conn: sqlite3.Connection) -> GraphLoadResult` -- Load all `*.yml` files from a directory into SQLite (two-pass: nodes then edges). Returns `GraphLoadResult` with `nodes_loaded`, `edges_loaded`, `errors`, `warnings`.
- `update_node_in_yaml(graph_dir: Path, conn: sqlite3.Connection, ref_id: str, *, summary: str | None = None, source: str | None = None) -> bool` -- Update a node's fields in YAML source and SQLite. Returns `True` if node was found and updated.
- `get_node_tags(conn: sqlite3.Connection, ref_id: str) -> set[str]` -- Extract tags from a node's `extra` JSON column. Returns an empty set when the node does not exist or has no `tags` key in its extra data.

### Module `src/beadloom/graph/diff.py`

- `compute_diff(project_root: Path, since: str = "HEAD") -> GraphDiff` -- Compare current graph YAML with state at a git ref. Raises `ValueError` on invalid ref.
- `render_diff(diff: GraphDiff, console: Console) -> None` -- Render a GraphDiff using Rich console output.
- `diff_to_dict(diff: GraphDiff) -> dict[str, object]` -- Serialize a GraphDiff to a JSON-compatible dict.

### Module `src/beadloom/graph/rule_engine.py`

- `load_rules(rules_path: Path) -> list[Rule]` -- Parse `rules.yml` and return validated `Rule` objects (union of `DenyRule | RequireRule | CycleRule | ImportBoundaryRule`). Raises `ValueError` on schema errors.
- `load_rules_with_tags(rules_path: Path) -> tuple[list[Rule], dict[str, list[str]]]` -- Parse `rules.yml` returning both rules and tag assignments from the optional top-level `tags:` block (schema v3). Returns `(rules, tag_assignments)` tuple.
- `validate_rules(rules: list[Rule], conn: sqlite3.Connection) -> list[str]` -- Validate rules against the database. Returns warning messages for ref_ids not found in nodes.
- `evaluate_deny_rules(conn: sqlite3.Connection, rules: list[DenyRule]) -> list[Violation]` -- Evaluate deny rules against code_imports. Supports tag-based matching via `get_node_tags()`.
- `evaluate_require_rules(conn: sqlite3.Connection, rules: list[RequireRule]) -> list[Violation]` -- Evaluate require rules against nodes and edges. Supports tag-based matching.
- `evaluate_cycle_rules(conn: sqlite3.Connection, rules: list[CycleRule]) -> list[Violation]` -- Evaluate cycle rules using iterative DFS over edges of specified kind(s). Reports each unique cycle once with the full path.
- `evaluate_import_boundary_rules(conn: sqlite3.Connection, rules: list[ImportBoundaryRule]) -> list[Violation]` -- Evaluate import boundary rules against code_imports using `fnmatch` glob patterns on file paths.
- `evaluate_all(conn: sqlite3.Connection, rules: list[Rule]) -> list[Violation]` -- Evaluate all rules (deny + require + cycle + import boundary) and return sorted violations.

### Module `src/beadloom/graph/import_resolver.py`

- `extract_imports(file_path: Path) -> list[ImportInfo]` -- Extract import statements from a source file using tree-sitter. Supports Python, TS/JS, Go, Rust, Kotlin, Java, Swift, Objective-C, C/C++.
- `resolve_import_to_node(import_path: str, file_path: Path, conn: sqlite3.Connection, scan_paths: list[str] | None = None, *, is_ts: bool = False) -> str | None` -- Map an import path to a graph node ref_id via code_symbols annotations or hierarchical source-prefix matching.
- `index_imports(project_root: Path, conn: sqlite3.Connection) -> int` -- Scan all source files, index imports into code_imports table, and create `depends_on` edges. Returns count of imports indexed.
- `create_import_edges(conn: sqlite3.Connection) -> int` -- Create `depends_on` edges from resolved code imports. Returns number of edges created.

### Module `src/beadloom/graph/linter.py`

- `lint(project_root: Path, *, rules_path: Path | None = None, reindex_before: bool = True) -> LintResult` -- Run the full lint process: optional reindex, load rules, evaluate, return results. Raises `LintError` on invalid configuration.
- `format_rich(result: LintResult) -> str` -- Format a `LintResult` as human-readable text with violation markers.
- `format_json(result: LintResult) -> str` -- Format a `LintResult` as structured JSON with violations array and summary.
- `format_porcelain(result: LintResult) -> str` -- Format a `LintResult` as machine-readable one-line-per-violation output.

### Public Data Classes

| Class | Module | Description |
|-------|--------|----------|
| `ParsedFile` | loader | Result of parsing a single YAML file: `nodes`, `edges` |
| `GraphLoadResult` | loader | Summary: `nodes_loaded`, `edges_loaded`, `errors`, `warnings` |
| `NodeChange` | diff | Frozen dataclass: `ref_id`, `kind`, `change_type`, `old_summary`, `new_summary` |
| `EdgeChange` | diff | Frozen dataclass: `src`, `dst`, `kind`, `change_type` |
| `GraphDiff` | diff | Frozen dataclass: `since_ref`, `nodes`, `edges`, property `has_changes` |
| `NodeMatcher` | rule_engine | Frozen dataclass: `ref_id`, `kind`, `tag`, method `matches(node_ref_id, node_kind, *, tags=None)` |
| `DenyRule` | rule_engine | Frozen dataclass: `name`, `description`, `from_matcher`, `to_matcher`, `unless_edge`, `severity` |
| `RequireRule` | rule_engine | Frozen dataclass: `name`, `description`, `for_matcher`, `has_edge_to`, `edge_kind`, `severity` |
| `CycleRule` | rule_engine | Frozen dataclass: `name`, `description`, `edge_kind` (str or tuple), `max_depth` (default 10), `severity` |
| `ImportBoundaryRule` | rule_engine | Frozen dataclass: `name`, `description`, `from_glob`, `to_glob`, `severity`. Matches file paths via fnmatch globs against `code_imports` |
| `Violation` | rule_engine | Frozen dataclass: `rule_name`, `rule_description`, `rule_type` (`deny`/`require`/`cycle`/`forbid_import`), `severity`, `file_path`, `line_number`, `from_ref_id`, `to_ref_id`, `message` |
| `ImportInfo` | import_resolver | Frozen dataclass: `file_path`, `line_number`, `import_path`, `resolved_ref_id` |
| `LintResult` | linter | Dataclass: `violations`, `rules_evaluated`, `files_scanned`, `imports_resolved`, `elapsed_ms`, properties `error_count`, `warning_count`, `has_errors` |
| `LintError` | linter | Exception raised on invalid lint configuration |

## Constraints

- Files must be valid YAML
- UTF-8 encoding
- Only files with the `.yml` extension (not `.yaml`)

## Testing

Tests: `tests/test_graph_loader.py`, `tests/test_cli_graph.py`, `tests/test_diff.py`, `tests/test_cli_diff.py`, `tests/test_rule_engine.py`, `tests/test_rule_severity.py`, `tests/test_cycle_rule.py`, `tests/test_import_boundary_rule.py`, `tests/test_linter.py`, `tests/test_cli_lint.py`, `tests/test_import_resolver.py`, `tests/test_import_scan.py`, `tests/test_symbol_diff_polish.py`
