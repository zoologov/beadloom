# beadloom:domain=application
# beadloom:feature=debt-report
"""Debt-report value types — the frozen data model shared across the package.

Owns the dataclasses produced and consumed by collection, scoring, trend, and
rendering: per-item weights/thresholds, the raw aggregated counts, the per-node
and per-category scores, the trend delta, and the assembled report.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebtWeights:
    """Per-item weights and thresholds for debt score computation.

    Configurable via ``config.yml`` ``debt_report`` section.
    """

    # Per-item weights
    rule_error: float = 3.0
    rule_warning: float = 1.0
    undocumented_node: float = 2.0
    stale_doc: float = 1.0
    untracked_file: float = 0.5
    oversized_domain: float = 2.0
    high_fan_out: float = 1.0
    dormant_domain: float = 0.5
    untested_domain: float = 1.0
    meta_doc_stale: float = 1.5
    # Thresholds
    oversized_symbols: int = 200
    high_fan_out_threshold: int = 10
    dormant_months: int = 3


@dataclass(frozen=True)
class DebtData:
    """Raw counts aggregated from all data sources."""

    error_count: int
    warning_count: int
    undocumented_count: int
    stale_count: int
    untracked_count: int
    oversized_count: int
    high_fan_out_count: int
    dormant_count: int
    untested_count: int
    # Per-node issue tracking for top offenders
    node_issues: dict[str, list[str]]
    # Meta-doc staleness (stale fact mentions in project docs)
    meta_doc_stale_count: int = 0


@dataclass(frozen=True)
class CategoryScore:
    """Weighted score for a single debt category."""

    name: str  # "rule_violations", "doc_gaps", "complexity", "test_gaps"
    score: float
    details: dict[str, int | float]


@dataclass(frozen=True)
class NodeDebt:
    """Debt contribution for a single graph node."""

    ref_id: str
    score: float
    reasons: list[str]


@dataclass(frozen=True)
class DebtTrend:
    """Score change vs a previous snapshot."""

    previous_snapshot: str  # ISO date
    previous_score: float
    delta: float
    category_deltas: dict[str, float]


@dataclass(frozen=True)
class DebtReport:
    """Complete debt report: score, categories, offenders, trend."""

    debt_score: float  # 0-100
    severity: str  # clean/low/medium/high/critical
    categories: list[CategoryScore]
    top_offenders: list[NodeDebt]
    trend: DebtTrend | None
