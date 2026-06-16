# beadloom:domain=application
# beadloom:feature=debt-report
"""Architecture debt report: score formula, data collection, and severity mapping.

Aggregates health signals from lint, sync-check, doctor, git_activity, and
test_mapper into a single 0-100 debt score with category breakdown and
per-node issue tracking.

This package decomposes the debt-report feature by responsibility (BDL-059 S4):

- :mod:`.models`  — the frozen value types (weights, data, scores, trend, report).
- :mod:`.config`  — ``config.yml`` -> typed :class:`DebtWeights`.
- :mod:`.collect` — aggregate the raw counts + per-node issues from all sources.
- :mod:`.scoring` — the weighted formula, severity label, and top offenders.
- :mod:`.trend`   — compare against the last snapshot for per-category deltas.
- :mod:`.render`  — JSON / Rich / trend-text output of a :class:`DebtReport`.

Every public symbol is re-exported here, so ``from beadloom.application.debt_report
import X`` is unchanged for all callers — the split is purely internal.
"""

from __future__ import annotations

# Private helpers are re-exported (``X as X``) so the historical
# ``from beadloom.application.debt_report import _foo`` paths (used by tests)
# keep working after the cohesion split — the public surface is unchanged.
from beadloom.application.debt_report.collect import (
    _count_dormant as _count_dormant,
)
from beadloom.application.debt_report.collect import (
    _count_high_fan_out as _count_high_fan_out,
)
from beadloom.application.debt_report.collect import (
    _count_oversized as _count_oversized,
)
from beadloom.application.debt_report.collect import (
    _count_stale as _count_stale,
)
from beadloom.application.debt_report.collect import (
    _count_undocumented as _count_undocumented,
)
from beadloom.application.debt_report.collect import (
    _count_untested as _count_untested,
)
from beadloom.application.debt_report.collect import (
    _count_untracked as _count_untracked,
)
from beadloom.application.debt_report.collect import (
    _count_violations as _count_violations,
)
from beadloom.application.debt_report.collect import (
    collect_debt_data,
)
from beadloom.application.debt_report.config import load_debt_weights
from beadloom.application.debt_report.models import (
    CategoryScore,
    DebtData,
    DebtReport,
    DebtTrend,
    DebtWeights,
    NodeDebt,
)
from beadloom.application.debt_report.render import (
    _CATEGORY_SHORT_MAP as _CATEGORY_SHORT_MAP,
)
from beadloom.application.debt_report.render import (
    _trend_arrow as _trend_arrow,
)
from beadloom.application.debt_report.render import (
    format_debt_json,
    format_debt_report,
    format_top_offenders_json,
    format_trend_section,
)
from beadloom.application.debt_report.scoring import (
    _ISSUE_WEIGHT_MAP as _ISSUE_WEIGHT_MAP,
)
from beadloom.application.debt_report.scoring import (
    _severity_label as _severity_label,
)
from beadloom.application.debt_report.scoring import (
    compute_debt_score,
    compute_top_offenders,
)
from beadloom.application.debt_report.trend import (
    _compute_snapshot_debt as _compute_snapshot_debt,
)
from beadloom.application.debt_report.trend import (
    compute_debt_trend,
)

__all__ = [
    "CategoryScore",
    "DebtData",
    "DebtReport",
    "DebtTrend",
    "DebtWeights",
    "NodeDebt",
    "collect_debt_data",
    "compute_debt_score",
    "compute_debt_trend",
    "compute_top_offenders",
    "format_debt_json",
    "format_debt_report",
    "format_top_offenders_json",
    "format_trend_section",
    "load_debt_weights",
]
