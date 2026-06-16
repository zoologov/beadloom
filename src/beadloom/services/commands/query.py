"""Read-only context/graph query commands: ctx, graph, why, search, prime."""
# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from typing import Any

from beadloom.services.commands._root import main


# beadloom:domain=context-oracle
def _format_markdown(bundle: dict[str, object]) -> str:
    """Format a context bundle as human-readable Markdown."""
    from typing import cast

    focus = cast("dict[str, str]", bundle["focus"])
    graph = cast("dict[str, list[dict[str, str]]]", bundle["graph"])
    text_chunks = cast("list[dict[str, str]]", bundle["text_chunks"])
    code_symbols = cast("list[dict[str, Any]]", bundle["code_symbols"])
    sync_status = cast("dict[str, Any]", bundle["sync_status"])
    warning = bundle.get("warning")

    lines: list[str] = []

    # Warning.
    if warning:
        lines.append(f"⚠ {warning}")
        lines.append("")

    # Focus.
    lines.append(f"# {focus['ref_id']} ({focus['kind']})")
    lines.append(f"{focus['summary']}")
    focus_links: list[dict[str, str]] = cast("list[dict[str, str]]", focus.get("links", []))
    if focus_links:
        link_strs = [f"{lnk.get('label', 'link')}: {lnk['url']}" for lnk in focus_links]
        lines.append(f"Links: {', '.join(link_strs)}")

    # Tests.
    tests_info = cast("dict[str, Any] | None", bundle.get("tests"))
    if tests_info is not None:
        file_count = len(tests_info.get("test_files", []))
        lines.append(
            f"Tests: {tests_info['framework']}, "
            f"{tests_info['test_count']} tests in {file_count} files "
            f"({tests_info['coverage_estimate']} coverage)"
        )

    # Activity.
    activity_info = cast("dict[str, Any] | None", focus.get("activity"))
    if activity_info is not None:
        _activity_emojis: dict[str, str] = {
            "hot": "\U0001f525",
            "warm": "\u2600\ufe0f",
            "cold": "\u2744\ufe0f",
            "dormant": "\U0001f9ca",
        }
        level: str = activity_info.get("level", "dormant")
        emoji = _activity_emojis.get(level, "")
        commits_30d = activity_info.get("commits_30d", 0)
        if level == "dormant":
            lines.append(f"Activity: {emoji} dormant")
        else:
            lines.append(f"Activity: {emoji} {level} ({commits_30d} commits/30d)")
    lines.append("")

    # Graph.
    lines.append("## Graph")
    lines.append("")
    for node in graph["nodes"]:
        lines.append(f"- **{node['ref_id']}** ({node['kind']}): {node['summary']}")
    lines.append("")
    if graph["edges"]:
        lines.append("### Edges")
        for edge in graph["edges"]:
            lines.append(f"- {edge['src']} —[{edge['kind']}]→ {edge['dst']}")
        lines.append("")

    # Text chunks.
    if text_chunks:
        lines.append("## Documentation")
        lines.append("")
        for chunk in text_chunks:
            lines.append("---")
            lines.append(f"**{chunk['heading']}** | `{chunk['section']}` | _{chunk['doc_path']}_")
            lines.append("")
            lines.append(chunk["content"])
            lines.append("")

    # Code symbols.
    if code_symbols:
        lines.append("## Code Symbols")
        lines.append("")
        for sym in code_symbols:
            lines.append(
                f"- `{sym['symbol_name']}` ({sym['kind']}) "
                f"in `{sym['file_path']}:{sym['line_start']}-{sym['line_end']}`"
            )
        lines.append("")

    # API Routes.
    routes = cast("list[dict[str, Any]]", bundle.get("routes", []))
    if routes:
        _gql_methods = {"QUERY", "MUTATION", "SUBSCRIPTION"}
        http_routes = [r for r in routes if r.get("method", "") not in _gql_methods]
        gql_routes = [r for r in routes if r.get("method", "") in _gql_methods]

        if http_routes:
            lines.append("## API Routes")
            lines.append("")
            for route in http_routes:
                handler = route.get("handler", "<anonymous>")
                file_ref = route.get("file", "")
                line_num = route.get("line", 0)
                lines.append(
                    f"- {route['method']:<7} {route['path']:<50} "
                    f"\u2192 {handler}() {file_ref}:{line_num}"
                )
            lines.append("")

        if gql_routes:
            lines.append("## GraphQL")
            lines.append("")
            for route in gql_routes:
                handler = route.get("handler", "<anonymous>")
                file_ref = route.get("file", "")
                line_num = route.get("line", 0)
                lines.append(
                    f"- {route['method']:<14} {route['path']:<40} "
                    f"\u2192 {handler}() {file_ref}:{line_num}"
                )
            lines.append("")

    # Sync status.
    stale = sync_status.get("stale_docs", [])
    if stale:
        lines.append("## Stale Docs")
        lines.append("")
        for doc in stale:
            lines.append(f"- {doc['doc_path']} ↔ {doc['code_path']}")
        lines.append("")

    return "\n".join(lines)


