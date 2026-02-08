# MCP Server

Beadloom provides an MCP (Model Context Protocol) server for integration with AI agents.

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
    "ref_ids": ["context-oracle"],
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
    "ref_ids": ["beadloom"],
    "depth": 2
  }
}
```

#### list_nodes

List all nodes in the knowledge graph.

```json
{
  "name": "list_nodes",
  "arguments": {}
}
```

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

## API

MCP server is implemented in `src/beadloom/mcp_server.py`:

- `create_server(project_root)` — creates an MCP Server with registered handlers
- Each tool has a sync handler (handle_*) for ease of testing
- `_dispatch_tool(conn, name, args)` — routes calls to handlers

## Testing

Tests in `tests/test_mcp_server.py` verify each handler directly (without MCP transport).
