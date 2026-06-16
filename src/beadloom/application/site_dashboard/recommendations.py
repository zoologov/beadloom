# beadloom:domain=application
# beadloom:feature=site-generation
"""Dashboard recommendations — prioritized, actionable items from gate data (G6).

Every recommendation derives from an existing gate code path (lint violations,
worst-debt offenders, stale docs, breaking/drift contracts) — no new metric is
computed here. The assembled list is severity-ordered and deterministically
tie-broken so the output is byte-stable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.site_dashboard._common import _UNHEALTHY_VERDICTS

if TYPE_CHECKING:
    import sqlite3

    from beadloom.application.debt_report import NodeDebt
    from beadloom.graph.linter import LintResult

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


def _node_link(ref_id: str | None) -> str:
    """Best-effort link to a node page (kind is unknown here; the dashboard root)."""
    if not ref_id:
        return "/dashboard"
    return f"/dashboard#{ref_id}"


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
