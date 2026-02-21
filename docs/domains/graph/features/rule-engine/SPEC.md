# Rule Engine

Architecture-as-Code rule engine: parse `rules.yml`, validate rule definitions, and evaluate them against the architecture graph and code imports.

**Source:** `src/beadloom/graph/rule_engine.py`

---

## Specification

### Purpose

Enforce architectural constraints declaratively. Rules are defined in a YAML file and evaluated against the graph database (nodes, edges, code_imports, code_symbols, file_index, and sync_state tables). Seven rule types exist:

| Type | Keyword | Semantics |
|------|---------|-----------|
| **deny** | `deny` | Forbid imports between matched nodes |
| **require** | `require` | Mandate specific edge relationships |
| **forbid_cycles** | `forbid_cycles` | Detect circular dependencies via DFS |
| **forbid_import** | `forbid_import` | Forbid file-level imports between glob-matched paths |
| **forbid_edge** | `forbid` | Forbid specific edge patterns between tagged node groups |
| **layer** | `layers` | Enforce layered architecture direction |
| **cardinality** | `check` | Enforce complexity limits per node |

### Constants

```python
VALID_NODE_KINDS: frozenset[str] = frozenset({
    "domain", "feature", "service", "entity", "adr"
})

VALID_EDGE_KINDS: frozenset[str] = frozenset({
    "part_of", "depends_on", "uses", "implements", "touches_entity", "touches_code"
})

SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1, 2, 3})
```

### Data Structures

All dataclasses are frozen (immutable).

#### `NodeMatcher`

Matches graph nodes by `ref_id`, `kind`, `tag`, and/or `exclude`. In deny rules, at least one of `ref_id`, `kind`, or `tag` must be non-`None`. In require rules, an empty matcher (`has_edge_to: {}`) is allowed and matches **any** node — used for "must have at least one edge of this kind" semantics.

| Field     | Type                        | Description                                                        |
|-----------|-----------------------------|--------------------------------------------------------------------|
| `ref_id`  | `str \| None`               | Exact ref_id to match, or `None` for any.                          |
| `kind`    | `str \| None`               | Node kind to match, or `None` for any.                             |
| `tag`     | `str \| None`               | Tag the node must have, or `None` for any.                         |
| `exclude` | `tuple[str, ...] \| None`   | Ref_ids to exclude from matching, or `None` for no exclusions.     |

```python
def matches(self, node_ref_id: str, node_kind: str, *, tags: set[str] | None = None) -> bool
```

Returns `False` immediately if `node_ref_id` is in `exclude`. Otherwise returns `True` if all non-`None` fields (`ref_id`, `kind`, `tag`) match the given node. The `tags` parameter is optional for backward compatibility; when `tags` is `None` and `self.tag` is set, the tag check is skipped.

In YAML, `exclude` accepts either a single string or a list of strings; both are normalized to a tuple internally by `_parse_node_matcher()`.

#### `DenyRule`

Forbids imports between nodes matched by `from_matcher` and `to_matcher`.

| Field          | Type              | Description                                       |
|----------------|-------------------|---------------------------------------------------|
| `name`         | `str`             | Unique rule name.                                 |
| `description`  | `str`             | Human-readable description.                       |
| `from_matcher` | `NodeMatcher`     | Matches the source (importing) node.              |
| `to_matcher`   | `NodeMatcher`     | Matches the target (imported) node.               |
| `unless_edge`  | `tuple[str, ...]` | Edge kinds that exempt the import from violation. |

#### `RequireRule`

Requires that matched nodes have at least one outgoing edge to a target node.

| Field         | Type           | Description                                        |
|---------------|----------------|----------------------------------------------------|
| `name`        | `str`          | Unique rule name.                                  |
| `description` | `str`          | Human-readable description.                        |
| `for_matcher` | `NodeMatcher`  | Matches nodes that must satisfy the rule.          |
| `has_edge_to` | `NodeMatcher`  | Matches the required target node.                  |
| `edge_kind`   | `str \| None`  | If set, restricts to edges of this specific kind.  |

#### `CycleRule`

Detects circular dependencies in the graph using iterative DFS.