# beadloom:domain=context-oracle
@main.command()
@click.argument("ref_ids", nargs=-1, required=True)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option("--markdown", "output_md", is_flag=True, help="Output as Markdown (default).")
@click.option("--depth", default=2, type=int, help="Graph traversal depth.")
@click.option("--max-nodes", default=20, type=int, help="Max nodes in subgraph.")
@click.option("--max-chunks", default=10, type=int, help="Max text chunks.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def ctx(
    ref_ids: tuple[str, ...],
    *,
    output_json: bool,
    output_md: bool,
    depth: int,
    max_nodes: int,
    max_chunks: int,
    project: Path | None,
) -> None:
    """Get context bundle for one or more ref_ids."""
    from beadloom.context_oracle.builder import build_context
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    try:
        bundle = build_context(
            conn,
            list(ref_ids),
            depth=depth,
            max_nodes=max_nodes,
            max_chunks=max_chunks,
        )
    except LookupError as exc:
        click.echo(f"Error: {exc}", err=True)
        conn.close()
        sys.exit(1)

    if output_json:
        click.echo(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        click.echo(_format_markdown(bundle))

    conn.close()


# beadloom:domain=graph-format
def _format_mermaid(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
) -> str:
    """Format graph as Mermaid flowchart."""
    lines = ["graph LR"]
    for node in nodes:
        rid = node["ref_id"]
        safe_id = rid.replace("-", "_")
        label = f"{rid}<br/>({node['kind']})"
        lines.append(f'    {safe_id}["{label}"]')
    for edge in edges:
        src = edge["src"].replace("-", "_")
        dst = edge["dst"].replace("-", "_")
        lines.append(f"    {src} -->|{edge['kind']}| {dst}")
    return "\n".join(lines)


# beadloom:domain=graph-format
@main.command()
@click.argument("ref_ids", nargs=-1)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option("--depth", default=2, type=int, help="Graph traversal depth.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["mermaid", "c4", "c4-plantuml"]),
    default="mermaid",
    help="Output format (default: mermaid).",
)
@click.option(
    "--level",
    "c4_level",
    type=click.Choice(["context", "container", "component"]),
    default="container",
    help="C4 diagram level (default: container). Only used with --format=c4|c4-plantuml.",
)
@click.option(
    "--scope",
    "c4_scope",
    default=None,
    help="Scope ref_id for --level=component (show internals of one container).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def graph(
    ref_ids: tuple[str, ...],
    *,
    output_json: bool,
    depth: int,
    fmt: str,
    c4_level: str,
    c4_scope: str | None,
    project: Path | None,
) -> None:
    """Show architecture graph (Mermaid, C4-Mermaid, C4-PlantUML, or JSON)."""
    from beadloom.context_oracle.builder import bfs_subgraph
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)

    # C4 formats use the C4 model pipeline
    if fmt in ("c4", "c4-plantuml"):
        from beadloom.graph.c4 import (
            filter_c4_nodes,
            map_to_c4,
            render_c4_mermaid,
            render_c4_plantuml,
        )

        c4_nodes, c4_rels = map_to_c4(conn)

        # Apply level filtering
        try:
            c4_nodes, c4_rels = filter_c4_nodes(c4_nodes, c4_rels, level=c4_level, scope=c4_scope)
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            conn.close()
            sys.exit(1)

        if fmt == "c4-plantuml":
            click.echo(render_c4_plantuml(c4_nodes, c4_rels, level=c4_level))
        else:
            click.echo(render_c4_mermaid(c4_nodes, c4_rels))
        conn.close()
        return

    # Default: mermaid or JSON
    if ref_ids:
        # BFS from specified focus nodes.
        nodes, edges = bfs_subgraph(conn, list(ref_ids), depth=depth)
    else:
        # All nodes and edges.
        node_rows = conn.execute("SELECT ref_id, kind, summary FROM nodes").fetchall()
        nodes = [
            {"ref_id": r["ref_id"], "kind": r["kind"], "summary": r["summary"]} for r in node_rows
        ]
        edge_rows = conn.execute("SELECT src_ref_id, dst_ref_id, kind FROM edges").fetchall()
        edges = [
            {"src": r["src_ref_id"], "dst": r["dst_ref_id"], "kind": r["kind"]} for r in edge_rows
        ]

    if output_json:
        click.echo(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2))
    else:
        click.echo(_format_mermaid(nodes, edges))

    conn.close()


