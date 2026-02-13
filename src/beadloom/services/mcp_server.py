"""MCP server: stdio-based tool server for AI agents."""

# beadloom:service=mcp-server

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import mcp
from mcp.server import Server
from mcp.types import TextContent

from beadloom import __version__
from beadloom.context_oracle.builder import bfs_subgraph, build_context
from beadloom.context_oracle.cache import ContextCache, SqliteCache, compute_etag
from beadloom.doc_sync.engine import check_sync, mark_synced_by_ref
from beadloom.graph.loader import update_node_in_yaml
from beadloom.infrastructure.db import get_meta, open_db
from beadloom.infrastructure.reindex import incremental_reindex

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# --- Mtime helpers for cache invalidation ---


def _compute_dir_mtime(directory: Path) -> float:
    """Return the max mtime of all files under *directory*."""
    max_mtime = 0.0
    if not directory.exists():
        return max_mtime
    for f in directory.rglob("*"):
        if f.is_file():
            try:
                mt = f.stat().st_mtime
                if mt > max_mtime:
                    max_mtime = mt
            except OSError:
                continue
    return max_mtime


def _compute_mtimes(project_root: Path) -> tuple[float, float]:
    """Compute (graph_mtime, docs_mtime) for a project."""
    graph_dir = project_root / ".beadloom" / "_graph"
    docs_dir = project_root / "docs"
    return _compute_dir_mtime(graph_dir), _compute_dir_mtime(docs_dir)


# --- Auto-reindex ---


def _is_index_stale(project_root: Path, conn: sqlite3.Connection) -> bool:
    """Check if the index is stale by comparing mtimes with last_reindex_at."""
    last_reindex = get_meta(conn, "last_reindex_at")
    if last_reindex is None:
        return False
    from datetime import datetime

    try:
        last_ts = datetime.fromisoformat(last_reindex).timestamp()
    except ValueError:
        return False
    graph_mt, docs_mt = _compute_mtimes(project_root)
    return max(graph_mt, docs_mt) > last_ts


def _ensure_fresh_index(project_root: Path, conn: sqlite3.Connection) -> bool:
    """Auto-reindex if stale. Returns ``True`` if reindex was performed."""
    if not _is_index_stale(project_root, conn):
        return False
    incremental_reindex(project_root)
    return True


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
        rows = conn.execute("SELECT ref_id, kind, summary FROM nodes").fetchall()

    return [{"ref_id": r["ref_id"], "kind": r["kind"], "summary": r["summary"]} for r in rows]


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
        "SELECT count(DISTINCT n.ref_id) FROM nodes n JOIN docs d ON d.ref_id = n.ref_id"
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


# --- Write tool handlers ---