| Field         | Type                       | Description                                        |
|---------------|----------------------------|----------------------------------------------------|
| `name`        | `str`                      | Unique rule name.                                  |
| `description` | `str`                      | Human-readable description.                        |
| `edge_kind`   | `str \| tuple[str, ...]`   | Edge kind(s) to check for cycles.                  |
| `max_depth`   | `int`                      | Maximum DFS depth (default 10).                    |
| `severity`    | `str`                      | `"error"` or `"warn"`.                             |

#### `ImportBoundaryRule`

Controls file-level import boundaries using fnmatch glob patterns against `code_imports`.

| Field         | Type           | Description                                        |
|---------------|----------------|----------------------------------------------------|
| `name`        | `str`          | Unique rule name.                                  |
| `description` | `str`          | Human-readable description.                        |
| `from_glob`   | `str`          | Glob pattern matching source file paths.           |
| `to_glob`     | `str`          | Glob pattern matching forbidden target file paths. |
| `severity`    | `str`          | `"error"` or `"warn"`.                             |

#### `ForbidEdgeRule`

Forbids graph edges between matched nodes (operates on `edges` table, unlike DenyRule which checks `code_imports`).

| Field          | Type              | Description                                        |
|----------------|-------------------|----------------------------------------------------|
| `name`         | `str`             | Unique rule name.                                  |
| `description`  | `str`             | Human-readable description.                        |
| `from_matcher` | `NodeMatcher`     | Matches the source node.                           |
| `to_matcher`   | `NodeMatcher`     | Matches the target node.                           |
| `edge_kind`    | `str \| None`     | If set, restricts to edges of this kind.           |
| `severity`     | `str`             | `"error"` or `"warn"`.                             |

#### `LayerDef`

Defines a single architecture layer for use in `LayerRule`.

| Field  | Type   | Description       |
|--------|--------|-------------------|
| `name` | `str`  | Layer name.       |
| `tag`  | `str`  | Tag identifying nodes in this layer. |

#### `LayerRule`

Enforces dependency direction between ordered architecture layers.

| Field        | Type                  | Description                                             |
|--------------|-----------------------|---------------------------------------------------------|
| `name`       | `str`                 | Unique rule name.                                       |
| `description`| `str`                 | Human-readable description.                             |
| `layers`     | `tuple[LayerDef, ...]`| Ordered layers (top to bottom).                         |
| `enforce`    | `str`                 | `"top-down"` — higher layers may depend on lower, not reverse. |
| `allow_skip` | `bool`                | If `False`, forbids skipping intermediate layers (default `True`). |
| `edge_kind`  | `str`                 | Edge kind to check (default `"uses"`).                  |
| `severity`   | `str`                 | `"error"` or `"warn"`.                                  |

#### `CardinalityRule`

Enforces complexity limits per node (architectural smell detection).

| Field              | Type              | Description                                    |
|--------------------|-------------------|------------------------------------------------|
| `name`             | `str`             | Unique rule name.                              |
| `description`      | `str`             | Human-readable description.                    |
| `for_matcher`      | `NodeMatcher`     | Matches nodes to check.                        |
| `max_symbols`      | `int \| None`     | Maximum symbols per node.                      |
| `max_files`        | `int \| None`     | Maximum files per node.                        |
| `min_doc_coverage` | `float \| None`   | Minimum documentation coverage percentage.     |
| `severity`         | `str`             | `"error"` or `"warn"` (default `"warn"`).      |

#### `Rule` (type alias)

```python
Rule = DenyRule | RequireRule | CycleRule | ImportBoundaryRule | ForbidEdgeRule | LayerRule | CardinalityRule
```

#### `Violation`

| Field              | Type           | Description                                     |
|--------------------|----------------|-------------------------------------------------|
| `rule_name`        | `str`          | Name of the violated rule.                      |
| `rule_description` | `str`          | Description of the violated rule.               |
| `rule_type`        | `str`          | `"deny"`, `"require"`, `"cycle"`, `"forbid_import"`, `"forbid"`, `"layer"`, or `"cardinality"`. |
| `severity`         | `str`          | `"error"` or `"warn"`.                          |
| `file_path`        | `str \| None`  | Source file path (for deny/import violations).   |
| `line_number`      | `int \| None`  | Line number (for deny/import violations).        |
| `from_ref_id`      | `str \| None`  | Source node ref_id.                              |
| `to_ref_id`        | `str \| None`  | Target node ref_id.                              |
| `message`          | `str`          | Human-readable explanation of the violation.     |

