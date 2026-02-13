# Doctor

Graph validation checks for data integrity and completeness.

Source: `src/beadloom/infrastructure/doctor.py`

## Specification

### Purpose

The doctor module runs a suite of read-only validation checks against the populated SQLite knowledge graph. It identifies structural issues such as missing summaries, orphaned documents, undocumented nodes, and isolated nodes. Each check returns one or more `Check` results with an associated severity level, enabling operators and CI pipelines to assess graph health without modifying any data.

### Severity Enum

Enumeration of check result severity levels.

| Value | String | Meaning |
|-------|--------|---------|
| `OK` | `"ok"` | No issues found for this check |
| `INFO` | `"info"` | Informational finding, no action required |
| `WARNING` | `"warning"` | Potential data quality issue, should be addressed |
| `ERROR` | `"error"` | Critical integrity violation |

Backed by `enum.Enum` with string values.

### Data Structures

#### Check (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Machine-readable check identifier (e.g., `"empty_summaries"`, `"isolated_nodes"`) |
| `severity` | `Severity` | Severity level of the finding |
| `description` | `str` | Human-readable description of the specific finding |

### Validation Checks

All four checks are private functions that accept a `sqlite3.Connection` and return `list[Check]`.

#### 1. `_check_empty_summaries`

Detects nodes where the `summary` column is empty string or `NULL`.

- **Query**: `SELECT ref_id FROM nodes WHERE summary = '' OR summary IS NULL`
- **On no issues**: Returns `[Check("empty_summaries", Severity.OK, "All nodes have summaries.")]`
- **On issues**: Returns one `Check` per affected node with `Severity.WARNING` and message `"Node '<ref_id>' has empty summary."`

#### 2. `_check_unlinked_docs`

Detects documents in the `docs` table that have no `ref_id` linking them to a graph node.

- **Query**: `SELECT path FROM docs WHERE ref_id IS NULL`
- **On no issues**: Returns `[Check("unlinked_docs", Severity.OK, "All docs are linked to nodes.")]`
- **On issues**: Returns one `Check` per affected document with `Severity.WARNING` and message `"Doc '<path>' has no ref_id -- unlinked from graph."`

#### 3. `_check_nodes_without_docs`

Detects graph nodes that have no associated documentation via a `LEFT JOIN` on the `docs` table.

- **Query**: `SELECT n.ref_id FROM nodes n LEFT JOIN docs d ON d.ref_id = n.ref_id WHERE d.id IS NULL`
- **On no issues**: Returns `[Check("nodes_without_docs", Severity.OK, "All nodes have documentation.")]`
- **On issues**: Returns one `Check` per affected node with `Severity.INFO` and message `"Node '<ref_id>' has no doc linked."`

#### 4. `_check_isolated_nodes`

Detects nodes with no incoming or outgoing edges (completely disconnected from the graph).

- **Query**: `SELECT n.ref_id FROM nodes n LEFT JOIN edges e1 ON e1.src_ref_id = n.ref_id LEFT JOIN edges e2 ON e2.dst_ref_id = n.ref_id WHERE e1.src_ref_id IS NULL AND e2.dst_ref_id IS NULL`
- **On no issues**: Returns `[Check("isolated_nodes", Severity.OK, "No isolated nodes.")]`
- **On issues**: Returns one `Check` per affected node with `Severity.INFO` and message `"Node '<ref_id>' has no edges (isolated)."`

### Execution Order

`run_checks` executes the four checks in a fixed order and concatenates results:

1. `_check_empty_summaries`
2. `_check_unlinked_docs`
3. `_check_nodes_without_docs`
4. `_check_isolated_nodes`

### CLI Interface

```
beadloom doctor [--project DIR]
```

- `--project DIR`: Path to the project root (defaults to current directory).
- Output: Formatted list of checks with severity markers via Rich console.

## API

### Public Functions

```python
def run_checks(conn: sqlite3.Connection) -> list[Check]
```

Run all validation checks against the database and return the combined list of `Check` results. The connection must point to a populated beadloom database (i.e., after `beadloom reindex` has been run).

### Public Classes

```python
class Severity(enum.Enum):
    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class Check:
    name: str
    severity: Severity
    description: str
```

## Invariants

- All four checks always execute; there is no mechanism to skip individual checks.
- Each check independently returns its own result list. A failure in one check does not affect others.
- When a check finds no issues, it returns exactly one `Check` with `Severity.OK`.
- When a check finds N issues, it returns exactly N `Check` objects (one per affected entity).
- `run_checks` never modifies the database. All operations are `SELECT` queries.

## Constraints

- Requires a populated SQLite database. Running doctor before `beadloom reindex` will produce misleading results (e.g., all checks return OK on empty tables).
- No auto-fix capability. Doctor is strictly read-only and diagnostic.
- No check prioritization or filtering. The caller receives all results and must decide how to present or act on them.
- The `ERROR` severity level exists in the enum but is not currently emitted by any built-in check.

## Testing

Tests should cover the following scenarios:

- **All-clear**: Verify that a well-formed graph (nodes with summaries, linked docs, edges) produces four `Severity.OK` results.
- **Empty summaries**: Insert nodes with `NULL` and `""` summaries; verify `WARNING` checks are returned with correct `ref_id` in the description.
- **Unlinked docs**: Insert docs with `ref_id IS NULL`; verify `WARNING` checks with correct `path`.
- **Nodes without docs**: Insert nodes with no corresponding `docs` rows; verify `INFO` checks.
- **Isolated nodes**: Insert nodes with no edges; verify `INFO` checks.
- **Mixed results**: Combine multiple issues and verify the full result list contains the expected number and types of checks.
- **Empty database**: Verify behavior on a schema with no rows (all checks should return OK since there are no entities to flag).
