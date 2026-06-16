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

This package decomposes the dashboard feature by responsibility (BDL-059 S4):

- :mod:`._common`        — shared verdict/severity constants + metric coercion.
- :mod:`.gate_metrics`   — the honest per-gate figures + recorded trends.
- :mod:`.ai_activity`    — the AI tech-writer run-record rollup (G9).
- :mod:`.recommendations`— prioritized, actionable items from gate data (G6).
- :mod:`.alerts`         — critical-first attention-banner alerts (BEAD-10).
- :mod:`.status_cards`   — threshold-colored per-metric cards (BEAD-10).
- :mod:`.assemble`       — orchestrate the data dict + render ``dashboard.md``.

Every public symbol is re-exported here, so ``from
beadloom.application.site_dashboard import X`` is unchanged for all callers —
the split is purely internal.
"""

from __future__ import annotations

# Private helpers are re-exported (``X as X``) so the historical
# ``from beadloom.application.site_dashboard import _foo`` paths (used by tests)
# keep working after the cohesion split — the public surface is unchanged.
from beadloom.application.site_dashboard.ai_activity import (
    _USD_PER_1M_TOKENS as _USD_PER_1M_TOKENS,
)
from beadloom.application.site_dashboard.alerts import (
    _build_alerts as _build_alerts,
)
from beadloom.application.site_dashboard.alerts import (
    _contract_alerts as _contract_alerts,
)
from beadloom.application.site_dashboard.assemble import (
    build_dashboard_data,
    render_dashboard_md,
    serialize_dashboard_data,
)
from beadloom.application.site_dashboard.gate_metrics import (
    _federated_metrics as _federated_metrics,
)
from beadloom.application.site_dashboard.gate_metrics import (
    _read_federated_payload as _read_federated_payload,
)
from beadloom.application.site_dashboard.recommendations import (
    _contract_recommendations as _contract_recommendations,
)
from beadloom.application.site_dashboard.recommendations import (
    _node_link as _node_link,
)
from beadloom.application.site_dashboard.status_cards import (
    _debt_card as _debt_card,
)
from beadloom.application.site_dashboard.status_cards import (
    _docs_card as _docs_card,
)
from beadloom.application.site_dashboard.status_cards import (
    _doctor_card as _doctor_card,
)
from beadloom.application.site_dashboard.status_cards import (
    _federated_card as _federated_card,
)

__all__ = [
    "build_dashboard_data",
    "render_dashboard_md",
    "serialize_dashboard_data",
]
