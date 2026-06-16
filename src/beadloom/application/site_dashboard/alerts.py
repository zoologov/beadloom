# beadloom:domain=application
# beadloom:feature=site-generation
"""Dashboard attention alerts — critical-first problem signalling (BEAD-10).

Derives the attention-banner alerts from the gate figures already computed
(lint errors, doctor errors, stale docs, high debt, breaking/drift contracts).
An empty list means all-clear. Severity-ordered (BREAKING leads), ties broken
deterministically so the output is byte-stable.
"""

from __future__ import annotations

from beadloom.application.site_dashboard._common import (
    _DEBT_ALERT_SEVERITY,
    _as_int,
)

# Alert severity ordering (lower = surfaced first). BREAKING contracts lead the
# attention banner, then errors (lint/doctor/drift), then warnings (stale/debt).
_ALERT_RANK: dict[str, int] = {"critical": 0, "error": 1, "warn": 2, "info": 3}


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
