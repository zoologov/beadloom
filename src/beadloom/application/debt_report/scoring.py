# beadloom:domain=application
# beadloom:feature=debt-report
"""Debt scoring — the weighted 0-100 formula, severity mapping, and top offenders.

Turns the raw :class:`DebtData` counts into a :class:`DebtReport`: per-category
weighted scores, the capped overall score, its severity label, and the ranked
worst-offender nodes.
"""

from __future__ import annotations

from beadloom.application.debt_report.models import (
    CategoryScore,
    DebtData,
    DebtReport,
    DebtWeights,
    NodeDebt,
)


def _severity_label(score: float) -> str:
    """Map a debt score to a severity string.

    Ranges (inclusive):
      0       -> clean
      1-10    -> low
      11-25   -> medium
      26-50   -> high
      51-100  -> critical
    """
    if score <= 0.0:
        return "clean"
    if score <= 10.0:
        return "low"
    if score <= 25.0:
        return "medium"
    if score <= 50.0:
        return "high"
    return "critical"


# Weight-to-issue reason mapping for per-node scoring
_ISSUE_WEIGHT_MAP: dict[str, str] = {
    "undocumented": "undocumented_node",
    "stale_doc": "stale_doc",
    "oversized": "oversized_domain",
    "high_fan_out": "high_fan_out",
    "dormant": "dormant_domain",
    "untested": "untested_domain",
}


def compute_top_offenders(
    data: DebtData,
    weights: DebtWeights,
    limit: int = 10,
) -> list[NodeDebt]:
    """Rank nodes by their debt contribution and return the top *limit*.

    Uses ``data.node_issues`` to calculate per-node debt score based on
    the number and type of issues, weighted by the debt weights
    configuration.

    Reason string formats handled:
    - ``"violation:error:<rule>"`` -- weighted by ``weights.rule_error``
    - ``"violation:warning:<rule>"`` -- weighted by ``weights.rule_warning``
    - ``"violation:<rule>"`` -- legacy format, defaults to ``weights.rule_error``
    - Issue keywords (``undocumented``, ``stale_doc``, etc.) -- looked up via
      ``_ISSUE_WEIGHT_MAP``
    """
    offenders: list[NodeDebt] = []

    for ref_id, reasons in data.node_issues.items():
        score = 0.0
        clean_reasons: list[str] = []

        for reason in reasons:
            if reason.startswith("violation:"):
                parts = reason.split(":", maxsplit=2)
                if len(parts) >= 3 and parts[1] == "warning":
                    score += weights.rule_warning
                else:
                    # "violation:error:<name>" or legacy "violation:<name>"
                    score += weights.rule_error
                clean_reasons.append(reason)
            elif reason in _ISSUE_WEIGHT_MAP:
                weight_attr = _ISSUE_WEIGHT_MAP[reason]
                score += getattr(weights, weight_attr)
                clean_reasons.append(reason)

        if score > 0:
            offenders.append(NodeDebt(
                ref_id=ref_id,
                score=score,
                reasons=clean_reasons,
            ))

    # Sort descending by score, then alphabetically by ref_id for stability
    offenders.sort(key=lambda o: (-o.score, o.ref_id))
    return offenders[:limit]


def compute_debt_score(
    data: DebtData,
    weights: DebtWeights | None = None,
) -> DebtReport:
    """Apply the weighted formula to compute the debt report.

    Formula::

        debt_score = min(100, sum(category_scores))

        category_scores:
          rule_violations = (errors * rule_error) + (warnings * rule_warning)
          doc_gaps        = (undocumented * undocumented_node)
                          + (stale * stale_doc) + (untracked * untracked_file)
          complexity      = (oversized * oversized_domain)
                          + (high_fan_out * high_fan_out) + (dormant * dormant_domain)
          test_gaps       = (untested * untested_domain)
    """
    if weights is None:
        weights = DebtWeights()

    # Category: rule_violations
    rule_score = (
        data.error_count * weights.rule_error
        + data.warning_count * weights.rule_warning
    )
    rule_cat = CategoryScore(
        name="rule_violations",
        score=rule_score,
        details={
            "errors": data.error_count,
            "warnings": data.warning_count,
        },
    )

    # Category: doc_gaps
    doc_score = (
        data.undocumented_count * weights.undocumented_node
        + data.stale_count * weights.stale_doc
        + data.untracked_count * weights.untracked_file
    )
    doc_cat = CategoryScore(
        name="doc_gaps",
        score=doc_score,
        details={
            "undocumented": data.undocumented_count,
            "stale": data.stale_count,
            "untracked": data.untracked_count,
        },
    )

    # Category: complexity
    complexity_score = (
        data.oversized_count * weights.oversized_domain
        + data.high_fan_out_count * weights.high_fan_out
        + data.dormant_count * weights.dormant_domain
    )
    complexity_cat = CategoryScore(
        name="complexity",
        score=complexity_score,
        details={
            "oversized": data.oversized_count,
            "high_fan_out": data.high_fan_out_count,
            "dormant": data.dormant_count,
        },
    )

    # Category: test_gaps
    test_score = data.untested_count * weights.untested_domain
    test_cat = CategoryScore(
        name="test_gaps",
        score=test_score,
        details={
            "untested": data.untested_count,
        },
    )

    categories = [rule_cat, doc_cat, complexity_cat, test_cat]

    # Category: meta_doc_staleness (only when stale mentions exist)
    if data.meta_doc_stale_count > 0:
        meta_doc_score = data.meta_doc_stale_count * weights.meta_doc_stale
        meta_doc_cat = CategoryScore(
            name="meta_doc_staleness",
            score=meta_doc_score,
            details={
                "meta_doc_stale": data.meta_doc_stale_count,
            },
        )
        categories.append(meta_doc_cat)

    raw_score = sum(c.score for c in categories)
    debt_score = min(100.0, raw_score)
    severity = _severity_label(debt_score)

    # Top offenders
    top_offenders = compute_top_offenders(data, weights)

    return DebtReport(
        debt_score=debt_score,
        severity=severity,
        categories=categories,
        top_offenders=top_offenders,
        trend=None,
    )