### rules.yml Schema

Schema supports versions 1, 2, and 3. Version 3 adds the optional top-level `tags:` block for bulk tag assignments.

```yaml
version: 3

# Optional (v3): bulk tag assignments — tag_name: [ref_id, ...]
tags:
  layer-service: [cli, mcp-server, tui]
  layer-domain: [context-oracle, doc-sync, graph, onboarding]

rules:
  # --- deny: forbid imports between matched nodes ---
  - name: <unique-rule-name>
    description: "<description>"
    deny:
      from: { ref_id: ..., kind: ..., tag: ..., exclude: [...] }  # NodeMatcher
      to:   { ref_id: ..., kind: ..., tag: ..., exclude: [...] }  # NodeMatcher
      unless_edge: [<edge_kind>, ...]    # optional, defaults to []

  # --- require: mandate specific edge relationships ---
  - name: <unique-rule-name>
    description: "<description>"
    require:
      for:         { ref_id: ..., kind: ..., exclude: [...] }  # NodeMatcher
      has_edge_to: { ref_id: ..., kind: ... }  # NodeMatcher (or {} for any node)
      edge_kind: <edge_kind>                   # optional

  # --- forbid_cycles: detect circular dependencies ---
  - name: <unique-rule-name>
    description: "<description>"
    severity: warn                             # optional, default: error
    forbid_cycles:
      edge_kind: depends_on                    # string or list of edge kinds

  # --- forbid_import: file-level import boundaries ---
  - name: <unique-rule-name>
    description: "<description>"
    forbid_import:
      from: "src/pkg/module_a/**"              # fnmatch glob pattern
      to: "src/pkg/module_b/**"                # fnmatch glob pattern

  # --- forbid (forbid_edge): forbid graph edges between tagged groups ---
  - name: <unique-rule-name>
    description: "<description>"
    forbid:
      from: { tag: ui-layer }                  # NodeMatcher with tag
      to: { tag: native-layer }
      edge_kind: uses                          # optional

  # --- layers: enforce layered architecture ---
  - name: <unique-rule-name>
    description: "<description>"
    severity: warn
    layers:
      - name: services
        tag: layer-service
      - name: domains
        tag: layer-domain
      - name: infrastructure
        tag: layer-infra
    enforce: top-down                          # higher layers may depend on lower
    allow_skip: true                           # optional, default: true
    edge_kind: depends_on                      # optional, default: uses

  # --- check (cardinality): enforce complexity limits ---
  - name: <unique-rule-name>
    description: "<description>"
    severity: warn
    check:
      for: { kind: domain }                    # NodeMatcher
      max_symbols: 200                         # optional
      max_files: 50                            # optional
      min_doc_coverage: 0.8                    # optional
```

Each rule must contain exactly one of: `deny`, `require`, `forbid_cycles`, `forbid_import`, `forbid`, `layers`, or `check`.

### Loading and Parsing

```python
def load_rules(rules_path: Path) -> list[Rule]
```

1. Read and parse `rules_path` with `yaml.safe_load`.
2. Validate top-level `version` field is in `SUPPORTED_SCHEMA_VERSIONS` ({1, 2, 3}). Raise `ValueError` on mismatch or absence.
3. If version 3, parse optional top-level `tags:` block for bulk tag assignments.
4. Iterate `rules` list. For each entry:
   a. Require a non-empty string `name` field.
   b. Enforce unique names (tracked via `seen_names` set). Raise `ValueError` on duplicate.
   c. Require exactly one of `deny`, `require`, `forbid_cycles`, `forbid_import`, `forbid`, `layers`, or `check`. Raise `ValueError` if none or multiple are present.
   d. Parse the corresponding block into the appropriate rule dataclass.
5. `NodeMatcher` parsing validates: for deny rules, at least one of `ref_id`, `kind`, or `tag` must be present. For require rules, `has_edge_to` accepts an empty dict `{}` (matches any node) via `allow_empty=True`. `kind` (if present) is validated against `VALID_NODE_KINDS`. `exclude` accepts a string or list, normalized to a tuple.

### Validation Against Database

