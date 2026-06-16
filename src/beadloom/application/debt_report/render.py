# beadloom:domain=application
# beadloom:feature=debt-report
"""Debt-report rendering — JSON serialization, Rich terminal output, trend text.

Turns a :class:`DebtReport` (and its :class:`DebtTrend`) into the output shapes
the CLI/MCP consume: the ``--json`` dict, the human Rich-rendered report, and the
plain-text trend section. No score is computed here — rendering only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from beadloom.application.debt_report.models import (
        DebtReport,
        DebtTrend,
        NodeDebt,
    )

# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------


def format_top_offenders_json(
    offenders: list[NodeDebt],
) -> list[dict[str, object]]:
    """Serialize a list of :class:`NodeDebt` to JSON-safe dicts.

    Each dict contains ``ref_id``, ``score``, and ``reasons`` keys.
    """
    return [
        {
            "ref_id": nd.ref_id,
            "score": nd.score,
            "reasons": list(nd.reasons),
        }
        for nd in offenders
    ]


def format_debt_json(
    report: DebtReport,
    category: str | None = None,
) -> dict[str, Any]:
    """Serialize a :class:`DebtReport` to a JSON-safe dict.

    Args:
        report: The debt report to serialize.
        category: Optional category name filter. When set, only the matching
            category is included in the ``categories`` list. Accepted short
            names are mapped to internal names via :data:`_CATEGORY_SHORT_MAP`.

    Returns:
        A dict with keys ``debt_score``, ``severity``, ``categories``,
        ``top_offenders``, and ``trend`` (``None`` when no trend data).
    """
    # Filter categories if requested
    cats = list(report.categories)
    if category is not None:
        internal = _CATEGORY_SHORT_MAP.get(category, category)
        cats = [c for c in cats if c.name == internal]

    categories_json: list[dict[str, object]] = [
        {
            "name": c.name,
            "score": c.score,
            "details": dict(c.details),
        }
        for c in cats
    ]

    trend_json: dict[str, object] | None = None
    if report.trend is not None:
        trend_json = {
            "previous_snapshot": report.trend.previous_snapshot,
            "previous_score": report.trend.previous_score,
            "delta": report.trend.delta,
            "category_deltas": dict(report.trend.category_deltas),
        }

    return {
        "debt_score": report.debt_score,
        "severity": report.severity,
        "categories": categories_json,
        "top_offenders": format_top_offenders_json(report.top_offenders),
        "trend": trend_json,
    }


# Short name -> internal category name mapping for CLI --category flag
_CATEGORY_SHORT_MAP: dict[str, str] = {
    "rules": "rule_violations",
    "docs": "doc_gaps",
    "complexity": "complexity",
    "tests": "test_gaps",
    "meta_docs": "meta_doc_staleness",
}


# ---------------------------------------------------------------------------
# Rich formatting (human-readable output)
# ---------------------------------------------------------------------------

_SEVERITY_INDICATORS: dict[str, tuple[str, str]] = {
    "clean": ("✓", "green"),       # ✓
    "low": ("●", "yellow"),         # ●
    "medium": ("▲", "yellow"),      # ▲
    "high": ("◆", "red"),           # ◆
    "critical": ("✖", "red bold"),  # ✖
}

_CATEGORY_DISPLAY_NAMES: dict[str, str] = {
    "rule_violations": "Rule Violations",
    "doc_gaps": "Documentation Gaps",
    "complexity": "Complexity Smells",
    "test_gaps": "Test Gaps",
    "meta_doc_staleness": "Meta-Doc Staleness",
}

_CATEGORY_DETAIL_LABELS: dict[str, dict[str, str]] = {
    "rule_violations": {"errors": "errors", "warnings": "warnings"},
    "doc_gaps": {"undocumented": "undocumented", "stale": "stale", "untracked": "untracked"},
    "complexity": {"oversized": "oversized", "high_fan_out": "high fan-out", "dormant": "dormant"},
    "test_gaps": {"untested": "untested"},
    "meta_doc_staleness": {"meta_doc_stale": "stale doc mentions"},
}


def format_debt_report(report: DebtReport) -> str:
    """Format a DebtReport as a Rich-rendered string for terminal display.

    Produces output with:
    - Header panel: "Architecture Debt Report"
    - Score line with severity label and visual indicator
    - Category breakdown table with per-category scores and item counts
    - Top offenders section (if any)
    """
    from io import StringIO

    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)

    # -- Header --
    console.print()
    console.rule("[bold]Architecture Debt Report[/bold]", style="blue")
    console.print()

    # -- Score line with severity indicator --
    indicator, style = _SEVERITY_INDICATORS.get(
        report.severity, ("?", "white"),
    )
    score_text = Text()
    score_text.append("  Debt Score: ", style="bold")
    score_text.append(f"{report.debt_score:.0f}", style=f"bold {style}")
    score_text.append(" / 100  ", style="bold")
    score_text.append(f"{indicator} {report.severity}", style=style)
    console.print(score_text)
    console.print()

    # -- Category Breakdown --
    console.rule("Category Breakdown", style="dim")
    console.print()

    for cat in report.categories:
        display_name = _CATEGORY_DISPLAY_NAMES.get(cat.name, cat.name)
        pts_label = "pt" if cat.score == 1.0 else "pts"
        dots = "." * (35 - len(display_name))
        console.print(
            f"  [bold]{display_name}[/bold] {dots}"
            f" {cat.score:.0f} {pts_label}"
        )

        # Detail lines
        detail_labels = _CATEGORY_DETAIL_LABELS.get(cat.name, {})
        detail_items = list(detail_labels.items())
        for i, (key, label) in enumerate(detail_items):
            value = cat.details.get(key, 0)
            prefix = "└──" if i == len(detail_items) - 1 else "├──"
            console.print(f"  {prefix} {label}: {value}")
        console.print()

    # -- Top Offenders --
    if report.top_offenders:
        console.rule("Top Offenders", style="dim")
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("#", justify="right", style="dim", width=4)
        table.add_column("Node", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Reasons")

        for idx, offender in enumerate(report.top_offenders, start=1):
            reasons_str = ", ".join(offender.reasons)
            pts_label = "pt" if offender.score == 1.0 else "pts"
            table.add_row(
                f"{idx}.",
                offender.ref_id,
                f"{offender.score:.0f} {pts_label}",
                reasons_str,
            )

        console.print(table)
        console.print()

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Trend rendering
# ---------------------------------------------------------------------------

# Category display names for trend rendering
_TREND_CATEGORY_NAMES: dict[str, str] = {
    "rule_violations": "Rules",
    "doc_gaps": "Docs",
    "complexity": "Complexity",
    "test_gaps": "Tests",
    "meta_doc_staleness": "Meta-Docs",
}


def _trend_arrow(delta: float) -> tuple[str, str]:
    """Return (arrow, label) for a delta value.

    Returns:
        ``("↓", "improved")`` for negative delta,
        ``("↑", "regressed")`` for positive delta,
        ``("=", "unchanged")`` for zero.
    """
    if delta < 0:
        return "↓", "improved"
    if delta > 0:
        return "↑", "regressed"
    return "=", "unchanged"


def format_trend_section(trend: DebtTrend | None) -> str:
    """Format the trend section as plain text.

    Renders::

        Trend (vs 2026-02-15):
          Overall:    25 -> 22  ↓ 3 improved
          Rules:      10 -> 8   ↓ 2
          Docs:       8  -> 8   = unchanged
          Complexity: 5  -> 4   ↓ 1
          Tests:      2  -> 2   = unchanged

    Returns ``"No baseline snapshot available"`` when *trend* is ``None``.
    """
    if trend is None:
        return "Trend: No baseline snapshot available"

    # Extract date portion (strip time if present)
    date_display = trend.previous_snapshot.split("T")[0]
    if " [" in date_display:
        date_display = date_display.split(" [")[0]

    lines: list[str] = [f"Trend (vs {date_display}):"]

    # Overall line
    current_score = trend.previous_score + trend.delta
    arrow, label = _trend_arrow(trend.delta)
    abs_delta = abs(trend.delta)
    delta_str = f"{abs_delta:.0f}" if abs_delta != 0 else ""
    lines.append(
        f"  Overall:    {trend.previous_score:.0f} -> {current_score:.0f}  "
        f"{arrow}{delta_str} {label}"
    )

    # Per-category lines
    for cat_name in (
        "rule_violations", "doc_gaps", "complexity", "test_gaps",
        "meta_doc_staleness",
    ):
        display = _TREND_CATEGORY_NAMES.get(cat_name, cat_name)
        cat_delta = trend.category_deltas.get(cat_name, 0.0)
        cat_arrow, cat_label = _trend_arrow(cat_delta)
        abs_d = abs(cat_delta)
        d_str = f"{abs_d:.0f}" if abs_d != 0 else ""
        # Pad display name for alignment
        padded_name = f"{display}:".ljust(14)
        lines.append(f"  {padded_name}{cat_arrow}{d_str} {cat_label}")

    return "\n".join(lines)
