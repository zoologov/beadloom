"""Beadloom CLI entry point."""

# beadloom:service=cli

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence
    from types import ModuleType
    from typing import Any

    from beadloom.application.active_table import ReconcileResult
    from beadloom.application.gate import GateResult
    from beadloom.graph.federation import GateFailure

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


def _warn_missing_parsers(project_root: Path) -> None:
    """Print a warning if configured languages lack tree-sitter parsers.

    Reads ``languages`` from ``.beadloom/config.yml`` and checks parser
    availability via ``check_parser_availability``.  When missing parsers
    are detected, emits a ``click.secho`` warning with install instructions.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.exists():
        return

    import yaml

    from beadloom.context_oracle.code_indexer import check_parser_availability

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    languages: list[str] = config.get("languages", [])
    if not languages:
        return

    # Normalise: config may store bare names ("python") or extensions (".py").
    # Map common language names to their canonical extensions.
    name_to_exts: dict[str, list[str]] = {
        "python": [".py"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "go": [".go"],
        "rust": [".rs"],
    }

    extensions: set[str] = set()
    for lang in languages:
        lang_lower = lang.lower().strip()
        if lang_lower.startswith("."):
            extensions.add(lang_lower)
        elif lang_lower in name_to_exts:
            extensions.update(name_to_exts[lang_lower])
        else:
            # Try treating it as an extension anyway.
            extensions.add(f".{lang_lower}")

    if not extensions:
        return

    availability = check_parser_availability(extensions)
    missing = sorted(ext for ext, available in availability.items() if not available)
    if not missing:
        return

    exts_str = ", ".join(missing)
    click.secho(
        f"\u26a0 No parser available for {exts_str} files.",
        fg="yellow",
    )
    click.secho(
        '  Install language support: uv tool install "beadloom[languages]"',
        fg="yellow",
    )


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


# beadloom:domain=graph
@main.command()
@click.option(
    "--out",
    "out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the export to FILE instead of stdout.",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def export(*, out: Path | None, project: Path | None) -> None:
    """Export the indexed graph as a deterministic federation artifact (JSON)."""
    from datetime import datetime, timezone

    from beadloom.graph.federation import (
        build_export,
        current_commit_sha,
        resolve_landscape,
        resolve_repo_name,
        serialize_export,
    )
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    repo = resolve_repo_name(project_root)
    landscape = resolve_landscape(project_root)
    conn = open_db(db_path)
    artifact = build_export(
        conn,
        repo=repo,
        # Emit landscape only when explicitly configured (≠ the repo default),
        # so an undeclared-landscape export keeps the F1 wire shape (U5).
        landscape=landscape if landscape != repo else None,
        commit_sha=current_commit_sha(project_root),
        exported_at=datetime.now(tz=timezone.utc).isoformat(),
        generator=f"beadloom {__version__}",
    )
    conn.close()

    rendered = serialize_export(artifact)
    if out is not None:
        out.write_text(rendered + "\n", encoding="utf-8")
        click.echo(f"Wrote export to {out}")
    else:
        click.echo(rendered)


# beadloom:domain=graph
@main.command()
@click.argument(
    "exports",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Hub project root (default: current directory).",
)
@click.option(
    "--fail-on",
    "fail_on",
    is_flag=False,
    flag_value="default",
    default=None,
    help=(
        "Exit 1 if any edge/contract verdict is in this comma-separated set "
        "(case-insensitive). A bare --fail-on or 'default' uses the safe set "
        "breaking,drift,orphaned_consumer,undeclared_producer. Safe verdicts "
        "(external/expected/dead/unmapped/confirmed/ok/cleanup_candidate) are "
        "rejected. The artifact is always written first."
    ),
)
def federate(
    *, exports: tuple[Path, ...], project: Path | None, fail_on: str | None
) -> None:
    """Aggregate >=2 satellite export artifacts into one federated graph.

    Composes the namespaced node/edge union, resolves ``@repo:node`` foreign
    refs, computes three-valued intent-vs-reality verdicts, reconciles AMQP
    contracts (both-sides vs one-sided), and reports per-satellite staleness.
    Writes ``.beadloom/federated.json`` + ``.beadloom/federated.txt`` in the hub.

    With ``--fail-on`` the run also acts as a landscape gate: it still writes the
    artifact and prints the report, THEN exits 1 if any edge/contract carries a
    verdict in the fail-set (so CI always has the artifact to upload).
    """
    from datetime import datetime, timezone

    from beadloom.graph.federation import (
        aggregate_exports,
        gate_failures,
        render_federation_report,
        serialize_federation,
    )

    minimum_satellites = 2  # a hub needs >=2 satellites to federate
    if len(exports) < minimum_satellites:
        click.echo("Error: federate needs at least two export artifacts.", err=True)
        sys.exit(1)

    fail_set = _parse_fail_on(fail_on) if fail_on is not None else None

    artifacts = _load_export_artifacts(exports)
    if artifacts is None:
        sys.exit(1)

    fed = aggregate_exports(artifacts, now=datetime.now(tz=timezone.utc).isoformat())

    project_root = project or Path.cwd()
    out_dir = project_root / ".beadloom"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "federated.json"
    report_path = out_dir / "federated.txt"
    report = render_federation_report(fed)
    json_path.write_text(serialize_federation(fed) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")

    # Print the report + artifact location FIRST, so the artifact is always
    # available even when the gate then fails the build.
    click.echo(report, nl=False)
    click.echo(f"Wrote federated graph to {json_path}")

    if fail_set is not None:
        failures = gate_failures(fed, fail_set)
        if failures:
            _report_gate_failures(failures)
            sys.exit(1)


def _parse_fail_on(raw: str) -> set[str]:
    """Parse the ``--fail-on`` CSV into a fail-set, rejecting safe verdicts.

    ``default`` (or a bare ``--fail-on``) expands to the safe-default set. Any
    explicit token in :data:`NEVER_FAIL_VERDICTS` is refused with a clear,
    non-zero error (principle 3 — a user cannot arm a false gate). Matching is
    case-insensitive; whitespace/empty tokens are ignored.
    """
    from beadloom.graph.federation import NEVER_FAIL_VERDICTS, SAFE_DEFAULT_FAIL_ON

    tokens = {t.strip().lower() for t in raw.split(",") if t.strip()}
    if not tokens or tokens == {"default"}:
        return set(SAFE_DEFAULT_FAIL_ON)
    rejected = sorted(tokens & NEVER_FAIL_VERDICTS)
    if rejected:
        click.echo(
            "Error: --fail-on rejects no-false-gate verdicts "
            f"({', '.join(rejected)}); these are intentional/healthy states, "
            "never a gate failure.",
            err=True,
        )
        sys.exit(2)
    tokens.discard("default")
    return tokens


def _report_gate_failures(
    failures: list[GateFailure],
) -> None:
    """Print each gate failure (identity + verdict + BREAKING names + hint) to stderr."""
    from beadloom.graph.federation import gate_failure_remediation

    click.echo(
        f"Landscape gate FAILED: {len(failures)} verdict(s) in the fail-set.",
        err=True,
    )
    for failure in failures:
        line = f"  [{failure.kind}] {failure.identity}: {failure.verdict.upper()}"
        if failure.missing:
            line += f" — missing: {', '.join(failure.missing)}"
        click.echo(line, err=True)
        hint = gate_failure_remediation(failure)
        if hint:
            click.echo(f"    fix: {hint}", err=True)


def _load_export_artifacts(
    paths: tuple[Path, ...],
) -> list[dict[str, object]] | None:
    """Load + minimally validate satellite export JSON files.

    Returns ``None`` (after printing an error) if any file is not a JSON object,
    so the caller can exit non-zero rather than silently aggregate garbage.
    """
    artifacts: list[dict[str, object]] = []
    for path in paths:
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            click.echo(f"Error: cannot read export {path}: {exc}", err=True)
            return None
        if not isinstance(parsed, dict):
            click.echo(f"Error: export {path} is not a JSON object.", err=True)
            return None
        artifacts.append(parsed)
    return artifacts


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


def _compute_context_metrics(
    conn: sqlite3.Connection,
    nodes_count: int,
    symbols_count: int,
) -> dict[str, object]:
    """Compute context bundle size metrics for the status display.

    Iterates over all nodes, builds context bundles, and measures their
    approximate token sizes using the chars/4 heuristic.
    """
    import sqlite3 as _sqlite3  # local import to satisfy TYPE_CHECKING usage

    from beadloom.context_oracle.builder import build_context, estimate_tokens

    ref_ids = [row[0] for row in conn.execute("SELECT ref_id FROM nodes").fetchall()]

    bundle_sizes: list[tuple[str, int]] = []
    for ref_id in ref_ids:
        try:
            bundle = build_context(conn, [ref_id], depth=1, max_nodes=10, max_chunks=5)
            bundle_text = json.dumps(bundle, ensure_ascii=False)
            tokens = estimate_tokens(bundle_text)
            bundle_sizes.append((ref_id, tokens))
        except (LookupError, _sqlite3.Error):
            continue

    if bundle_sizes:
        avg_tokens = sum(t for _, t in bundle_sizes) // len(bundle_sizes)
        largest_ref, largest_tokens = max(bundle_sizes, key=lambda x: x[1])
    else:
        avg_tokens = 0
        largest_ref = ""
        largest_tokens = 0

    return {
        "avg_bundle_tokens": avg_tokens,
        "largest_bundle_tokens": largest_tokens,
        "largest_bundle_ref_id": largest_ref,
        "total_symbols": symbols_count,
    }


# beadloom:service=cli
@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option("--debt-report", "debt_report", is_flag=True, help="Show architecture debt report.")
@click.option(
    "--fail-if",
    "fail_if_expr",
    default=None,
    help="CI gate: exit 1 if condition met (score>N or errors>N). Requires --debt-report.",
)
@click.option(
    "--category",
    default=None,
    help="Filter debt report to a specific category: rules, docs, complexity, tests.",
)
def status(
    *,
    project: Path | None,
    output_json: bool,
    debt_report: bool,
    fail_if_expr: str | None,
    category: str | None,
) -> None:
    """Show project index statistics with health trends."""
    from beadloom.infrastructure.db import get_meta, open_db
    from beadloom.infrastructure.health import compute_trend, get_latest_snapshots

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)

    # --- Debt report mode ---
    if debt_report:
        from beadloom.application.debt_report import (
            _CATEGORY_SHORT_MAP,
            collect_debt_data,
            compute_debt_score,
            format_debt_json,
            format_debt_report,
            load_debt_weights,
        )

        # Validate --category early
        valid_categories = set(_CATEGORY_SHORT_MAP.keys()) | set(_CATEGORY_SHORT_MAP.values())
        if category is not None and category not in valid_categories:
            conn.close()
            click.echo(
                f"Error: invalid category '{category}'. Valid: rules, docs, complexity, tests",
                err=True,
            )
            sys.exit(1)

        # Validate --fail-if expression early
        _fail_if_pattern = re.compile(r"^(score|errors)>(\d+)$")
        fail_if_metric: str | None = None
        fail_if_threshold: int = 0
        if fail_if_expr is not None:
            match = _fail_if_pattern.match(fail_if_expr)
            if match is None:
                conn.close()
                click.echo(
                    f"Error: invalid --fail-if expression '{fail_if_expr}'. "
                    "Expected: score>N or errors>N",
                    err=True,
                )
                sys.exit(1)
            fail_if_metric = match.group(1)
            fail_if_threshold = int(match.group(2))

        weights = load_debt_weights(project_root)
        debt_data = collect_debt_data(conn, project_root, weights)
        report = compute_debt_score(debt_data, weights)
        conn.close()

        if output_json:
            click.echo(
                json.dumps(
                    format_debt_json(report, category=category),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            # For human output with category filter, rebuild report with filtered categories
            if category is not None:
                from beadloom.application.debt_report import DebtReport

                internal = _CATEGORY_SHORT_MAP.get(category, category)
                filtered_cats = [c for c in report.categories if c.name == internal]
                report = DebtReport(
                    debt_score=report.debt_score,
                    severity=report.severity,
                    categories=filtered_cats,
                    top_offenders=report.top_offenders,
                    trend=report.trend,
                )
            click.echo(format_debt_report(report))

        # Evaluate --fail-if condition
        if fail_if_metric is not None:
            should_fail = False
            if fail_if_metric == "score":
                should_fail = report.debt_score > fail_if_threshold
            elif fail_if_metric == "errors":
                error_count = 0
                for cat in report.categories:
                    if cat.name == "rule_violations":
                        error_count = int(cat.details.get("errors", 0))
                        break
                should_fail = error_count > fail_if_threshold
            if should_fail:
                sys.exit(1)

        return

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

    # Context metrics: measure bundle sizes per node.
    context_metrics = _compute_context_metrics(conn, nodes_count, symbols_count)

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
            "context_metrics": context_metrics,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    # Rich-formatted output.
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Header panel.
    console.print(
        Panel(
            f"Last reindex: {last_reindex}",
            title=f"Beadloom v{version}",
            border_style="blue",
        )
    )
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
    console.print()

    # Context Metrics section.
    ctx_table = Table(title="Context Metrics", show_header=False, box=None, padding=(0, 1))
    ctx_table.add_column("metric", style="cyan")
    ctx_table.add_column("value", justify="right")
    avg_tokens = context_metrics["avg_bundle_tokens"]
    largest_tokens = context_metrics["largest_bundle_tokens"]
    largest_ref = context_metrics["largest_bundle_ref_id"]
    total_syms = context_metrics["total_symbols"]
    ctx_table.add_row("Avg bundle size", f"~{avg_tokens:,} tokens")
    if largest_ref:
        ctx_table.add_row("Largest bundle", f"{largest_ref} -- {largest_tokens:,} tokens")
    else:
        ctx_table.add_row("Largest bundle", f"~{largest_tokens:,} tokens")
    ctx_table.add_row("Total indexed", f"{total_syms:,} symbols")
    console.print(ctx_table)


# beadloom:domain=doc-sync
@main.command("sync-check")
@click.option("--porcelain", is_flag=True, help="TAB-separated machine-readable output.")
@click.option("--json", "output_json", is_flag=True, help="Structured JSON output.")
@click.option("--report", "output_report", is_flag=True, help="Markdown report for CI posting.")
@click.option("--ref", "ref_filter", default=None, help="Filter by ref_id.")
@click.option(
    "--since",
    "since_ref",
    default=None,
    help="Baseline = code state at this git ref (e.g. the push's parent commit) "
    "instead of the stored sync_state. Reports pairs whose code drifted since "
    "the ref while the doc was not correspondingly updated.",
)
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
    since_ref: str | None,
    project: Path | None,
) -> None:
    """Check doc-code synchronization status.

    Exit codes: 0 = all ok, 1 = error, 2 = stale pairs found.
    """
    from beadloom.doc_sync.engine import (
        _validate_git_ref,
        check_reference_drift,
        check_sync,
        check_sync_since,
    )
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    if since_ref is not None and (
        set(since_ref) == {"0"} or not _validate_git_ref(project_root, since_ref)
    ):
        click.echo(f"Error: Invalid git ref: '{since_ref}'", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    if since_ref is not None:
        results = check_sync_since(conn, project_root=project_root, since=since_ref)
        # `--since` is a ref-relative symbol-pair view; reference surfaces have no
        # git-ref baseline, so they are not evaluated in that mode.
        references: list[dict[str, Any]] = []
    else:
        results = check_sync(conn, project_root=project_root)
        references = check_reference_drift(conn, project_root)
    conn.close()

    if ref_filter:
        results = [r for r in results if r["ref_id"] == ref_filter]

    has_stale = any(r["status"] == "stale" for r in results)
    # Surface drift is advisory (warning) — it NEVER affects the exit code.
    drifted_refs = [r for r in references if r["status"] == "surface_drift"]

    if output_json:
        ok_count = sum(1 for r in results if r["status"] == "ok")
        stale_count = sum(1 for r in results if r["status"] == "stale")
        summary: dict[str, Any] = {
            "total": len(results),
            "ok": ok_count,
            "stale": stale_count,
        }
        data: dict[str, Any] = {
            "summary": summary,
            "pairs": [
                {
                    "status": r["status"],
                    "ref_id": r["ref_id"],
                    "doc_path": r["doc_path"],
                    "code_path": r["code_path"],
                    "reason": r.get("reason", "ok"),
                    **({"details": r["details"]} if r.get("details") else {}),
                }
                for r in results
            ],
        }
        # Reference-doc surface drift (BDL-057 Layer 2) is additive and only
        # applies to the stored-baseline mode — `--since` is a ref-relative
        # symbol-pair view with no reference baseline, so its JSON shape is left
        # untouched (the `pairs` array above is unchanged in both modes).
        if since_ref is None:
            summary["surface_drift"] = len(drifted_refs)
            data["references"] = [
                {
                    "status": r["status"],
                    "doc_path": r["doc_path"],
                    "watches": r["watches"],
                    "reason": r["reason"],
                    "severity": r["severity"],
                }
                for r in references
            ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_report:
        click.echo(_build_sync_report(results))
    elif porcelain:
        for r in results:
            reason = r.get("reason", "ok")
            click.echo(
                f"{r['status']}\t{r['ref_id']}\t{r['doc_path']}\t{r['code_path']}\t{reason}"
            )
        for r in references:
            # ref_id/code_path columns are empty for a reference doc (no pairing).
            click.echo(f"{r['status']}\t\t{r['doc_path']}\t\t{r['reason']}")
    else:
        if not results and not references:
            click.echo("No sync pairs found.")
        else:
            for r in results:
                marker = "[stale]" if r["status"] == "stale" else "[ok]"
                reason = r.get("reason", "ok")
                details = r.get("details", "")

                if reason == "untracked_files" and details:
                    click.echo(f"  {marker} {r['ref_id']}: {r['doc_path']} (untracked: {details})")
                elif reason == "missing_modules" and details:
                    click.echo(
                        f"  {marker} {r['ref_id']}: {r['doc_path']} (missing modules: {details})"
                    )
                elif r["status"] == "stale" and reason not in (
                    "ok",
                    "untracked_files",
                    "missing_modules",
                ):
                    click.echo(
                        f"  {marker} {r['ref_id']}: {r['doc_path']} "
                        f"<-> {r['code_path']} ({reason})"
                    )
                else:
                    click.echo(f"  {marker} {r['ref_id']}: {r['doc_path']} <-> {r['code_path']}")

            for r in references:
                marker = "[warn]" if r["status"] == "surface_drift" else "[ok]"
                if r["status"] == "surface_drift":
                    click.echo(
                        f"  {marker} {r['doc_path']} (surface drift: watches="
                        f"{r['watches']}; run `beadloom sync-update {r['doc_path']}`)"
                    )
                else:
                    click.echo(f"  {marker} {r['doc_path']} (watches={r['watches']})")

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
        lines.extend(
            [
                "",
                "### Stale Documents",
                "",
                "| Node | Doc | Changed Code |",
                "|------|-----|-------------|",
            ]
        )
        for r in stale_pairs:
            lines.append(f"| {r['ref_id']} | `{r['doc_path']}` | `{r['code_path']}` |")
        lines.extend(
            [
                "",
                "> Run `beadloom sync-update <ref_id>` to review and update.",
            ]
        )
    else:
        lines.extend(["", "All documentation is up to date."])

    return "\n".join(lines)


_HOOK_TEMPLATE_WARN = """\
#!/bin/sh
# pre-commit hook managed by beadloom