```python
def validate_rules(rules: list[Rule], conn: sqlite3.Connection) -> list[str]
```

Collects all `ref_id` values from all matchers across all rules. Queries the `nodes` table for each. Returns a list of warning strings for any `ref_id` not found in the database. This is advisory (warnings, not errors).

### Evaluation

#### Deny Rule Evaluation

```python
def evaluate_deny_rules(conn: sqlite3.Connection, rules: list[DenyRule]) -> list[Violation]
```

Algorithm:
1. Query all rows from `code_imports` where `resolved_ref_id IS NOT NULL`.
2. For each import row `(file_path, line_number, import_path, resolved_ref_id)`:
   a. Determine the source node by calling `_get_file_node(file_path, conn)`, which inspects `code_symbols.annotations` JSON for keys (`domain`, `service`, `feature`) whose values match a `nodes.ref_id`.
   b. Skip if no source node is found.
   c. Skip self-references (source == target).
   d. Look up full `(ref_id, kind)` for both source and target via `_get_node`.
   e. For each deny rule, check whether `from_matcher` matches the source and `to_matcher` matches the target.
   f. If both match, check for exemption: if `unless_edge` is non-empty, query `edges` table for any edge of those kinds between source and target. If found, skip.
   g. Otherwise, emit a `Violation`.

#### Require Rule Evaluation

```python
def evaluate_require_rules(conn: sqlite3.Connection, rules: list[RequireRule]) -> list[Violation]
```

Algorithm:
1. Fetch all `(ref_id, kind)` from the `nodes` table.
2. For each rule, iterate all nodes. If `for_matcher` matches a node:
   a. Query all outgoing edges from that node (`edges WHERE src_ref_id = ?`).
   b. For each edge, optionally filter by `edge_kind`. Look up the target node via `_get_node`.
   c. If any target matches `has_edge_to`, the node satisfies the rule.
   d. If no matching edge is found, emit a `Violation`.

#### Combined Evaluation

```python
def evaluate_all(conn: sqlite3.Connection, rules: list[Rule]) -> list[Violation]
```

Partitions rules by type into `DenyRule`, `RequireRule`, `CycleRule`, `ImportBoundaryRule`, `ForbidEdgeRule`, `LayerRule`, and `CardinalityRule` lists. Calls the corresponding `evaluate_*` function for each type. Concatenates results and sorts by `(rule_name, file_path or "")`.

### Internal Helpers

| Function              | Description                                                                                    |
|-----------------------|------------------------------------------------------------------------------------------------|
| `_parse_node_matcher` | Parse a dict into a `NodeMatcher`, validating `kind` against `VALID_NODE_KINDS`. Accepts `allow_empty=True` for require rule targets. Normalizes `exclude` (string or list) to tuple. |
| `_parse_deny_rule`    | Parse a deny block into a `DenyRule` with validated matchers and `unless_edge`.                 |
| `_parse_require_rule` | Parse a require block into a `RequireRule` with validated matchers and optional `edge_kind`.    |
| `_parse_cycle_rule`   | Parse a forbid_cycles block into a `CycleRule` with edge_kind and optional max_depth.          |
| `_parse_import_boundary_rule` | Parse a forbid_import block into an `ImportBoundaryRule` with from/to glob patterns.  |
| `_parse_forbid_edge_rule`     | Parse a forbid block into a `ForbidEdgeRule` with from/to matchers and optional edge_kind. |
| `_parse_layer_rule`   | Parse a layers block into a `LayerRule` with ordered `LayerDef` entries.                       |
| `_parse_cardinality_rule`     | Parse a check block into a `CardinalityRule` with threshold fields.                      |
| `_get_file_node`      | Look up the owning node for a file via `code_symbols.annotations` JSON.                        |
| `_get_node`           | Return `(ref_id, kind)` tuple for a node, or `None`.                                          |
| `_edge_exists`        | Return `True` if an edge of any of the specified kinds exists between two nodes.               |

---

## API

### Public Functions

