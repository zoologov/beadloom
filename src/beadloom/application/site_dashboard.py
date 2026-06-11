# beadloom:domain=application
# beadloom:feature=site-generation
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
from dataclasses import dataclass
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

# Alert severity ordering (lower = surfaced first). BREAKING contracts lead the
# attention banner, then errors (lint/doctor/drift), then warnings (stale/debt).
_ALERT_RANK: dict[str, int] = {"critical": 0, "error": 1, "warn": 2, "info": 3}

# Debt severities that warrant an attention alert (the debt report's own labels;
# ``high`` -> error, ``critical`` -> critical). Below ``high`` is not alerted.
_DEBT_ALERT_SEVERITY: dict[str, str] = {"high": "error", "critical": "critical"}


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
# AI tech-writer activity — run-record store, honest by construction (G9)
# ---------------------------------------------------------------------------

# The append-only run-record store the CI harness emits (one record per run):
# ``{ts, platform, docs_refreshed[], input_tokens, output_tokens, model, gate,
# pr_url}``. We read it independently (the harness lives in ``tools/`` and is
# not importable from the ``application`` layer) — absent/empty/corrupt all
# degrade to "no data" (never an error).
_AI_RUNS_FILENAME = "ai_techwriter_runs.json"

# Blended $/1M-token rate used ONLY to turn the FACT (token counts from the
# model API) into a clearly-labeled ESTIMATE. Tiered/changing pricing makes any
# dollar figure approximate, so the dashboard never presents this as a hard
# cost — see ``cost_estimate.is_estimate`` / ``cost_estimate.label``.
_USD_PER_1M_TOKENS = 0.40


@dataclass(frozen=True)
class _AiRun:
    """One normalized run-record (typed, so cumulative math stays type-safe)."""

    ts: str
    platform: str
    gate: str
    docs_refreshed: int
    input_tokens: int
    output_tokens: int


