"""Federation + gate commands: export, federate, lint, ci (+ gate formatters)."""
# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from beadloom.application.gate import GateResult
    from beadloom.graph.federation import GateFailure

from beadloom import __version__
from beadloom.services.commands._root import main


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
def federate(*, exports: tuple[Path, ...], project: Path | None, fail_on: str | None) -> None:
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
    from beadloom.application.reindex import incremental_reindex
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

    # The reindex-before-lint is a services-layer orchestration concern: the CLI
    # injects the application reindex so the graph-layer linter stays pure.
    reindex_cb = None if no_reindex else incremental_reindex

    try:
        result = run_lint(project_root, reindex=reindex_cb)
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