```python
def load_rules(rules_path: Path) -> list[Rule]: ...
def load_rules_with_tags(rules_path: Path) -> tuple[list[Rule], dict[str, list[str]]]: ...
def validate_rules(rules: list[Rule], conn: sqlite3.Connection) -> list[str]: ...
def evaluate_deny_rules(conn: sqlite3.Connection, rules: list[DenyRule]) -> list[Violation]: ...
def evaluate_require_rules(conn: sqlite3.Connection, rules: list[RequireRule]) -> list[Violation]: ...
def evaluate_cycle_rules(conn: sqlite3.Connection, rules: list[CycleRule]) -> list[Violation]: ...
def evaluate_import_boundary_rules(conn: sqlite3.Connection, rules: list[ImportBoundaryRule]) -> list[Violation]: ...
def evaluate_forbid_edge_rules(conn: sqlite3.Connection, rules: list[ForbidEdgeRule]) -> list[Violation]: ...
def evaluate_layer_rules(conn: sqlite3.Connection, rules: list[LayerRule]) -> list[Violation]: ...
def evaluate_cardinality_rules(conn: sqlite3.Connection, rules: list[CardinalityRule]) -> list[Violation]: ...
def evaluate_all(conn: sqlite3.Connection, rules: list[Rule]) -> list[Violation]: ...
```

### Public Classes

```python
@dataclass(frozen=True)
class NodeMatcher:
    ref_id: str | None = None
    kind: str | None = None
    tag: str | None = None
    exclude: tuple[str, ...] | None = None
    def matches(self, node_ref_id: str, node_kind: str, *, tags: set[str] | None = None) -> bool: ...

@dataclass(frozen=True)
class DenyRule:
    name: str
    description: str
    from_matcher: NodeMatcher
    to_matcher: NodeMatcher
    unless_edge: tuple[str, ...]
    severity: str = "error"

@dataclass(frozen=True)
class RequireRule:
    name: str
    description: str
    for_matcher: NodeMatcher
    has_edge_to: NodeMatcher
    edge_kind: str | None = None
    severity: str = "error"

@dataclass(frozen=True)
class CycleRule:
    name: str
    description: str
    edge_kind: str | tuple[str, ...]
    max_depth: int = 10
    severity: str = "error"

@dataclass(frozen=True)
class ImportBoundaryRule:
    name: str
    description: str
    from_glob: str
    to_glob: str
    severity: str = "error"

@dataclass(frozen=True)
class ForbidEdgeRule:
    name: str
    description: str
    from_matcher: NodeMatcher
    to_matcher: NodeMatcher
    edge_kind: str | None = None
    severity: str = "error"

@dataclass(frozen=True)
class LayerDef:
    name: str
    tag: str

@dataclass(frozen=True)
class LayerRule:
    name: str
    description: str
    layers: tuple[LayerDef, ...]
    enforce: str = "top-down"
    allow_skip: bool = True
    edge_kind: str = "uses"
    severity: str = "error"

@dataclass(frozen=True)
class CardinalityRule:
    name: str
    description: str
    for_matcher: NodeMatcher
    max_symbols: int | None = None
    max_files: int | None = None
    min_doc_coverage: float | None = None
    severity: str = "warn"

Rule = DenyRule | RequireRule | CycleRule | ImportBoundaryRule | ForbidEdgeRule | LayerRule | CardinalityRule

@dataclass(frozen=True)
class Violation:
    rule_name: str
    rule_description: str
    rule_type: str
    severity: str
    file_path: str | None
    line_number: int | None
    from_ref_id: str | None
    to_ref_id: str | None
    message: str
```

### CLI

```
beadloom lint [--format {rich,json,porcelain}] [--strict] [--no-reindex]
```

| Flag           | Default | Description                                                        |
|----------------|---------|--------------------------------------------------------------------|
| `--format`     | `rich`  | Output format: `rich` (colored tables), `json`, or `porcelain`.    |
| `--strict`     | `False` | Exit with code `1` if any violations are found.                    |
| `--no-reindex` | `False` | Skip import reindexing before evaluation.                          |

**Exit codes:**

| Code | Meaning                                   |
|------|-------------------------------------------|
| `0`  | No violations (or violations without `--strict`). |
| `1`  | Violations detected (with `--strict`).    |
| `2`  | Configuration error (missing/invalid `rules.yml`). |

---

## Invariants

