"""Showcase A — the AaC/DocAsCode metrics dashboard (BDL-040 BEAD-02).

Builds the dashboard *data* — a deterministic, JSON-safe dict — and renders the
human ``dashboard.md`` page. Every number is produced by the SAME code path as
its CLI gate, so the site can never publish a figure the gate would contradict
(honest by construction):

- **lint** — :func:`beadloom.graph.linter.lint` (count + severity breakdown).
- **debt** — :func:`beadloom.application.debt_report.compute_debt_score`
  (+ ``compute_debt_trend`` when a snapshot exists), serialized via
  ``format_debt_json`` — the exact ``status --debt-report --json`` shape.
- **docs** — coverage % + ``sync_state`` freshness % + stale count (the persisted
  result of the last ``sync-check``; read-only, never re-mutating the DB).
- **doctor** — :func:`beadloom.application.doctor.run_checks` pass/fail summary.
- **federated** — when a ``federated.json`` (``federate`` output) is given:
  per-service edge-verdict health + contract-verdict counts.

The ``.data.json`` is the single source for any VitePress widget — numbers are
computed here in Python; the front-end never invents a figure. Output is
deterministic (sorted keys, no wall-clock).
"""

# beadloom:domain=application

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from beadloom.application.debt_report import (
    collect_debt_data,
    compute_debt_score,
    compute_debt_trend,
    format_debt_json,
    load_debt_weights,
)
from beadloom.application.doctor import Severity, run_checks
from beadloom.graph.linter import lint

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)

# Edge/contract verdicts treated as unhealthy (a real, actionable cross-repo
# problem) — drives the per-service ``healthy`` flag in the federated rollup.
_UNHEALTHY_VERDICTS = frozenset({"drift", "breaking"})


def _lint_metrics(project_root: Path) -> dict[str, object]:
    """Lint count + severity breakdown via the exact ``beadloom lint`` path.

    Reindex is skipped (``reindex_before=False``): the dashboard runs over the
    already-indexed DB and must not mutate it, matching the gate's verdict on
    the current index.
    """
    result = lint(project_root, reindex_before=False)
    by_severity: dict[str, int] = {}
    for violation in result.violations:
        by_severity[violation.severity] = by_severity.get(violation.severity, 0) + 1
    # Stable keys so the diffed output is byte-identical run to run.
    by_severity.setdefault("error", 0)
    by_severity.setdefault("warn", 0)
    return {
        "violations": len(result.violations),
        "errors": result.error_count,
        "warnings": result.warning_count,
        "by_severity": dict(sorted(by_severity.items())),
    }


def _debt_metrics(
    conn: sqlite3.Connection, project_root: Path
) -> dict[str, object]:
    """Debt score/categories/offenders via the exact ``--debt-report`` path."""
    from dataclasses import replace

    weights = load_debt_weights(project_root)
    report = compute_debt_score(collect_debt_data(conn, project_root, weights), weights)
    trend = compute_debt_trend(conn, report, project_root, weights)
    if trend is not None:
        # compute_debt_score always returns trend=None; attach the computed trend.
        report = replace(report, trend=trend)
    return format_debt_json(report)


def _docs_metrics(conn: sqlite3.Connection) -> dict[str, object]:
    """Coverage % + freshness % + stale count from the persisted sync state.

    Reads ``sync_state`` (the output the last ``sync-check`` wrote) read-only —
    the same data the gate reports — never re-running the mutating check.
    """
    nodes = int(conn.execute("SELECT count(*) FROM nodes").fetchone()[0])
    covered = int(
        conn.execute(
            "SELECT count(DISTINCT n.ref_id) FROM nodes n "
            "JOIN docs d ON d.ref_id = n.ref_id"
        ).fetchone()[0]
    )
    total_pairs = int(conn.execute("SELECT count(*) FROM sync_state").fetchone()[0])
    stale = int(
        conn.execute(
            "SELECT count(*) FROM sync_state WHERE status = 'stale'"
        ).fetchone()[0]
    )
    fresh = total_pairs - stale
    coverage_pct = round(covered / nodes * 100.0, 1) if nodes else 0.0
    freshness_pct = round(fresh / total_pairs * 100.0, 1) if total_pairs else 100.0
    return {
        "nodes": nodes,
        "documented": covered,
        "coverage_pct": coverage_pct,
        "tracked_pairs": total_pairs,
        "fresh": fresh,
        "stale": stale,
        "freshness_pct": freshness_pct,
    }


