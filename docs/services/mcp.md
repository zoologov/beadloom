# MCP Server

Beadloom provides an MCP (Model Context Protocol) server with 13 tools for integration with AI agents.

## Specification

### Transport

The server operates via stdio transport. Launch:

```bash
beadloom mcp-serve [--project DIR]
```

Configuration for Claude Code (`.mcp.json`):

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

Automatic setup: `beadloom setup-mcp`

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

## Testing

Tests in `tests/test_mcp_server.py` and `tests/test_mcp_new_tools.py` verify each handler directly (without MCP transport).
