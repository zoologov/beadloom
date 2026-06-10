# Doctor

Graph validation checks for data integrity and completeness.

Source: `src/beadloom/application/doctor.py`

## Specification

### Purpose

The doctor module runs a suite of read-only validation checks against the populated SQLite architecture graph. It identifies structural issues such as missing summaries, orphaned documents, undocumented nodes, isolated nodes, symbol drift, stale sync entries, source coverage gaps, and agent instruction drift. Each check returns one or more `Check` results with an associated severity level, enabling operators and CI pipelines to assess graph health without modifying any data.

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

Checks 1–7 are private functions that accept a `sqlite3.Connection` and return `list[Check]`. Check 8 (`_check_agent_instructions`) accepts a `pathlib.Path` (the project root) instead.

#### 1. `_check_empty_summaries`

Detects nodes where the `summary` column is empty string or `NULL`.

- **Query**: `SELECT ref_id FROM nodes WHERE summary = '' OR summary IS NULL`
- **On no issues**: Returns `[Check("empty_summaries", Severity.OK, "All nodes have summaries.")]`
- **On issues**: Returns one `Check` per affected node with `Severity.WARNING` and message `"Node '<ref_id>' has empty summary."`

#### 2. `_check_unlinked_docs`

Detects documents in the `docs` table that have no `ref_id` linking them to a graph node.

- **Query**: `SELECT path FROM docs WHERE ref_id IS NULL`
- **On no issues**: Returns `[Check("unlinked_docs", Severity.OK, "All docs are linked to nodes.")]`
- **On issues**: Returns one `Check` per affected document with `Severity.WARNING` and message `"Doc '<path>' has no ref_id — unlinked from graph."`

#### 3. `_check_nodes_without_docs`

Detects graph nodes that have no associated documentation via a `LEFT JOIN` on the `docs` table.

- **Query**: `SELECT n.ref_id FROM nodes n LEFT JOIN docs d ON d.ref_id = n.ref_id WHERE d.id IS NULL`
- **On no issues**: Returns `[Check("nodes_without_docs", Severity.OK, "All nodes have documentation.")]`
- **On issues**: Returns one `Check` per affected node with `Severity.WARNING` and message `"Node '<ref_id>' has no doc linked."`

#### 4. `_check_isolated_nodes`

Detects nodes with no incoming or outgoing edges (completely disconnected from the graph).

- **Query**: `SELECT n.ref_id FROM nodes n LEFT JOIN edges e1 ON e1.src_ref_id = n.ref_id LEFT JOIN edges e2 ON e2.dst_ref_id = n.ref_id WHERE e1.src_ref_id IS NULL AND e2.dst_ref_id IS NULL`
- **On no issues**: Returns `[Check("isolated_nodes", Severity.OK, "No isolated nodes.")]`
- **On issues**: Returns one `Check` per affected node with `Severity.INFO` and message `"Node '<ref_id>' has no edges (isolated)."`

#### 5. `_check_symbol_drift`

Detects nodes where code symbols have changed since the last documentation sync. Uses the `symbols_hash` column in `sync_state` (added in BEAD-08) to compare the stored hash against the current computed hash via `_compute_symbols_hash()`.

- **Query**: `SELECT ref_id, doc_path, symbols_hash FROM sync_state WHERE symbols_hash != '' AND status = 'ok'`
- **On missing column**: Gracefully returns `[Check("symbol_drift", Severity.OK, "symbols_hash column not present — skipping drift check.")]`
- **On no entries**: Returns `[Check("symbol_drift", Severity.OK, "No sync entries with symbols_hash to check.")]`
- **On no drift**: Returns `[Check("symbol_drift", Severity.OK, "No symbol drift detected.")]`
- **On drift**: Returns one `Check` per drifted node with `Severity.WARNING` and message `"Node '<ref_id>' has code changes since last doc update (<doc_path>)"`

#### 6. `_check_stale_sync`

Reports `sync_state` entries that are already marked as stale.

- **Query**: `SELECT ref_id, doc_path, code_path FROM sync_state WHERE status = 'stale'`
- **On missing table**: Returns `[Check("stale_sync", Severity.OK, "sync_state not available — skipping.")]`
- **On no stale entries**: Returns `[Check("stale_sync", Severity.OK, "No stale sync entries.")]`
- **On stale entries**: Returns one `Check` per stale entry with `Severity.WARNING` and message `"Sync stale for '<ref_id>': doc=<doc_path>, code=<code_path>"`

