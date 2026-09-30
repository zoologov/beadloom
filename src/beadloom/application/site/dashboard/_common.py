# beadloom:domain=application
# beadloom:feature=site-generation
"""Dashboard shared primitives — verdict/severity constants + metric coercion.

Small cohesive helpers used across the dashboard panels (gate metrics,
recommendations, alerts, status cards) so the thresholds and JSON-value coercion
live in exactly one place.
"""

from __future__ import annotations

# Edge/contract verdicts treated as unhealthy (a real, actionable cross-repo
# problem) — drives the per-service ``healthy`` flag in the federated rollup and
# the contract recommendation/alert filters.
_UNHEALTHY_VERDICTS = frozenset({"drift", "breaking"})

# Debt severities that warrant an attention alert (the debt report's own labels;
# ``high`` -> error, ``critical`` -> critical). Below ``high`` is not alerted.
_DEBT_ALERT_SEVERITY: dict[str, str] = {"high": "error", "critical": "critical"}


def _as_int(value: object) -> int:
    """Coerce a metric value (typed ``object`` from the data dict) to ``int``."""
    return int(value) if isinstance(value, (int, float)) else 0


def _as_float(value: object) -> float:
    """Coerce a metric value (typed ``object`` from the data dict) to ``float``."""
    return float(value) if isinstance(value, (int, float)) else 0.0