def handle_update_node(
    conn: sqlite3.Connection,
    project_root: Path,
    *,
    ref_id: str,
    summary: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Update a graph node's summary/source in YAML and SQLite."""
    graph_dir = project_root / ".beadloom" / "_graph"
    if not graph_dir.is_dir():
        msg = f"Graph directory not found: {graph_dir}"
        raise LookupError(msg)

    updated = update_node_in_yaml(
        graph_dir,
        conn,
        ref_id,
        summary=summary,
        source=source,
    )
    if not updated:
        msg = f"Node '{ref_id}' not found in graph YAML"
        raise LookupError(msg)

    return {"updated": True, "ref_id": ref_id}


def handle_mark_synced(
    conn: sqlite3.Connection,
    project_root: Path,
    *,
    ref_id: str,
) -> dict[str, Any]:
    """Mark all doc-code pairs for ref_id as synced."""
    count = mark_synced_by_ref(conn, ref_id, project_root)
    return {"ref_id": ref_id, "pairs_synced": count}


def handle_search(
    conn: sqlite3.Connection,
    *,
    query: str,
    kind: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search using FTS5 with fallback to SQL LIKE."""
    from beadloom.context_oracle.search import has_fts5, search_fts5

    if has_fts5(conn):
        return search_fts5(conn, query, kind=kind, limit=limit)

    # Fallback to SQL LIKE when FTS5 is not populated.
    like_pattern = f"%{query}%"
    if kind:
        rows = conn.execute(
            "SELECT ref_id, kind, summary FROM nodes "
            "WHERE kind = ? AND (ref_id LIKE ? OR summary LIKE ?) "
            "LIMIT ?",
            (kind, like_pattern, like_pattern, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT ref_id, kind, summary FROM nodes "
            "WHERE ref_id LIKE ? OR summary LIKE ? "
            "LIMIT ?",
            (like_pattern, like_pattern, limit),
        ).fetchall()

    return [{"ref_id": r["ref_id"], "kind": r["kind"], "summary": r["summary"]} for r in rows]


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
    mcp.Tool(
        name="update_node",
        description=(
            "Update a graph node's summary or metadata. Modifies YAML graph "
            "(source of truth) and SQLite index. Use after reading context to "
            "improve node descriptions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ref_id": {
                    "type": "string",
                    "description": "Node identifier",
                },
                "summary": {
                    "type": "string",
                    "description": "New summary text (optional)",
                },
                "source": {
                    "type": "string",
                    "description": "New source path (optional)",
                },
            },
            "required": ["ref_id"],
        },
    ),
    mcp.Tool(
        name="mark_synced",
        description=(
            "Mark documentation as synchronized with code for a ref_id. "
            "Call this after updating stale documentation to reset sync state."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ref_id": {
                    "type": "string",
                    "description": "Node whose doc-code pairs should be marked synced",
                },
            },
            "required": ["ref_id"],
        },
    ),
    mcp.Tool(
        name="search",
        description=(
            "Search for nodes, documents, and code symbols by keyword. "
            "Returns ranked results with ref_ids and summaries."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keywords)",
                },
                "kind": {
                    "type": "string",
                    "enum": ["domain", "feature", "service", "entity", "adr"],
                    "description": "Filter by node kind (optional)",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Max results",
                },
            },
            "required": ["query"],
        },
    ),
    mcp.Tool(
        name="generate_docs",
        description=(
            "Generate or enrich documentation for a graph node. Returns structured data: "
            "node summary, public API symbols, dependencies, dependents, and a prompt "
            "for writing human-readable documentation. After generating, use update_node "
            "to save improved summaries. Call without ref_id for all nodes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ref_id": {
                    "type": "string",
                    "description": "Node to generate docs for. Omit for all nodes.",
                },
            },
        },
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
    cache = ContextCache()

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def _list_tools() -> list[mcp.Tool]:
        return _TOOLS

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def _call_tool(
        name: str,
        arguments: dict[str, Any] | None,
    ) -> list[TextContent]:
        args = arguments or {}
        conn = open_db(db_path)
        try:
            # Auto-reindex if stale (4.3).
            reindexed = _ensure_fresh_index(project_root, conn)
            if reindexed:
                # Reopen connection after reindex (schema may have changed).
                conn.close()
                conn = open_db(db_path)
                cache.clear()

            l2 = SqliteCache(conn)
            result = _dispatch_tool(
                conn,
                name,
                args,
                project_root=project_root,
                cache=cache,
                l2_cache=l2,
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=False, indent=2),
                )
            ]
        except LookupError as exc:
            return [TextContent(type="text", text=f"Error: {exc}")]
        finally:
            conn.close()

    return server


def _dispatch_tool(
    conn: sqlite3.Connection,
    name: str,
    args: dict[str, Any],
    project_root: Path | None = None,
    cache: ContextCache | None = None,
    l2_cache: SqliteCache | None = None,
) -> Any:
    """Route tool call to the appropriate handler."""
    if name == "get_context":
        ref_id = args["ref_id"]
        depth = args.get("depth", 2)
        max_nodes = args.get("max_nodes", 20)
        max_chunks = args.get("max_chunks", 10)
        cache_key = f"{ref_id}:{depth}:{max_nodes}:{max_chunks}"

        # L1 cache check
        if cache is not None and project_root is not None:
            graph_mt, docs_mt = _compute_mtimes(project_root)
            entry = cache.get_entry(
                ref_id,
                depth,
                max_nodes,
                max_chunks,
                graph_mtime=graph_mt,
                docs_mtime=docs_mt,
            )
            if entry is not None:
                return {
                    "cached": True,
                    "etag": compute_etag(entry.bundle),
                    "unchanged_since": entry.created_at_iso,
                    "hint": "Context unchanged since last request. Use previous bundle.",
                }
        else:
            graph_mt = 0.0
            docs_mt = 0.0

        # L2 cache check
        if l2_cache is not None:
            l2_result = l2_cache.get(
                cache_key,
                graph_mtime=graph_mt,
                docs_mtime=docs_mt,
            )
            if l2_result is not None:
                bundle = l2_result[0]
                if cache is not None:
                    cache.put(
                        ref_id,
                        depth,
                        max_nodes,
                        max_chunks,
                        bundle,
                        graph_mtime=graph_mt,
                        docs_mtime=docs_mt,
                    )
                return bundle

        bundle = handle_get_context(
            conn,
            ref_id=ref_id,
            depth=depth,
            max_nodes=max_nodes,
            max_chunks=max_chunks,
        )

        if cache is not None:
            cache.put(
                ref_id,
                depth,
                max_nodes,
                max_chunks,
                bundle,
                graph_mtime=graph_mt,
                docs_mtime=docs_mt,
            )
        if l2_cache is not None:
            l2_cache.put(
                cache_key,
                bundle,
                graph_mtime=graph_mt,
                docs_mtime=docs_mt,
            )

        return bundle

    if name == "get_graph":
        ref_id = args["ref_id"]
        depth = args.get("depth", 2)

        # L1 cache (graph key space: "graph:<ref_id>")
        cache_ref = f"graph:{ref_id}"
        graph_cache_key = f"graph:{ref_id}:{depth}"
        if cache is not None and project_root is not None:
            graph_mt, _ = _compute_mtimes(project_root)
            entry = cache.get_entry(
                cache_ref,
                depth,
                0,
                0,
                graph_mtime=graph_mt,
            )
            if entry is not None:
                return {
                    "cached": True,
                    "etag": compute_etag(entry.bundle),
                    "unchanged_since": entry.created_at_iso,
                    "hint": "Graph unchanged since last request. Use previous result.",
                }
        else:
            graph_mt = 0.0

        # L2 cache check
        if l2_cache is not None:
            l2_result = l2_cache.get(
                graph_cache_key,
                graph_mtime=graph_mt,
            )
            if l2_result is not None:
                result = l2_result[0]
                if cache is not None:
                    cache.put(
                        cache_ref,
                        depth,
                        0,
                        0,
                        result,
                        graph_mtime=graph_mt,
                        docs_mtime=0.0,
                    )
                return result

        result = handle_get_graph(conn, ref_id=ref_id, depth=depth)

        if cache is not None:
            cache.put(
                cache_ref,
                depth,
                0,
                0,
                result,
                graph_mtime=graph_mt,
                docs_mtime=0.0,
            )
        if l2_cache is not None:
            l2_cache.put(
                graph_cache_key,
                result,
                graph_mtime=graph_mt,
                docs_mtime=0.0,
            )

        return result

    if name == "list_nodes":
        return handle_list_nodes(conn, kind=args.get("kind"))
    if name == "sync_check":
        return handle_sync_check(
            conn,
            ref_id=args.get("ref_id"),
            project_root=project_root,
        )
    if name == "get_status":
        return handle_get_status(conn)

    # --- Write tools ---
    if name == "update_node":
        if project_root is None:
            msg = "update_node requires project_root"
            raise ValueError(msg)
        result = handle_update_node(
            conn,
            project_root,
            ref_id=args["ref_id"],
            summary=args.get("summary"),
            source=args.get("source"),
        )
        # Invalidate cache for this ref_id.
        if cache is not None:
            cache.clear_ref(args["ref_id"])
        if l2_cache is not None:
            l2_cache.clear_ref(args["ref_id"])
        return result

    if name == "mark_synced":
        if project_root is None:
            msg = "mark_synced requires project_root"
            raise ValueError(msg)
        return handle_mark_synced(
            conn,
            project_root,
            ref_id=args["ref_id"],
        )

    if name == "search":
        return handle_search(
            conn,
            query=args["query"],
            kind=args.get("kind"),
            limit=args.get("limit", 10),
        )

    if name == "generate_docs":
        if project_root is None:
            msg = "generate_docs requires project_root"
            raise ValueError(msg)
        from beadloom.onboarding.doc_generator import generate_polish_data

        ref_id = args.get("ref_id")
        return generate_polish_data(project_root, ref_id=ref_id)

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)
