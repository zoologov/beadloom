# beadloom:domain=application
# beadloom:feature=site-generation
"""Dashboard gate metrics — the honest per-gate figures + recorded trends.

Every metric here is produced by the SAME code path as its CLI gate (lint /
debt / sync-check / doctor / federate) so the site can never publish a figure
the gate would contradict. Plus :func:`_trends`: the recorded metrics-history
time-series (only real points, no fabrication).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from beadloom.application.debt_report import (
    DebtReport,
    collect_debt_data,
    compute_debt_score,
    compute_debt_trend,
    load_debt_weights,
)
from beadloom.application.doctor import Severity, run_checks
from beadloom.application.site_dashboard._common import _UNHEALTHY_VERDICTS
from beadloom.application.site_metrics_history import MetricsPoint, read_history

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.graph.linter import LintResult

logger = logging.getLogger(__name__)


def _lint_metrics(result: LintResult) -> dict[str, object]:
    """Lint count + severity breakdown from a precomputed ``beadloom lint`` result.

    The result is computed once (no reindex — read-only over the
    already-indexed DB) and shared with the recommendation panel so the dashboard
    figure and the lint hotspots can never disagree.
    """
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


def _debt_report(conn: sqlite3.Connection, project_root: Path) -> DebtReport:
    """Compute the debt report via the exact ``--debt-report`` path (with trend)."""
    from dataclasses import replace

    weights = load_debt_weights(project_root)
    report = compute_debt_score(collect_debt_data(conn, project_root, weights), weights)
    trend = compute_debt_trend(conn, report, project_root, weights)
    if trend is not None:
        # compute_debt_score always returns trend=None; attach the computed trend.
        report = replace(report, trend=trend)
    return report


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


def _read_federated_payload(federated: Path) -> dict[str, object] | None:
    """Read the federated artifact JSON (dict), logging + ``None`` on failure."""
    try:
        payload = json.loads(federated.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Could not read federated artifact %s", federated)
        return None
    return payload if isinstance(payload, dict) else None


def _federated_metrics(payload: dict[str, object]) -> dict[str, object]:
    """Per-service edge-verdict health + contract-verdict counts.

    Reuses the F2 ``federate`` output verbatim (``edges[].verdict`` /
    ``contracts[].verdict`` / ``repos[]``) — no re-derivation of verdicts.
    """
    raw_edges = payload.get("edges", [])
    raw_repos = payload.get("repos", [])
    raw_contracts = payload.get("contracts", [])
    edges = [e for e in raw_edges if isinstance(e, dict)] if isinstance(raw_edges, list) else []
    repos = [r for r in raw_repos if isinstance(r, dict)] if isinstance(raw_repos, list) else []
    contracts = (
        [c for c in raw_contracts if isinstance(c, dict)]
        if isinstance(raw_contracts, list)
        else []
    )

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


def _trends(project_root: Path) -> list[dict[str, object]]:
    """Serialize the recorded metrics-history series (sorted by ts).

    HONEST: returns *only* real recorded points (no interpolation, no fabricated
    samples). Sparse at first is correct; the series grows one point per
    ``docs site`` run plus any structural backfill from ``graph_snapshots``.
    """
    series: list[MetricsPoint] = read_history(project_root)
    return [
        {
            "ts": p.ts,
            "lint_violations": p.lint_violations,
            "debt_score": p.debt_score,
            "coverage_pct": p.coverage_pct,
            "sync_pct": p.sync_pct,
            "nodes": p.nodes,
            "edges": p.edges,
            "symbols": p.symbols,
        }
        for p in series
    ]