# beadloom:domain=onboarding
@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--update", is_flag=True, help="Also regenerate AGENTS.md.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: cwd).",
)
def prime(*, as_json: bool, update: bool, project: Path | None) -> None:
    """Output compact project context for AI agent injection."""
    project_root = project or Path.cwd()

    if update:
        from beadloom.onboarding import generate_agents_md

        generate_agents_md(project_root)

    from beadloom.onboarding import prime_context

    fmt = "json" if as_json else "markdown"
    result = prime_context(project_root, fmt=fmt)

    if as_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        click.echo(result)


# beadloom:domain=search
@main.command()
@click.argument("query")
@click.option(
    "--kind",
    type=click.Choice(["domain", "feature", "service", "entity", "adr"]),
    default=None,
    help="Filter results by node kind.",
)
@click.option("--limit", default=10, type=int, help="Max results.")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def search(
    query: str,
    *,
    kind: str | None,
    limit: int,
    output_json: bool,
    project: Path | None,
) -> None:
    """Search nodes and documentation by keyword.

    Uses FTS5 full-text search when available, falls back to SQL LIKE.
    Run `beadloom reindex` first to populate the search index.
    """
    from beadloom.context_oracle.search import has_fts5, search_fts5
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)

    if has_fts5(conn):
        results = search_fts5(conn, query, kind=kind, limit=limit)
    else:
        # Fallback to LIKE.
        like_pattern = f"%{query}%"
        if kind:
            rows = conn.execute(
                "SELECT ref_id, kind, summary FROM nodes "
                "WHERE kind = ? AND (ref_id LIKE ? OR summary LIKE ?) LIMIT ?",
                (kind, like_pattern, like_pattern, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ref_id, kind, summary FROM nodes "
                "WHERE ref_id LIKE ? OR summary LIKE ? LIMIT ?",
                (like_pattern, like_pattern, limit),
            ).fetchall()
        results = [
            {"ref_id": r["ref_id"], "kind": r["kind"], "summary": r["summary"]} for r in rows
        ]

    conn.close()

    if output_json:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if not results:
            click.echo("No results found.")
        else:
            for r in results:
                snippet = r.get("snippet", "")
                click.echo(f"  [{r['kind']}] {r['ref_id']}: {r['summary']}")
                if snippet:
                    click.echo(f"    {snippet}")


# beadloom:domain=impact-analysis
@main.command()
@click.argument("ref_id")
@click.option("--depth", default=3, type=int, help="BFS traversal depth.")
@click.option("--json", "as_json", is_flag=True, help="JSON output.")
@click.option("--reverse", is_flag=True, help="Focus on what this node depends on.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["panel", "tree"]),
    default="panel",
    help="Output format: panel (Rich, default) or tree (plain text for CI).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def why(
    ref_id: str,
    *,
    depth: int,
    as_json: bool,
    reverse: bool,
    fmt: str,
    project: Path | None,
) -> None:
    """Show impact analysis for a node (upstream deps + downstream dependents)."""
    from beadloom.context_oracle.why import (
        analyze_node,
        render_why,
        render_why_tree,
        result_to_dict,
    )
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    try:
        result = analyze_node(conn, ref_id, depth=depth, reverse=reverse)
    except LookupError as exc:
        click.echo(f"Error: {exc}", err=True)
        conn.close()
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    elif fmt == "tree":
        click.echo(render_why_tree(result))
    else:
        from rich.console import Console

        console = Console()
        render_why(result, console)

    conn.close()
