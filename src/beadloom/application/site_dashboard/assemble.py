# beadloom:domain=application
# beadloom:feature=site-generation
"""Dashboard assembly + render — the deterministic data dict and ``dashboard.md``.

Orchestrates every panel (gate metrics, federated rollup, alerts, status cards,
trends, AI activity, recommendations) into a single JSON-safe dict, serializes it
deterministically (sorted keys, no wall-clock), and renders the human page that
mounts the client-side widgets. The widgets read the serialized figures verbatim
— this layer never invents a number; every value comes from its gate's own path.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from beadloom.application.debt_report import format_debt_json
from beadloom.application.site_dashboard.ai_activity import _ai_techwriter
from beadloom.application.site_dashboard.alerts import _build_alerts
from beadloom.application.site_dashboard.gate_metrics import (
    _debt_report,
    _docs_metrics,
    _doctor_metrics,
    _federated_metrics,
    _lint_metrics,
    _read_federated_payload,
    _trends,
)
from beadloom.application.site_dashboard.recommendations import _build_recommendations
from beadloom.application.site_dashboard.status_cards import _build_status_cards
from beadloom.graph.linter import lint

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)


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
    lint_result = lint(project_root)
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
