"""MCP server: stdio-based tool server for AI agents."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import mcp
from mcp.server import Server

from beadloom import __version__
from beadloom.context_builder import bfs_subgraph, build_context
from beadloom.db import get_meta, open_db
from beadloom.sync_engine import check_sync

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# --- Tool handler functions (sync, testable without transport) ---


# beadloom:service=mcp-server
def handle_get_context(
    conn: sqlite3.Connection,
    *,
    ref_id: str,
    depth: int = 2,
    max_nodes: int = 20,
    max_chunks: int = 10,
) -> dict[str, Any]:
    """Get context bundle for a ref_id."""
    return build_context(
        conn,
        [ref_id],
        depth=depth,
        max_nodes=max_nodes,
        max_chunks=max_chunks,
    )


def handle_get_graph(
    conn: sqlite3.Connection,
    *,
    ref_id: str,
    depth: int = 2,
) -> dict[str, Any]:
    """Get subgraph around a node."""
    nodes, edges = bfs_subgraph(conn, [ref_id], depth=depth)
    return {"nodes": nodes, "edges": edges}


def handle_list_nodes(
    conn: sqlite3.Connection,
    kind: str | None = None,
) -> list[dict[str, str]]:
    """List all graph nodes, optionally filtered by kind."""
    if kind:
        rows = conn.execute(
            "SELECT ref_id, kind, summary FROM nodes WHERE kind = ?",
            (kind,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT ref_id, kind, summary FROM nodes"
        ).fetchall()

    return [
        {"ref_id": r["ref_id"], "kind": r["kind"], "summary": r["summary"]}
        for r in rows
    ]


def handle_sync_check(
    conn: sqlite3.Connection,
    ref_id: str | None = None,
    project_root: Path | None = None,
) -> list[dict[str, str]]:
    """Check sync status, optionally for a specific ref_id."""
    results = check_sync(conn, project_root=project_root)
    if ref_id:
        results = [r for r in results if r["ref_id"] == ref_id]
    return results


def handle_get_status(
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Get project index statistics."""
    nodes_count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    edges_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
    docs_count = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
    chunks_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    symbols_count = conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0]
    stale_count = conn.execute(
        "SELECT count(*) FROM sync_state WHERE status = 'stale'"
    ).fetchone()[0]

    covered = conn.execute(
        "SELECT count(DISTINCT n.ref_id) FROM nodes n "
        "JOIN docs d ON d.ref_id = n.ref_id"
    ).fetchone()[0]

    return {
        "nodes_count": nodes_count,
        "edges_count": edges_count,
        "docs_count": docs_count,
        "chunks_count": chunks_count,
        "symbols_count": symbols_count,
        "stale_count": stale_count,
        "doc_coverage": covered,
        "last_reindex": get_meta(conn, "last_reindex_at"),
        "beadloom_version": get_meta(conn, "beadloom_version"),
    }


# --- MCP Server creation ---

_TOOLS = [
    mcp.Tool(
        name="get_context",
        description=(
            "Get a compact context bundle for a feature/domain/service/entity "
            "by ref_id. Returns graph, relevant documentation chunks, and code "
            "symbols. Includes sync status and stale index warnings."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ref_id": {
                    "type": "string",
                    "description": "Node identifier (e.g. PROJ-123, routing)",
                },
                "depth": {
                    "type": "integer",
                    "default": 2,
                    "description": "Graph traversal depth",
                },
                "max_nodes": {
                    "type": "integer",
                    "default": 20,
                    "description": "Max nodes in subgraph",
                },
                "max_chunks": {
                    "type": "integer",
                    "default": 10,
                    "description": "Max text chunks in bundle",
                },
            },
            "required": ["ref_id"],
        },
    ),
    mcp.Tool(
        name="get_graph",
        description="Get a subgraph around a node. Returns nodes and edges as JSON.",
        inputSchema={
            "type": "object",
            "properties": {
                "ref_id": {"type": "string"},
                "depth": {"type": "integer", "default": 2},
            },
            "required": ["ref_id"],
        },
    ),
    mcp.Tool(
        name="list_nodes",
        description=(
            "List all graph nodes, optionally filtered by kind. "
            "Returns ref_id, kind, and summary for each node."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["domain", "feature", "service", "entity", "adr"],
                },
            },
        },
    ),
    mcp.Tool(
        name="sync_check",
        description=(
            "Check if documentation is up-to-date with code. "
            "Returns list of stale docs with changed code paths."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ref_id": {
                    "type": "string",
                    "description": "Check specific node. Omit for full project check.",
                },
            },
        },
    ),
    mcp.Tool(
        name="get_status",
        description=(
            "Get project documentation coverage and index status. "
            "Returns coverage percentages and stale doc count."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
]


def create_server(project_root: Path) -> Server:
    """Create and configure the MCP server for a project."""
    server = Server(
        name="beadloom",
        version=__version__,
        instructions="Beadloom Context Oracle — knowledge graph for AI-assisted development.",
    )

    db_path = project_root / ".beadloom" / "beadloom.db"

    @server.list_tools()  # type: ignore[misc]
    async def _list_tools() -> list[mcp.Tool]:
        return _TOOLS

    @server.call_tool()  # type: ignore[misc]
    async def _call_tool(
        name: str,
        arguments: dict[str, Any] | None,
    ) -> list[mcp.TextContent]:
        args = arguments or {}
        conn = open_db(db_path)
        try:
            result = _dispatch_tool(conn, name, args, project_root=project_root)
            return [mcp.TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2),
            )]
        except LookupError as exc:
            return [mcp.TextContent(type="text", text=f"Error: {exc}")]
        finally:
            conn.close()

    return server


def _dispatch_tool(
    conn: sqlite3.Connection,
    name: str,
    args: dict[str, Any],
    project_root: Path | None = None,
) -> Any:
    """Route tool call to the appropriate handler."""
    if name == "get_context":
        return handle_get_context(
            conn,
            ref_id=args["ref_id"],
            depth=args.get("depth", 2),
            max_nodes=args.get("max_nodes", 20),
            max_chunks=args.get("max_chunks", 10),
        )
    if name == "get_graph":
        return handle_get_graph(
            conn,
            ref_id=args["ref_id"],
            depth=args.get("depth", 2),
        )
    if name == "list_nodes":
        return handle_list_nodes(conn, kind=args.get("kind"))
    if name == "sync_check":
        return handle_sync_check(
            conn, ref_id=args.get("ref_id"), project_root=project_root,
        )
    if name == "get_status":
        return handle_get_status(conn)

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)