# --- Lint check (ruff) ---
if command -v uv >/dev/null 2>&1; then
  echo "Running ruff check..."
  uv run ruff check src/ tests/ 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Warning: ruff lint violations detected"
  fi
fi

# --- Type check (mypy) ---
if command -v uv >/dev/null 2>&1; then
  echo "Running mypy..."
  uv run mypy 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Warning: mypy type errors detected"
  fi
fi

# --- Doc sync check ---
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

# --- ACTIVE / tracker coherence ---
# Guarded no-op: only runs when BOTH `bd` and `beadloom` are installed. In any
# repo without `bd` (or without ACTIVE tables) this block does nothing and never
# blocks the commit. Auto-fixes the bead-status tables + tracked issues.jsonl
# and restages them so the commit is coherent by construction. `--stage` stages
# EXACTLY the reconciled ACTIVE.md(s) + the exported jsonl — never an unrelated
# concurrently-edited doc in the same subtree.
if command -v bd >/dev/null 2>&1 && command -v beadloom >/dev/null 2>&1; then
  beadloom active-sync --stage >/dev/null 2>&1
fi
"""

_HOOK_TEMPLATE_BLOCK = """\
#!/bin/sh
# pre-commit hook managed by beadloom
failed=0

# --- Lint check (ruff) ---
if command -v uv >/dev/null 2>&1; then
  echo "Running ruff check..."
  uv run ruff check src/ tests/ 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Error: ruff lint violations — commit blocked"
    echo "Run: uv run ruff check --fix src/ tests/"
    failed=1
  fi
