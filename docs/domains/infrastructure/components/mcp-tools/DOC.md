# MCP Tools (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/mcp_tools.py`

---

## Overview

The canonical, single-source-of-truth catalog of MCP tool names. The MCP server
builds full `mcp.Tool` objects (with input schemas) from this catalog, and the
agent-facing docs generator enumerates the same list — so the documented tool
count can never drift from the registered count. Lives in `infrastructure` (the
lowest layer) so both `services` and `onboarding` may depend on it without
violating the layering rules.

## Public surface

- `MCP_TOOL_CATALOG` — the canonical ordered tuple of `McpToolDoc` entries
  (currently 18 tools, each a `(name, description)` pair).
- `mcp_tool_names()` — the tuple of tool names derived from the catalog.
- `McpToolDoc` — a `NamedTuple` of `(name, description)` for one tool.

## Collaborators

The MCP server (`services/mcp_server.py`) builds full `mcp.Tool` objects (with
input schemas) from this catalog; the onboarding AGENTS.md generator
(`scanner.generate_agents_md`) enumerates the same list. A drift-guard test
pins `mcp_tool_names()` to the live MCP `_TOOLS` registry, so the documented
tool count can never diverge from the registered count.

> Component doc (BDL-051). Public surface verified against `mcp_tools.py`.