def _coerce_int(value: object) -> int:
    """Coerce a JSON-loaded value to a non-negative int (0 on anything else)."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    return 0


def _read_ai_runs(project_root: Path) -> list[dict[str, object]]:
    """Read the run-record store; absent/empty/corrupt -> ``[]`` (no data)."""
    store = project_root / ".beadloom" / _AI_RUNS_FILENAME
    if not store.is_file():
        return []
    try:
        payload = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Could not read AI tech-writer run store %s", store)
        return []
    if not isinstance(payload, list):
        return []
    return [r for r in payload if isinstance(r, dict)]


def _ai_run_row(raw: dict[str, object]) -> _AiRun | None:
    """Normalize one stored record; skip rows without a usable ``ts``."""
    ts = raw.get("ts")
    if not isinstance(ts, str) or not ts:
        return None
    refreshed = raw.get("docs_refreshed")
    docs_count = len(refreshed) if isinstance(refreshed, list) else 0
    return _AiRun(
        ts=ts,
        platform=str(raw.get("platform", "")),
        gate=str(raw.get("gate", "")),
        docs_refreshed=docs_count,
        input_tokens=_coerce_int(raw.get("input_tokens")),
        output_tokens=_coerce_int(raw.get("output_tokens")),
    )


def _ai_cost_estimate(input_tokens: int, output_tokens: int) -> dict[str, object]:
    """A clearly-labeled $ ESTIMATE (tokens are fact; $ is approximate)."""
    total = input_tokens + output_tokens
    usd = round(total / 1_000_000 * _USD_PER_1M_TOKENS, 4)
    return {
        "usd": usd,
        "rate_usd_per_1m": _USD_PER_1M_TOKENS,
        "is_estimate": True,
        "label": f"est. @ ${_USD_PER_1M_TOKENS}/1M tokens",
    }


def _ai_techwriter(project_root: Path) -> dict[str, object]:
    """Honest AI tech-writer activity from the run-record store (G9).

    Returns per-run + cumulative docs-refreshed and input/output token spend
    (sorted by ts; ONLY real recorded runs — no interpolation, sparse-at-first
    is correct, mirroring ``trends``). Token counts are FACTS from the record;
    the $ figure is a clearly-labeled estimate. Absent/empty/corrupt store ->
    an empty (but present) section.
    """
    rows = [row for raw in _read_ai_runs(project_root) if (row := _ai_run_row(raw))]
    rows.sort(key=lambda r: r.ts)

    cum_docs = cum_in = cum_out = 0
    runs: list[dict[str, object]] = []
    for row in rows:
        cum_docs += row.docs_refreshed
        cum_in += row.input_tokens
        cum_out += row.output_tokens
        runs.append(
            {
                "ts": row.ts,
                "platform": row.platform,
                "gate": row.gate,
                "docs_refreshed": row.docs_refreshed,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "cumulative_docs": cum_docs,
                "cumulative_input_tokens": cum_in,
                "cumulative_output_tokens": cum_out,
            }
        )

    return {
        "runs": runs,
        "totals": {
            "runs": len(runs),
            "docs_refreshed": cum_docs,
            "input_tokens": cum_in,
            "output_tokens": cum_out,
        },
        "cost_estimate": _ai_cost_estimate(cum_in, cum_out),
    }


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


# ---------------------------------------------------------------------------
# Attention alerts — critical-first problem signalling (BEAD-10)
# ---------------------------------------------------------------------------


def _as_int(value: object) -> int:
    """Coerce a metric value (typed ``object`` from the data dict) to ``int``."""
    return int(value) if isinstance(value, (int, float)) else 0


def _as_float(value: object) -> float:
    """Coerce a metric value (typed ``object`` from the data dict) to ``float``."""
    return float(value) if isinstance(value, (int, float)) else 0.0


def _alert(kind: str, severity: str, message: str) -> dict[str, object]:
    """Build one attention alert in the documented shape."""
    return {"kind": kind, "severity": severity, "message": message}


def _contract_alerts(
    federated_payload: dict[str, object] | None,
) -> list[dict[str, object]]:
    """BREAKING (critical) / DRIFT (error) contract alerts from the rollup."""
    if not isinstance(federated_payload, dict):
        return []
    contracts = federated_payload.get("contracts")
    if not isinstance(contracts, list):
        return []
    counts: dict[str, int] = {"breaking": 0, "drift": 0}
    for item in contracts:
        if not isinstance(item, dict):
            continue
        verdict = str(item.get("verdict", "")).lower()
        if verdict in counts:
            counts[verdict] += 1
    alerts: list[dict[str, object]] = []
    if counts["breaking"]:
        alerts.append(
            _alert(
                "contract",
                "critical",
                f"{counts['breaking']} BREAKING contract(s) — reconcile producer/consumer",
            )
        )
    if counts["drift"]:
        alerts.append(
            _alert(
                "contract",
                "error",
                f"{counts['drift']} DRIFT contract(s) — producer/consumer diverging",
            )
        )
    return alerts


def _build_alerts(
    lint_data: dict[str, object],
    debt_data: dict[str, object],
    docs_data: dict[str, object],
    doctor_data: dict[str, object],
    federated_payload: dict[str, object] | None,
) -> list[dict[str, object]]:
    """Derive the attention banner alerts — exactly the real, current problems.

    Honest by construction: every alert maps to a gate figure already computed
    above (lint errors, doctor errors, stale docs, high debt, BREAKING/DRIFT
    contracts). An empty list means all-clear. Severity-ordered (BREAKING leads),
    ties broken deterministically by (kind, message) so the output is byte-stable.
    """
    alerts: list[dict[str, object]] = []
    alerts.extend(_contract_alerts(federated_payload))

    lint_errors = _as_int(lint_data.get("errors", 0))
    if lint_errors:
        alerts.append(
            _alert("lint", "error", f"{lint_errors} lint error(s) — run `beadloom lint`")
        )

    doctor_errors = _as_int(doctor_data.get("errors", 0))
    if doctor_errors:
        alerts.append(
            _alert(
                "doctor",
                "error",
                f"{doctor_errors} doctor error(s) — run `beadloom doctor`",
            )
        )

    stale = _as_int(docs_data.get("stale", 0))
    if stale:
        alerts.append(
            _alert(
                "stale_doc",
                "warn",
                f"{stale} stale doc(s) — refresh and re-run `beadloom sync-check`",
            )
        )

    debt_sev = str(debt_data.get("severity", ""))
    if debt_sev in _DEBT_ALERT_SEVERITY:
        score = debt_data.get("debt_score")
        alerts.append(
            _alert(
                "debt",
                _DEBT_ALERT_SEVERITY[debt_sev],
                f"debt {debt_sev} (score {score}) — see the debt report",
            )
        )

    alerts.sort(
        key=lambda a: (
            _ALERT_RANK.get(str(a["severity"]), 9),
            str(a["kind"]),
            str(a["message"]),
        )
    )
    return alerts


# ---------------------------------------------------------------------------
# Status cards — threshold-colored per metric group (BEAD-10)
# ---------------------------------------------------------------------------


def _card(
    group: str, label: str, status: str, value: str, detail: str
) -> dict[str, object]:
    """Build one status card; ``status`` is the deterministic severity (color)."""
    return {
        "group": group,
        "label": label,
        "status": status,
        "value": value,
        "detail": detail,
    }


def _lint_card(d: dict[str, object]) -> dict[str, object]:
    errors = _as_int(d.get("errors", 0))
    warnings = _as_int(d.get("warnings", 0))
    status = "error" if errors else ("warn" if warnings else "ok")
    return _card(
        "lint",
        "Lint",
        status,
        str(d.get("violations", 0)),
        f"{errors} errors, {warnings} warnings",
    )


def _debt_card(d: dict[str, object]) -> dict[str, object]:
    sev = str(d.get("severity", ""))
    status = "error" if sev in _DEBT_ALERT_SEVERITY else (
        "warn" if sev == "medium" else "ok"
    )
    return _card(
        "debt",
        "Debt",
        status,
        f"{d.get('debt_score', 0)} / 100",
        sev or "clean",
    )


def _docs_card(d: dict[str, object]) -> dict[str, object]:
    stale = _as_int(d.get("stale", 0))
    coverage = _as_float(d.get("coverage_pct", 0.0))
    status = "warn" if stale else ("warn" if coverage < 80.0 else "ok")
    return _card(
        "docs",
        "Docs",
        status,
        f"{coverage}% covered",
        f"{stale} stale of {d.get('tracked_pairs', 0)} tracked",
    )


def _doctor_card(d: dict[str, object]) -> dict[str, object]:
    errors = _as_int(d.get("errors", 0))
    warnings = _as_int(d.get("warnings", 0))
    status = "error" if errors else ("warn" if warnings else "ok")
    return _card(
        "doctor",
        "Doctor",
        status,
        "PASS" if d.get("passed") else "FAIL",
        f"{errors} errors, {warnings} warnings",
    )


def _federated_card(rollup: dict[str, object]) -> dict[str, object]:
    verdicts = rollup.get("contract_verdicts", {})
    counts = verdicts if isinstance(verdicts, dict) else {}
    breaking = int(counts.get("breaking", 0))
    drift = int(counts.get("drift", 0))
    status = "error" if breaking else ("warn" if drift else "ok")
    return _card(
        "federated",
        "Contracts",
        status,
        f"{rollup.get('contract_count', 0)} contracts",
        f"{breaking} breaking, {drift} drift",
    )


def _build_status_cards(
    lint_data: dict[str, object],
    debt_data: dict[str, object],
    docs_data: dict[str, object],
    doctor_data: dict[str, object],
    rollup: dict[str, object] | None,
) -> list[dict[str, object]]:
    """Compact, threshold-colored cards per metric group (deterministic order).

    Thresholds live here in Python (the card ``status`` is data); the frontend
    only paints the color. Card values are taken verbatim from the gate figures
    already computed — no new metric is invented.
    """
    cards = [
        _lint_card(lint_data),
        _debt_card(debt_data),
        _docs_card(docs_data),
        _doctor_card(doctor_data),
    ]
    if rollup is not None:
        cards.append(_federated_card(rollup))
    return cards


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
        time-series), ``ai_techwriter`` (the run-record activity: per-run +
        cumulative docs-refreshed and token spend; tokens are FACT, $ is a
        labeled estimate) and ``recommendations`` (a prioritized, actionable
        list). Every value comes from the corresponding gate's own code path;
        trends and AI-activity series are exactly the recorded points (no
        fabrication).
    """
    lint_result = lint(project_root, reindex_before=False)
    report = _debt_report(conn, project_root)
    federated_payload = (
        _read_federated_payload(federated) if federated is not None else None
    )
    rollup = _federated_metrics(federated_payload) if federated_payload else None
    lint_data = _lint_metrics(lint_result)
    debt_data = format_debt_json(report)
    docs_data = _docs_metrics(conn)
    doctor_data = _doctor_metrics(conn, project_root)
    return {
        "lint": lint_data,
        "debt": debt_data,
        "docs": docs_data,
        "doctor": doctor_data,
        "federated": rollup,
        "alerts": _build_alerts(
            lint_data, debt_data, docs_data, doctor_data, federated_payload
        ),
        "status_cards": _build_status_cards(
            lint_data, debt_data, docs_data, doctor_data, rollup
        ),
        "trends": _trends(project_root),
        "ai_techwriter": _ai_techwriter(project_root),
        "recommendations": _build_recommendations(
            conn, lint_result, report.top_offenders, federated_payload
        ),
    }