fi

# --- Type check (mypy) ---
if command -v uv >/dev/null 2>&1; then
  echo "Running mypy..."
  uv run mypy 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Error: mypy type errors — commit blocked"
    failed=1
  fi
fi

# --- Doc sync check ---
stale=$(beadloom sync-check --porcelain 2>/dev/null)
exit_code=$?

if [ $exit_code -eq 2 ]; then
  echo "Error: stale documentation detected — commit blocked"
  echo "$stale"
  echo ""
  echo "Run: beadloom sync-update <ref_id> to update docs"
  failed=1
fi

if [ $exit_code -eq 1 ]; then
  echo "Warning: beadloom sync-check failed (index may be stale)"
fi

# --- ACTIVE / tracker coherence ---
# Guarded no-op: only runs when BOTH `bd` and `beadloom` are installed. In any
# repo without `bd` (or without ACTIVE tables) this block does nothing and never
# blocks the commit. Auto-fixes the bead-status tables + tracked issues.jsonl
# and restages them so the commit is coherent by construction (never blocks).
# `--stage` stages EXACTLY the reconciled ACTIVE.md(s) + the exported jsonl —
# never an unrelated concurrently-edited doc in the same subtree.
if command -v bd >/dev/null 2>&1 && command -v beadloom >/dev/null 2>&1; then
  beadloom active-sync --stage >/dev/null 2>&1
fi

if [ $failed -ne 0 ]; then
  exit 1
fi
"""

# Pre-push hook: the AUTHORITATIVE blocking Beadloom Gate. Runs the full
# `beadloom ci` Gate (incremental reindex -> lint -> coverage-lint -> sync-check
# -> doctor) and exits non-zero to BLOCK the push on red. Guarded + fail-safe:
# in any repo without `beadloom` on PATH the hook is a safe no-op (never blocks).
# Idempotent (re-running install-hooks overwrites cleanly). `--no-verify` is the
# documented escape hatch. The pre-commit hook stays the lighter warn check; the
# full Gate lives here so it isn't duplicated on every commit.
_HOOK_TEMPLATE_PRE_PUSH = """\
#!/bin/sh
# pre-push hook managed by beadloom -- the blocking Beadloom Gate.

# Fail-safe: outside a Beadloom flow repo (no `beadloom` on PATH) this hook is a
# safe no-op so it never blocks a push in a repo that does not use Beadloom.
if ! command -v beadloom >/dev/null 2>&1; then
  exit 0
fi

echo "Running Beadloom Gate (beadloom ci)..."
beadloom ci
if [ $? -ne 0 ]; then
  echo ""
  echo "Beadloom Gate failed (docs stale / lint / coverage / doctor)."
  echo "Run the tech-writer (or /coordinator) to refresh docs, then re-push."
  echo "To override (discouraged): git push --no-verify"
  exit 1
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
@click.option("--remove", is_flag=True, help="Remove the selected hook(s).")
@click.option(
    "--pre-commit",
    "pre_commit",
    is_flag=True,
    help="Operate on the pre-commit hook only (default: both pre-commit + pre-push).",
)
@click.option(
    "--pre-push",
    "pre_push",
    is_flag=True,
    help="Operate on the pre-push Gate hook only (default: both pre-commit + pre-push).",
)
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
    pre_commit: bool,
    pre_push: bool,
    project: Path | None,
) -> None:
    """Install or remove beadloom git hooks.

    By default installs BOTH the pre-commit hook (lighter warn/block check) and
    the pre-push hook (the authoritative blocking Beadloom Gate). Use
    ``--pre-commit`` / ``--pre-push`` to select one. ``--remove`` removes the
    selected hook(s).
    """
    import stat

    project_root = project or Path.cwd()
    hooks_dir = project_root / ".git" / "hooks"

    if not hooks_dir.exists():
        click.echo("Error: .git/hooks not found. Is this a git repository?", err=True)
        sys.exit(1)

    # No selector -> operate on both hooks.
    do_pre_commit = pre_commit or not (pre_commit or pre_push)
    do_pre_push = pre_push or not (pre_commit or pre_push)

    if remove:
        _remove_hooks(hooks_dir, pre_commit=do_pre_commit, pre_push=do_pre_push)
        return

    if do_pre_commit:
        template = _HOOK_TEMPLATE_BLOCK if mode == "block" else _HOOK_TEMPLATE_WARN
        _write_hook(hooks_dir / "pre-commit", template, stat)
        click.echo(f"Installed pre-commit hook (mode: {mode}).")
    if do_pre_push:
        _write_hook(hooks_dir / "pre-push", _HOOK_TEMPLATE_PRE_PUSH, stat)
        click.echo("Installed pre-push hook (Beadloom Gate, blocking).")


def _write_hook(hook_path: Path, template: str, stat_mod: ModuleType) -> None:
    """Write an executable git hook (idempotent overwrite)."""
    hook_path.write_text(template)
    hook_path.chmod(
        hook_path.stat().st_mode
        | stat_mod.S_IXUSR
        | stat_mod.S_IXGRP
        | stat_mod.S_IXOTH
    )


def _remove_hooks(hooks_dir: Path, *, pre_commit: bool, pre_push: bool) -> None:
    """Remove the selected git hook(s); report what was removed."""
    targets: list[str] = []
    if pre_commit:
        targets.append("pre-commit")
    if pre_push:
        targets.append("pre-push")
    removed_any = False
    for name in targets:
        path = hooks_dir / name
        if path.exists():
            path.unlink()
            click.echo(f"Removed {name} hook.")
            removed_any = True
    if not removed_any:
        click.echo("No matching hook to remove.")


# beadloom:component=active-table
def _bd_statuses_from_list(beads: list[dict[str, object]]) -> dict[str, str]:
    """Build ``{bead_id -> status_token}`` from a ``bd list --json`` payload.

    Each bead's own ``status`` is taken verbatim, except that an ``open`` bead
    with at least one *open blocker* is reported as ``"blocked"`` so the ACTIVE
    table reflects readiness. A blocker is a ``dependencies`` entry of type
    ``blocks`` whose target bead is not ``closed`` (parent-child links never
    block). Malformed entries are skipped defensively (best-effort, never raises).
    """
    statuses: dict[str, str] = {}
    blockers: dict[str, list[str]] = {}
    for bead in beads:
        bead_id = bead.get("id")
        status = bead.get("status")
        if not isinstance(bead_id, str) or not isinstance(status, str):
            continue
        statuses[bead_id] = status
        deps = bead.get("dependencies")
        targets: list[str] = []
        if isinstance(deps, list):
            for dep in deps:
                if not isinstance(dep, dict) or dep.get("type") != "blocks":
                    continue
                target = dep.get("depends_on_id")
                if isinstance(target, str):
                    targets.append(target)
        blockers[bead_id] = targets

    for bead_id, status in list(statuses.items()):
        if status != "open":
            continue
        if any(statuses.get(t) not in (None, "closed") for t in blockers.get(bead_id, [])):
            statuses[bead_id] = "blocked"
    return statuses


# beadloom:component=active-table
def _query_bd_statuses(project_root: Path) -> dict[str, str] | None:
    """Return bead-id -> status from ``bd list --json``, or None if bd unavailable.

    Funnels through :func:`bd_seam.run_bd` (mockable). Returns ``None`` when ``bd``
    is not installed (``BdUnavailableError``) or the call/JSON fails — the caller
    treats ``None`` as "skip, no-op" so a non-flow repo is never affected.
    """
    from beadloom.services.bd_seam import BdUnavailableError, run_bd

    try:
        result = run_bd(["list", "--json"], cwd=str(project_root))
    except BdUnavailableError:
        return None
    if not result.ok:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    beads = [b for b in payload if isinstance(b, dict)]
    return _bd_statuses_from_list(beads)


# beadloom:component=active-table
def _jsonl_is_tracked(project_root: Path) -> bool:
    """True when ``.beads/issues.jsonl`` exists AND is git-tracked in *project_root*."""
    import subprocess

    jsonl = project_root / ".beads" / "issues.jsonl"
    if not jsonl.is_file():
        return False
    try:
        # Fixed argv, no shell; queries the index for the tracked path.
        completed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".beads/issues.jsonl"],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0


# beadloom:component=active-table
def _export_jsonl(project_root: Path) -> bool:
    """Best-effort ``bd export -o .beads/issues.jsonl`` when the jsonl is tracked.

    Keeps the tracked tracker artifact honest across branch/squash-merge (the
    bd-close jsonl-drift fix). Skips silently if ``bd`` is unavailable or the
    jsonl isn't tracked — never raises. Returns ``True`` when ``bd export`` was
    actually run (so a caller may stage the exact jsonl path), else ``False``.
    """
    from beadloom.services.bd_seam import BdUnavailableError, run_bd

    if not _jsonl_is_tracked(project_root):
        return False
    try:
        run_bd(["export", "-o", ".beads/issues.jsonl"], cwd=str(project_root))
    except BdUnavailableError:
        return False
    return True