- Rule names are unique within a single `rules.yml` file.
- Each rule contains exactly one of `deny`, `require`, `forbid_cycles`, `forbid_import`, `forbid`, `layers`, or `check` (never multiple, never none).
- Self-references (`source_ref_id == target_ref_id`) are skipped during deny evaluation and never produce violations.
- `evaluate_all` output is deterministically sorted by `(rule_name, file_path or "")`.
- `NodeMatcher.matches` returns `False` if `node_ref_id` is in `exclude`. Otherwise returns `True` only when all non-`None` fields match. An empty matcher (`NodeMatcher()`) matches any node.
- All `kind` values in matchers are validated against `VALID_NODE_KINDS` at parse time.
- All edge kind values (`unless_edge`, `edge_kind`) are validated against `VALID_EDGE_KINDS` at parse time.
- Rules support `error` and `warn` severity levels (default varies by rule type).

---

## Constraints

- `rules.yml` must declare a version in `SUPPORTED_SCHEMA_VERSIONS` ({1, 2, 3}). Unsupported versions are rejected with `ValueError`.
- `NodeMatcher` must have at least one of `ref_id`, `kind`, or `tag` in deny rules; providing none raises `ValueError`. In require rules, `has_edge_to` accepts empty `{}` for "any node" matching.
- Deny rules depend on the `code_imports` table being populated (typically via a prior `reindex` step).
- Require rules depend on the `nodes` and `edges` tables.
- `validate_rules` is advisory: it returns warnings but does not raise exceptions.
- The `_get_file_node` helper relies on `code_symbols.annotations` being valid JSON with keys like `domain`, `service`, or `feature` whose values correspond to `nodes.ref_id`.

---

## Testing

### Parsing Tests

- **Valid deny rule.** Parse a well-formed deny rule YAML. Assert returned `DenyRule` has correct matchers and `unless_edge`.
- **Valid require rule.** Parse a well-formed require rule YAML. Assert returned `RequireRule` has correct matchers and `edge_kind`.
- **Missing version.** Assert `ValueError` on `rules.yml` without `version`.
- **Wrong version.** Assert `ValueError` on `version: 2`.
- **Duplicate name.** Assert `ValueError` when two rules share a name.
- **Both deny and require.** Assert `ValueError` when a rule has both blocks.
- **Neither deny nor require.** Assert `ValueError` when a rule has neither block.
- **Invalid node kind.** Assert `ValueError` for `kind: "unknown"` in a matcher.
- **Invalid edge kind.** Assert `ValueError` for `unless_edge: ["unknown"]`.
- **Matcher missing both fields.** Assert `ValueError` when `NodeMatcher` has neither `ref_id` nor `kind` (in deny rules).
- **Empty matcher in require rules.** Assert `has_edge_to: {}` parses successfully and matches any node.
- **Empty matcher detects violations.** Assert nodes without outgoing edges of the required kind produce violations.
- **Empty matcher satisfied.** Assert adding any `part_of` edge satisfies the empty-matcher rule.
- **Empty for-matcher rejected in deny.** Assert empty matchers are still rejected in deny rule positions.

### Deny Evaluation Tests

- **Violation detected.** Insert nodes, a code_import, and code_symbols annotation creating a forbidden path. Assert one `Violation` with correct `rule_name`, `file_path`, `line_number`, `from_ref_id`, `to_ref_id`.
- **Exemption via unless_edge.** Add an edge of the exempted kind. Assert no violations.
- **Self-reference skipped.** Import where source and target resolve to the same node. Assert no violations.
- **No matching import.** Imports that do not match `from_matcher` or `to_matcher`. Assert no violations.

### Require Evaluation Tests

- **Violation detected.** Create a node matching `for_matcher` with no outgoing edge to the required target. Assert one `Violation`.
- **Satisfied.** Create a node with a matching outgoing edge. Assert no violations.
- **Edge kind filter.** Require a specific `edge_kind`. Assert violation when edge exists but with wrong kind.

### Validation Tests

- **Unknown ref_id warning.** Create rules referencing a `ref_id` not in `nodes`. Assert `validate_rules` returns a warning string.
- **All ref_ids exist.** Assert empty warning list.

### Combined Evaluation Tests

- **Mixed rules.** Combine deny and require rules. Assert violations from both types are returned and sorted correctly by `(rule_name, file_path)`.
- **Empty rules list.** Assert `evaluate_all` returns an empty list.
