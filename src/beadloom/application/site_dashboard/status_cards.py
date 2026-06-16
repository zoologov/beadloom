# beadloom:domain=application
# beadloom:feature=site-generation
"""Dashboard status cards — compact, threshold-colored per metric group (BEAD-10).

Thresholds live here in Python (the card ``status`` is data); the frontend only
paints the color. Card values are taken verbatim from the gate figures already
computed — no new metric is invented.
"""

from __future__ import annotations

from beadloom.application.site_dashboard._common import (
    _DEBT_ALERT_SEVERITY,
    _as_float,
    _as_int,
)


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
