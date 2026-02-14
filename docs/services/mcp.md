# MCP Server

Beadloom provides an MCP (Model Context Protocol) server with 10 tools for integration with AI agents.

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

Returns JSON with fields: version, focus, graph (nodes + edges), text_chunks, code_symbols, sync_status.

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

Check doc↔code synchronization.

```json
{
  "name": "sync_check",
  "arguments": {
    "ref_id": "context-oracle"
  }
}
```

#### get_status

Get index statistics.

```json
{
  "name": "get_status",
  "arguments": {}
}
```

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

#### mark_synced

Mark all doc↔code pairs for a ref_id as synced (after updating docs).

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

Returns JSON with: nodes (ref_id, kind, summary, source, symbols, dependencies, existing_doc), architecture (mermaid diagram), and instructions (AI enrichment prompt). Omit `ref_id` for all nodes.

#### prime

Get compact project context for session start. Call this at the beginning of every session.

```json
{
  "name": "prime",
  "arguments": {}
}
```

Returns JSON with: project name, version, architecture summary (domain/service/feature counts, symbols), health (stale docs, lint violations, last reindex), architecture rules, domain list, and agent instructions.

## API

MCP server is implemented in `src/beadloom/services/mcp_server.py`:

- `create_server(project_root)` — creates an MCP Server with registered handlers
- Each tool has a sync handler (handle_*) for ease of testing
- `_dispatch_tool(conn, name, args)` — routes calls to handlers

## Testing

Tests in `tests/test_mcp_server.py` verify each handler directly (without MCP transport).
