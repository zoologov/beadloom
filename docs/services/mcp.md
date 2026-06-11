# MCP Server

Beadloom provides an MCP (Model Context Protocol) server with 18 tools for integration with AI agents: 14 read/write tools over the architecture graph, plus four **process-tools** (`task_init` / `bead_context` / `complete_bead` / `checkpoint`, added in BDL-048) that make the deterministic steps of Beadloom's multi-agent dev flow callable from any MCP client. See the [Agentic Dev Flow guide](../guides/agentic-flow.md).

## Specification

### Transport

The server operates via stdio transport. Launch:

```bash
beadloom mcp-serve [--project DIR]
```

Configuration for supported editors/tools:

```bash
# Claude Code (default) — writes .mcp.json
beadloom setup-mcp

# Cursor — writes .cursor/mcp.json
beadloom setup-mcp --tool cursor

# Windsurf — writes ~/.codeium/windsurf/mcp_config.json (global)
beadloom setup-mcp --tool windsurf

# Remove configuration
beadloom setup-mcp --remove
```

Claude Code (`.mcp.json`):

```json
{
  "mcpServers": {
    "beadloom": {
      "command": "beadloom",
      "args": ["mcp-serve"]
    }
  }
}
```

Cursor (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "beadloom": {
      "command": "beadloom",
      "args": ["mcp-serve"]
    }
  }
}
```

Windsurf (`~/.codeium/windsurf/mcp_config.json`):

```json
{
  "mcpServers": {
    "beadloom": {
      "command": "beadloom",
      "args": ["mcp-serve", "--project", "/path/to/project"]
    }
  }
}
```

Note: Windsurf uses a global config, so the `--project` path is automatically included.

### Features

- **Auto-reindex**: before each tool call, checks if the index is stale by comparing file mtimes with `last_reindex_at`. If stale, runs `incremental_reindex()` transparently.
- **Two-level caching**: L1 in-memory `ContextCache` for `get_context` and `get_graph` (keyed by ref_id + params + file mtimes), L2 `SqliteCache` for persistence across calls. Cache is invalidated on `update_node` calls and after auto-reindex.

### Available Tools

#### get_context

Get a context bundle for a set of ref_id(s).

```json
{
  "name": "get_context",
  "arguments": {
    "ref_id": "context-oracle",
    "depth": 2,
    "max_nodes": 20,
    "max_chunks": 10
  }
}
```

Returns JSON with fields: version, focus, graph (nodes + edges), text_chunks, code_symbols, sync_status. Supports L1/L2 caching -- returns `{"cached": true, "etag": ..., "hint": ...}` when unchanged.

#### get_graph

Get a subgraph from specified nodes or the entire graph.

```json
{
  "name": "get_graph",
  "arguments": {
    "ref_id": "beadloom",
    "depth": 2
  }
}
```

Supports L1/L2 caching with mtime-based invalidation.

#### list_nodes

List all nodes in the architecture graph.

```json
{
  "name": "list_nodes",
  "arguments": {
    "kind": "domain"
  }
}
```

`kind` is optional. When provided, filters by node type: `domain`, `feature`, `service`, `entity`, `adr`.

#### sync_check

Check doc-code synchronization.

```json
{
  "name": "sync_check",
  "arguments": {
    "ref_id": "context-oracle"
  }
}
```

Returns list of sync pairs with `status`, `ref_id`, `doc_path`, `code_path`, `reason`, and optional `details`.

#### get_status

Get index statistics.

```json
{
  "name": "get_status",
  "arguments": {}
}
```

Returns: `nodes_count`, `edges_count`, `docs_count`, `chunks_count`, `symbols_count`, `stale_count`, `doc_coverage`, `last_reindex`, `beadloom_version`.

#### update_node

Update a graph node's summary or source path in YAML and SQLite.

```json
{
  "name": "update_node",
  "arguments": {
    "ref_id": "context-oracle",
    "summary": "Updated description",
    "source": "src/beadloom/context_oracle/"
  }
}
```

Invalidates L1 and L2 cache for the affected ref_id.

#### mark_synced

Mark all doc-code pairs for a ref_id as synced (after updating docs).

```json
{
  "name": "mark_synced",
  "arguments": {
    "ref_id": "context-oracle"
  }
}
```

Returns: `{ "ref_id": "...", "pairs_synced": N }`.

#### search

Search nodes and documentation by keyword (FTS5 with LIKE fallback).

```json
{
  "name": "search",
  "arguments": {
    "query": "context",
    "kind": "domain",
    "limit": 10
  }
}
```

#### generate_docs

Generate structured documentation data from the architecture graph for AI-driven enrichment.

```json
{
  "name": "generate_docs",
  "arguments": {
    "ref_id": "context-oracle"
  }
}
```

Returns JSON with: nodes (ref_id, kind, summary, source, symbols, dependencies, existing_doc, symbol_changes), architecture (mermaid diagram), and instructions (AI enrichment prompt). Omit `ref_id` for all nodes.

#### prime

Get compact project context for session start. Call this at the beginning of every session.

```json
{
  "name": "prime",
  "arguments": {}
}
```

Returns JSON with: project name, version, architecture summary (domain/service/feature counts, symbols), health (stale docs, lint violations, last reindex), architecture rules, domain list, and agent instructions.

#### why

Impact analysis: show upstream dependencies and downstream dependents for a node.

```json
{
  "name": "why",
  "arguments": {
    "ref_id": "context-oracle"
  }
}
```

Returns: `ref_id`, flattened `upstream` list, flattened `downstream` list, and `impact_summary`.

#### diff

Show graph changes since a git ref (commit, branch, tag).

```json
{
  "name": "diff",
  "arguments": {
    "since": "HEAD~1"
  }
}
```

Returns: `since`, `added_nodes`, `removed_nodes`, `changed_nodes` (with old/new summaries), `added_edges`, `removed_edges`.

#### lint

Run architecture lint rules. Returns violations as JSON.

```json
{
  "name": "lint",
  "arguments": {
    "severity": "all"
  }
}
```

`severity` filter: `all` (default), `error`, `warn`. Returns: `violations` list (each with `rule`, `severity`, `rule_type`, `file_path`, `line_number`, `from_ref_id`, `to_ref_id`, `message`) and `summary` (`errors`, `warnings`, `rules_evaluated`).

#### get_debt_report

Get architecture debt report with score, categories, and top offenders.

```json
{
  "name": "get_debt_report",
  "arguments": {
    "trend": true,
    "category": "rule_violations"
  }
}
```

`trend` (boolean, default false): include trend vs last snapshot. `category` (string, optional): filter to specific category -- accepts `rule_violations`, `doc_gaps`, `complexity`, `test_gaps` (or short names: `rules`, `docs`, `tests`). Returns: `debt_score` (0-100), `severity` (clean/low/medium/high/critical), `categories` list (each with `name`, `score`, `details`), `top_offenders` list (each with `ref_id`, `score`, `reasons`), and `trend` (null or object with `previous_snapshot`, `previous_score`, `delta`, `category_deltas`).

### Process-tools (BDL-048)

Four tools that expose the deterministic steps of Beadloom's multi-agent dev flow to any MCP client. They are single deterministic operations — they do **NOT** orchestrate or spawn sub-agents (orchestration stays in the harness; see the honest boundary in the [Agentic Dev Flow guide](../guides/agentic-flow.md)). The three bead-touching tools drive the `bd` (beads) CLI through a thin, mockable seam (`services/bd_seam.py:run_bd`); if `bd` is absent they return a structured `{"status": "ERROR", ...}`.

#### task_init

Scaffold a work item: create its docs folder + per-type skeletons and a valid 4-role bead DAG.

```json
{
  "name": "task_init",
  "arguments": {
    "type": "feature",
    "key": "ABC-123"
  }
}
```

`type` (one of `epic`, `feature`, `bug`, `task`, `chore`) selects the doc set (PRD/RFC/CONTEXT/PLAN/ACTIVE for `epic`/`feature`; BRIEF/ACTIVE otherwise) and the bead type. `key` names the `.claude/development/docs/features/<key>/` folder. Creates a dev → test → review → tech-writer bead DAG (each role depending on the previous) via `bd`. Returns `{ "status": "OK", "bead_ids": [...], "doc_paths": [...] }` (or `{"status": "ERROR", ...}` with the partial `doc_paths`).

#### bead_context

Return ONE structured payload for a bead: graph context + impact + doc excerpt + active rules.

```json
{
  "name": "bead_context",
  "arguments": {
    "bead": "bd-42"
  }
}
```

Resolves the bead's graph ref from a `ref:` (or `area:`) token in the bead's design/description via `bd show`, then reuses `context_oracle` (ctx + why) and `graph/rule_engine` (active rules). Read-only and deterministic. Returns `{ "status": "OK", "bead", "ref_id", "context", "impact", "active_rules", "doc_excerpt" }` (a `CONTEXT.md`/`ACTIVE.md` excerpt when locatable, else null). Returns `{"status": "ERROR", ...}` when the ref cannot be resolved or is not in the graph.

#### complete_bead

The **refusing completion gate**: run `beadloom ci` (+ tests) before closing a bead.

```json
{
  "name": "complete_bead",
  "arguments": {
    "bead": "bd-42",
    "run_tests": true
  }
}
```

Runs the `beadloom ci` gate (reindex → lint → sync-check → config-check → doctor, via `application/gate.run_ci_gate`) and, when `run_tests` is true (the default), the test suite. **On PASS** it closes the bead (`bd close --suggest-next`) and returns `{ "status": "PASS", "bead", "findings": [], "next": ... }`. **On FAIL** it does NOT close the bead — it returns `{ "status": "FAIL", "bead", "findings": [...] }` so the agent must fix the findings first. Set `run_tests=false` for a fast gate-only check (skips the suite). This gate is **advisory-strong**, not the true enforcement point — `beadloom ci` in CI remains the single source of true enforcement.

#### checkpoint

Record a checkpoint: a `bd comments add` plus a timestamped ACTIVE.md note.

```json
{
  "name": "checkpoint",
  "arguments": {
    "bead": "bd-42",
    "text": "CHECKPOINT: wired the parser"
  }
}
```

Adds `text` as a bead comment (preserves history) and, best-effort, appends a timestamped progress line to the bead's ACTIVE.md (skipped cleanly when the file cannot be located). Returns `{ "status": "OK", "bead", "comment_added": true, "active_updated": <bool> }`.

## API

MCP server is implemented in `src/beadloom/services/mcp_server.py`:

- `create_server(project_root)` -- creates an MCP Server with registered handlers, auto-reindex, and two-level caching
- `_dispatch_tool(conn, name, args, project_root?, cache?, l2_cache?)` -- routes calls to handlers with cache management
- `_ensure_fresh_index(project_root, conn)` -- auto-reindex if stale (compares file mtimes with `last_reindex_at`)
- `_is_index_stale(project_root, conn)` -- check staleness by comparing graph/docs mtimes

Handler functions (sync, testable without MCP transport):
- `handle_get_context(conn, *, ref_id, depth=2, max_nodes=20, max_chunks=10)` -- context bundle
- `handle_get_graph(conn, *, ref_id, depth=2)` -- subgraph
- `handle_list_nodes(conn, kind=None)` -- list nodes
- `handle_sync_check(conn, ref_id=None, project_root=None)` -- sync status
- `handle_get_status(conn)` -- index statistics
- `handle_update_node(conn, project_root, *, ref_id, summary=None, source=None)` -- update node
- `handle_mark_synced(conn, project_root, *, ref_id)` -- mark synced
- `handle_search(conn, *, query, kind=None, limit=10)` -- FTS5 search
- `handle_why(conn, *, ref_id, depth=3)` -- impact analysis with flattened upstream/downstream
- `handle_diff(project_root, *, since="HEAD~1")` -- graph diff
- `handle_lint(project_root, *, severity="all")` -- architecture lint
- `handle_get_debt_report(conn, project_root, *, trend=False, category=None)` -- architecture debt report

Process-tool handlers (BDL-048; the three bead-touching ones drive `bd` via the `services/bd_seam.py:run_bd` seam):
- `handle_task_init(project_root, *, type_, key)` -- scaffold docs folder + per-type skeletons + a 4-role bead DAG (dev → test → review → tech-writer)
- `handle_bead_context(project_root, *, bead)` -- one payload: ctx + why + CONTEXT/ACTIVE excerpt + active rules (resolves the bead's graph ref from `bd show`)
- `handle_complete_bead(project_root, *, bead, run_tests=True)` -- the refusing gate: `run_ci_gate` (+ tests); PASS closes the bead (`bd close --suggest-next`), FAIL returns findings and does NOT close; advisory-strong (CI is the true gate)
- `handle_checkpoint(project_root, *, bead, text)` -- `bd comments add` + best-effort timestamped ACTIVE.md note

The `bd` seam lives in `src/beadloom/services/bd_seam.py`: `run_bd(args, *, cwd=None)` returns a `BdResult(returncode, stdout, stderr)` (with `.ok`), and raises `BdUnavailableError` with a clear message when the `bd` binary is not on PATH. Tests patch this seam so the process-tools run without a real `bd` binary.

## Testing

Tests in `tests/test_mcp_server.py` and `tests/test_mcp_new_tools.py` verify each read/write handler directly (without MCP transport). The process-tools are tested in `tests/test_mcp_process_tools.py` (with the `bd` seam + gate mocked — `complete_bead` is asserted to REFUSE on a red gate and to close on green) and the seam itself in `tests/test_bd_seam.py`.
