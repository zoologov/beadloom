"""Beadloom CLI entry point."""

# beadloom:service=cli

from __future__ import annotations

import json
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
def reindex(*, project: Path | None, docs_dir: Path | None) -> None:
    """Drop and rebuild the SQLite index from Git sources."""
    from beadloom.reindex import reindex as do_reindex

    project_root = project or Path.cwd()
    result = do_reindex(project_root, docs_dir=docs_dir)

    click.echo(f"Nodes:   {result.nodes_loaded}")
    click.echo(f"Edges:   {result.edges_loaded}")
    click.echo(f"Docs:    {result.docs_indexed}")
    click.echo(f"Chunks:  {result.chunks_indexed}")
    click.echo(f"Symbols: {result.symbols_indexed}")
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
def status(*, project: Path | None) -> None:
    """Show project index statistics."""
    from beadloom.db import get_meta, open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)

    nodes_count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    edges_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
    docs_count = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
    chunks_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    symbols_count = conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0]
    stale_count = conn.execute(
        "SELECT count(*) FROM sync_state WHERE status = 'stale'"
    ).fetchone()[0]

    # Per-kind breakdown.
    kind_rows = conn.execute(
        "SELECT kind, count(*) as cnt FROM nodes GROUP BY kind ORDER BY cnt DESC"
    ).fetchall()

    # Coverage: nodes with at least one doc linked.
    covered = conn.execute(
        "SELECT count(DISTINCT n.ref_id) FROM nodes n JOIN docs d ON d.ref_id = n.ref_id"
    ).fetchone()[0]

    last_reindex = get_meta(conn, "last_reindex_at", "never")
    version = get_meta(conn, "beadloom_version", "unknown")

    conn.close()

    click.echo(f"Beadloom v{version}")
    click.echo(f"Last reindex: {last_reindex}")
    click.echo("")
    click.echo(f"  Nodes:        {nodes_count}")
    for kr in kind_rows:
        click.echo(f"    {kr['kind']:12s} {kr['cnt']}")
    click.echo(f"  Edges:        {edges_count}")
    click.echo(f"  Docs:         {docs_count}")
    click.echo(f"  Chunks:       {chunks_count}")
    click.echo(f"  Code symbols: {symbols_count}")
    click.echo("")
    coverage_pct = (covered / nodes_count * 100) if nodes_count > 0 else 0
    click.echo(f"  Doc coverage: {covered}/{nodes_count} ({coverage_pct:.0f}%)")
    if stale_count > 0:
        click.echo(f"  Stale docs:   {stale_count}")


# beadloom:domain=doc-sync
@main.command("sync-check")
@click.option("--porcelain", is_flag=True, help="TAB-separated machine-readable output.")
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

    if porcelain:
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
@click.option("--auto", is_flag=True, help="Use LLM to auto-update docs (requires config).")
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
    auto: bool,
    project: Path | None,
) -> None:
    """Show sync status and update docs for a ref_id.

    Use --check to only display status without opening an editor.
    Use --auto to update docs using LLM (requires llm config in config.yml).
    """
    from beadloom.db import open_db
    from beadloom.sync_engine import check_sync

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    # Handle --auto mode.
    if auto:
        _handle_auto_sync(project_root, ref_id)
        return

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