def _doctor_metrics(
    conn: sqlite3.Connection, project_root: Path
) -> dict[str, object]:
    """Integrity pass/fail summary via the exact ``beadloom doctor`` path."""
    checks = run_checks(conn, project_root=project_root)
    by_severity: dict[str, int] = {}
    for check in checks:
        by_severity[check.severity.value] = by_severity.get(check.severity.value, 0) + 1
    errors = sum(1 for c in checks if c.severity is Severity.ERROR)
    warnings = sum(1 for c in checks if c.severity is Severity.WARNING)
    return {
        "total": len(checks),
        "errors": errors,
        "warnings": warnings,
        "passed": errors == 0,
        "by_severity": dict(sorted(by_severity.items())),
    }


def _count_verdicts(items: list[dict[str, object]]) -> dict[str, int]:
    """Count ``verdict`` values across *items*, sorted by verdict for stability."""
    counts: dict[str, int] = {}
    for item in items:
        verdict = str(item.get("verdict", ""))
        if not verdict:
            continue
        counts[verdict] = counts.get(verdict, 0) + 1
    return dict(sorted(counts.items()))


def _federated_metrics(federated: Path) -> dict[str, object] | None:
    """Per-service edge-verdict health + contract-verdict counts.

    Reuses the F2 ``federate`` output verbatim (``edges[].verdict`` /
    ``contracts[].verdict`` / ``repos[]``) — no re-derivation of verdicts.
    """
    try:
        payload = json.loads(federated.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Could not read federated artifact %s", federated)
        return None
    if not isinstance(payload, dict):
        return None

    raw_edges = payload.get("edges", [])
    raw_repos = payload.get("repos", [])
    raw_contracts = payload.get("contracts", [])
    edges = [e for e in raw_edges if isinstance(e, dict)]
    repos = [r for r in raw_repos if isinstance(r, dict)]
    contracts = [c for c in raw_contracts if isinstance(c, dict)]

    # Group edge verdicts per producing repo.
    per_repo: dict[str, list[dict[str, object]]] = {}
    for edge in edges:
        repo = str(edge.get("repo", ""))
        per_repo.setdefault(repo, []).append(edge)

    known_repos = {str(r.get("repo", "")) for r in repos if r.get("repo")}
    all_repos = sorted(known_repos | {r for r in per_repo if r})

    services: list[dict[str, object]] = []
    for repo in all_repos:
        verdicts = _count_verdicts(per_repo.get(repo, []))
        healthy = not any(v in _UNHEALTHY_VERDICTS for v in verdicts)
        services.append({"repo": repo, "verdicts": verdicts, "healthy": healthy})

    return {
        "repo_count": len(repos),
        "edge_count": len(edges),
        "contract_count": len(contracts),
        "contract_verdicts": _count_verdicts(contracts),
        "services": services,
    }


def build_dashboard_data(
    conn: sqlite3.Connection,
    *,
    project_root: Path,
    federated: Path | None = None,
) -> dict[str, object]:
    """Build the deterministic dashboard data dict (honest by construction).

    Args:
        conn: An open connection to the indexed graph DB.
        project_root: Project root (for the lint/debt/doctor gate paths).
        federated: Optional ``federate`` output JSON; enables the rollup section.

    Returns:
        A JSON-safe dict with ``lint`` / ``debt`` / ``docs`` / ``doctor`` and a
        ``federated`` section (``None`` when no artifact is given). Every value
        comes from the corresponding gate's own code path.
    """
    return {
        "lint": _lint_metrics(project_root),
        "debt": _debt_metrics(conn, project_root),
        "docs": _docs_metrics(conn),
        "doctor": _doctor_metrics(conn, project_root),
        "federated": _federated_metrics(federated) if federated is not None else None,
    }


def serialize_dashboard_data(data: dict[str, object]) -> str:
    """Serialize the dashboard data to deterministic JSON (sorted keys)."""
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _lint_section(lint_data: dict[str, object]) -> list[str]:
    return [
        "## Lint",
        "",
        f"- Violations: {lint_data['violations']} "
        f"({lint_data['errors']} errors, {lint_data['warnings']} warnings)",
        "",
    ]


def _debt_section(debt_data: dict[str, object]) -> list[str]:
    lines = [
        "## Debt",
        "",
        f"- Score: {debt_data['debt_score']} / 100 ({debt_data['severity']})",
        "",
    ]
    categories = debt_data.get("categories", [])
    if isinstance(categories, list) and categories:
        lines.append("### Categories")
        lines.append("")
        for cat in categories:
            if isinstance(cat, dict):
                lines.append(f"- {cat.get('name')}: {cat.get('score')}")
        lines.append("")
    return lines


def _docs_section(docs_data: dict[str, object]) -> list[str]:
    return [
        "## Documentation",
        "",
        f"- Coverage: {docs_data['coverage_pct']}% "
        f"({docs_data['documented']}/{docs_data['nodes']} nodes)",
        f"- Freshness: {docs_data['freshness_pct']}% "
        f"({docs_data['stale']} stale of {docs_data['tracked_pairs']} tracked)",
        "",
    ]


def _doctor_section(doctor_data: dict[str, object]) -> list[str]:
    status = "PASS" if doctor_data["passed"] else "FAIL"
    return [
        "## Doctor",
        "",
        f"- Integrity: {status} "
        f"({doctor_data['errors']} errors, {doctor_data['warnings']} warnings "
        f"across {doctor_data['total']} checks)",
        "",
    ]


def _federated_section(rollup: dict[str, object]) -> list[str]:
    lines = [
        "## Federated landscape",
        "",
        f"- {rollup['repo_count']} services, {rollup['edge_count']} cross-repo edges, "
        f"{rollup['contract_count']} contracts",
        "",
        "### Contract verdicts",
        "",
    ]
    contract_verdicts = rollup.get("contract_verdicts", {})
    if isinstance(contract_verdicts, dict):
        for verdict, count in contract_verdicts.items():
            lines.append(f"- {verdict.upper()}: {count}")
    lines.append("")
    lines.append("### Service health")
    lines.append("")
    services = rollup.get("services", [])
    if isinstance(services, list):
        for svc in services:
            if isinstance(svc, dict):
                badge = "healthy" if svc.get("healthy") else "at risk"
                lines.append(f"- {svc.get('repo')}: {badge}")
    lines.append("")
    return lines


def render_dashboard_md(data: dict[str, object]) -> str:
    """Render the human ``dashboard.md`` page from the dashboard data.

    Every figure is taken verbatim from *data* (the same dict serialized to
    ``dashboard.data.json``) — the page never recomputes a metric.
    """
    lint_data = data["lint"]
    debt_data = data["debt"]
    docs_data = data["docs"]
    doctor_data = data["doctor"]
    federated = data["federated"]

    lines: list[str] = [
        "---",
        "title: Metrics dashboard",
        "---",
        "",
        "# Metrics dashboard",
        "",
        "Generated by `beadloom docs site` — every number comes from the same code "
        "path as its gate (`lint` / `status --debt-report` / `sync-check` / "
        "`doctor` / `federate`). Honest by construction.",
        "",
    ]
    assert isinstance(lint_data, dict)
    assert isinstance(debt_data, dict)
    assert isinstance(docs_data, dict)
    assert isinstance(doctor_data, dict)
    lines.extend(_lint_section(lint_data))
    lines.extend(_debt_section(debt_data))
    lines.extend(_docs_section(docs_data))
    lines.extend(_doctor_section(doctor_data))
    if isinstance(federated, dict):
        lines.extend(_federated_section(federated))
    return "\n".join(lines) + "\n"
