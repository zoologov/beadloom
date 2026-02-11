"""Beadloom CLI entry point."""

# beadloom:service=cli

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import click

from beadloom import __version__


# beadloom:service=cli
@click.group()
@click.version_option(version=__version__, prog_name="beadloom")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output (errors only).")
@click.pass_context
def main(ctx: click.Context, *, verbose: bool, quiet: bool) -> None:
    """Beadloom - Context Oracle + Doc Sync Engine."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


# beadloom:domain=context-oracle
def _format_markdown(bundle: dict[str, object]) -> str:
    """Format a context bundle as human-readable Markdown."""
    from typing import Any, cast

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

    # Sync status.
    stale = sync_status.get("stale_docs", [])
    if stale:
        lines.append("## Stale Docs")
        lines.append("")
        for doc in stale:
            lines.append(f"- {doc['doc_path']} ↔ {doc['code_path']}")
        lines.append("")

    return "\n".join(lines)


# beadloom:domain=reindex
@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--docs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Documentation directory (default: from config.yml or 'docs/').",
)
@click.option(
    "--full",
    is_flag=True,
    default=False,
    help="Force full rebuild (drop all tables and re-create).",
)
def reindex(*, project: Path | None, docs_dir: Path | None, full: bool) -> None:
    """Rebuild the SQLite index from Git sources.

    By default, performs an incremental reindex (only changed files).
    Use --full to force a complete rebuild.
    """
    project_root = project or Path.cwd()

    if full:
        from beadloom.reindex import reindex as do_reindex

        result = do_reindex(project_root, docs_dir=docs_dir)
    else:
        from beadloom.reindex import incremental_reindex

        result = incremental_reindex(project_root, docs_dir=docs_dir)

    if result.nothing_changed:
        # Nothing changed — show current DB totals instead.
        db_path = project_root / ".beadloom" / "beadloom.db"
        if db_path.exists():
            import sqlite3

            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                counts = {
                    "Nodes": conn.execute("SELECT count(*) FROM nodes").fetchone()[0],
                    "Edges": conn.execute("SELECT count(*) FROM edges").fetchone()[0],
                    "Docs": conn.execute("SELECT count(*) FROM docs").fetchone()[0],
                    "Symbols": conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0],
                }
                click.echo("No changes detected. Index is up to date.")
                for label, count in counts.items():
                    click.echo(f"{label + ':':9s}{count}")
            finally:
                conn.close()
        else:
            click.echo("No changes detected.")
    else:
        click.echo(f"Nodes:   {result.nodes_loaded}")
        click.echo(f"Edges:   {result.edges_loaded}")
        click.echo(f"Docs:    {result.docs_indexed}")
        click.echo(f"Chunks:  {result.chunks_indexed}")
        click.echo(f"Symbols: {result.symbols_indexed}")
        click.echo(f"Imports: {result.imports_indexed}")
        click.echo(f"Rules:   {result.rules_loaded}")
    if result.errors:
        click.echo("")
        for err in result.errors:
            click.echo(f"  [ERR] {err}")
    if result.warnings:
        click.echo("")
        for warn in result.warnings:
            click.echo(f"  [warn] {warn}")


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
    from beadloom.context_builder import build_context
    from beadloom.db import open_db

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
    project: Path | None,
) -> None:
    """Show knowledge graph (Mermaid or JSON)."""
    from beadloom.context_builder import bfs_subgraph
    from beadloom.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)

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


# beadloom:domain=doctor
@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def doctor(*, project: Path | None) -> None:
    """Run validation checks on the knowledge graph."""
    from beadloom.db import open_db
    from beadloom.doctor import Severity, run_checks

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    checks = run_checks(conn)
    conn.close()

    icons = {
        Severity.OK: "[ok]",
        Severity.INFO: "[info]",
        Severity.WARNING: "[warn]",
        Severity.ERROR: "[ERR]",
    }

    for check in checks:
        icon = icons.get(check.severity, "[?]")
        click.echo(f"  {icon} {check.description}")


# beadloom:service=cli
@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
def status(*, project: Path | None, output_json: bool) -> None:
    """Show project index statistics with health trends."""
    from beadloom.db import get_meta, open_db
    from beadloom.health import compute_trend, get_latest_snapshots

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)

    nodes_count: int = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    edges_count: int = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
    docs_count: int = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
    chunks_count: int = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    symbols_count: int = conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0]
    stale_count: int = conn.execute(
        "SELECT count(*) FROM sync_state WHERE status = 'stale'"
    ).fetchone()[0]

    # Per-kind breakdown.
    kind_rows = conn.execute(
        "SELECT kind, count(*) as cnt FROM nodes GROUP BY kind ORDER BY cnt DESC"
    ).fetchall()

    # Coverage: nodes with at least one doc linked.
    covered: int = conn.execute(
        "SELECT count(DISTINCT n.ref_id) FROM nodes n JOIN docs d ON d.ref_id = n.ref_id"
    ).fetchone()[0]

    # Per-kind coverage.
    kind_coverage_rows = conn.execute(
        "SELECT n.kind, count(DISTINCT n.ref_id) as covered "
        "FROM nodes n JOIN docs d ON d.ref_id = n.ref_id GROUP BY n.kind"
    ).fetchall()
    kind_covered: dict[str, int] = {r["kind"]: r["covered"] for r in kind_coverage_rows}
    kind_total: dict[str, int] = {r["kind"]: r["cnt"] for r in kind_rows}

    # Isolated nodes count.
    isolated_count: int = conn.execute(
        "SELECT count(*) FROM nodes n "
        "LEFT JOIN edges e1 ON e1.src_ref_id = n.ref_id "
        "LEFT JOIN edges e2 ON e2.dst_ref_id = n.ref_id "
        "WHERE e1.src_ref_id IS NULL AND e2.dst_ref_id IS NULL"
    ).fetchone()[0]

    # Empty summaries count.
    empty_summaries: int = conn.execute(
        "SELECT count(*) FROM nodes WHERE summary = '' OR summary IS NULL"
    ).fetchone()[0]

    last_reindex = get_meta(conn, "last_reindex_at", "never")
    version = get_meta(conn, "beadloom_version", "unknown")

    # Trend data.
    snapshots = get_latest_snapshots(conn, n=2)
    current = snapshots[0] if snapshots else None
    previous = snapshots[1] if len(snapshots) >= 2 else None
    trends = compute_trend(current, previous) if current and previous else {}

    conn.close()

    coverage_pct = (covered / nodes_count * 100) if nodes_count > 0 else 0.0

    if output_json:
        data = {
            "version": version,
            "last_reindex": last_reindex,
            "nodes_count": nodes_count,
            "edges_count": edges_count,
            "docs_count": docs_count,
            "chunks_count": chunks_count,
            "symbols_count": symbols_count,
            "coverage_pct": round(coverage_pct, 1),
            "covered_count": covered,
            "stale_count": stale_count,
            "isolated_count": isolated_count,
            "empty_summaries": empty_summaries,
            "by_kind": {kr["kind"]: kr["cnt"] for kr in kind_rows},
            "trends": trends,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    # Rich-formatted output.
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Header panel.
    console.print(Panel(
        f"Last reindex: {last_reindex}",
        title=f"Beadloom v{version}",
        border_style="blue",
    ))
    console.print()

    # Summary line.
    t_nodes = trends.get("nodes_count", "")
    t_edges = trends.get("edges_count", "")
    t_docs = trends.get("docs_count", "")
    console.print(
        f"  Nodes: [bold]{nodes_count}[/] {t_nodes}   "
        f"Edges: [bold]{edges_count}[/] {t_edges}   "
        f"Docs: [bold]{docs_count}[/] {t_docs}   "
        f"Symbols: [bold]{symbols_count}[/]"
    )
    console.print()

    # Two-column layout: By Kind + Doc Coverage.
    kind_table = Table(title="By Kind", show_header=False, box=None, padding=(0, 1))
    kind_table.add_column("kind", style="cyan")
    kind_table.add_column("count", justify="right")
    for kr in kind_rows:
        kind_table.add_row(kr["kind"], str(kr["cnt"]))

    cov_table = Table(title="Doc Coverage", show_header=False, box=None, padding=(0, 1))
    cov_table.add_column("scope", style="cyan")
    cov_table.add_column("coverage", justify="right")
    cov_table.add_column("trend")

    cov_trend = trends.get("coverage_pct", "")
    cov_table.add_row(
        "Overall",
        f"{covered}/{nodes_count} ({coverage_pct:.0f}%)",
        cov_trend,
    )
    for kind_name in sorted(kind_total):
        kc = kind_covered.get(kind_name, 0)
        kt = kind_total[kind_name]
        kpct = (kc / kt * 100) if kt > 0 else 0
        cov_table.add_row(kind_name, f"{kc}/{kt} ({kpct:.0f}%)", "")

    console.print(kind_table)
    console.print()
    console.print(cov_table)
    console.print()

    # Health section.
    health_table = Table(title="Health", show_header=False, box=None, padding=(0, 1))
    health_table.add_column("metric", style="cyan")
    health_table.add_column("value", justify="right")
    health_table.add_column("trend")

    stale_trend = trends.get("stale_count", "")
    iso_trend = trends.get("isolated_count", "")
    health_table.add_row("Stale docs", str(stale_count), stale_trend)
    health_table.add_row("Isolated nodes", str(isolated_count), iso_trend)
    health_table.add_row("Empty summaries", str(empty_summaries), "")
    console.print(health_table)


# beadloom:domain=doc-sync
@main.command("sync-check")
@click.option("--porcelain", is_flag=True, help="TAB-separated machine-readable output.")
@click.option("--json", "output_json", is_flag=True, help="Structured JSON output.")
@click.option("--report", "output_report", is_flag=True, help="Markdown report for CI posting.")
@click.option("--ref", "ref_filter", default=None, help="Filter by ref_id.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def sync_check(
    *,
    porcelain: bool,
    output_json: bool,
    output_report: bool,
    ref_filter: str | None,
    project: Path | None,
) -> None:
    """Check doc-code synchronization status.

    Exit codes: 0 = all ok, 1 = error, 2 = stale pairs found.
    """
    from beadloom.db import open_db
    from beadloom.sync_engine import check_sync

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    results = check_sync(conn, project_root=project_root)
    conn.close()

    if ref_filter:
        results = [r for r in results if r["ref_id"] == ref_filter]

    has_stale = any(r["status"] == "stale" for r in results)

    if output_json:
        ok_count = sum(1 for r in results if r["status"] == "ok")
        stale_count = sum(1 for r in results if r["status"] == "stale")
        data = {
            "summary": {
                "total": len(results),
                "ok": ok_count,
                "stale": stale_count,
            },
            "pairs": [
                {
                    "status": r["status"],
                    "ref_id": r["ref_id"],
                    "doc_path": r["doc_path"],
                    "code_path": r["code_path"],
                }
                for r in results
            ],
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_report:
        click.echo(_build_sync_report(results))
    elif porcelain:
        for r in results:
            click.echo(f"{r['status']}\t{r['ref_id']}\t{r['doc_path']}\t{r['code_path']}")
    else:
        if not results:
            click.echo("No sync pairs found.")
        else:
            for r in results:
                marker = "[stale]" if r["status"] == "stale" else "[ok]"
                click.echo(f"  {marker} {r['ref_id']}: {r['doc_path']} <-> {r['code_path']}")

    if has_stale:
        sys.exit(2)


def _build_sync_report(results: list[dict[str, str]]) -> str:
    """Build a Markdown report from sync-check results."""
    ok_count = sum(1 for r in results if r["status"] == "ok")
    stale_count = sum(1 for r in results if r["status"] == "stale")
    stale_pairs = [r for r in results if r["status"] == "stale"]

    lines: list[str] = [
        "## Beadloom Doc Sync Report",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| OK | {ok_count} |",
        f"| Stale | {stale_count} |",
    ]

    if stale_pairs:
        lines.extend([
            "",
            "### Stale Documents",
            "",
            "| Node | Doc | Changed Code |",
            "|------|-----|-------------|",
        ])
        for r in stale_pairs:
            lines.append(f"| {r['ref_id']} | `{r['doc_path']}` | `{r['code_path']}` |")
        lines.extend([
            "",
            "> Run `beadloom sync-update <ref_id>` to review and update.",
        ])
    else:
        lines.extend(["", "All documentation is up to date."])

    return "\n".join(lines)


_HOOK_TEMPLATE_WARN = """\
#!/bin/sh
# pre-commit hook managed by beadloom
stale=$(beadloom sync-check --porcelain 2>/dev/null)
exit_code=$?

