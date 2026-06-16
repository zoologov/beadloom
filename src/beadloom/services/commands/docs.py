"""The ``docs`` command group: generate, polish, site, audit."""
# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Sequence

from beadloom.services.commands._root import main


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
    from beadloom.infrastructure.db import connection

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    out = out_dir if out_dir is not None else project_root / "site"
    with connection(db_path) as conn:
        result = generate_site(conn, out, project_root=project_root, federated=federated)
    click.echo(f"Generated {len(result.written)} files under {out}")


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
    from beadloom.infrastructure.db import connection

    # Validate --fail-if early (before doing any work)
    fail_condition: tuple[str, str, int] | None = None
    if fail_if_expr is not None:
        fail_condition = parse_fail_condition(fail_if_expr)

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    with connection(db_path) as conn:
        result = run_audit(
            project_root,
            conn,
            scan_paths=list(scan_paths) if scan_paths else None,
        )

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