# beadloom:component=active-table
def _stage_reconciled(
    project_root: Path,
    changed_files: list[Path],
    *,
    exported_jsonl: bool,
) -> None:
    """``git add`` EXACTLY the reconciled ACTIVE.md paths (+ the exported jsonl).

    Replaces the old broad ``git add -u .claude/development/docs/features`` in the
    hook, which over-staged any concurrently-edited sibling doc in that subtree.
    Best-effort and guarded: no paths → no-op; no git / failure → silently skip
    (never raises, never stages anything beyond the supplied paths).
    """
    import subprocess

    paths = [str(p) for p in changed_files]
    if exported_jsonl:
        paths.append(".beads/issues.jsonl")
    if not paths:
        return
    try:
        # Fixed argv (no shell); `--` guards the explicit, reconciled paths only.
        subprocess.run(  # noqa: S603
            ["git", "add", "--", *paths],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return


# beadloom:component=active-table
@main.command("active-sync")
@click.option("--epic", "epic", default=None, help="Reconcile only this epic's ACTIVE.md.")
@click.option(
    "--check",
    "check_only",
    is_flag=True,
    help="Report drift without writing; exit 1 if any drift, 0 if clean.",
)
@click.option("--json", "output_json", is_flag=True, help="Machine-readable JSON output.")
@click.option(
    "--no-export",
    "no_export",
    is_flag=True,
    help="Skip the `bd export` jsonl sync (fix mode only).",
)
@click.option(
    "--stage",
    "stage",
    is_flag=True,
    help="git add EXACTLY the reconciled ACTIVE.md(s) + the exported jsonl "
    "(fix mode only); never stages unrelated files. Best-effort (no git → skip).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def active_sync(
    *,
    epic: str | None,
    check_only: bool,
    output_json: bool,
    no_export: bool,
    stage: bool,
    project: Path | None,
) -> None:
    """Reconcile ACTIVE.md bead-status tables from ``bd`` (the source of truth).

    For each epic's ACTIVE.md, rewrites the bead-status table's Status cells to
    match ``bd`` (rich coordinator notes are preserved when the state agrees).
    Default = fix mode (writes + syncs the tracked ``.beads/issues.jsonl`` via
    ``bd export``); ``--check`` reports drift without writing (exit 1 on drift).

    No-op contract: if ``bd`` is unavailable OR there is no ACTIVE file with a
    bead-status table, this exits 0 and writes nothing (a non-flow repo is never
    affected). With ``--stage`` (fix mode), ``git add`` is run on EXACTLY the
    reconciled ACTIVE.md paths + the exported jsonl — nothing else (so a
    concurrently-edited sibling doc is never collaterally staged).
    """
    from beadloom.application.active_table import reconcile_active_tables

    project_root = project or Path.cwd()

    if not _has_active_table(project_root, epic):
        click.echo("active-sync: no ACTIVE.md bead tables — nothing to reconcile (skipped).")
        return

    bd_statuses = _query_bd_statuses(project_root)
    if bd_statuses is None:
        click.echo("active-sync: bd unavailable — skipped.")
        return

    if check_only:
        _active_sync_check(project_root, bd_statuses, epic=epic, output_json=output_json)
        return

    result = reconcile_active_tables(project_root, bd_statuses, epic=epic)
    exported = False if no_export else _export_jsonl(project_root)
    if stage:
        _stage_reconciled(project_root, result.changed_files, exported_jsonl=exported)
    _emit_active_sync(result, output_json=output_json, check=False)


# beadloom:component=active-table
def _has_active_table(project_root: Path, epic: str | None) -> bool:
    """True when at least one in-scope ACTIVE.md contains a bead-status table."""
    from beadloom.application.active_table import (
        _discover_active_files,
        _find_status_column,
    )

    for path in _discover_active_files(project_root, epic):
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError:
            continue
        if _find_status_column(lines) is not None:
            return True
    return False


# beadloom:component=active-table
def _active_sync_check(
    project_root: Path,
    bd_statuses: dict[str, str],
    *,
    epic: str | None,
    output_json: bool,
) -> None:
    """``--check`` mode: detect drift on a throwaway copy, never write; exit 1 on drift."""
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp) / "proj"
        src = project_root / ".claude" / "development" / "docs" / "features"
        if src.is_dir():
            shutil.copytree(
                src, sandbox / ".claude" / "development" / "docs" / "features"
            )
        from beadloom.application.active_table import reconcile_active_tables

        result = reconcile_active_tables(sandbox, bd_statuses, epic=epic)
    drift = bool(result.drifted_rows)
    _emit_active_sync(result, output_json=output_json, check=True)
    if drift:
        sys.exit(1)


# beadloom:component=active-table
def _emit_active_sync(
    result: ReconcileResult,
    *,
    output_json: bool,
    check: bool,
) -> None:
    """Print the reconcile outcome (JSON or human-readable)."""
    if output_json:
        payload = {
            "changed_files": [str(p) for p in result.changed_files],
            "drifted_rows": [
                {"path": str(p), "bead_id": bid, "old": old, "new": new}
                for (p, bid, old, new) in result.drifted_rows
            ],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not result.drifted_rows:
        click.echo("active-sync: ACTIVE tables already coherent.")
        return
    verb = "would update" if check else "updated"
    click.echo(f"active-sync: {verb} {len(result.drifted_rows)} row(s):")
    for path, bead_id, old, new in result.drifted_rows:
        click.echo(f"  {path}: {bead_id}  {old!r} -> {new!r}")


# beadloom:domain=doc-sync
def _mark_synced_noninteractive(
    conn: sqlite3.Connection,
    project_root: Path,
    *,
    ref_id: str | None,
    all_refs: bool,
) -> None:
    """Re-baseline freshness for a ref (or every stale ref) without prompting.

    Wraps ``mark_synced_by_ref``: recomputes hashes + symbols_hash and records
    ``status='ok'``. Prints a concise, deterministic summary and exits 0.
    """
    from beadloom.doc_sync.engine import (
        check_sync,
        mark_reference_synced,
        mark_synced_by_ref,
    )

    if all_refs:
        results = check_sync(conn, project_root=project_root)
        stale_refs = sorted({r["ref_id"] for r in results if r["status"] == "stale"})
        total = 0
        for ref in stale_refs:
            rows = mark_synced_by_ref(conn, ref, project_root)
            total += rows
            click.echo(f"Re-baselined {ref}: {rows} pair(s).")
        # Also clear any reference-doc surface drift (BDL-057 Layer 2; advisory).
        ref_docs = mark_reference_synced(conn, None, project_root, all_docs=True)
        if not stale_refs and not ref_docs:
            click.echo("No stale refs to re-baseline.")
            return
        if stale_refs:
            click.echo(f"Marked {len(stale_refs)} ref(s) synced ({total} pair(s) total).")
        if ref_docs:
            click.echo(f"Re-baselined {ref_docs} reference doc(s).")
        return

    assert ref_id is not None  # guaranteed by the command-level validation
    # A reference doc (watches annotation) is addressed by its doc_path; try that
    # first so `sync-update docs/architecture.md --yes` clears surface drift.
    ref_docs = mark_reference_synced(conn, ref_id, project_root)
    if ref_docs:
        click.echo(f"Re-baselined reference doc {ref_id}.")
        return

    rows = mark_synced_by_ref(conn, ref_id, project_root)
    if rows == 0:
        click.echo(f"No sync pairs found for {ref_id}; nothing to re-baseline.")
        return
    click.echo(f"Re-baselined {ref_id}: {rows} pair(s).")


@main.command("sync-update")
@click.argument("ref_id", required=False)
@click.option("--check", "check_only", is_flag=True, help="Only show status, don't open editor.")
@click.option(
    "--yes",
    "-y",
    "assume_yes",
    is_flag=True,
    help="Non-interactive: re-baseline freshness without an editor or prompt.",
)
@click.option(
    "--all",
    "all_refs",
    is_flag=True,
    help="With --yes: re-baseline every currently-stale ref (for the fixpoint loop).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def sync_update(
    ref_id: str | None,
    *,
    check_only: bool,
    assume_yes: bool,
    all_refs: bool,
    project: Path | None,
) -> None:
    """Show sync status and update docs for a ref_id.

    Use --check to only display status without opening an editor.

    Use --yes (-y) for a non-interactive re-baseline (no editor/prompt): records
    that the doc(s) match the code now. Add --all to re-baseline every stale ref
    in one call (useful for an automated fixpoint loop).

    For automated doc updates, use your AI agent (Claude Code, Cursor, etc.)
    with Beadloom's MCP tools (update_node, mark_synced).
    """
    from beadloom.doc_sync.engine import check_sync
    from beadloom.infrastructure.db import open_db

    if all_refs and not assume_yes:
        raise click.UsageError("--all requires --yes (non-interactive only).")
    if all_refs and ref_id is not None:
        raise click.UsageError("--all and an explicit REF_ID are mutually exclusive.")
    if not all_refs and ref_id is None:
        raise click.UsageError("Provide a REF_ID (or use --all with --yes).")

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)

    if assume_yes:
        _mark_synced_noninteractive(conn, project_root, ref_id=ref_id, all_refs=all_refs)
        conn.close()
        return

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
    from beadloom.doc_sync.engine import mark_synced

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


def _mcp_path_for_editor(editor: str, project_root: Path) -> str:
    """Return the MCP config file path for display."""
    paths = {
        "claude-code": ".mcp.json",
        "cursor": ".cursor/mcp.json",
        "windsurf": "~/.codeium/windsurf/mcp_config.json",
    }
    return paths.get(editor, ".mcp.json")


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


