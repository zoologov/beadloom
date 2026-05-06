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
    DebtReport,
    NodeDebt,
    collect_debt_data,
    compute_debt_score,
    compute_debt_trend,
    format_debt_json,
    load_debt_weights,
)
from beadloom.application.doctor import Severity, run_checks
from beadloom.application.site_metrics_history import (
    MetricsPoint,
    read_history,
)
from beadloom.graph.linter import LintResult, lint

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)

# Edge/contract verdicts treated as unhealthy (a real, actionable cross-repo
# problem) — drives the per-service ``healthy`` flag in the federated rollup.
_UNHEALTHY_VERDICTS = frozenset({"drift", "breaking"})

# Recommendation severity ordering (lower = surfaced first). The panel is
# severity-ordered so the most actionable problems lead.
_SEVERITY_RANK: dict[str, int] = {
    "critical": 0,
    "error": 0,
    "warn": 1,
    "warning": 1,
    "info": 2,
}

# How many worst-debt offenders to surface as recommendations (the debt report
# already returns its own ``top_offenders`` cut; we mirror that honest slice).
_MAX_DEBT_RECS = 5


def _lint_metrics(result: LintResult) -> dict[str, object]:
    """Lint count + severity breakdown from a precomputed ``beadloom lint`` result.

    The result is computed once (``reindex_before=False`` — read-only over the
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


# ---------------------------------------------------------------------------
# Trends — honest time-series, exactly the recorded points (G5)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Recommendations — prioritized + actionable, from the existing gate data (G6)
# ---------------------------------------------------------------------------


def _rec(
    kind: str, severity: str, target: str, message: str, link: str
) -> dict[str, object]:
    """Build one recommendation item in the documented shape."""
    return {
        "kind": kind,
        "severity": severity,
        "target": target,
        "message": message,
        "link": link,
    }


def _lint_recommendations(result: LintResult) -> list[dict[str, object]]:
    """One recommendation per real lint violation (same data as ``beadloom lint``)."""
    recs: list[dict[str, object]] = []
    for v in result.violations:
        target = v.from_ref_id or v.to_ref_id or v.rule_name
        # Message is the gate's own text verbatim (honest); the actionable
        # remediation hint is appended when the rule engine provides one.
        message = v.message
        if v.remediation:
            message = f"{message} — {v.remediation}"
        recs.append(_rec("lint", v.severity, target, message, _node_link(v.from_ref_id)))
    return recs


def _debt_recommendations(offenders: list[NodeDebt]) -> list[dict[str, object]]:
    """Worst-debt nodes as warnings (mirrors ``debt_report`` top offenders)."""
    recs: list[dict[str, object]] = []
    for nd in offenders[:_MAX_DEBT_RECS]:
        reasons = "; ".join(nd.reasons) if nd.reasons else "accumulated debt"
        message = f"debt score {nd.score}: {reasons}"
        recs.append(_rec("debt", "warn", nd.ref_id, message, _node_link(nd.ref_id)))
    return recs


def _stale_doc_recommendations(conn: sqlite3.Connection) -> list[dict[str, object]]:
    """Stale docs to refresh (the persisted ``sync-check`` result, read-only)."""
    rows = conn.execute(
        "SELECT DISTINCT ref_id FROM sync_state WHERE status = 'stale' ORDER BY ref_id"
    ).fetchall()
    return [
        _rec(
            "stale_doc",
            "warn",
            str(row["ref_id"]),
            "doc is stale vs its code — refresh and re-run sync-check",
            _node_link(str(row["ref_id"])),
        )
        for row in rows
    ]


def _contract_recommendations(
    payload: dict[str, object] | None,
) -> list[dict[str, object]]:
    """Contract risks (BREAKING/DRIFT) from a federated artifact, when present."""
    if not isinstance(payload, dict):
        return []
    contracts = payload.get("contracts")
    if not isinstance(contracts, list):
        return []
    recs: list[dict[str, object]] = []
    for item in contracts:
        if not isinstance(item, dict):
            continue
        verdict = str(item.get("verdict", "")).lower()
        if verdict not in _UNHEALTHY_VERDICTS:
            continue
        key = str(item.get("contract_key", ""))
        severity = "error" if verdict == "breaking" else "warn"
        recs.append(
            _rec(
                "contract",
                severity,
                key,
                f"contract {verdict.upper()} — reconcile producer/consumer",
                "/landscape",
            )
        )
    return recs


def _node_link(ref_id: str | None) -> str:
    """Best-effort link to a node page (kind is unknown here; the dashboard root)."""
    if not ref_id:
        return "/dashboard"
    return f"/dashboard#{ref_id}"


def _build_recommendations(
    conn: sqlite3.Connection,
    lint_result: LintResult,
    offenders: list[NodeDebt],
    federated_payload: dict[str, object] | None,
) -> list[dict[str, object]]:
    """Assemble + severity-order the recommendation panel (honest by construction).

    Every item derives from an existing gate code path — no new metric is
    computed here. The list is severity-ordered (errors first); ties broken
    deterministically by (kind, target) so the output is byte-stable.
    """
    recs: list[dict[str, object]] = []
    recs.extend(_lint_recommendations(lint_result))
    recs.extend(_contract_recommendations(federated_payload))
    recs.extend(_stale_doc_recommendations(conn))
    recs.extend(_debt_recommendations(offenders))
    recs.sort(
        key=lambda r: (
            _SEVERITY_RANK.get(str(r["severity"]), 9),
            str(r["kind"]),
            str(r["target"]),
            str(r["message"]),
        )
    )
    return recs


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
        A JSON-safe dict with ``lint`` / ``debt`` / ``docs`` / ``doctor`` /
        ``federated`` (``None`` when no artifact) plus ``trends`` (the recorded
        time-series) and ``recommendations`` (a prioritized, actionable list).
        Every value comes from the corresponding gate's own code path; trends
        are exactly the recorded points (no fabrication).
    """
    lint_result = lint(project_root, reindex_before=False)
    report = _debt_report(conn, project_root)
    federated_payload = (
        _read_federated_payload(federated) if federated is not None else None
    )
    rollup = _federated_metrics(federated_payload) if federated_payload else None
    return {
        "lint": _lint_metrics(lint_result),
        "debt": format_debt_json(report),
        "docs": _docs_metrics(conn),
        "doctor": _doctor_metrics(conn, project_root),
        "federated": rollup,
        "trends": _trends(project_root),
        "recommendations": _build_recommendations(
            conn, lint_result, report.top_offenders, federated_payload
        ),
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


def _widgets_section() -> list[str]:
    """Mount the committed ECharts widgets (BEAD-04, theme-registered globals).

    Each widget loads ``dashboard.data.json`` (emitted alongside this page) and
    renders client-side via ``vue-echarts``. The numbers it shows are exactly the
    serialized data values — the front-end never invents a figure. With JS
    disabled the widgets render nothing and the honest textual summary below
    remains the source of truth (graceful degradation).
    """
    return [
        "<ClientOnly>",
        "  <HealthGauges />",
        "  <CategoryChart />",
        "  <TrendCharts />",
        "  <Recommendations />",
        "</ClientOnly>",
        "",
    ]


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
    lines.extend(_widgets_section())
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