if [ $exit_code -eq 2 ]; then
  echo "Warning: stale documentation detected"
  echo "$stale"
  echo ""
  echo "Run: beadloom sync-update <ref_id> to update docs"
fi

if [ $exit_code -eq 1 ]; then
  echo "Warning: beadloom sync-check failed (index may be stale)"
fi
"""

_HOOK_TEMPLATE_BLOCK = """\
#!/bin/sh
# pre-commit hook managed by beadloom
stale=$(beadloom sync-check --porcelain 2>/dev/null)
exit_code=$?

if [ $exit_code -eq 2 ]; then
  echo "Error: stale documentation detected — commit blocked"
  echo "$stale"
  echo ""
  echo "Run: beadloom sync-update <ref_id> to update docs"
  exit 1
fi

if [ $exit_code -eq 1 ]; then
  echo "Warning: beadloom sync-check failed (index may be stale)"
fi
"""


# beadloom:domain=doc-sync
@main.command("install-hooks")
@click.option(
    "--mode",
    type=click.Choice(["warn", "block"]),
    default="warn",
    help="Hook mode: warn (default) or block commits on stale docs.",
)
@click.option("--remove", is_flag=True, help="Remove the pre-commit hook.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def install_hooks(
    *,
    mode: str,
    remove: bool,
    project: Path | None,
) -> None:
    """Install or remove beadloom pre-commit hook."""
    import stat

    project_root = project or Path.cwd()
    hooks_dir = project_root / ".git" / "hooks"

    if not hooks_dir.exists():
        click.echo("Error: .git/hooks not found. Is this a git repository?", err=True)
        sys.exit(1)

    hook_path = hooks_dir / "pre-commit"

    if remove:
        if hook_path.exists():
            hook_path.unlink()
            click.echo("Removed pre-commit hook.")
        else:
            click.echo("No pre-commit hook to remove.")
        return

    template = _HOOK_TEMPLATE_BLOCK if mode == "block" else _HOOK_TEMPLATE_WARN
    hook_path.write_text(template)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    click.echo(f"Installed pre-commit hook (mode: {mode}).")


# beadloom:domain=doc-sync
@main.command("sync-update")
@click.argument("ref_id")
@click.option("--check", "check_only", is_flag=True, help="Only show status, don't open editor.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def sync_update(
    ref_id: str,
    *,
    check_only: bool,
    project: Path | None,
) -> None:
    """Show sync status and update docs for a ref_id.

    Use --check to only display status without opening an editor.

    For automated doc updates, use your AI agent (Claude Code, Cursor, etc.)
    with Beadloom's MCP tools (update_node, mark_synced).
    """
    from beadloom.db import open_db
    from beadloom.sync_engine import check_sync

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    results = check_sync(conn, project_root=project_root)
    filtered = [r for r in results if r["ref_id"] == ref_id]

    if not filtered:
        click.echo(f"No sync pairs found for {ref_id}.")
        conn.close()
        return

    stale = [r for r in filtered if r["status"] == "stale"]

    if check_only:
        for r in filtered:
            marker = "[stale]" if r["status"] == "stale" else "[ok]"
            click.echo(f"  {marker} {r['doc_path']} <-> {r['code_path']}")
        conn.close()
        return

    if not stale:
        click.echo(f"All docs for {ref_id} are up to date.")
        conn.close()
        return

    # Interactive mode: open editor for each stale doc.
    from beadloom.sync_engine import mark_synced

    # Group stale pairs by doc_path (one doc may have multiple code files).
    doc_stale: dict[str, list[dict[str, str]]] = {}
    for r in stale:
        doc_stale.setdefault(r["doc_path"], []).append(r)

    for doc_path, pairs in doc_stale.items():
        click.echo(f"\n  Doc: {doc_path}")
        for r in pairs:
            click.echo(f"    Code changed: {r['code_path']}")

        doc_full_path = project_root / "docs" / doc_path
        if not doc_full_path.exists():
            click.echo(f"    Warning: {doc_full_path} does not exist, skipping.")
            continue

        if not click.confirm(f"\n  Open {doc_path} in editor?", default=True):
            continue

        # Open in $EDITOR.
        click.edit(filename=str(doc_full_path))

        # Mark all pairs for this doc as synced.
        for r in pairs:
            mark_synced(conn, r["doc_path"], r["code_path"], project_root)
        click.echo(f"  Synced: {doc_path}")

    conn.close()


# beadloom:service=mcp-server
_MCP_TOOL_CONFIGS: dict[str, dict[str, str]] = {
    "claude-code": {"path_template": "{project}/.mcp.json", "scope": "project"},
    "cursor": {"path_template": "{project}/.cursor/mcp.json", "scope": "project"},
    "windsurf": {
        "path_template": "{home}/.codeium/windsurf/mcp_config.json",
        "scope": "global",
    },
}


@main.command("setup-mcp")
@click.option("--remove", is_flag=True, help="Remove beadloom from MCP config.")
@click.option(
    "--tool",
    "tool_name",
    type=click.Choice(["claude-code", "cursor", "windsurf"]),
    default="claude-code",
    help="Editor/tool to configure (default: claude-code).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def setup_mcp(*, remove: bool, tool_name: str, project: Path | None) -> None:
    """Create or update MCP config for beadloom MCP server.

    Supports Claude Code (.mcp.json), Cursor (.cursor/mcp.json),
    and Windsurf (~/.codeium/windsurf/mcp_config.json).
    """
    import shutil

    project_root = project or Path.cwd()
    tool_cfg = _MCP_TOOL_CONFIGS[tool_name]

    mcp_json_path = Path(
        tool_cfg["path_template"].format(
            project=project_root,
            home=Path.home(),
        )
    )

    # Ensure parent directory exists.
    mcp_json_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing or create new.
    if mcp_json_path.exists():
        data = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    else:
        data = {"mcpServers": {}}

    if "mcpServers" not in data:
        data["mcpServers"] = {}

    if remove:
        data["mcpServers"].pop("beadloom", None)
        mcp_json_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        click.echo(f"Removed beadloom from {mcp_json_path}")
        return

    # Find beadloom command path.
    beadloom_path = shutil.which("beadloom") or "beadloom"

    args: list[str] = ["mcp-serve"]
    # Global configs need explicit --project path.
    if tool_cfg["scope"] == "global":
        args.extend(["--project", str(project_root.resolve())])

    data["mcpServers"]["beadloom"] = {
        "command": beadloom_path,
        "args": args,
    }

    mcp_json_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    click.echo(f"Updated {mcp_json_path}")


# beadloom:domain=links
_LINK_LABEL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"github\.com/.+/pull/"), "github-pr"),
    (re.compile(r"github\.com/.+/issues/"), "github"),
    (re.compile(r"(.*\.atlassian\.net/|jira\.)"), "jira"),
    (re.compile(r"linear\.app/"), "linear"),
]


def _detect_link_label(url: str) -> str:
    """Auto-detect tracker label from URL pattern."""
    for pattern, label in _LINK_LABEL_PATTERNS:
        if pattern.search(url):
            return label
    return "link"


@main.command()
@click.argument("ref_id")
@click.argument("url", required=False, default=None)
@click.option("--label", default=None, help="Link label (auto-detected if omitted).")
@click.option("--remove", "remove_url", default=None, help="URL to remove.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def link(
    ref_id: str,
    url: str | None,
    *,
    label: str | None,
    remove_url: str | None,
    project: Path | None,
) -> None:
    """Manage external tracker links on graph nodes.

    Add a link: beadloom link AUTH-001 https://github.com/org/repo/issues/42

    List links: beadloom link AUTH-001

    Remove a link: beadloom link AUTH-001 --remove https://github.com/org/repo/issues/42
    """
    import yaml

    project_root = project or Path.cwd()
    graph_dir = project_root / ".beadloom" / "_graph"

    if not graph_dir.is_dir():
        click.echo("Error: graph directory not found. Run `beadloom init` first.", err=True)
        sys.exit(1)

    # Find the YAML file containing this ref_id.
    target_file: Path | None = None
    target_data: dict[str, object] | None = None
    node_index: int | None = None

    for yml_path in sorted(graph_dir.glob("*.yml")):
        text = yml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if data is None:
            continue
        for i, node in enumerate(data.get("nodes") or []):
            if node.get("ref_id") == ref_id:
                target_file = yml_path
                target_data = data
                node_index = i
                break
        if target_file is not None:
            break

    if target_file is None or target_data is None or node_index is None:
        click.echo(f"Error: node '{ref_id}' not found in graph YAML files.", err=True)
        sys.exit(1)

    from typing import cast as _cast

    nodes_list: list[dict[str, object]] = _cast(
        "list[dict[str, object]]", target_data.get("nodes") or []
    )
    node = nodes_list[node_index]
    links: list[dict[str, str]] = _cast(
        "list[dict[str, str]]", node.get("links") or []
    )

    # List links mode.
    if url is None and remove_url is None:
        if not links:
            click.echo(f"No links for {ref_id}.")
        else:
            for lnk in links:
                click.echo(f"  [{lnk.get('label', 'link')}] {lnk['url']}")
        return

    # Remove mode.
    if remove_url is not None:
        original_len = len(links)
        links = [lnk for lnk in links if lnk["url"] != remove_url]
        if len(links) == original_len:
            click.echo(f"Link not found: {remove_url}")
            return
        node["links"] = links if links else None
        if not links and "links" in node:
            del node["links"]
        target_file.write_text(
            yaml.dump(target_data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        click.echo(f"Removed link from {ref_id}.")
        return

    # Add mode — url is guaranteed non-None at this point.
    assert url is not None
    detected_label = label or _detect_link_label(url)
    # Check for duplicates.
    if any(lnk["url"] == url for lnk in links):
        click.echo(f"Link already exists: {url}")
        return

    links.append({"url": url, "label": detected_label})
    node["links"] = links
    target_file.write_text(
        yaml.dump(target_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    click.echo(f"Added [{detected_label}] {url} to {ref_id}.")


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
    from beadloom.db import open_db
    from beadloom.search import has_fts5, search_fts5

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
            {"ref_id": r["ref_id"], "kind": r["kind"], "summary": r["summary"]}
            for r in rows
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


# beadloom:service=mcp-server
@main.command("mcp-serve")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def mcp_serve(*, project: Path | None) -> None:
    """Run the beadloom MCP server (stdio transport)."""
    import anyio

    from beadloom.mcp_server import create_server

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    server = create_server(project_root)

    async def _run() -> None:
        from mcp import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    anyio.run(_run)


# beadloom:domain=onboarding
@main.command()
@click.option("--bootstrap", is_flag=True, help="Bootstrap: generate graph from code.")
@click.option(
    "--preset",
    type=click.Choice(["monolith", "microservices", "monorepo"]),
    default=None,
    help="Architecture preset (auto-detected if omitted).",
)
@click.option(
    "--import",
    "import_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Import: classify existing documentation from directory.",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def init(
    *,
    bootstrap: bool,
    preset: str | None,
    import_path: Path | None,
    project: Path | None,
) -> None:
    """Initialize beadloom in a project."""
    from beadloom.onboarding import bootstrap_project, import_docs

    project_root = project or Path.cwd()

    if bootstrap:
        result = bootstrap_project(project_root, preset_name=preset)
        scan = result["scan"]
        click.echo(f"Preset: {result['preset']}")
        click.echo(f"Scanned {scan['file_count']} files")
        click.echo(
            f"Generated {result['nodes_generated']} nodes, "
            f"{result['edges_generated']} edges"
        )

        # Auto-reindex to populate import analysis and depends_on edges.
        from beadloom.db import open_db
        from beadloom.reindex import reindex as do_reindex

        ri = do_reindex(project_root)
        if ri.imports_indexed > 0:
            db_path = project_root / ".beadloom" / "beadloom.db"
            conn = open_db(db_path)
            dep_count = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE kind = 'depends_on'"
            ).fetchone()[0]
            conn.close()
            click.echo(
                f"Indexed {ri.imports_indexed} imports, "
                f"{dep_count} dependency edges"
            )
        click.echo(f"Config: {project_root / '.beadloom' / 'config.yml'}")
        click.echo(
            f"Agent instructions: "
            f"{project_root / '.beadloom' / 'AGENTS.md'}"
        )
        return

    if import_path:
        results = import_docs(project_root, import_path)
        click.echo(f"Classified {len(results)} documents:")
        for r in results:
            click.echo(f"  [{r['kind']}] {r['path']}")
        click.echo("")
        click.echo(
            "Next: review .beadloom/_graph/imported.yml, "
            "then run `beadloom reindex`"
        )
        return

    # Default: interactive mode.
    from beadloom.onboarding import interactive_init

    result = interactive_init(project_root)
    if result["mode"] == "cancelled":
        sys.exit(0)


# beadloom:domain=impact-analysis
@main.command()
@click.argument("ref_id")
@click.option("--depth", default=3, type=int, help="BFS traversal depth.")
@click.option("--json", "as_json", is_flag=True, help="JSON output.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def why(ref_id: str, *, depth: int, as_json: bool, project: Path | None) -> None:
    """Show impact analysis for a node (upstream deps + downstream dependents)."""
    from beadloom.db import open_db
    from beadloom.why import analyze_node, render_why, result_to_dict

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    try:
        result = analyze_node(conn, ref_id, depth=depth)
    except LookupError as exc:
        click.echo(f"Error: {exc}", err=True)
        conn.close()
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    else:
        from rich.console import Console

        console = Console()
        render_why(result, console)

    conn.close()


# beadloom:domain=graph-diff
@main.command("diff")
@click.option("--since", default="HEAD", help="Git ref to compare against.")
@click.option("--json", "as_json", is_flag=True, help="JSON output.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def diff_cmd(*, since: str, as_json: bool, project: Path | None) -> None:
    """Show graph changes since a git ref.

    Compares current graph YAML with state at the given ref (default: HEAD).
    Exit code 0 = no changes, 1 = changes detected.
    """
    from beadloom.diff import compute_diff, diff_to_dict, render_diff

    project_root = project or Path.cwd()
    graph_dir = project_root / ".beadloom" / "_graph"

    if not graph_dir.is_dir():
        click.echo("Error: graph directory not found. Run `beadloom init` first.", err=True)
        sys.exit(1)

    try:
        result = compute_diff(project_root, since=since)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(diff_to_dict(result), ensure_ascii=False, indent=2))
    else:
        from rich.console import Console

        console = Console()
        render_diff(result, console)

    if result.has_changes:
        sys.exit(1)


# beadloom:domain=tui
@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def ui(*, project: Path | None) -> None:
    """Launch interactive terminal dashboard.

    Browse domains, nodes, edges, and documentation coverage.
    Requires textual: pip install beadloom[tui]
    """
    try:
        from beadloom.tui import launch
    except ImportError:
        click.echo(
            "Error: TUI requires 'textual'. "
            "Install with: pip install beadloom[tui]",
            err=True,
        )
        sys.exit(1)

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    try:
        launch(db_path=db_path, project_root=project_root)
    except ImportError:
        click.echo(
            "Error: TUI requires 'textual'. "
            "Install with: pip install beadloom[tui]",
            err=True,
        )
        sys.exit(1)


# beadloom:domain=watcher
@main.command("watch")
@click.option("--debounce", default=500, type=int, help="Debounce delay in ms.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def watch_cmd(*, debounce: int, project: Path | None) -> None:
    """Watch files and auto-reindex on changes.

    Monitors graph YAML, documentation, and source files.
    Graph changes trigger full reindex; other changes trigger incremental.
    Requires watchfiles: pip install beadloom[watch]
    """
    try:
        from beadloom.watcher import watch
    except ImportError:
        click.echo(
            "Error: watch requires 'watchfiles'. "
            "Install with: pip install beadloom[watch]",
            err=True,
        )
        sys.exit(1)

    project_root = project or Path.cwd()
    graph_dir = project_root / ".beadloom" / "_graph"

    if not graph_dir.is_dir():
        click.echo("Error: graph directory not found. Run `beadloom init` first.", err=True)
        sys.exit(1)

    try:
        watch(project_root, debounce_ms=debounce)
    except ImportError:
        click.echo(
            "Error: watch requires 'watchfiles'. "
            "Install with: pip install beadloom[watch]",
            err=True,
        )
        sys.exit(1)


# beadloom:domain=context-oracle
@main.command()
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "json", "porcelain"]),
    default=None,
    help="Output format (default: rich if TTY, porcelain if piped).",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit 1 if violations found.",
)
@click.option(
    "--no-reindex",
    is_flag=True,
    default=False,
    help="Skip reindex before linting.",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def lint(
    *,
    fmt: str | None,
    strict: bool,
    no_reindex: bool,
    project: Path | None,
) -> None:
    """Run architecture lint rules against the project.

    Checks cross-boundary imports against rules defined in rules.yml.
    Exit codes: 0 = clean or violations without --strict,
    1 = violations with --strict, 2 = configuration error.
    """
    from beadloom.linter import LintError
    from beadloom.linter import format_json as _format_json
    from beadloom.linter import format_porcelain as _format_porcelain
    from beadloom.linter import format_rich as _format_rich
    from beadloom.linter import lint as run_lint

    project_root = project or Path.cwd()

    # Resolve output format: explicit flag > TTY detection.
    if fmt is None:
        fmt = "rich" if sys.stdout.isatty() else "porcelain"

    try:
        result = run_lint(project_root, reindex_before=not no_reindex)
    except LintError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    formatters = {
        "rich": _format_rich,
        "json": _format_json,
        "porcelain": _format_porcelain,
    }
    output = formatters[fmt](result)
    if output:
        click.echo(output)

    if strict and result.violations:
        sys.exit(1)