def serialize_dashboard_data(data: dict[str, object]) -> str:
    """Serialize the dashboard data to deterministic JSON (sorted keys)."""
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _widgets_section() -> list[str]:
    """Mount the committed widgets — critical-first (banner + cards lead).

    The attention banner (``AlertBanner``) + threshold-colored status cards
    (``StatusCards``) signal problems first; the ECharts widgets (BEAD-04) follow.
    Each widget loads ``dashboard.data.json`` (emitted alongside this page) and
    renders client-side. The numbers/states it shows are exactly the serialized
    data values — the front-end never invents a figure or a severity. These
    ``ClientOnly`` mounts are the single presentation surface for the dashboard
    (BEAD-12: the verbose textual metric dump was removed); the honest data lives
    in ``dashboard.data.json``, computed by ``build_dashboard_data`` (unchanged).
    """
    return [
        "<ClientOnly>",
        "  <AlertBanner />",
        "  <StatusCards />",
        "  <HealthGauges />",
        "  <CategoryChart />",
        "  <TrendCharts />",
        "  <AiTechwriterActivity />",
        "  <Recommendations />",
        "</ClientOnly>",
        "",
    ]


def render_dashboard_md(data: dict[str, object]) -> str:
    """Render the human ``dashboard.md`` page from the dashboard data.

    The page is the title + a short intro + the ``ClientOnly`` component mounts.
    The widgets are the single presentation surface; they read the honest figures
    from ``dashboard.data.json`` (this function never recomputes a metric, and
    ``build_dashboard_data`` — the source of those figures — is unchanged).
    """
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
    return "\n".join(lines) + "\n"
