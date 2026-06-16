"""Index lifecycle + graph inspection commands: reindex, doctor, diff, link."""
# beadloom:component=cli-commands

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import click

from beadloom.services.commands._root import _warn_missing_parsers, main


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
        from beadloom.application.reindex import reindex as do_reindex

        result = do_reindex(project_root, docs_dir=docs_dir)
    else:
        from beadloom.application.reindex import incremental_reindex

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

    # Warn about missing language parsers when symbols == 0.
    if result.symbols_indexed == 0 and not result.nothing_changed:
        _warn_missing_parsers(project_root)


# beadloom:domain=doctor
@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def doctor(*, project: Path | None) -> None:
    """Run validation checks on the architecture graph."""
    from beadloom.application.doctor import Severity, run_checks
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    checks = run_checks(conn, project_root=project_root)
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
    from beadloom.graph.diff import compute_diff, diff_to_dict, render_diff

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
    links: list[dict[str, str]] = _cast("list[dict[str, str]]", node.get("links") or [])

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
