# Doctor

Graph validation checks for data integrity and completeness.

Source: `src/beadloom/infrastructure/doctor.py`

## Specification

### Purpose

The doctor module runs a suite of read-only validation checks against the populated SQLite architecture graph. It identifies structural issues such as missing summaries, orphaned documents, undocumented nodes, isolated nodes, symbol drift, stale sync entries, and source coverage gaps. Each check returns one or more `Check` results with an associated severity level, enabling operators and CI pipelines to assess graph health without modifying any data.

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

All seven checks are private functions that accept a `sqlite3.Connection` and return `list[Check]`.

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

#### 5. `_check_symbol_drift`

Detects nodes where code symbols have changed since the last documentation sync. Uses the `symbols_hash` column in `sync_state` (added in BEAD-08) to compare the stored hash against the current computed hash via `_compute_symbols_hash()`.

- **Query**: `SELECT ref_id, doc_path, symbols_hash FROM sync_state WHERE symbols_hash != '' AND status = 'ok'`
- **On missing column**: Gracefully returns `[Check("symbol_drift", Severity.OK, "symbols_hash column not present -- skipping drift check.")]`
- **On no entries**: Returns `[Check("symbol_drift", Severity.OK, "No sync entries with symbols_hash to check.")]`
- **On no drift**: Returns `[Check("symbol_drift", Severity.OK, "No symbol drift detected.")]`
- **On drift**: Returns one `Check` per drifted node with `Severity.WARNING` and message `"Node '<ref_id>' has code changes since last doc update (<doc_path>)"`

#### 6. `_check_stale_sync`

Reports `sync_state` entries that are already marked as stale.

- **Query**: `SELECT ref_id, doc_path, code_path FROM sync_state WHERE status = 'stale'`
- **On missing table**: Returns `[Check("stale_sync", Severity.OK, "sync_state not available -- skipping.")]`
- **On no stale entries**: Returns `[Check("stale_sync", Severity.OK, "No stale sync entries.")]`
- **On stale entries**: Returns one `Check` per stale entry with `Severity.WARNING` and message `"Sync stale for '<ref_id>': doc=<doc_path>, code=<code_path>"`

#### 7. `_check_source_coverage`

Checks for nodes with untracked source files. Uses `check_source_coverage()` from `doc_sync.engine` to detect Python files in a node's source directory that are not tracked in `sync_state` or `code_symbols`. Derives `project_root` from the database file path via `PRAGMA database_list`.

- **On error determining project root**: Returns `[Check("source_coverage", Severity.OK, "Could not determine project root -- skipping source coverage check.")]`
- **On check failure**: Returns `[Check("source_coverage", Severity.OK, "Source coverage check failed -- skipping.")]`
- **On no gaps**: Returns `[Check("source_coverage", Severity.OK, "All source files are tracked.")]`
- **On gaps**: Returns one `Check` per node with untracked files, `Severity.WARNING` and message `"Node '<ref_id>' has untracked source files: <file_names>"`

### Execution Order

`run_checks` executes the seven checks in a fixed order and concatenates results:

1. `_check_empty_summaries`
2. `_check_unlinked_docs`
3. `_check_nodes_without_docs`
4. `_check_isolated_nodes`
5. `_check_symbol_drift`
6. `_check_stale_sync`
7. `_check_source_coverage`

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

Run all 7 validation checks against the database and return the combined list of `Check` results. The connection must point to a populated beadloom database (i.e., after `beadloom reindex` has been run).

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

- All seven checks always execute; there is no mechanism to skip individual checks.
- Each check independently returns its own result list. A failure in one check does not affect others.
- When a check finds no issues, it returns exactly one `Check` with `Severity.OK`.
- When a check finds N issues, it returns exactly N `Check` objects (one per affected entity).
- `run_checks` never modifies the database. All operations are `SELECT` queries (plus the `check_source_coverage` call which is also read-only).
- `_check_symbol_drift` and `_check_stale_sync` gracefully handle missing columns or tables (e.g., pre-migration databases) by returning an OK check with a skip message.
- `_check_source_coverage` gracefully handles errors in determining the project root or running the coverage check, returning an OK check with a skip message.

## Constraints

- Requires a populated SQLite database. Running doctor before `beadloom reindex` will produce misleading results (e.g., all checks return OK on empty tables).
- No auto-fix capability. Doctor is strictly read-only and diagnostic.
- No check prioritization or filtering. The caller receives all results and must decide how to present or act on them.
- The `ERROR` severity level exists in the enum but is not currently emitted by any built-in check.
- `_check_symbol_drift` depends on `doc_sync.engine._compute_symbols_hash` being available; it imports the function at call time.
- `_check_source_coverage` depends on `doc_sync.engine.check_source_coverage` and derives `project_root` from the database path via `PRAGMA database_list`.

## Testing

Test files: `tests/test_doctor.py`, `tests/test_doctor_drift.py`

Tests should cover the following scenarios:

- **All-clear**: Verify that a well-formed graph (nodes with summaries, linked docs, edges) produces seven `Severity.OK` results.
- **Empty summaries**: Insert nodes with `NULL` and `""` summaries; verify `WARNING` checks are returned with correct `ref_id` in the description.
- **Unlinked docs**: Insert docs with `ref_id IS NULL`; verify `WARNING` checks with correct `path`.
- **Nodes without docs**: Insert nodes with no corresponding `docs` rows; verify `INFO` checks.
- **Isolated nodes**: Insert nodes with no edges; verify `INFO` checks.
- **Symbol drift**: Modify code symbols after establishing a baseline `symbols_hash`; verify `WARNING` checks are returned for drifted nodes.
- **Symbol drift graceful degradation**: Verify that missing `symbols_hash` column returns OK with skip message.
- **Stale sync entries**: Insert `sync_state` rows with `status = 'stale'`; verify `WARNING` checks.
- **Source coverage gaps**: Create nodes with source directories containing untracked files; verify `WARNING` checks.
- **Source coverage graceful degradation**: Verify that errors in determining project root return OK with skip message.
- **Mixed results**: Combine multiple issues and verify the full result list contains the expected number and types of checks.
- **Empty database**: Verify behavior on a schema with no rows (all checks should return OK since there are no entities to flag).
