# Rule Engine

Architecture-as-Code rule engine: parse `rules.yml`, validate rule definitions, and evaluate them against the knowledge graph and code imports.

**Source:** `src/beadloom/graph/rule_engine.py`

---

## Specification

### Purpose

Enforce architectural constraints declaratively. Rules are defined in a YAML file and evaluated against the graph database (nodes, edges, and code_imports tables). Two rule types exist: **deny rules** that forbid certain import relationships between nodes, and **require rules** that mandate the existence of specific edge relationships.

### Constants

```python
VALID_NODE_KINDS: frozenset[str] = frozenset({
    "domain", "feature", "service", "entity", "adr"
})

VALID_EDGE_KINDS: frozenset[str] = frozenset({
    "part_of", "depends_on", "uses", "implements", "touches_entity", "touches_code"
})

RULES_SCHEMA_VERSION = 1
```

### Data Structures

All dataclasses are frozen (immutable).

#### `NodeMatcher`

Matches graph nodes by `ref_id` and/or `kind`. At least one field must be non-`None`.

| Field    | Type           | Description                                     |
|----------|----------------|-------------------------------------------------|
| `ref_id` | `str \| None`  | Exact ref_id to match, or `None` for any.       |
| `kind`   | `str \| None`  | Node kind to match, or `None` for any.          |

```python
def matches(self, node_ref_id: str, node_kind: str) -> bool
```

Returns `True` if both non-`None` fields match the given node's `ref_id` and `kind`.

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

#### `Rule` (type alias)

```python
Rule = DenyRule | RequireRule
```

#### `Violation`

| Field              | Type           | Description                                     |
|--------------------|----------------|-------------------------------------------------|
| `rule_name`        | `str`          | Name of the violated rule.                      |
| `rule_description` | `str`          | Description of the violated rule.               |
| `rule_type`        | `str`          | `"deny"` or `"require"`.                        |
| `file_path`        | `str \| None`  | Source file path (for deny violations).          |
| `line_number`      | `int \| None`  | Line number (for deny violations).              |
| `from_ref_id`      | `str \| None`  | Source node ref_id.                              |
| `to_ref_id`        | `str \| None`  | Target node ref_id.                              |
| `message`          | `str`          | Human-readable explanation of the violation.     |

### rules.yml Schema

```yaml
version: 1
rules:
  - name: <unique-rule-name>
    description: "<human-readable description>"
    deny:                          # exactly one of 'deny' or 'require'
      from: { ref_id: ..., kind: ... }   # NodeMatcher (at least one field)
      to:   { ref_id: ..., kind: ... }   # NodeMatcher (at least one field)
      unless_edge: [<edge_kind>, ...]    # optional, defaults to []
    # OR
    require:
      for:         { ref_id: ..., kind: ... }  # NodeMatcher
      has_edge_to: { ref_id: ..., kind: ... }  # NodeMatcher
      edge_kind: <edge_kind>                   # optional
```

### Loading and Parsing

```python
def load_rules(rules_path: Path) -> list[Rule]
```

1. Read and parse `rules_path` with `yaml.safe_load`.
2. Validate top-level `version` field equals `RULES_SCHEMA_VERSION` (currently `1`). Raise `ValueError` on mismatch or absence.
3. Iterate `rules` list. For each entry:
   a. Require a non-empty string `name` field.
   b. Enforce unique names (tracked via `seen_names` set). Raise `ValueError` on duplicate.
   c. Require exactly one of `deny` or `require` blocks. Raise `ValueError` if both or neither are present.
   d. Parse the corresponding block:
      - **Deny:** Extract `from` and `to` as `NodeMatcher` instances. Parse `unless_edge` as a list of edge kinds (validated against `VALID_EDGE_KINDS`).
      - **Require:** Extract `for` and `has_edge_to` as `NodeMatcher` instances. Parse optional `edge_kind` (validated against `VALID_EDGE_KINDS`).
4. `NodeMatcher` parsing validates: at least one of `ref_id` or `kind` is present; `kind` (if present) is in `VALID_NODE_KINDS`.

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

Partitions rules into `DenyRule` and `RequireRule` lists. Calls `evaluate_deny_rules` and `evaluate_require_rules` respectively. Concatenates results and sorts by `(rule_name, file_path or "")`.

### Internal Helpers

| Function              | Description                                                                                    |
|-----------------------|------------------------------------------------------------------------------------------------|
| `_parse_node_matcher` | Parse a dict into a `NodeMatcher`, validating `kind` against `VALID_NODE_KINDS`.               |
| `_parse_deny_rule`    | Parse a deny block into a `DenyRule` with validated matchers and `unless_edge`.                 |
| `_parse_require_rule` | Parse a require block into a `RequireRule` with validated matchers and optional `edge_kind`.    |
| `_get_file_node`      | Look up the owning node for a file via `code_symbols.annotations` JSON.                        |
| `_get_node`           | Return `(ref_id, kind)` tuple for a node, or `None`.                                          |
| `_edge_exists`        | Return `True` if an edge of any of the specified kinds exists between two nodes.               |

---

## API

### Public Functions

```python
def load_rules(rules_path: Path) -> list[Rule]: ...
def validate_rules(rules: list[Rule], conn: sqlite3.Connection) -> list[str]: ...
def evaluate_deny_rules(conn: sqlite3.Connection, rules: list[DenyRule]) -> list[Violation]: ...
def evaluate_require_rules(conn: sqlite3.Connection, rules: list[RequireRule]) -> list[Violation]: ...
def evaluate_all(conn: sqlite3.Connection, rules: list[Rule]) -> list[Violation]: ...
```

### Public Classes

```python
@dataclass(frozen=True)
class NodeMatcher:
    ref_id: str | None = None
    kind: str | None = None
    def matches(self, node_ref_id: str, node_kind: str) -> bool: ...

@dataclass(frozen=True)
class DenyRule:
    name: str
    description: str
    from_matcher: NodeMatcher
    to_matcher: NodeMatcher
    unless_edge: tuple[str, ...]

@dataclass(frozen=True)
class RequireRule:
    name: str
    description: str
    for_matcher: NodeMatcher
    has_edge_to: NodeMatcher
    edge_kind: str | None = None

Rule = DenyRule | RequireRule

@dataclass(frozen=True)
class Violation:
    rule_name: str
    rule_description: str
    rule_type: str
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
- Each rule contains exactly one of `deny` or `require` (never both, never neither).
- Self-references (`source_ref_id == target_ref_id`) are skipped during deny evaluation and never produce violations.
- `evaluate_all` output is deterministically sorted by `(rule_name, file_path or "")`.
- `NodeMatcher.matches` returns `True` only when all non-`None` fields match.
- All `kind` values in matchers are validated against `VALID_NODE_KINDS` at parse time.
- All edge kind values (`unless_edge`, `edge_kind`) are validated against `VALID_EDGE_KINDS` at parse time.

---

## Constraints

- `rules.yml` must declare `version: 1`. Other versions are rejected with `ValueError`.
- `NodeMatcher` must have at least one of `ref_id` or `kind`; providing neither raises `ValueError`.
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
- **Matcher missing both fields.** Assert `ValueError` when `NodeMatcher` has neither `ref_id` nor `kind`.

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