@main.command("setup-rules")
@click.option(
    "--tool",
    "tool_name",
    type=click.Choice(["cursor", "windsurf", "cline"]),
    default=None,
    help="Target IDE (default: auto-detect all).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--refresh",
    is_flag=True,
    default=False,
    help="Refresh auto-managed sections in .claude/CLAUDE.md and regenerate AGENTS.md.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what --refresh would change without modifying files.",
)
def setup_rules(
    *,
    tool_name: str | None,
    project: Path | None,
    refresh: bool,
    dry_run: bool,
) -> None:
    """Create IDE rules files that reference .beadloom/AGENTS.md.

    Auto-detects installed IDEs (Cursor, Windsurf, Cline) by marker
    files and creates thin adapter files. Does not overwrite existing files.

    With --refresh, also refreshes auto-managed sections in .claude/CLAUDE.md
    and regenerates .beadloom/AGENTS.md.  Use --dry-run with --refresh to
    preview changes without writing.
    """
    from beadloom.onboarding.scanner import (
        _RULES_ADAPTER_TEMPLATE,
        _RULES_CONFIGS,
        generate_agents_md,
        refresh_claude_md,
        setup_rules_auto,
    )

    project_root = project or Path.cwd()

    if dry_run and not refresh:
        click.echo("Error: --dry-run requires --refresh.", err=True)
        raise SystemExit(1)

    if refresh:
        # Refresh CLAUDE.md auto-managed sections.
        changed = refresh_claude_md(project_root, dry_run=dry_run)
        if changed:
            verb = "Would update" if dry_run else "Updated"
            click.echo(f"{verb} .claude/CLAUDE.md sections: {', '.join(changed)}")
        else:
            click.echo(".claude/CLAUDE.md: no changes needed.")

        # Regenerate AGENTS.md (unless dry-run).
        if not dry_run:
            agents_path = generate_agents_md(project_root)
            click.echo(f"Regenerated {agents_path.relative_to(project_root)}")
        else:
            click.echo("Would regenerate .beadloom/AGENTS.md")
        return

    if tool_name:
        # Explicit IDE specified — create without marker detection.
        cfg = _RULES_CONFIGS[tool_name]
        rules_path = project_root / cfg["path"]
        if rules_path.exists():
            click.echo(f"Skipped: {cfg['path']} already exists.")
            return
        rules_path.write_text(_RULES_ADAPTER_TEMPLATE, encoding="utf-8")
        click.echo(f"Created {cfg['path']}")
    else:
        # Auto-detect.
        created = setup_rules_auto(project_root)
        if created:
            for f in created:
                click.echo(f"Created {f}")
        else:
            click.echo("No IDE markers detected. Use --tool to specify.")


# beadloom:domain=onboarding
@main.command("setup-ai-techwriter")
@click.option(
    "--platform",
    type=click.Choice(["github", "gitlab"]),
    required=True,
    help="CI platform to scaffold for (github or gitlab).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def setup_ai_techwriter(*, platform: str, project: Path | None) -> None:
    """Scaffold the AI tech-writer into this repo (BDL-047 / F4.1, G8).

    In the setup-* family (alongside setup-mcp / setup-rules). The harness ships
    inside the installed ``beadloom`` package (BDL-051 / S2), so this no longer
    vendors any Python: it idempotently drops the chosen platform's CI wrapper
    (which invokes ``python -m beadloom.ai_agents.ai_techwriter``), the operator
    artifacts ``tools/ai_techwriter/{recipe.yaml,provision-runner.sh}`` (copied
    from package data for reference + runner provisioning), and the
    getting-started guide ``docs/guides/ai-techwriter.md``. Re-running cleanly
    overwrites the generated files.
    """
    from beadloom.onboarding.ai_techwriter_setup import scaffold

    project_root = project or Path.cwd()
    created = scaffold(project_root, platform=platform)
    for path in created:
        click.echo(f"Wrote {path.relative_to(project_root)}")
    click.echo(
        "Next: 1) pick a box (>=4 GB RAM), 2) get a runner registration token + "
        "add the QWEN_API_KEY secret/variable, 3) on the VPS run "
        "./tools/ai_techwriter/provision-runner.sh --platform <github|gitlab> "
        "--repo <url> --token <tok>, then commit + enable the pipeline. "
        "See docs/guides/ai-techwriter.md."
    )


# beadloom:domain=onboarding
@main.command("setup-agentic-flow")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite hand-edited scaffolded flow files (default: preserve them).",
)
@click.option(
    "--tool",
    "tools",
    multiple=True,
    type=click.Choice(["claude", "cursor"]),
    help="Tool adapter set(s) to generate (repeatable). Default: flow.yml or claude.",
)
@click.option(
    "--architecture",
    "architecture",
    type=click.Choice(["ddd", "fsd"]),
    default=None,
    help="Architecture methodology overlay. Default: flow.yml or ddd.",
)
@click.option(
    "--stack",
    "stack",
    default=None,
    help=(
        "Comma-separated stack overlays "
        "(python,fastapi,javascript,typescript,vuejs). Default: flow.yml or "
        "auto-detected."
    ),
)
def setup_agentic_flow(
    *,
    project: Path | None,
    force: bool,
    tools: tuple[str, ...],
    architecture: str | None,
    stack: str | None,
) -> None:
    """Scaffold Beadloom's proven multi-agent dev flow into this repo (BDL-048/052).

    In the setup-* family (alongside setup-rules / setup-mcp). Composes the role
    subagents from CORE + the selected architecture overlay (``ddd``/``fsd``) +
    the selected stack overlays, then writes the per-tool adapter set(s) — for
    ``claude`` to ``.claude/agents/*`` (+ ``.claude/commands/*`` + a per-project
    ``.claude/CLAUDE.md``), for ``cursor`` to ``.cursor/agents/*`` (+ a Cursor
    orchestrator pointer). Selection comes from ``.beadloom/flow.yml`` (or the
    ``--tool``/``--architecture``/``--stack`` flags, which override it; defaults
    are ``claude`` / ``ddd`` / auto-detected stack). A drift-guard test keeps
    every generated adapter byte-identical to its composition. User prose
    outside CLAUDE.md auto-regions is never touched; --force overwrites
    hand-edited Claude flow files.
    """
    from beadloom.onboarding.agentic_flow_setup import scaffold
    from beadloom.onboarding.flow_config import FlowConfigError, resolve_flow_config
    from beadloom.onboarding.role_adapters import generate_adapters

    project_root = project or Path.cwd()
    stack_tuple = (
        tuple(s.strip() for s in stack.split(",") if s.strip())
        if stack is not None
        else ()
    )
    try:
        config = resolve_flow_config(
            project_root,
            tools=tools,
            architecture=architecture,
            stack=stack_tuple,
        )
    except FlowConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"Composing roles: architecture={config.architecture}, "
        f"stack={','.join(config.stack)}, tools={','.join(config.tools)}"
    )
    adapters = generate_adapters(config, project_root)
    for tool, files in adapters.agents.items():
        for rel in files:
            click.echo(f"Wrote {rel} ({tool})")
    for rel in adapters.extra:
        click.echo(f"Wrote {rel}")

    result = scaffold(project_root, force=force, include_agents=False)

    for name in result.commands_written:
        click.echo(f"Wrote .claude/commands/{name}.md")
    for name in result.commands_skipped:
        click.echo(f"Skipped .claude/commands/{name}.md (hand-edited; use --force)")
    if result.claude_md is not None:
        click.echo(f"Wrote {result.claude_md.relative_to(project_root)}")

    click.echo(
        "\nHonest boundary: the coordinator + Agent-spawn are Claude-Code-native "
        "(orchestration stays in the harness). The Beadloom MCP process-tools are "
        "the deterministic, tool-agnostic substrate the flow calls — MCP serves "
        "tools, not orchestration. The single source of TRUE enforcement remains "
        "`beadloom ci` in CI (lint/sync-check/config-check/doctor); the in-flow "
        "gates are advisory-strong, not a substitute for CI."
    )
    click.echo(
        "Next: 1) `beadloom config-check` keeps the scaffolded flow + CLAUDE.md "
        "auto-regions honest, 2) `beadloom setup-mcp` wires the process-tools for "
        "your IDE, 3) start work with `/task-init` then `/coordinator`."
    )