#### 7. `_check_source_coverage`

Checks for nodes with untracked source files. Uses `check_source_coverage()` from `doc_sync.engine` to detect Python files in a node's source directory that are not tracked in `sync_state` or `code_symbols`. Derives `project_root` from the database file path via `PRAGMA database_list`.

- **On error determining project root**: Returns `[Check("source_coverage", Severity.OK, "Could not determine project root — skipping source coverage check.")]`
- **On check failure**: Returns `[Check("source_coverage", Severity.OK, "Source coverage check failed — skipping.")]`
- **On no gaps**: Returns `[Check("source_coverage", Severity.OK, "All source files are tracked.")]`
- **On gaps**: Returns one `Check` per node with untracked files, `Severity.WARNING` and message `"Node '<ref_id>' has untracked source files: <file_names>"`

#### 8. `_check_agent_instructions`

Validates agent instruction files (`.claude/CLAUDE.md` and `.beadloom/AGENTS.md`) for factual drift against actual runtime state. Accepts a `pathlib.Path` (the project root) rather than a database connection.

Reads both instruction files, extracts factual claims via regex, and compares them with live introspection of the codebase. Performs up to 6 sub-checks:

1. **Version** (`agent_instructions_version`): Extracts `**Current version:** X.Y.Z` from CLAUDE.md and compares against `beadloom.__version__` (falling back to `importlib.metadata`).
2. **Packages** (`agent_instructions_packages`): Extracts backtick-wrapped directory names (e.g., `` `infrastructure/` ``) from CLAUDE.md lines mentioning "Architecture", "DDD", or "packages", and compares against actual `src/beadloom/` subdirectories containing `__init__.py`.
3. **CLI commands** (`agent_instructions_cli_commands`): Reports the actual count of registered Click commands via `main.commands` introspection. Always returns `Severity.OK` (informational).
4. **MCP tools** (`agent_instructions_mcp_tools`): Extracts tool names from AGENTS.md table rows (pattern: `` | `tool_name` | ``) and compares the count against `len(_TOOLS)` from `mcp_server`.
5. **Stack keywords** (`agent_instructions_stack`): Extracts the `**Stack:**` line from CLAUDE.md and verifies it contains expected keywords (`python`, `sqlite`).
6. **Test framework** (`agent_instructions_test_framework`): Extracts the `**Tests:**` line from CLAUDE.md and verifies it mentions `pytest`.

- **On neither file existing**: Returns an empty list (no checks emitted).
- **On individual sub-check match**: Returns `Check(name, Severity.OK, ...)`.
- **On individual sub-check drift**: Returns `Check(name, Severity.WARNING, ...)`.

### Helper Functions

The following private helpers support `_check_agent_instructions`:

| Function | Description |
|----------|-------------|
| `_extract_version_claim(text)` | Extract version string from `**Current version:** X.Y.Z` pattern |
| `_extract_package_claims(text)` | Extract backtick-wrapped directory names from Architecture/DDD lines |
| `_get_actual_version()` | Read `beadloom.__version__` (falls back to `importlib.metadata`) |
| `_get_actual_cli_commands()` | Introspect Click `main.commands` for registered command names |
| `_get_actual_mcp_tool_count()` | Count tools in `mcp_server._TOOLS` list |
| `_get_actual_packages(project_root)` | Scan `src/beadloom/` for directories with `__init__.py` |

### Execution Order

`run_checks` executes checks in a fixed order and concatenates results:

1. `_check_empty_summaries`
2. `_check_unlinked_docs`
3. `_check_nodes_without_docs`
4. `_check_isolated_nodes`
5. `_check_symbol_drift`
6. `_check_stale_sync`
7. `_check_source_coverage`
8. `_check_agent_instructions` (only when `project_root` is provided)

### CLI Interface

```
beadloom doctor [--project DIR]
```

- `--project DIR`: Path to the project root (defaults to current directory).
- Output: Formatted list of checks with severity icons (`[ok]`, `[info]`, `[warn]`, `[ERR]`) via `click.echo`.
- The CLI passes `project_root` to `run_checks`, enabling the agent instructions check.
- Exits with code 1 if the database file is not found at `.beadloom/beadloom.db`.

