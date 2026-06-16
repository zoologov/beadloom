"""The ``status`` command — presentation of index/health stats (logic in application.status)."""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import click

from beadloom.services.commands._root import main


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
    from beadloom.infrastructure.db import open_db

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

    # --- Normal mode: gather the read payload from the application layer ---
    from beadloom.application.status import gather_status

    data = gather_status(conn, project_root)
    conn.close()

    if output_json:
        click.echo(json.dumps(_status_json(data), ensure_ascii=False, indent=2))
        return

    _render_status(data)


def _status_json(data: object) -> dict[str, object]:
    """Build the ``status --json`` payload from gathered :class:`StatusData`."""
    from beadloom.application.status import StatusData

    assert isinstance(data, StatusData)
    return {
        "version": data.version,
        "last_reindex": data.last_reindex,
        "nodes_count": data.nodes_count,
        "edges_count": data.edges_count,
        "docs_count": data.docs_count,
        "chunks_count": data.chunks_count,
        "symbols_count": data.symbols_count,
        "coverage_pct": round(data.coverage_pct, 1),
        "covered_count": data.covered,
        "stale_count": data.stale_count,
        "isolated_count": data.isolated_count,
        "empty_summaries": data.empty_summaries,
        "by_kind": {kr["kind"]: kr["cnt"] for kr in data.kind_rows},
        "trends": data.trends,
        "context_metrics": data.context_metrics,
    }


def _render_status(data: object) -> None:
    """Render gathered :class:`StatusData` as the Rich status dashboard."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    from beadloom.application.status import StatusData

    assert isinstance(data, StatusData)

    nodes_count = data.nodes_count
    coverage_pct = data.coverage_pct
    trends = data.trends
    kind_rows = data.kind_rows
    kind_total = data.kind_total
    kind_covered = data.kind_covered
    context_metrics = data.context_metrics

    console = Console()

    # Header panel.
    console.print(
        Panel(
            f"Last reindex: {data.last_reindex}",
            title=f"Beadloom v{data.version}",
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
        f"Edges: [bold]{data.edges_count}[/] {t_edges}   "
        f"Docs: [bold]{data.docs_count}[/] {t_docs}   "
        f"Symbols: [bold]{data.symbols_count}[/]"
    )
    console.print()

    # Two-column layout: By Kind + Doc Coverage.
    kind_table = Table(title="By Kind", show_header=False, box=None, padding=(0, 1))
    kind_table.add_column("kind", style="cyan")
    kind_table.add_column("count", justify="right")
    for kr in kind_rows:
        kind_table.add_row(str(kr["kind"]), str(kr["cnt"]))

    cov_table = Table(title="Doc Coverage", show_header=False, box=None, padding=(0, 1))
    cov_table.add_column("scope", style="cyan")
    cov_table.add_column("coverage", justify="right")
    cov_table.add_column("trend")

    cov_trend = trends.get("coverage_pct", "")
    cov_table.add_row(
        "Overall",
        f"{data.covered}/{nodes_count} ({coverage_pct:.0f}%)",
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
    health_table.add_row("Stale docs", str(data.stale_count), stale_trend)
    health_table.add_row("Isolated nodes", str(data.isolated_count), iso_trend)
    health_table.add_row("Empty summaries", str(data.empty_summaries), "")
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
