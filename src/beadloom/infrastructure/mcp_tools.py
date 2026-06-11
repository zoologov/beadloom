# beadloom:domain=infrastructure
# beadloom:component=mcp-tools
"""Canonical catalog of MCP tools — single source of truth for tool names.

The MCP server (``services/mcp_server.py``) builds full ``mcp.Tool`` objects
(with input schemas) from this catalog, and agent-facing documentation
(``onboarding`` ``generate_agents_md``) enumerates the same catalog.  Keeping a
single ordered list here means the documented tool count can never drift from
the registered count (BDL-UX-Issues #93).

This module lives in ``infrastructure`` (the lowest, domain-agnostic layer) so
both the ``services`` and ``onboarding`` layers may depend on it without
violating the architecture layering rules.
"""

# beadloom:domain=infrastructure

from __future__ import annotations

from typing import NamedTuple


class McpToolDoc(NamedTuple):
    """Documentation entry for a single MCP tool.

    ``name`` is the registered tool name; ``summary`` is the one-line
    description shown in agent-facing docs (``AGENTS.md``).
    """

    name: str
    summary: str


# Ordered catalog — the canonical, single source of truth for MCP tool names.
# Order matches the registration order in ``services/mcp_server.py`` ``_TOOLS``.
MCP_TOOL_CATALOG: tuple[McpToolDoc, ...] = (
    McpToolDoc("get_context", "Full context bundle (graph + docs + code)"),
    McpToolDoc("get_graph", "Subgraph around a node"),
    McpToolDoc("list_nodes", "List nodes, optionally by kind"),
    McpToolDoc("sync_check", "Check doc-code freshness"),
    McpToolDoc("get_status", "Index statistics and coverage"),
    McpToolDoc("update_node", "Update node summary or source"),
    McpToolDoc("mark_synced", "Mark doc-code pair as synchronized"),
    McpToolDoc("search", "Full-text search across nodes and docs"),
    McpToolDoc("generate_docs", "Enrichment data for AI doc polish"),
    McpToolDoc("prime", "Compact project context for session start"),
    McpToolDoc("why", "Impact analysis — upstream and downstream deps"),
    McpToolDoc("diff", "Graph changes since a git ref"),
    McpToolDoc("lint", "Architecture boundary violations with severity"),
    McpToolDoc("get_debt_report", "Architecture debt report with score and offenders"),
    McpToolDoc("task_init", "Scaffold a work item: docs folder + 4-role bead DAG"),
    McpToolDoc("bead_context", "One payload: ctx + why + doc excerpt + active rules"),
    McpToolDoc("complete_bead", "Refusing gate: run beadloom ci (+tests); close only on PASS"),
    McpToolDoc("checkpoint", "bd comment + timestamped ACTIVE.md progress note"),
)


def mcp_tool_names() -> tuple[str, ...]:
    """Return the registered MCP tool names in catalog order."""
    return tuple(entry.name for entry in MCP_TOOL_CATALOG)
