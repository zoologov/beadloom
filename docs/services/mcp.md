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

Returns JSON with fields: version, focus, graph (nodes + edges), text_chunks, code_symbols, sync_status, constraints, intent, routes, tests. Supports L1/L2 caching -- returns `{"cached": true, "etag": ..., "hint": ...}` when unchanged.

The `intent` field carries the epics whose planning documents declared the focus node, so an agent asking what a node IS also learns what it is FOR. It is filled when the server knows the project root, and reports `{"status": "not_checked", "reason": "intent_space_not_read"}` when it does not -- a different statement from "no epic declares this node", which is `{"status": "none_declared"}` and carries the number of epics that were read. See `docs/domains/context-oracle/components/node-intent/DOC.md`.

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

Since BDL-061 S4b the result also carries `incomplete` rows — a document that is
current and does not carry the shape its kind requires (`missing_sections`,
`section_not_in_use`). They are `warn`: reported, never blocking. The tool
resolves the required sections from the project's composed doc templates, so an
`ref_id`-less call is the honest whole-project view.

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

Resolves the bead's graph ref from a `ref:`, `refs:` or `area:` token in the bead's design/description via `bd show`, then reuses `context_oracle` (ctx + why) and `graph/rule_engine` (active rules). Read-only and deterministic. Returns `{ "status": "OK", "bead", "ref_id", "context", "impact", "active_rules", "doc_excerpt" }` (a `CONTEXT.md`/`ACTIVE.md` excerpt when locatable, else null). Returns `{"status": "ERROR", ...}` when the ref cannot be resolved or is not in the graph.

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

Runs the `beadloom ci` gate (reindex → lint → sync-check → docs audit → docs-quality → doc-spaces → config-check → doctor, via `application/gate.run_ci_gate`) and, when `run_tests` is true (the default), the test suite. **On PASS** it closes the bead (`bd close --suggest-next`), best-effort flips the bead's row in the epic's `ACTIVE.md` bead-status table to `✓ done`, and returns `{ "status": "PASS", "bead", "findings": [], "next": ..., "active_updated": <bool> }`. **On FAIL** it does NOT close the bead and leaves the table untouched — it returns `{ "status": "FAIL", "bead", "findings": [...] }` so the agent must fix the findings first. Set `run_tests=false` for a fast gate-only check (skips the suite). This gate is **advisory-strong**, not the true enforcement point — `beadloom ci` in CI remains the single source of true enforcement.

#### checkpoint

Record a checkpoint: a `bd comments add` plus ACTIVE.md note + bead-status table row update.

```json
{
  "name": "checkpoint",
  "arguments": {
    "bead": "bd-42",
    "text": "CHECKPOINT: wired the parser",
    "status": "in progress"
  }
}
```

Adds `text` as a bead comment (preserves history) and, best-effort: appends a timestamped progress line to the bead's ACTIVE.md AND flips the bead's row in the ACTIVE.md bead-status table to `status` (default `"in progress"`). Both ACTIVE.md updates are skipped cleanly when the file/table/row cannot be located. Returns `{ "status": "OK", "bead", "comment_added": true, "active_updated": <bool>, "table_updated": <bool> }`.

The bead-status table updater (`_set_active_table_status`) is deterministic and **tolerant**: it matches the bead-id as a whole token in the row's first cell (so `…mukc.1` never collaterally matches `…mukc.10`), replaces the row's last (status) cell, and preserves every other row and the file's formatting; a missing file, no table, or no matching row is a no-op (returns `False`, file unchanged). It never raises and never corrupts the file — so it cannot fail the tool or the close.

## API

MCP server is implemented in `src/beadloom/services/mcp_server.py`:

- `create_server(project_root)` -- creates an MCP Server with registered handlers, auto-reindex, and two-level caching

Beadloom requires **mcp >= 2.0**. The 2.0 low-level API takes its handlers as
constructor arguments (`Server(on_list_tools=..., on_call_tool=...)`) instead of
the `@server.list_tools()` / `@server.call_tool()` decorators of 1.x, and the
handlers exchange protocol result models (`ListToolsResult`, `CallToolResult`)
rather than bare lists. One behavioural consequence is explicit here: 1.x
wrapped an exception raised by a tool handler into an error result, while 2.0
hands it to the runner, so `create_server` classifies a dispatch failure
(unknown tool, missing `ref_id`) itself and returns `CallToolResult(is_error=True)`
— the agent gets a correctable in-band message instead of a protocol error.
- `_dispatch_tool(conn, name, args, project_root?, cache?, l2_cache?)` -- routes calls to handlers with cache management
- `_ensure_fresh_index(project_root, conn)` -- auto-reindex if stale (compares file mtimes with `last_reindex_at`)
- `_is_index_stale(project_root, conn)` -- check staleness by comparing graph/docs mtimes