## API

### Public Functions

```python
def run_checks(
    conn: sqlite3.Connection,
    *,
    project_root: Path | None = None,
) -> list[Check]
```

Run all validation checks against the database and return the combined list of `Check` results. The connection must point to a populated beadloom database (i.e., after `beadloom reindex` has been run). When `project_root` is provided, also runs `_check_agent_instructions` to validate CLAUDE.md and AGENTS.md for factual drift.

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

- Checks 1–7 always execute; check 8 (`_check_agent_instructions`) runs only when `project_root` is provided.
- Each check independently returns its own result list. A failure in one check does not affect others.
- When a check finds no issues, it returns exactly one `Check` with `Severity.OK`.
- When a check finds N issues, it returns exactly N `Check` objects (one per affected entity).
- `run_checks` never modifies the database. All operations are `SELECT` queries (plus the `check_source_coverage` call which is also read-only).
- `_check_symbol_drift` and `_check_stale_sync` gracefully handle missing columns or tables (e.g., pre-migration databases) by returning an OK check with a skip message.
- `_check_source_coverage` gracefully handles errors in determining the project root or running the coverage check, returning an OK check with a skip message.
- `_check_agent_instructions` gracefully handles missing instruction files by returning an empty list (no checks emitted). Individual sub-checks are independent.

## Constraints

- Requires a populated SQLite database. Running doctor before `beadloom reindex` will produce misleading results (e.g., all checks return OK on empty tables).
- No auto-fix capability. Doctor is strictly read-only and diagnostic.
- No check prioritization or filtering. The caller receives all results and must decide how to present or act on them.
- The `ERROR` severity level exists in the enum but is not currently emitted by any built-in check.
- `_check_symbol_drift` depends on `doc_sync.engine._compute_symbols_hash` being available; it imports the function at call time.
- `_check_source_coverage` depends on `doc_sync.engine.check_source_coverage` and derives `project_root` from the database path via `PRAGMA database_list`.
- `_check_agent_instructions` depends on regex patterns matching the expected format of CLAUDE.md and AGENTS.md. Changes to those file formats may require updating the extraction patterns.

## Testing

Test files: `tests/test_doctor.py`, `tests/test_doctor_drift.py`, `tests/test_doctor_instructions.py`

Tests should cover the following scenarios:

- **All-clear**: Verify that a well-formed graph (nodes with summaries, linked docs, edges) produces `Severity.OK` results for checks 1–7.
- **Empty summaries**: Insert nodes with `NULL` and `""` summaries; verify `WARNING` checks are returned with correct `ref_id` in the description.
- **Unlinked docs**: Insert docs with `ref_id IS NULL`; verify `WARNING` checks with correct `path`.
- **Nodes without docs**: Insert nodes with no corresponding `docs` rows; verify `WARNING` checks.
- **Isolated nodes**: Insert nodes with no edges; verify `INFO` checks.
- **Symbol drift**: Modify code symbols after establishing a baseline `symbols_hash`; verify `WARNING` checks are returned for drifted nodes.
- **Symbol drift graceful degradation**: Verify that missing `symbols_hash` column returns OK with skip message.
- **Stale sync entries**: Insert `sync_state` rows with `status = 'stale'`; verify `WARNING` checks.
- **Source coverage gaps**: Create nodes with source directories containing untracked files; verify `WARNING` checks.
- **Source coverage graceful degradation**: Verify that errors in determining project root return OK with skip message.
- **Agent instructions — version drift**: Create a CLAUDE.md with a mismatched version claim; verify `WARNING`.
- **Agent instructions — package drift**: Create a CLAUDE.md listing packages that don't exist on disk; verify `WARNING`.
- **Agent instructions — MCP tool drift**: Create an AGENTS.md with a tool table whose count doesn't match `_TOOLS`; verify `WARNING`.
- **Agent instructions — missing files**: Verify that when neither CLAUDE.md nor AGENTS.md exist, `_check_agent_instructions` returns an empty list.
- **Agent instructions — all clear**: Verify that matching claims produce `Severity.OK` for each sub-check.
- **Mixed results**: Combine multiple issues and verify the full result list contains the expected number and types of checks.
- **Empty database**: Verify behavior on a schema with no rows (all checks should return OK since there are no entities to flag).
