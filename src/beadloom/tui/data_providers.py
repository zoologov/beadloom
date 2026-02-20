# beadloom:service=tui
"""Thin data provider wrappers over existing Beadloom infrastructure APIs.

Each provider accepts a sqlite3.Connection and project_root Path,
and provides read-only access to a specific data domain.
All providers support refresh() for reactive updates after reindex.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GraphDataProvider:
    """Read-only access to architecture graph nodes and edges."""

    conn: sqlite3.Connection
    project_root: Path

    _nodes: list[dict[str, str]] = field(default_factory=list, init=False, repr=False)
    _edges: list[dict[str, str]] = field(default_factory=list, init=False, repr=False)

    def refresh(self) -> None:
        """Reload nodes and edges from the database."""
        self._nodes = [
            {"ref_id": r["ref_id"], "kind": r["kind"], "summary": r["summary"]}
            for r in self.conn.execute(
                "SELECT ref_id, kind, summary FROM nodes ORDER BY kind, ref_id"
            ).fetchall()
        ]
        self._edges = [
            {"src": r["src_ref_id"], "dst": r["dst_ref_id"], "kind": r["kind"]}
            for r in self.conn.execute(
                "SELECT src_ref_id, dst_ref_id, kind FROM edges ORDER BY src_ref_id"
            ).fetchall()
        ]

    def get_nodes(self) -> list[dict[str, str]]:
        """Return all graph nodes."""
        if not self._nodes:
            self.refresh()
        return list(self._nodes)

    def get_edges(self) -> list[dict[str, str]]:
        """Return all graph edges."""
        if not self._edges:
            self.refresh()
        return list(self._edges)

    def get_node(self, ref_id: str) -> dict[str, str] | None:
        """Return a single node by ref_id, or None if not found."""
        row = self.conn.execute(
            "SELECT ref_id, kind, summary FROM nodes WHERE ref_id = ?",
            (ref_id,),
        ).fetchone()
        if row is None:
            return None
        return {"ref_id": row["ref_id"], "kind": row["kind"], "summary": row["summary"]}

    def get_hierarchy(self) -> dict[str, list[str]]:
        """Return parent->children mapping via part_of edges."""
        rows = self.conn.execute(
            "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"
        ).fetchall()
        hierarchy: dict[str, list[str]] = {}
        for row in rows:
            parent = row["dst_ref_id"]
            child = row["src_ref_id"]
            hierarchy.setdefault(parent, []).append(child)
        return hierarchy


@dataclass
class LintDataProvider:
    """Read-only access to architecture lint violations."""

    conn: sqlite3.Connection
    project_root: Path

    _violations: list[dict[str, str | None]] = field(
        default_factory=list, init=False, repr=False
    )

    def refresh(self) -> None:
        """Re-evaluate lint rules and cache violations."""
        from beadloom.graph.rule_engine import evaluate_all, load_rules

        rules_path = self.project_root / ".beadloom" / "_graph" / "rules.yml"
        if not rules_path.exists():
            self._violations = []
            return

        try:
            rules = load_rules(rules_path)
            violations = evaluate_all(self.conn, rules)
            self._violations = [
                {
                    "rule_name": v.rule_name,
                    "severity": v.severity,
                    "from_ref_id": v.from_ref_id,
                    "to_ref_id": v.to_ref_id,
                    "description": v.rule_description,
                }
                for v in violations
            ]
        except (ValueError, OSError) as exc:
            logger.warning("Lint evaluation failed: %s", exc)
            self._violations = []

    def get_violations(self) -> list[dict[str, str | None]]:
        """Return all lint violations."""
        if not self._violations:
            self.refresh()
        return list(self._violations)

    def get_violation_count(self) -> int:
        """Return total violation count."""
        return len(self.get_violations())


@dataclass
class SyncDataProvider:
    """Read-only access to doc-code synchronization status."""

    conn: sqlite3.Connection
    project_root: Path

    _results: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def refresh(self) -> None:
        """Re-run sync check and cache results."""
        from beadloom.doc_sync.engine import check_sync

        try:
            self._results = check_sync(self.conn, project_root=self.project_root)
        except (OSError, ValueError) as exc:
            logger.warning("Sync check failed: %s", exc)
            self._results = []

    def get_sync_results(self) -> list[dict[str, Any]]:
        """Return all sync pair results."""
        if not self._results:
            self.refresh()
        return list(self._results)

    def get_stale_count(self) -> int:
        """Return number of stale doc-code pairs."""
        return sum(1 for r in self.get_sync_results() if r.get("status") == "stale")

    def get_coverage(self) -> float:
        """Return documentation coverage percentage (0-100)."""
        results = self.get_sync_results()
        if not results:
            return 0.0
        ok_count = sum(1 for r in results if r.get("status") == "ok")
        return (ok_count / len(results)) * 100.0


@dataclass
class DebtDataProvider:
    """Read-only access to architecture debt report."""

    conn: sqlite3.Connection
    project_root: Path

    _report: Any = field(default=None, init=False, repr=False)

    def refresh(self) -> None:
        """Recompute debt report and cache it."""
        from beadloom.infrastructure.debt_report import (
            collect_debt_data,
            compute_debt_score,
            load_debt_weights,
        )

        try:
            weights = load_debt_weights(self.project_root)
            debt_data = collect_debt_data(self.conn, self.project_root, weights)
            self._report = compute_debt_score(debt_data, weights)
        except (OSError, ValueError) as exc:
            logger.warning("Debt report failed: %s", exc)
            self._report = None

    def get_debt_report(self) -> Any:
        """Return the full DebtReport object, or None on error."""
        if self._report is None:
            self.refresh()
        return self._report

    def get_score(self) -> float:
        """Return the debt score (0-100), or 0.0 on error."""
        report = self.get_debt_report()
        if report is None:
            return 0.0
        return float(report.debt_score)


@dataclass
class ActivityDataProvider:
    """Read-only access to git activity analysis."""

    conn: sqlite3.Connection
    project_root: Path

    _activities: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def refresh(self) -> None:
        """Re-analyze git activity and cache results."""
        from beadloom.infrastructure.git_activity import analyze_git_activity

        # Build source_dirs from nodes table
        rows = self.conn.execute(
            "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
        ).fetchall()
        source_dirs: dict[str, str] = {}
        for row in rows:
            src = str(row["source"])
            if src.strip():
                source_dirs[str(row["ref_id"])] = src

        if not source_dirs:
            self._activities = {}
            return

        try:
            self._activities = analyze_git_activity(self.project_root, source_dirs)
        except (OSError, ValueError) as exc:
            logger.warning("Git activity analysis failed: %s", exc)
            self._activities = {}

    def get_activity(self) -> dict[str, Any]:
        """Return activity mapping {ref_id: GitActivity}."""
        if not self._activities:
            self.refresh()
        return dict(self._activities)


@dataclass
class WhyDataProvider:
    """Read-only access to impact analysis (why)."""

    conn: sqlite3.Connection
    project_root: Path

    def refresh(self) -> None:
        """No-op: why analysis is on-demand per ref_id."""

    def analyze(self, ref_id: str, *, reverse: bool = False) -> Any:
        """Run impact analysis on a single node.

        Returns a WhyResult or None on error.
        """
        from beadloom.context_oracle.why import analyze_node

        try:
            return analyze_node(self.conn, ref_id, reverse=reverse)
        except LookupError as exc:
            logger.warning("Why analysis failed for %s: %s", ref_id, exc)
            return None


@dataclass
class ContextDataProvider:
    """Read-only access to context bundle building."""

    conn: sqlite3.Connection
    project_root: Path

    def refresh(self) -> None:
        """No-op: context bundles are on-demand per ref_id."""

    def get_context(self, ref_id: str) -> dict[str, Any] | None:
        """Build a context bundle for a ref_id.

        Returns the bundle dict or None on error.
        """
        from beadloom.context_oracle.builder import build_context

        try:
            return build_context(self.conn, [ref_id])
        except LookupError as exc:
            logger.warning("Context build failed for %s: %s", ref_id, exc)
            return None

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text string."""
        from beadloom.context_oracle.builder import estimate_tokens

        return estimate_tokens(text)