# beadloom:domain=llm-updater
def _handle_auto_sync(project_root: Path, ref_id: str) -> None:
    """Handle --auto flag: call LLM to auto-update stale docs."""
    import difflib

    import yaml as _yaml

    from beadloom.db import open_db
    from beadloom.llm_updater import LLMError, auto_update_doc, parse_llm_config
    from beadloom.sync_engine import check_sync, mark_synced

    # 1. Parse LLM config.
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.exists():
        click.echo(
            "Error: LLM not configured. Add 'llm' section to .beadloom/config.yml",
            err=True,
        )
        sys.exit(1)

    raw_config = _yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    llm_raw = raw_config.get("llm")
    if not llm_raw:
        click.echo(
            "Error: LLM not configured. Add 'llm' section to .beadloom/config.yml",
            err=True,
        )
        sys.exit(1)

    try:
        llm_config = parse_llm_config(llm_raw)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # Validate API key is available before doing any work.
    import os

    if not os.environ.get(llm_config.api_key_env):
        click.echo(
            f"Error: API key not found. Set environment variable: {llm_config.api_key_env}",
            err=True,
        )
        sys.exit(1)

    # 2. Find stale pairs.
    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    results = check_sync(conn, project_root=project_root)
    stale = [r for r in results if r["ref_id"] == ref_id and r["status"] == "stale"]

    if not stale:
        click.echo(f"All docs for {ref_id} are up to date.")
        conn.close()
        return

    # 3. Group by doc and collect code changes.
    doc_stale: dict[str, list[dict[str, str]]] = {}
    for r in stale:
        doc_stale.setdefault(r["doc_path"], []).append(r)

    for doc_rel_path, pairs in doc_stale.items():
        doc_full_path = project_root / "docs" / doc_rel_path
        if not doc_full_path.exists():
            click.echo(f"  Warning: {doc_full_path} does not exist, skipping.")
            continue

        # Read changed code files.
        code_changes: list[dict[str, str]] = []
        for r in pairs:
            code_file = project_root / r["code_path"]
            if code_file.is_file():
                code_changes.append({
                    "code_path": r["code_path"],
                    "content": code_file.read_text(encoding="utf-8"),
                })

        if not code_changes:
            continue

        click.echo(f"\n  Updating: {doc_rel_path}")
        for c in code_changes:
            click.echo(f"    Changed: {c['code_path']}")

        # 4. Call LLM.
        click.echo(
            f"  Calling {llm_config.provider}/{llm_config.model}..."
        )
        try:
            proposed = auto_update_doc(
                llm_config,
                doc_full_path,
                code_changes,
            )
        except LLMError as exc:
            click.echo(f"  Error: {exc}", err=True)
            continue

        # 5. Show diff.
        original = doc_full_path.read_text(encoding="utf-8")
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"a/{doc_rel_path}",
            tofile=f"b/{doc_rel_path}",
        )
        diff_text = "".join(diff)

        if not diff_text:
            click.echo("  No changes proposed.")
            for r in pairs:
                mark_synced(conn, r["doc_path"], r["code_path"], project_root)
            continue

        click.echo("\n  Proposed changes:")
        click.echo(diff_text)

        # 6. Confirm.
        action = click.prompt(
            "  Apply changes?",
            type=click.Choice(["yes", "edit", "no"]),
            default="yes",
        )

        if action == "yes":
            doc_full_path.write_text(proposed, encoding="utf-8")
            for r in pairs:
                mark_synced(conn, r["doc_path"], r["code_path"], project_root)
            click.echo(f"  Applied and synced: {doc_rel_path}")
        elif action == "edit":
            # Write proposed content, then open in editor.
            doc_full_path.write_text(proposed, encoding="utf-8")
            click.edit(filename=str(doc_full_path))
            for r in pairs:
                mark_synced(conn, r["doc_path"], r["code_path"], project_root)
            click.echo(f"  Edited and synced: {doc_rel_path}")
        else:
            click.echo(f"  Skipped: {doc_rel_path}")

    conn.close()


# beadloom:service=mcp-server
@main.command("setup-mcp")
@click.option("--remove", is_flag=True, help="Remove beadloom from .mcp.json.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def setup_mcp(*, remove: bool, project: Path | None) -> None:
    """Create or update .mcp.json for beadloom MCP server."""
    import shutil

    project_root = project or Path.cwd()
    mcp_json_path = project_root / ".mcp.json"

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
        click.echo("Removed beadloom from .mcp.json.")
        return

    # Find beadloom command path.
    beadloom_path = shutil.which("beadloom") or "beadloom"

    data["mcpServers"]["beadloom"] = {
        "command": beadloom_path,
        "args": ["mcp-serve"],
    }

    mcp_json_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    click.echo(f"Updated {mcp_json_path}")


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
    import_path: Path | None,
    project: Path | None,
) -> None:
    """Initialize beadloom in a project."""
    from beadloom.onboarding import bootstrap_project, import_docs

    project_root = project or Path.cwd()

    if bootstrap:
        result = bootstrap_project(project_root)
        scan = result["scan"]
        click.echo(f"Scanned {scan['file_count']} files")
        click.echo(f"Generated {result['nodes_generated']} nodes")
        click.echo(f"Config: {project_root / '.beadloom' / 'config.yml'}")
        click.echo("")
        click.echo("Next: review .beadloom/_graph/*.yml, then run `beadloom reindex`")
        return

    if import_path:
        results = import_docs(project_root, import_path)
        click.echo(f"Classified {len(results)} documents:")
        for r in results:
            click.echo(f"  [{r['kind']}] {r['path']}")
        click.echo("")
        click.echo("Next: review .beadloom/_graph/imported.yml, then run `beadloom reindex`")
        return

    # Default: interactive mode.
    from beadloom.onboarding import interactive_init

    result = interactive_init(project_root)
    if result["mode"] == "cancelled":
        sys.exit(0)
