"""Architecture debt report: score formula, data collection, and severity mapping.

Aggregates health signals from lint, sync-check, doctor, git_activity, and
test_mapper into a single 0-100 debt score with category breakdown and
per-node issue tracking.
"""

# beadloom:domain=infrastructure

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures (all frozen)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_debt_weights(project_root: Path) -> DebtWeights:
    """Load debt weights from ``config.yml`` ``debt_report`` section.

    Falls back to defaults for missing keys or missing file.
    """
    config_path = project_root / "config.yml"
    if not config_path.is_file():
        return DebtWeights()

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        logger.warning("Failed to read config.yml, using default weights")
        return DebtWeights()

    if not isinstance(data, dict):
        return DebtWeights()

    debt_section = data.get("debt_report")
    if not isinstance(debt_section, dict):
        return DebtWeights()

    # Merge weights
    weights_data = debt_section.get("weights", {})
    thresholds_data = debt_section.get("thresholds", {})

    if not isinstance(weights_data, dict):
        weights_data = {}
    if not isinstance(thresholds_data, dict):
        thresholds_data = {}

    defaults = DebtWeights()
    kwargs: dict[str, float | int] = {}

    # Weight fields
    weight_fields = {
        "rule_error", "rule_warning", "undocumented_node", "stale_doc",
        "untracked_file", "oversized_domain", "high_fan_out",
        "dormant_domain", "untested_domain", "meta_doc_stale",
    }
    for field_name in weight_fields:
        if field_name in weights_data:
            kwargs[field_name] = float(weights_data[field_name])

    # Threshold fields (mapped from config names to dataclass names)
    threshold_map = {
        "oversized_symbols": "oversized_symbols",
        "high_fan_out": "high_fan_out_threshold",
        "dormant_months": "dormant_months",
    }
    for config_key, field_name in threshold_map.items():
        if config_key in thresholds_data:
            kwargs[field_name] = int(thresholds_data[config_key])

    # Build with defaults for unset fields
    all_fields = {f.name for f in fields(DebtWeights)}
    for fname in all_fields:
        if fname not in kwargs:
            kwargs[fname] = getattr(defaults, fname)

    return DebtWeights(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------


def _count_undocumented(conn: sqlite3.Connection) -> tuple[int, list[str]]:
    """Count nodes that have no associated documentation.

    Returns (count, list_of_ref_ids).
    """
    rows = conn.execute(
        "SELECT n.ref_id FROM nodes n "
        "LEFT JOIN docs d ON d.ref_id = n.ref_id "
        "WHERE d.id IS NULL"
    ).fetchall()
    ref_ids = [str(r[0]) for r in rows]
    return len(ref_ids), ref_ids


def _count_stale(conn: sqlite3.Connection) -> tuple[int, list[str]]:
    """Count sync_state entries with status='stale'.

    Returns (count, list_of_ref_ids).
    """
    rows = conn.execute(
        "SELECT DISTINCT ref_id FROM sync_state WHERE status = 'stale'"
    ).fetchall()
    ref_ids = [str(r[0]) for r in rows]
    return len(ref_ids), ref_ids


def _count_untracked(conn: sqlite3.Connection) -> int:
    """Count untracked source files (nodes with source but not tracked).

    This is a simplified check: nodes with a source directory
    that have no sync_state entries.
    """
    rows = conn.execute(
        "SELECT n.ref_id FROM nodes n "
        "WHERE n.source IS NOT NULL "
        "AND n.ref_id NOT IN (SELECT DISTINCT ref_id FROM sync_state)"
    ).fetchall()
    return len(rows)


def _count_oversized(
    conn: sqlite3.Connection, threshold: int,
) -> tuple[int, list[str]]:
    """Count nodes whose source directory has more symbols than threshold.

    Returns (count, list_of_ref_ids).
    """
    nodes = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()

    oversized_refs: list[str] = []
    for node in nodes:
        ref_id = str(node[0])
        source = str(node[1])
        prefix = source.rstrip("/") + "/"
        row = conn.execute(
            "SELECT COUNT(*) FROM code_symbols WHERE file_path LIKE ?",
            (prefix + "%",),
        ).fetchone()
        count = int(row[0]) if row else 0
        if count > threshold:
            oversized_refs.append(ref_id)

    return len(oversized_refs), oversized_refs


def _count_high_fan_out(
    conn: sqlite3.Connection, threshold: int,
) -> tuple[int, list[str]]:
    """Count nodes with more outgoing edges than threshold.

    Returns (count, list_of_ref_ids).
    """
    rows = conn.execute(
        "SELECT src_ref_id, COUNT(*) as cnt FROM edges "
        "GROUP BY src_ref_id HAVING cnt > ?",
        (threshold,),
    ).fetchall()
    ref_ids = [str(r[0]) for r in rows]
    return len(ref_ids), ref_ids


def _count_dormant(
    conn: sqlite3.Connection,
    project_root: Path,
) -> tuple[int, list[str]]:
    """Count dormant domains (no git activity in 90 days).

    Returns (count, list_of_ref_ids).
    """
    try:
        from beadloom.infrastructure.git_activity import analyze_git_activity
    except ImportError:
        return 0, []

    # Build source_dirs from nodes
    nodes = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()
    source_dirs: dict[str, str] = {}
    for node in nodes:
        source_dirs[str(node[0])] = str(node[1])

    if not source_dirs:
        return 0, []

    try:
        activities = analyze_git_activity(project_root, source_dirs)
    except (OSError, ValueError):
        return 0, []

    dormant_refs: list[str] = []
    for ref_id, activity in activities.items():
        if activity.activity_level == "dormant":
            dormant_refs.append(ref_id)

    return len(dormant_refs), dormant_refs


def _count_untested(
    conn: sqlite3.Connection,
    project_root: Path,
) -> tuple[int, list[str]]:
    """Count domains/features with no test coverage.

    Returns (count, list_of_ref_ids).
    """
    try:
        from beadloom.context_oracle.test_mapper import map_tests
    except ImportError:
        return 0, []

    # Build source_dirs from nodes
    nodes = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()
    source_dirs: dict[str, str] = {}
    for node in nodes:
        source_dirs[str(node[0])] = str(node[1])

    if not source_dirs:
        return 0, []

    try:
        mappings = map_tests(project_root, source_dirs)
    except (OSError, ValueError):
        return 0, []

    untested_refs: list[str] = []
    for ref_id, mapping in mappings.items():
        if mapping.coverage_estimate == "none":
            untested_refs.append(ref_id)

    return len(untested_refs), untested_refs


def _count_violations(
    conn: sqlite3.Connection,
    project_root: Path,
) -> tuple[int, int, dict[str, list[str]]]:
    """Count rule violations (errors and warnings).

    Returns (error_count, warning_count, per_node_violations).
    """
    try:
        from beadloom.graph.rule_engine import evaluate_all, load_rules
    except ImportError:
        return 0, 0, {}

    rules_path = project_root / "rules.yml"
    if not rules_path.is_file():
        # Also try .beadloom/rules.yml
        rules_path = project_root / ".beadloom" / "rules.yml"
        if not rules_path.is_file():
            return 0, 0, {}

    try:
        rules = load_rules(rules_path)
        violations = evaluate_all(conn, rules)
    except (ValueError, OSError):
        return 0, 0, {}

    errors = 0
    warnings = 0
    node_violations: dict[str, list[str]] = {}

    for v in violations:
        if v.severity == "error":
            errors += 1
        else:
            warnings += 1

        # Track per-node with severity prefix for weighted scoring
        if v.from_ref_id:
            sev = "error" if v.severity == "error" else "warning"
            node_violations.setdefault(v.from_ref_id, []).append(
                f"violation:{sev}:{v.rule_name}"
            )

    return errors, warnings, node_violations


def collect_debt_data(
    conn: sqlite3.Connection,
    project_root: Path,
    weights: DebtWeights | None = None,
) -> DebtData:
    """Aggregate debt data from all data sources.

    Collects counts from rule engine, sync state, doctor, git activity,
    and test mapper.
    """
    if weights is None:
        weights = DebtWeights()

    node_issues: dict[str, list[str]] = {}

    # 1. Rule violations
    error_count, warning_count, violation_nodes = _count_violations(
        conn, project_root
    )
    for ref_id, reasons in violation_nodes.items():
        node_issues.setdefault(ref_id, []).extend(reasons)

    # 2. Undocumented nodes
    undocumented_count, undoc_refs = _count_undocumented(conn)
    for ref_id in undoc_refs:
        node_issues.setdefault(ref_id, []).append("undocumented")

    # 3. Stale docs
    stale_count, stale_refs = _count_stale(conn)
    for ref_id in stale_refs:
        node_issues.setdefault(ref_id, []).append("stale_doc")

    # 4. Untracked files
    untracked_count = _count_untracked(conn)

    # 5. Oversized domains
    oversized_count, oversized_refs = _count_oversized(
        conn, weights.oversized_symbols
    )
    for ref_id in oversized_refs:
        node_issues.setdefault(ref_id, []).append("oversized")

    # 6. High fan-out
    high_fan_out_count, fan_out_refs = _count_high_fan_out(
        conn, weights.high_fan_out_threshold
    )
    for ref_id in fan_out_refs:
        node_issues.setdefault(ref_id, []).append("high_fan_out")

    # 7. Dormant domains
    dormant_count, dormant_refs = _count_dormant(conn, project_root)
    for ref_id in dormant_refs:
        node_issues.setdefault(ref_id, []).append("dormant")

    # 8. Untested domains
    untested_count, untested_refs = _count_untested(conn, project_root)
    for ref_id in untested_refs:
        node_issues.setdefault(ref_id, []).append("untested")

    return DebtData(
        error_count=error_count,
        warning_count=warning_count,
        undocumented_count=undocumented_count,
        stale_count=stale_count,
        untracked_count=untracked_count,
        oversized_count=oversized_count,
        high_fan_out_count=high_fan_out_count,
        dormant_count=dormant_count,
        untested_count=untested_count,
        node_issues=node_issues,
    )


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

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
    "clean": ("\u2713", "green"),       # ✓
    "low": ("\u25cf", "yellow"),         # ●
    "medium": ("\u25b2", "yellow"),      # ▲
    "high": ("\u25c6", "red"),           # ◆
    "critical": ("\u2716", "red bold"),  # ✖
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
        report.severity, ("\u003f", "white"),
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
            prefix = "\u2514\u2500\u2500" if i == len(detail_items) - 1 else "\u251c\u2500\u2500"
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
# Trend tracking (BEAD-04)
# ---------------------------------------------------------------------------

# Category display names for trend rendering
_TREND_CATEGORY_NAMES: dict[str, str] = {
    "rule_violations": "Rules",
    "doc_gaps": "Docs",
    "complexity": "Complexity",
    "test_gaps": "Tests",
    "meta_doc_staleness": "Meta-Docs",
}


def _compute_snapshot_debt(
    snapshot_nodes: list[dict[str, str]],
    snapshot_edges: list[dict[str, str]],
    snapshot_symbols_count: int,
    weights: DebtWeights,
) -> tuple[float, dict[str, float]]:
    """Compute a debt score from snapshot data.

    Uses only structural data available in the snapshot: nodes and edges.
    Computes the complexity category (high fan-out) from edges and
    approximates undocumented nodes (all nodes in snapshot are assumed
    undocumented, since docs table is not captured in snapshots).

    Returns (total_score, per_category_scores).
    """
    # Count high fan-out from snapshot edges
    edge_counts: dict[str, int] = {}
    for edge in snapshot_edges:
        src = edge.get("src_ref_id", "")
        if src:
            edge_counts[src] = edge_counts.get(src, 0) + 1

    high_fan_out = sum(
        1 for cnt in edge_counts.values() if cnt > weights.high_fan_out_threshold
    )

    # Complexity category score from snapshot
    complexity_score = float(high_fan_out) * weights.high_fan_out

    # Undocumented: snapshot doesn't store docs, so we count all nodes as
    # potentially undocumented. To avoid misleading trend data, we set
    # doc-related categories to 0 (not computable from snapshot).
    # Rule violations and test gaps are also not computable from snapshot.
    category_scores = {
        "rule_violations": 0.0,
        "doc_gaps": 0.0,
        "complexity": complexity_score,
        "test_gaps": 0.0,
        "meta_doc_staleness": 0.0,
    }
    total = sum(category_scores.values())
    return min(100.0, total), category_scores


def compute_debt_trend(
    conn: sqlite3.Connection,
    current_report: DebtReport,
    project_root: Path,
    weights: DebtWeights | None = None,
) -> DebtTrend | None:
    """Compare current debt score against the last snapshot.

    Returns ``None`` if no previous snapshot exists.
    Recomputes the debt score from the snapshot's structural data to get
    an accurate trend comparison for the complexity category.

    For categories not stored in snapshots (rules, docs, tests), the
    trend compares against the category scores from the snapshot's
    recomputed structural debt.

    Args:
        conn: Database connection.
        current_report: The current debt report.
        project_root: Project root directory.
        weights: Optional debt weights override.

    Returns:
        A :class:`DebtTrend` or ``None`` if no snapshot exists.
    """
    import json

    from beadloom.graph.snapshot import list_snapshots

    if weights is None:
        weights = load_debt_weights(project_root)

    snapshots = list_snapshots(conn)
    if not snapshots:
        return None

    # Use the most recent snapshot
    latest = snapshots[0]

    # Load snapshot data
    row = conn.execute(
        "SELECT nodes_json, edges_json, symbols_count, label, created_at "
        "FROM graph_snapshots WHERE id = ?",
        (latest.id,),
    ).fetchone()
    if row is None:
        return None

    snapshot_nodes: list[dict[str, str]] = json.loads(row["nodes_json"])
    snapshot_edges: list[dict[str, str]] = json.loads(row["edges_json"])
    symbols_count: int = row["symbols_count"]
    snapshot_label: str = row["label"] or ""
    snapshot_date: str = row["created_at"]

    # Build the display string: prefer label, fallback to date
    snapshot_display = f"{snapshot_date} [{snapshot_label}]" if snapshot_label else snapshot_date

    # Compute debt from snapshot structural data
    prev_total, prev_categories = _compute_snapshot_debt(
        snapshot_nodes, snapshot_edges, symbols_count, weights,
    )

    # Build per-category deltas
    current_categories: dict[str, float] = {
        cat.name: cat.score for cat in current_report.categories
    }
    category_deltas: dict[str, float] = {}
    for cat_name in (
        "rule_violations", "doc_gaps", "complexity", "test_gaps",
        "meta_doc_staleness",
    ):
        current_val = current_categories.get(cat_name, 0.0)
        prev_val = prev_categories.get(cat_name, 0.0)
        category_deltas[cat_name] = current_val - prev_val

    delta = current_report.debt_score - prev_total

    return DebtTrend(
        previous_snapshot=snapshot_display,
        previous_score=prev_total,
        delta=delta,
        category_deltas=category_deltas,
    )


def _trend_arrow(delta: float) -> tuple[str, str]:
    """Return (arrow, label) for a delta value.

    Returns:
        ``("\u2193", "improved")`` for negative delta,
        ``("\u2191", "regressed")`` for positive delta,
        ``("=", "unchanged")`` for zero.
    """
    if delta < 0:
        return "\u2193", "improved"
    if delta > 0:
        return "\u2191", "regressed"
    return "=", "unchanged"


def format_trend_section(trend: DebtTrend | None) -> str:
    """Format the trend section as plain text.

    Renders::

        Trend (vs 2026-02-15):
          Overall:    25 -> 22  \u2193 3 improved
          Rules:      10 -> 8   \u2193 2
          Docs:       8  -> 8   = unchanged
          Complexity: 5  -> 4   \u2193 1
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