# beadloom:domain=onboarding
@main.command("setup-branch-protection")
@click.option(
    "--repo",
    "repo_slug",
    required=True,
    metavar="OWNER/NAME",
    help="GitHub repository as owner/name (e.g. acme/widget).",
)
@click.option(
    "--branch",
    default="main",
    show_default=True,
    help="Branch to protect (the trunk).",
)
@click.option(
    "--check",
    "contexts",
    multiple=True,
    metavar="CONTEXT",
    help=(
        "Required status-check context name (repeatable; replaces the default "
        "entirely). Default: the consolidated ci.yml job check-runs — 'gate', "
        "'tests (3.10)', 'tests (3.11)', 'tests (3.12)', 'tests (3.13)', "
        "'site-build', 'ai-techwriter' (these are ci.yml's job names + matrix "
        "legs). A context MUST match a real GitHub check-run name EXACTLY and "
        "must NOT be a path-filtered workflow's check (it would not run on every "
        "PR, which stalls PRs under strict checks)."
    ),
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the exact `gh api` call + payload without invoking GitHub.",
)
def setup_branch_protection(
    *,
    repo_slug: str,
    branch: str,
    contexts: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Configure trunk-based branch protection on ``main`` via ``gh api`` (BDL-049).

    Idempotently sets `main` (or ``--branch``) protection so the trunk-based flow
    is enforced: a PR is required (no direct push), the consolidated ``ci.yml``
    checks (``gate`` / ``tests (3.10..3.13)`` / ``site-build`` /
    ``ai-techwriter`` — ci.yml's job names + matrix legs) are REQUIRED status
    checks, ``enforce_admins: true`` + 0 required reviews so the owner is never
    locked out (can self-merge). Safe to re-run (a declarative PUT).
    ``--dry-run`` documents the exact call without touching GitHub.

    Required check contexts must match real GitHub check-run names EXACTLY and
    must NOT be path-filtered workflow checks (they would not run on every PR, so
    under ``strict`` the PR/``main`` would never become mergeable). Override the
    default with repeatable ``--check``.
    """
    from beadloom.onboarding.branch_protection import (
        DEFAULT_STATUS_CHECK_CONTEXTS,
        BranchProtectionRequest,
        apply_branch_protection,
    )

    if "/" not in repo_slug or repo_slug.count("/") != 1 or repo_slug.startswith("/"):
        raise click.BadParameter("--repo must be OWNER/NAME (e.g. acme/widget).")
    owner, repo = repo_slug.split("/", 1)
    if not owner or not repo:
        raise click.BadParameter("--repo must be OWNER/NAME (e.g. acme/widget).")
    check_contexts = contexts or DEFAULT_STATUS_CHECK_CONTEXTS

    if dry_run:
        request = BranchProtectionRequest(
            owner=owner,
            repo=repo,
            branch=branch,
            status_check_contexts=tuple(check_contexts),
        )
        click.echo("gh " + " ".join(request.gh_args()))
        click.echo("--- payload (stdin) ---")
        click.echo(request.payload_json())
        return

    apply_branch_protection(
        owner,
        repo,
        branch=branch,
        status_check_contexts=tuple(check_contexts),
    )
    click.echo(
        f"Protected {owner}/{repo}@{branch}: PR required, "
        f"{', '.join(check_contexts)} a required check, owner still mergeable."
    )


# beadloom:domain=onboarding
@main.command("config-check")
@click.option(
    "--fix",
    is_flag=True,
    default=False,
    help="Regenerate drifted agent-config artifacts, then re-check.",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def config_check(*, fix: bool, project: Path | None) -> None:
    """Check that generated agent-config is in sync with the graph.

    Regenerates AGENTS.md + the auto-managed sections of CLAUDE.md + IDE
    adapters in memory and diffs them against disk.  Exits 1 on drift,
    0 when clean.  With --fix, regenerates via ``setup-rules --refresh``
    and re-checks.
    """
    from beadloom.infrastructure.db import open_db
    from beadloom.onboarding import check_config_drift
    from beadloom.onboarding.scanner import generate_agents_md, refresh_claude_md

    project_root = project or Path.cwd()

    if fix:
        # Regenerate via the same refresh path used by `setup-rules --refresh`.
        refresh_claude_md(project_root)
        generate_agents_md(project_root)
        from beadloom.onboarding.scanner import setup_rules_auto

        setup_rules_auto(project_root)

        # Re-drop drifted agentic-flow files (only if the flow is scaffolded —
        # never force the flow onto a repo that did not adopt it). Restores the
        # vendored agents/commands; CLAUDE.md regions are already refreshed
        # above, so user prose outside the auto-regions is preserved.
        from beadloom.onboarding.config_sync import (
            refresh_agentic_flow_files,
            refresh_composed_adapters,
        )

        refresh_agentic_flow_files(project_root)
        # Recompose the per-tool role adapters from .beadloom/flow.yml (no-op
        # when flow.yml is absent/invalid). The composer owns .claude/agents/*
        # + .cursor/agents/* once a flow.yml exists.
        refresh_composed_adapters(project_root)

    db_path = project_root / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    try:
        drifts = check_config_drift(project_root, conn)
    finally:
        conn.close()

    if not drifts:
        click.echo("Agent-config in sync — no drift.")
        return

    click.echo(f"Agent-config drift detected ({len(drifts)}):", err=True)
    for drift in drifts:
        click.echo(f"  - {drift.file}: {drift.reason}", err=True)
    click.echo(
        "  Run `beadloom setup-rules --refresh` (or `config-check --fix`) to fix.",
        err=True,
    )
    raise SystemExit(1)


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

    from beadloom.services.mcp_server import create_server

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
@main.group()
def docs() -> None:
    """Documentation generation and management."""


@docs.command("generate")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def docs_generate(*, project: Path | None) -> None:
    """Generate doc skeletons from the architecture graph."""
    from beadloom.onboarding.doc_generator import generate_skeletons

    project_root = project or Path.cwd()
    result = generate_skeletons(project_root)
    click.echo(
        f"Created {result['files_created']} files, skipped {result['files_skipped']} existing"
    )


@docs.command("polish")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--ref-id",
    default=None,
    help="Polish specific node docs only.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
def docs_polish(
    *,
    project: Path | None,
    ref_id: str | None,
    fmt: str,
) -> None:
    """Output structured data for AI agent to enrich documentation."""
    from beadloom.onboarding.doc_generator import format_polish_text, generate_polish_data

    project_root = project or Path.cwd()
    data = generate_polish_data(project_root, ref_id=ref_id)
    if fmt == "json":
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(format_polish_text(data))


# beadloom:domain=application
@docs.command("site")
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Output directory for the generated site tree (default: site/).",
)
@click.option(
    "--federated",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="A federated.json for the landscape map (consumed by a later showcase).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def docs_site(
    *,
    out_dir: Path | None,
    federated: Path | None,
    project: Path | None,
) -> None:
    """Generate a VitePress content tree from the architecture graph.

    Reads the indexed graph read-only and emits an architecture overview,
    one page per node (with summary, symbols, edges-as-links, and an embedded
    C4/Mermaid diagram), and the VitePress nav/sidebar config — under --out
    (default site/). Never writes into the source docs/ tree.
    """
    from beadloom.application.site import generate_site
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    out = out_dir if out_dir is not None else project_root / "site"
    conn = open_db(db_path)
    try:
        result = generate_site(conn, out, project_root=project_root, federated=federated)
    finally:
        conn.close()
    click.echo(f"Generated {len(result.written)} files under {out}")


# beadloom:feature=docs-audit
@docs.command("audit")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option("--stale-only", is_flag=True, help="Show only stale mentions.")
@click.option("--verbose", "verbose_flag", is_flag=True, help="Show fresh and unmatched too.")
@click.option(
    "--path",
    "scan_paths",
    multiple=True,
    help="Custom scan paths (glob patterns).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--fail-if",
    "fail_if_expr",
    type=str,
    default=None,
    help="Exit non-zero when condition met (e.g., stale>0, stale>5).",
)
def docs_audit(
    *,
    output_json: bool,
    stale_only: bool,
    verbose_flag: bool,
    scan_paths: tuple[str, ...],
    project: Path | None,
    fail_if_expr: str | None,
) -> None:
    """Detect stale facts in project documentation."""
    from beadloom.doc_sync.audit import parse_fail_condition, run_audit
    from beadloom.infrastructure.db import open_db

    # Validate --fail-if early (before doing any work)
    fail_condition: tuple[str, str, int] | None = None
    if fail_if_expr is not None:
        fail_condition = parse_fail_condition(fail_if_expr)

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    try:
        result = run_audit(
            project_root,
            conn,
            scan_paths=list(scan_paths) if scan_paths else None,
        )
    finally:
        conn.close()

    stale = [f for f in result.findings if f.status == "stale"]
    fresh = [f for f in result.findings if f.status == "fresh"]

    if output_json:
        _docs_audit_json(result, stale, fresh, fail_condition=fail_condition)
    else:
        _docs_audit_rich(
            result,
            stale,
            fresh,
            stale_only=stale_only,
            verbose=verbose_flag,
            project_root=project_root,
        )

    # CI gate check (after output so user sees results)
    if fail_condition is not None:
        metric, op, threshold = fail_condition
        if metric == "stale":
            stale_count = len(stale)
            should_fail = (op == ">" and stale_count > threshold) or (
                op == ">=" and stale_count >= threshold
            )
            if should_fail:
                click.echo(
                    f"CI gate triggered: {stale_count} stale mention(s) "
                    f"(threshold: {metric}{op}{threshold})",
                    err=True,
                )
                sys.exit(1)


def _docs_audit_json(
    result: object,
    stale: Sequence[object],
    fresh: Sequence[object],
    *,
    fail_condition: tuple[str, str, int] | None = None,
) -> None:
    """Emit docs audit results as JSON."""
    from beadloom.doc_sync.audit import AuditFinding, AuditResult

    assert isinstance(result, AuditResult)

    facts_out: dict[str, dict[str, str | int]] = {}
    for name, fact in result.facts.items():
        facts_out[name] = {"value": fact.value, "source": fact.source}

    stale_out: list[dict[str, str | int]] = []
    for finding in stale:
        assert isinstance(finding, AuditFinding)
        stale_out.append(
            {
                "file": str(finding.mention.file.name),
                "line": finding.mention.line,
                "fact": finding.mention.fact_name,
                "mentioned": str(finding.mention.value),
                "actual": str(finding.fact.value),
            }
        )

    fresh_out: list[dict[str, str | int | float]] = []
    for finding in fresh:
        assert isinstance(finding, AuditFinding)
        fresh_out.append(
            {
                "file": str(finding.mention.file.name),
                "line": finding.mention.line,
                "fact": finding.mention.fact_name,
                "mentioned": str(finding.mention.value),
                "tolerance": finding.tolerance,
            }
        )

    unmatched_out: list[dict[str, str | int]] = []
    for mention in result.unmatched:
        unmatched_out.append(
            {
                "file": str(mention.file.name),
                "line": mention.line,
                "value": str(mention.value),
                "context": mention.context,
            }
        )

    data: dict[str, object] = {
        "facts": facts_out,
        "stale": stale_out,
        "fresh": fresh_out,
        "unmatched": unmatched_out,
        "summary": {
            "stale_count": len(stale_out),
            "fresh_count": len(fresh_out),
            "unmatched_count": len(unmatched_out),
        },
    }

    if fail_condition is not None:
        metric, op, threshold = fail_condition
        stale_count = len(stale_out)
        triggered = (op == ">" and stale_count > threshold) or (
            op == ">=" and stale_count >= threshold
        )
        data["ci_gate"] = {
            "expression": f"{metric}{op}{threshold}",
            "stale_count": stale_count,
            "threshold": threshold,
            "triggered": triggered,
        }

    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def _format_tolerance(tolerance: float) -> str:
    """Format tolerance for CLI display.

    Returns ``"OK"`` for exact match (0.0) or ``"OK (tolerance: +/-N%)"``
    for non-zero tolerance.
    """
    if tolerance <= 0.0:
        return "OK"
    pct = int(tolerance * 100)
    return f"OK (tolerance: \u00b1{pct}%)"


def _docs_audit_rich(
    result: object,
    stale: Sequence[object],
    fresh: Sequence[object],
    *,
    stale_only: bool,
    verbose: bool,
    project_root: Path | None = None,
) -> None:
    """Emit docs audit results with Rich formatting."""
    from rich.console import Console

    from beadloom.doc_sync.audit import AuditFinding, AuditResult

    assert isinstance(result, AuditResult)

    _root = (project_root or Path.cwd()).resolve()

    def _rel_path(file_path: Path) -> str:
        """Return path relative to project root, falling back to name."""
        try:
            return str(file_path.relative_to(_root))
        except ValueError:
            return str(file_path.name)

    console = Console()

    # Title
    console.print()
    console.print("Documentation Audit", style="bold")
    console.print("[bold]" + "=" * 50 + "[/bold]")
    console.print()

    # Fact labels that need disambiguation suffixes
    _fact_suffixes: dict[str, str] = {
        "test_count": " (symbols)",
    }

    # Ground Truth
    console.print("[bold]Ground Truth[/bold] (from project state)")
    for name, fact in sorted(result.facts.items()):
        label = name.replace("_", " ") + _fact_suffixes.get(name, "")
        console.print(f"  {label}: [cyan]{fact.value}[/cyan]")
    console.print()

    # Stale Mentions
    if stale:
        console.print("[bold red]Stale Mentions[/bold red]")
        console.print("[dim]" + "-" * 50 + "[/dim]")
        stale_files: set[str] = set()
        for finding in stale:
            assert isinstance(finding, AuditFinding)
            fname = _rel_path(finding.mention.file)
            stale_files.add(fname)
            console.print(
                f"  {fname}:{finding.mention.line:<12}"
                f" {finding.mention.fact_name:<16}"
                f' [red]"{finding.mention.value}"[/red]'
                f" -> {finding.fact.value}"
            )
        console.print()
        console.print(
            f"  [bold red]{len(stale)} stale mention(s) across"
            f" {len(stale_files)} file(s)[/bold red]"
        )
        console.print()
    else:
        console.print("[green]No stale mentions found.[/green]")
        console.print()

    # Fresh (verified)
    if not stale_only and fresh:
        console.print("[bold green]Fresh (verified)[/bold green]")
        console.print("[dim]" + "-" * 50 + "[/dim]")
        for finding in fresh:
            assert isinstance(finding, AuditFinding)
            fname = _rel_path(finding.mention.file)
            tol_label = _format_tolerance(finding.tolerance)
            console.print(
                f"  {fname}:{finding.mention.line:<12}"
                f" {finding.mention.fact_name:<16}"
                f' [green]"{finding.mention.value}"[/green]'
                f" [green]{tol_label}[/green]"
            )
        console.print()
        console.print(f"  [green]{len(fresh)} verified mention(s)[/green]")
        console.print()

    # Unmatched (only in verbose mode)
    if verbose and result.unmatched:
        console.print("[dim]Unmatched Numbers (ignored)[/dim]")
        console.print("[dim]" + "-" * 50 + "[/dim]")
        for mention in result.unmatched:
            fname = _rel_path(mention.file)
            console.print(
                f"  [dim]{fname}:{mention.line:<12}"
                f' "{mention.value}" -- no keyword match (skipped)[/dim]'
            )
        console.print()


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
    "--mode",
    "init_mode",
    type=click.Choice(["bootstrap", "import", "both"]),
    default=None,
    help="Init mode for non-interactive usage.",
)
@click.option(
    "--yes",
    "-y",
    "non_interactive",
    is_flag=True,
    help="Non-interactive mode: no prompts, use defaults.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing .beadloom/ directory.",
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
    init_mode: str | None,
    non_interactive: bool,
    force: bool,
    project: Path | None,
) -> None:
    """Initialize beadloom in a project."""
    from beadloom.onboarding import bootstrap_project, import_docs

    project_root = project or Path.cwd()

    # Non-interactive mode: --yes / -y flag.
    if non_interactive:
        from beadloom.onboarding.scanner import non_interactive_init

        mode = init_mode or "bootstrap"
        result = non_interactive_init(project_root, mode=mode, force=force)

        if result["mode"] == "skipped":
            click.echo("Warning: .beadloom/ already exists. Use --force to overwrite.")
            return

        # Print summary for non-interactive mode.
        click.echo(f"Initialized beadloom (mode: {result['mode']})")
        if "bootstrap" in result:
            bs = result["bootstrap"]
            click.echo(
                f"  Graph: {bs['nodes_generated']} nodes, "
                f"{bs['edges_generated']} edges (preset: {bs['preset']})"
            )
        if result.get("reindex"):
            ri = result["reindex"]
            click.echo(f"  Index: {ri['symbols']} symbols, {ri['imports']} imports")
        if result.get("import"):
            click.echo(f"  Imported: {len(result['import'])} documents")
        return

    if bootstrap:
        result = bootstrap_project(project_root, preset_name=preset)

        # Generate doc skeletons.
        from beadloom.onboarding.doc_generator import generate_skeletons

        docs_result = generate_skeletons(project_root, result["nodes"], result["edges"])

        # Auto-reindex to populate import analysis and depends_on edges.
        from beadloom.application.reindex import reindex as do_reindex

        ri = do_reindex(project_root)

        # Count dependency edges from DB.
        dep_count = 0
        if ri.imports_indexed > 0:
            from beadloom.infrastructure.db import open_db

            db_path = project_root / ".beadloom" / "beadloom.db"
            conn = open_db(db_path)
            dep_count = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE kind = 'depends_on'"
            ).fetchone()[0]
            conn.close()

        # Print summary.
        click.echo("")
        click.echo(
            f"\u2713 Graph: {result['nodes_generated']} nodes, "
            f"{result['edges_generated']} edges (preset: {result['preset']})"
        )
        if result.get("rules_generated", 0) > 0:
            click.echo(
                f"\u2713 Rules: {result['rules_generated']} rules in .beadloom/_graph/rules.yml"
            )
        if docs_result["files_skipped"] > 0:
            click.echo(
                f"\u2713 Docs: {docs_result['files_created']} skeletons created, "
                f"{docs_result['files_skipped']} skipped (pre-existing)"
            )
        else:
            click.echo(f"\u2713 Docs: {docs_result['files_created']} skeletons created")
        if result.get("mcp_editor"):
            click.echo(
                f"\u2713 MCP: configured for {result['mcp_editor']} "
                f"({_mcp_path_for_editor(result['mcp_editor'], project_root)})"
            )
        if result.get("rules_files"):
            for rf in result["rules_files"]:
                click.echo(f"\u2713 IDE rules: {rf}")
        click.echo(
            f"\u2713 Index: {ri.symbols_indexed} symbols, "
            f"{ri.imports_indexed} imports"
            + (f", {dep_count} dependency edges" if dep_count else "")
        )

        # Warn about missing language parsers when symbols == 0.
        if ri.symbols_indexed == 0:
            _warn_missing_parsers(project_root)

        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. Review docs/ and .beadloom/_graph/services.yml")
        click.echo("  2. Run 'beadloom lint' to validate architecture")
        click.echo("  3. Run 'beadloom docs polish' with your AI agent for richer docs")
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


# beadloom:domain=tui
def _launch_tui(*, project: Path | None, no_watch: bool) -> None:
    """Shared implementation for tui/ui commands."""
    try:
        from beadloom.tui import launch
    except ImportError:
        click.echo(
            "Error: TUI requires 'textual'. Install with: pip install beadloom[tui]",
            err=True,
        )
        sys.exit(1)

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    try:
        launch(db_path=db_path, project_root=project_root, no_watch=no_watch)
    except ImportError:
        click.echo(
            "Error: TUI requires 'textual'. Install with: pip install beadloom[tui]",
            err=True,
        )
        sys.exit(1)


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--no-watch",
    is_flag=True,
    default=False,
    help="Disable file watcher.",
)
def tui(*, project: Path | None, no_watch: bool) -> None:
    """Launch interactive terminal dashboard.

    Multi-screen architecture workstation with graph explorer,
    debt gauge, lint panel, doc status, and keyboard actions.
    Requires textual: pip install beadloom[tui]
    """
    _launch_tui(project=project, no_watch=no_watch)


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--no-watch",
    is_flag=True,
    default=False,
    help="Disable file watcher.",
)
def ui(*, project: Path | None, no_watch: bool) -> None:
    """Launch interactive terminal dashboard (alias for 'tui').

    Browse domains, nodes, edges, and documentation coverage.
    Requires textual: pip install beadloom[tui]
    """
    _launch_tui(project=project, no_watch=no_watch)


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
        from beadloom.application.watcher import watch
    except ImportError:
        click.echo(
            "Error: watch requires 'watchfiles'. Install with: pip install beadloom[watch]",
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
            "Error: watch requires 'watchfiles'. Install with: pip install beadloom[watch]",
            err=True,
        )
        sys.exit(1)


# beadloom:domain=context-oracle
@main.command()
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "json", "porcelain", "github"]),
    default=None,
    help="Output format (default: rich if TTY, porcelain if piped). "
    "'github' emits GitHub Actions ::error annotations.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit 1 if error-level violations found (warnings OK).",
)
@click.option(
    "--fail-on-warn",
    is_flag=True,
    default=False,
    help="Exit 1 on any violation including warnings.",
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
    fail_on_warn: bool,
    no_reindex: bool,
    project: Path | None,
) -> None:
    """Run architecture lint rules against the project.

    Checks cross-boundary imports against rules defined in rules.yml.
    Exit codes: 0 = clean or violations below threshold,
    1 = violations with --strict (errors only) or --fail-on-warn (any),
    2 = configuration error.
    """
    from beadloom.graph.linter import LintError
    from beadloom.graph.linter import format_github as _format_github
    from beadloom.graph.linter import format_json as _format_json
    from beadloom.graph.linter import format_porcelain as _format_porcelain
    from beadloom.graph.linter import format_rich as _format_rich
    from beadloom.graph.linter import lint as run_lint

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
        "github": _format_github,
    }
    output = formatters[fmt](result)
    if output:
        click.echo(output)
    elif not result.violations:
        click.echo(f"0 violations, {result.rules_evaluated} rules evaluated")

    if fail_on_warn and result.violations:
        sys.exit(1)
    if strict and result.has_errors:
        sys.exit(1)


# beadloom:domain=application
@main.command()
@click.option(
    "--hub",
    "hub",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Satellite export artifact(s); when given, run the federate landscape gate.",
)
@click.option(
    "--fail-on",
    "fail_on",
    is_flag=False,
    flag_value="default",
    default=None,
    help=(
        "Federate fail-set (comma-separated, case-insensitive). A bare --fail-on "
        "or 'default' uses breaking,drift,orphaned_consumer,undeclared_producer; "
        "no-false-gate verdicts are rejected. Only used with --hub."
    ),
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["rich", "json", "github"]),
    default=None,
    help="Output format (default: rich if TTY, github otherwise).",
)
@click.option(
    "--no-reindex",
    is_flag=True,
    default=False,
    help="Skip the reindex step (caller reindexes separately).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def ci(
    *,
    hub: tuple[Path, ...],
    fail_on: str | None,
    fmt: str | None,
    no_reindex: bool,
    project: Path | None,
) -> None:
    """Run the unified CI gate (reindex -> lint -> sync-check -> config-check -> federate).

    Composes the existing checkers into one verdict with a single exit code:
    0 when every step passed, 1 when any step failed. The output names EVERY
    step that ran and its honest result (PASS/FAIL/SKIP) — never a green that
    silently skipped a step. ``--format`` applies uniformly across all steps
    (findings share the agent-actionable {kind, rule, severity, locations, why,
    remediation} shape). With ``--hub`` the cross-service landscape gate runs.
    """
    from beadloom.application.gate import run_ci_gate

    project_root = project or Path.cwd()
    fail_set = _parse_fail_on(fail_on) if fail_on is not None else None

    if fmt is None:
        fmt = "rich" if sys.stdout.isatty() else "github"

    result = run_ci_gate(
        project_root,
        fail_on=fail_set,
        hub_exports=list(hub),
        no_reindex=no_reindex,
    )

    output = _format_gate(result, fmt)
    if output:
        click.echo(output)

    if not result.ok:
        sys.exit(1)


def _format_gate(result: GateResult, fmt: str) -> str:
    """Render a :class:`GateResult` in the requested uniform format."""
    if fmt == "json":
        return _format_gate_json(result)
    if fmt == "github":
        return _format_gate_github(result)
    return _format_gate_rich(result)


def _format_gate_rich(result: GateResult) -> str:
    """Human report: one honest line per step, then findings, then the verdict."""
    lines: list[str] = ["Beadloom CI gate", ""]
    for step in result.steps:
        lines.append(f"  [{step.status}] {step.name}: {step.summary}")
    findings = result.findings
    if findings:
        lines.append("")
        for f in findings:
            loc = _finding_location(f)
            prefix = f"{loc}: " if loc else ""
            lines.append(f"  - {prefix}{f.get('why', '')}")
            remediation = f.get("remediation")
            if remediation:
                lines.append(f"      fix: {remediation}")
    lines.append("")
    lines.append("PASS — gate clean" if result.ok else "FAIL — gate blocked")
    return "\n".join(lines)


def _format_gate_json(result: GateResult) -> str:
    """Structured JSON: ``ok`` + per-step status + shared-shape findings."""
    steps = [
        {
            "name": step.name,
            "status": step.status,
            "passed": step.passed,
            "skipped": step.skipped,
            "summary": step.summary,
            "findings": step.findings,
        }
        for step in result.steps
    ]
    return json.dumps({"ok": result.ok, "steps": steps}, indent=2)


def _format_gate_github(result: GateResult) -> str:
    """GitHub Actions annotations — one ::error per finding + a step summary.

    Emits the valid workflow-command shape ``::error file=<path>,line=<n>::<msg>``
    (matching ``beadloom lint --format github`` / ``linter.format_github``). The
    ``file``/``line`` parameters are comma-separated key=value pairs, NOT a
    ``file=<path:line>`` colon-joined string (which GitHub does not parse).
    """
    lines: list[str] = []
    for step in result.steps:
        lines.append(f"::notice::{step.name} {step.status}: {step.summary}")
    for f in result.findings:
        level = "error" if f.get("severity") == "error" else "warning"
        param = _finding_github_params(f)
        msg = f"{f.get('rule', '')}: {f.get('why', '')}"
        remediation = f.get("remediation")
        if remediation:
            msg += f" — {remediation}"
        msg = msg.replace("\r\n", "%0A").replace("\n", "%0A").replace("\r", "%0A")
        lines.append(f"::{level}{param}::{msg}")
    return "\n".join(lines)


def _finding_github_params(finding: dict[str, object]) -> str:
    """GitHub annotation parameter string: `` file=<path>,line=<n>`` or ``''``.

    Reads the finding's first location ``{file, line}`` and renders the
    workflow-command parameter shape (leading space, comma-separated). Returns
    an empty string for graph-level findings with no file location.
    """
    locations = finding.get("locations")
    if not isinstance(locations, list) or not locations:
        return ""
    first = locations[0]
    if not isinstance(first, dict):
        return ""
    file = first.get("file")
    if not isinstance(file, str) or not file:
        return ""
    params = [f"file={file}"]
    line = first.get("line")
    if isinstance(line, int):
        params.append(f"line={line}")
    return " " + ",".join(params)


def _finding_location(finding: dict[str, object]) -> str:
    """Extract ``file[:line]`` from a finding's first location, or empty string.

    Used by the human-readable (rich) gate report only; GitHub annotations use
    :func:`_finding_github_params` for the correct ``file=,line=`` shape.
    """
    locations = finding.get("locations")
    if not isinstance(locations, list) or not locations:
        return ""
    first = locations[0]
    if not isinstance(first, dict):
        return ""
    file = first.get("file")
    if not isinstance(file, str):
        return ""
    line = first.get("line")
    return f"{file}:{line}" if isinstance(line, int) else file


# beadloom:domain=graph-snapshot
@main.group()
def snapshot() -> None:
    """Architecture snapshot management."""


@snapshot.command("save")
@click.option("--label", default=None, help="Optional label for the snapshot (e.g. v1.6.0).")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def snapshot_save(*, label: str | None, project: Path | None) -> None:
    """Save the current graph state as a snapshot."""
    from beadloom.graph.snapshot import save_snapshot
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    snap_id = save_snapshot(conn, label=label)
    conn.close()

    label_str = f" ({label})" if label else ""
    click.echo(f"Snapshot #{snap_id} saved{label_str}.")


@snapshot.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def snapshot_list(*, output_json: bool, project: Path | None) -> None:
    """List all saved architecture snapshots."""
    from beadloom.graph.snapshot import list_snapshots
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    snapshots = list_snapshots(conn)
    conn.close()

    if not snapshots:
        click.echo("No snapshots found.")
        return

    if output_json:
        data = [
            {
                "id": s.id,
                "label": s.label,
                "created_at": s.created_at,
                "node_count": s.node_count,
                "edge_count": s.edge_count,
                "symbols_count": s.symbols_count,
            }
            for s in snapshots
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for s in snapshots:
            label_str = f" [{s.label}]" if s.label else ""
            click.echo(
                f"  #{s.id}{label_str}  {s.created_at}  "
                f"nodes={s.node_count} edges={s.edge_count} symbols={s.symbols_count}"
            )


@snapshot.command("compare")
@click.argument("old_id", type=int)
@click.argument("new_id", type=int)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def snapshot_compare(
    old_id: int,
    new_id: int,
    *,
    output_json: bool,
    project: Path | None,
) -> None:
    """Compare two architecture snapshots."""
    from beadloom.graph.snapshot import compare_snapshots
    from beadloom.infrastructure.db import open_db

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    conn = open_db(db_path)
    try:
        diff = compare_snapshots(conn, old_id, new_id)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        conn.close()
        sys.exit(1)

    conn.close()

    if output_json:
        data = {
            "old_id": diff.old_id,
            "new_id": diff.new_id,
            "has_changes": diff.has_changes,
            "added_nodes": diff.added_nodes,
            "removed_nodes": diff.removed_nodes,
            "changed_nodes": diff.changed_nodes,
            "added_edges": diff.added_edges,
            "removed_edges": diff.removed_edges,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not diff.has_changes:
        click.echo(f"No changes between snapshot #{old_id} and #{new_id}.")
        return

    click.echo(f"Snapshot diff: #{old_id} -> #{new_id}")
    click.echo()

    if diff.added_nodes:
        click.echo("Added nodes:")
        for n in diff.added_nodes:
            click.echo(f"  + {n['ref_id']} ({n.get('kind', '')}): {n.get('summary', '')}")

    if diff.removed_nodes:
        click.echo("Removed nodes:")
        for n in diff.removed_nodes:
            click.echo(f"  - {n['ref_id']} ({n.get('kind', '')}): {n.get('summary', '')}")

    if diff.changed_nodes:
        click.echo("Changed nodes:")
        for n in diff.changed_nodes:
            click.echo(f"  ~ {n['ref_id']} ({n.get('kind', '')})")
            click.echo(f"    was: {n.get('old_summary', '')}")
            click.echo(f"    now: {n.get('new_summary', '')}")

    if diff.added_edges:
        click.echo("Added edges:")
        for e in diff.added_edges:
            click.echo(f"  + {e['src_ref_id']} --[{e['kind']}]--> {e['dst_ref_id']}")

    if diff.removed_edges:
        click.echo("Removed edges:")
        for e in diff.removed_edges:
            click.echo(f"  - {e['src_ref_id']} --[{e['kind']}]--> {e['dst_ref_id']}")