Handler functions (sync, testable without MCP transport):
- `handle_get_context(conn, *, ref_id, depth=2, max_nodes=20, max_chunks=10, project_root=None)` -- context bundle; `project_root` is what lets the bundle carry recorded intent, and without it the bundle says intent was not checked rather than absent
- `handle_get_graph(conn, *, ref_id, depth=2)` -- subgraph
- `handle_list_nodes(conn, kind=None)` -- list nodes
- `handle_sync_check(conn, ref_id=None, project_root=None)` -- sync status, including the `incomplete` document-shape rows when `project_root` is given (the required sections are resolved from that root, so they cannot be resolved without one)
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
- `handle_bead_context(project_root, *, bead)` -- one payload: ctx + why + CONTEXT/ACTIVE excerpt + active rules (resolves the bead's graph ref from `bd show`, through the same `application.waves.declared_refs` parser AND the same `application.waves.compose_declaration` composer `beadloom waves` reads a bead's declared scope with, so the tool and the wave planner cannot come to disagree about what a bead said -- the composer matters as much as the parser, because this tool used to join the tracker's fields with a space where both CLI callers joined them with a newline, and a dangling `refs:` header then adopted the next field's first word; the ALPHABETICALLY first declared ref is the one this tool builds a bundle for, since the parser returns them sorted)
- `handle_complete_bead(project_root, *, bead, run_tests=True)` -- the refusing gate: `run_ci_gate` (+ tests); PASS closes the bead (`bd close --suggest-next`) + best-effort flips its ACTIVE.md table row to `✓ done`, FAIL returns findings and does NOT close (table untouched); advisory-strong (CI is the true gate)
- The suite runner behind it (`_run_test_suite`) reads pytest's output with a stated `encoding="utf-8"`, `errors="replace"`. It keeps only the summary line, and that line carries a test id, a path or an arrow often enough that inheriting the image's locale turned "the suite failed" into an unrelated decode error on a non-UTF-8 container; `replace` because the string is shown to an agent as prose, so a visible U+FFFD beats an exception (BDL-061.42)
- `handle_checkpoint(project_root, *, bead, text, status="in progress")` -- `bd comments add` + best-effort timestamped ACTIVE.md note + best-effort ACTIVE.md table row → `status`
- `_set_active_table_status(active_path, bead_id, status)` -- deterministic, tolerant markdown-table row updater (whole-token bead-id match in the first cell; replaces the last cell; no-op + `False` on missing file/table/row; never raises)

The `bd` seam lives in `src/beadloom/services/bd_seam.py`: `run_bd(args, *, cwd=None)` returns a `BdResult(returncode, stdout, stderr)` (with `.ok`), and raises `BdUnavailableError` when `bd` cannot be run **to completion** — missing from PATH, present but not executable, wedged past the 60 s timeout, or answering in bytes that cannot be decoded. The message always names the underlying class — *bd could not be run to completion (TimeoutExpired: …)* — and `FileNotFoundError` keeps its own wording because installing `bd` is the one remedy a reader can act on. A non-zero *exit* is not this case: that is `bd` answering, and it comes back as a `BdResult`. Output is decoded with an explicit `utf-8` / `surrogateescape` codec rather than the ambient locale, so one non-UTF-8 byte in a bead title cannot turn a tool call into a crash (BDL-061.37). Tests patch this seam so the process-tools run without a real `bd` binary.

Setup and configuration commands are in `src/beadloom/services/commands/setup.py`. Only
`mcp_serve` belongs to this service; the rest carry `# beadloom:domain=onboarding` and are
specified in the [onboarding domain](../domains/onboarding/README.md). They share the module
because they share the `setup-*` option surface, which is why a change to any of them makes
both documents stale:

- `mcp_serve(*, project)` -- launch the MCP server over stdio; exits 1 with `Run `beadloom reindex` first` when the index is absent
- `setup_mcp(*, remove, tool_name, project)` -- create, update or remove the MCP config for a supported editor
- `setup_rules(*, tool_name, project, refresh, dry_run)` -- generate IDE adapter files; `--refresh` re-renders the `CLAUDE.md` auto-regions and `--dry-run` previews without writing
- `setup_ai_techwriter(*, platform, project)` -- scaffold the AI tech-writer harness for `github` or `gitlab`
- `setup_agentic_flow(*, project, force, tools, architecture, stack)` -- compose and write the agentic dev flow; selection is flag over `flow.yml` over default
- `setup_branch_protection(*, repo_slug, branch, contexts, dry_run)` -- apply branch protection via `gh api`; `--dry-run` prints the call and payload without touching GitHub
- `config_check(*, fix, project)` -- report agent-config drift. Warnings print `! <file>: <reason>` with a `-> <remediation>` line and **do not block**; the command exits 1 only on error-severity drift, and a clean run says `Agent-config in sync — no blocking drift` with the warning count appended when there is one
- `init(*, bootstrap, preset, import_path, init_mode, non_interactive, force, project)` -- project initialization; also appends Beadloom's generated working set to the project's `.gitignore`, once

## Testing

Tests in `tests/test_mcp_server.py` and `tests/test_mcp_new_tools.py` verify each read/write handler directly (without MCP transport). `TestMcpProtocolHandlers` additionally drives the registered `tools/list` and `tools/call` entries the way the runner does — including the unknown-tool in-band error — so a protocol-layer change cannot pass on `create_server` merely returning an object. The process-tools are tested in `tests/test_mcp_process_tools.py` (with the `bd` seam + gate mocked — `complete_bead` is asserted to REFUSE on a red gate and to close on green) and the seam itself in `tests/test_bd_seam.py`.
