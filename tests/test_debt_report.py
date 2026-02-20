"""Tests for beadloom.infrastructure.debt_report — debt score formula + data collection."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.debt_report import (
    CategoryScore,
    DebtData,
    DebtReport,
    DebtTrend,
    DebtWeights,
    NodeDebt,
    _compute_snapshot_debt,
    _count_oversized,
    _count_untracked,
    _severity_label,
    _trend_arrow,
    collect_debt_data,
    compute_debt_score,
    compute_debt_trend,
    compute_top_offenders,
    format_debt_json,
    format_top_offenders_json,
    format_trend_section,
    load_debt_weights,
)

# Note: format_debt_report is imported locally in test methods to avoid
# circular import issues with Rich, and to test that the public API is
# importable from the module.

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True)
    c = open_db(db_path)
    create_schema(c)
    return c


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    return tmp_path


# ===========================================================================
# 1. Dataclass immutability tests
# ===========================================================================


class TestDataclassImmutability:
    def test_debt_weights_frozen(self) -> None:
        w = DebtWeights()
        with pytest.raises(FrozenInstanceError):
            w.rule_error = 99.0  # type: ignore[misc]

    def test_debt_data_frozen(self) -> None:
        d = DebtData(
            error_count=0,
            warning_count=0,
            undocumented_count=0,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues={},
        )
        with pytest.raises(FrozenInstanceError):
            d.error_count = 5  # type: ignore[misc]

    def test_category_score_frozen(self) -> None:
        cs = CategoryScore(name="test", score=1.0, details={})
        with pytest.raises(FrozenInstanceError):
            cs.score = 99.0  # type: ignore[misc]

    def test_node_debt_frozen(self) -> None:
        nd = NodeDebt(ref_id="x", score=1.0, reasons=["a"])
        with pytest.raises(FrozenInstanceError):
            nd.ref_id = "y"  # type: ignore[misc]

    def test_debt_trend_frozen(self) -> None:
        dt = DebtTrend(
            previous_snapshot="2026-01-01",
            previous_score=10.0,
            delta=-5.0,
            category_deltas={},
        )
        with pytest.raises(FrozenInstanceError):
            dt.delta = 0.0  # type: ignore[misc]

    def test_debt_report_frozen(self) -> None:
        r = DebtReport(
            debt_score=0.0,
            severity="clean",
            categories=[],
            top_offenders=[],
            trend=None,
        )
        with pytest.raises(FrozenInstanceError):
            r.debt_score = 50.0  # type: ignore[misc]


# ===========================================================================
# 2. Severity label tests
# ===========================================================================


class TestSeverityLabel:
    def test_score_0_is_clean(self) -> None:
        assert _severity_label(0.0) == "clean"

    def test_score_1_is_low(self) -> None:
        assert _severity_label(1.0) == "low"

    def test_score_10_is_low(self) -> None:
        assert _severity_label(10.0) == "low"

    def test_score_11_is_medium(self) -> None:
        assert _severity_label(11.0) == "medium"

    def test_score_25_is_medium(self) -> None:
        assert _severity_label(25.0) == "medium"

    def test_score_26_is_high(self) -> None:
        assert _severity_label(26.0) == "high"

    def test_score_50_is_high(self) -> None:
        assert _severity_label(50.0) == "high"

    def test_score_51_is_critical(self) -> None:
        assert _severity_label(51.0) == "critical"

    def test_score_100_is_critical(self) -> None:
        assert _severity_label(100.0) == "critical"


# ===========================================================================
# 3. compute_debt_score tests
# ===========================================================================


class TestComputeDebtScore:
    def _zero_data(self) -> DebtData:
        return DebtData(
            error_count=0,
            warning_count=0,
            undocumented_count=0,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues={},
        )

    def test_zero_debt_produces_clean(self) -> None:
        data = self._zero_data()
        report = compute_debt_score(data)
        assert report.debt_score == 0.0
        assert report.severity == "clean"
        assert len(report.categories) == 4

    def test_known_values_exact_score(self) -> None:
        """2 errors (3 each) + 1 warning (1) = 7 for rule_violations.
        3 undocumented (2 each) = 6 for doc_gaps.
        Total = 13 -> medium.
        """
        data = DebtData(
            error_count=2,
            warning_count=1,
            undocumented_count=3,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues={},
        )
        report = compute_debt_score(data)
        assert report.debt_score == 13.0
        assert report.severity == "medium"

    def test_all_categories_contribute(self) -> None:
        """Each category has exactly 1 item with default weight."""
        data = DebtData(
            error_count=1,    # 3.0
            warning_count=1,  # 1.0
            undocumented_count=1,  # 2.0
            stale_count=1,    # 1.0
            untracked_count=1,  # 0.5
            oversized_count=1,  # 2.0
            high_fan_out_count=1,  # 1.0
            dormant_count=1,  # 0.5
            untested_count=1,  # 1.0
            node_issues={},
        )
        report = compute_debt_score(data)
        expected = 3.0 + 1.0 + 2.0 + 1.0 + 0.5 + 2.0 + 1.0 + 0.5 + 1.0
        assert report.debt_score == expected

    def test_score_capped_at_100(self) -> None:
        data = DebtData(
            error_count=100,
            warning_count=100,
            undocumented_count=100,
            stale_count=100,
            untracked_count=100,
            oversized_count=100,
            high_fan_out_count=100,
            dormant_count=100,
            untested_count=100,
            node_issues={},
        )
        report = compute_debt_score(data)
        assert report.debt_score == 100.0
        assert report.severity == "critical"

    def test_custom_weights(self) -> None:
        data = DebtData(
            error_count=1,
            warning_count=0,
            undocumented_count=0,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues={},
        )
        weights = DebtWeights(rule_error=10.0)
        report = compute_debt_score(data, weights)
        assert report.debt_score == 10.0

    def test_categories_have_correct_names(self) -> None:
        data = self._zero_data()
        report = compute_debt_score(data)
        names = {c.name for c in report.categories}
        assert names == {"rule_violations", "doc_gaps", "complexity", "test_gaps"}

    def test_top_offenders_sorted_descending(self) -> None:
        data = DebtData(
            error_count=0,
            warning_count=0,
            undocumented_count=0,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues={
                "node-a": ["undocumented"],
                "node-b": ["undocumented", "oversized", "untested"],
                "node-c": ["stale_doc"],
            },
        )
        report = compute_debt_score(data)
        if report.top_offenders:
            scores = [o.score for o in report.top_offenders]
            assert scores == sorted(scores, reverse=True)

    def test_top_offenders_limited_to_10(self) -> None:
        """Even with many nodes, top_offenders is at most 10."""
        issues: dict[str, list[str]] = {}
        for i in range(20):
            issues[f"node-{i}"] = ["undocumented"]
        data = DebtData(
            error_count=0,
            warning_count=0,
            undocumented_count=20,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues=issues,
        )
        report = compute_debt_score(data)
        assert len(report.top_offenders) <= 10


# ===========================================================================
# 4. load_debt_weights tests
# ===========================================================================


class TestLoadDebtWeights:
    def test_defaults_when_no_config(self, project_root: Path) -> None:
        weights = load_debt_weights(project_root)
        assert weights == DebtWeights()
        assert weights.rule_error == 3.0
        assert weights.rule_warning == 1.0

    def test_full_custom_config(self, project_root: Path) -> None:
        config = {
            "debt_report": {
                "weights": {
                    "rule_error": 5,
                    "rule_warning": 2,
                    "undocumented_node": 3,
                    "stale_doc": 2,
                    "untracked_file": 1,
                    "oversized_domain": 4,
                    "high_fan_out": 3,
                    "dormant_domain": 1,
                    "untested_domain": 2,
                },
                "thresholds": {
                    "oversized_symbols": 300,
                    "high_fan_out": 15,
                    "dormant_months": 6,
                },
            }
        }
        config_path = project_root / "config.yml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")

        weights = load_debt_weights(project_root)
        assert weights.rule_error == 5.0
        assert weights.rule_warning == 2.0
        assert weights.oversized_symbols == 300
        assert weights.high_fan_out_threshold == 15
        assert weights.dormant_months == 6

    def test_partial_config_merges_with_defaults(self, project_root: Path) -> None:
        config = {
            "debt_report": {
                "weights": {
                    "rule_error": 10,
                },
            }
        }
        config_path = project_root / "config.yml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")

        weights = load_debt_weights(project_root)
        assert weights.rule_error == 10.0
        # Everything else is default
        assert weights.rule_warning == 1.0
        assert weights.undocumented_node == 2.0
        assert weights.oversized_symbols == 200

    def test_config_without_debt_report_section(self, project_root: Path) -> None:
        config = {"some_other_key": {"foo": "bar"}}
        config_path = project_root / "config.yml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")

        weights = load_debt_weights(project_root)
        assert weights == DebtWeights()


# ===========================================================================
# 5. collect_debt_data tests
# ===========================================================================


class TestCollectDebtData:
    def test_empty_project(
        self, conn: sqlite3.Connection, project_root: Path
    ) -> None:
        """A fresh project with no data sources should produce zero counts."""
        data = collect_debt_data(conn, project_root)
        assert data.error_count == 0
        assert data.warning_count == 0
        assert data.undocumented_count == 0
        assert data.stale_count == 0
        assert data.untracked_count == 0
        assert data.oversized_count == 0
        assert data.high_fan_out_count == 0
        assert data.dormant_count == 0
        assert data.untested_count == 0

    def test_counts_undocumented_nodes(
        self, conn: sqlite3.Connection, project_root: Path
    ) -> None:
        """Nodes without docs should be counted as undocumented."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("alpha", "domain", "Alpha domain"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("beta", "domain", "Beta domain"),
        )
        # Only alpha has a doc
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            ("alpha.md", "domain", "alpha", "abc123"),
        )
        conn.commit()

        data = collect_debt_data(conn, project_root)
        assert data.undocumented_count == 1  # beta has no doc

    def test_counts_stale_docs(
        self, conn: sqlite3.Connection, project_root: Path
    ) -> None:
        """sync_state entries with status='stale' should be counted."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("alpha", "domain", "Alpha"),
        )
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, "
            "code_hash_at_sync, doc_hash_at_sync, synced_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "alpha.md", "src/alpha.py", "alpha",
                "h1", "h2", "2026-01-01T00:00:00", "stale",
            ),
        )
        conn.commit()

        data = collect_debt_data(conn, project_root)
        assert data.stale_count == 1

    def test_counts_oversized_domains(
        self, conn: sqlite3.Connection, project_root: Path
    ) -> None:
        """Domains with more than oversized_symbols threshold symbols."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("big-domain", "domain", "Big", "src/big/"),
        )
        # Insert 201 code symbols
        for i in range(201):
            conn.execute(
                "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                "line_start, line_end, annotations, file_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"src/big/mod{i}.py", f"func_{i}", "function", 1, 10, "{}", "h"),
            )
        conn.commit()

        data = collect_debt_data(conn, project_root)
        assert data.oversized_count == 1

    def test_counts_high_fan_out(
        self, conn: sqlite3.Connection, project_root: Path
    ) -> None:
        """Nodes with more than high_fan_out_threshold outgoing edges."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("hub", "feature", "Hub"),
        )
        for i in range(11):
            target = f"target-{i}"
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
                (target, "feature", f"Target {i}"),
            )
            conn.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
                ("hub", target, "uses"),
            )
        conn.commit()

        data = collect_debt_data(conn, project_root)
        assert data.high_fan_out_count == 1

    def test_node_issues_populated(
        self, conn: sqlite3.Connection, project_root: Path
    ) -> None:
        """node_issues dict should track which nodes have which problems."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("lonely", "domain", "Lonely domain"),
        )
        conn.commit()

        data = collect_debt_data(conn, project_root)
        # "lonely" has no doc -> undocumented
        assert "lonely" in data.node_issues
        assert "undocumented" in data.node_issues["lonely"]


# ===========================================================================
# 6. Edge case / integration tests
# ===========================================================================


class TestEdgeCases:
    def test_compute_with_none_weights_uses_defaults(self) -> None:
        data = DebtData(
            error_count=1,
            warning_count=0,
            undocumented_count=0,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues={},
        )
        report = compute_debt_score(data, None)
        assert report.debt_score == 3.0  # default rule_error weight

    def test_debt_report_trend_is_none_by_default(self) -> None:
        data = DebtData(
            error_count=0,
            warning_count=0,
            undocumented_count=0,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues={},
        )
        report = compute_debt_score(data)
        assert report.trend is None

    def test_category_details_populated(self) -> None:
        data = DebtData(
            error_count=2,
            warning_count=3,
            undocumented_count=0,
            stale_count=0,
            untracked_count=0,
            oversized_count=0,
            high_fan_out_count=0,
            dormant_count=0,
            untested_count=0,
            node_issues={},
        )
        report = compute_debt_score(data)
        rule_cat = next(
            c for c in report.categories if c.name == "rule_violations"
        )
        assert rule_cat.details["errors"] == 2
        assert rule_cat.details["warnings"] == 3

    def test_debt_weights_defaults_match_spec(self) -> None:
        """Verify default weights match Strategy 5.10 spec."""
        w = DebtWeights()
        assert w.rule_error == 3.0
        assert w.rule_warning == 1.0
        assert w.undocumented_node == 2.0
        assert w.stale_doc == 1.0
        assert w.untracked_file == 0.5
        assert w.oversized_domain == 2.0
        assert w.high_fan_out == 1.0
        assert w.dormant_domain == 0.5
        assert w.untested_domain == 1.0
        assert w.oversized_symbols == 200
        assert w.high_fan_out_threshold == 10
        assert w.dormant_months == 3


# ===========================================================================
# 7. compute_top_offenders (BEAD-06) — standalone public API
# ===========================================================================


class TestComputeTopOffenders:
    """Tests for the standalone public compute_top_offenders function."""

    @staticmethod
    def _zero_data(**overrides: object) -> DebtData:
        defaults: dict[str, object] = {
            "error_count": 0,
            "warning_count": 0,
            "undocumented_count": 0,
            "stale_count": 0,
            "untracked_count": 0,
            "oversized_count": 0,
            "high_fan_out_count": 0,
            "dormant_count": 0,
            "untested_count": 0,
            "node_issues": {},
        }
        defaults.update(overrides)
        return DebtData(**defaults)  # type: ignore[arg-type]

    # -- Ranking correctness --

    def test_nodes_ranked_by_score_descending(self) -> None:
        """Nodes with higher debt score appear first."""
        data = self._zero_data(
            node_issues={
                "node-low": ["stale_doc"],
                "node-high": ["undocumented", "oversized"],
                "node-mid": ["undocumented"],
            }
        )
        result = compute_top_offenders(data, DebtWeights())
        assert len(result) == 3
        assert result[0].ref_id == "node-high"
        assert result[1].ref_id == "node-mid"
        assert result[2].ref_id == "node-low"

    def test_scores_computed_correctly(self) -> None:
        """Each reason maps to its configured weight."""
        data = self._zero_data(
            node_issues={
                "alpha": ["undocumented", "stale_doc", "oversized"],
            }
        )
        result = compute_top_offenders(data, DebtWeights())
        assert len(result) == 1
        assert result[0].score == 5.0

    def test_violation_error_uses_rule_error_weight(self) -> None:
        """violation:error:<name> should use rule_error weight."""
        data = self._zero_data(
            node_issues={"v-node": ["violation:error:no-orphans"]}
        )
        result = compute_top_offenders(data, DebtWeights(rule_error=3.0))
        assert len(result) == 1
        assert result[0].score == 3.0

    def test_violation_warning_uses_rule_warning_weight(self) -> None:
        """violation:warning:<name> should use rule_warning weight."""
        data = self._zero_data(
            node_issues={"w-node": ["violation:warning:prefer-docs"]}
        )
        result = compute_top_offenders(data, DebtWeights(rule_warning=1.0))
        assert len(result) == 1
        assert result[0].score == 1.0

    def test_mixed_violation_severities(self) -> None:
        """Node with both error and warning violations scores correctly."""
        data = self._zero_data(
            node_issues={
                "mixed": [
                    "violation:error:rule-a",
                    "violation:warning:rule-b",
                    "violation:error:rule-c",
                ],
            }
        )
        weights = DebtWeights(rule_error=3.0, rule_warning=1.0)
        result = compute_top_offenders(data, weights)
        assert len(result) == 1
        assert result[0].score == 7.0  # 3.0 + 1.0 + 3.0

    def test_legacy_violation_format_uses_rule_error(self) -> None:
        """Bare 'violation:<name>' (no severity) defaults to rule_error."""
        data = self._zero_data(
            node_issues={"legacy": ["violation:some-rule"]}
        )
        result = compute_top_offenders(data, DebtWeights(rule_error=3.0))
        assert len(result) == 1
        assert result[0].score == 3.0

    # -- Reasons --

    def test_reasons_populated_per_node(self) -> None:
        """Each node's reasons list matches its input issues."""
        data = self._zero_data(
            node_issues={
                "multi": ["undocumented", "stale_doc", "oversized"],
            }
        )
        result = compute_top_offenders(data, DebtWeights())
        assert len(result) == 1
        assert "undocumented" in result[0].reasons
        assert "stale_doc" in result[0].reasons
        assert "oversized" in result[0].reasons

    def test_single_reason_node(self) -> None:
        """Node with a single issue has exactly one reason."""
        data = self._zero_data(node_issues={"single": ["dormant"]})
        result = compute_top_offenders(data, DebtWeights())
        assert len(result) == 1
        assert result[0].reasons == ["dormant"]

    def test_multi_reason_node_all_present(self) -> None:
        """Node with many issues lists all of them."""
        reasons = [
            "undocumented", "stale_doc", "oversized",
            "high_fan_out", "dormant", "untested",
            "violation:error:rule-x",
        ]
        data = self._zero_data(node_issues={"heavy": reasons})
        result = compute_top_offenders(data, DebtWeights())
        assert len(result) == 1
        assert len(result[0].reasons) == 7

    # -- Limit --

    def test_default_limit_is_10(self) -> None:
        """With more than 10 nodes, only top 10 are returned."""
        issues: dict[str, list[str]] = {}
        for i in range(15):
            issues[f"node-{i:02d}"] = ["undocumented"]
        data = self._zero_data(node_issues=issues)
        result = compute_top_offenders(data, DebtWeights())
        assert len(result) == 10

    def test_custom_limit_5(self) -> None:
        """Custom limit=5 returns at most 5 nodes."""
        issues: dict[str, list[str]] = {}
        for i in range(12):
            issues[f"node-{i:02d}"] = ["stale_doc"]
        data = self._zero_data(node_issues=issues)
        result = compute_top_offenders(data, DebtWeights(), limit=5)
        assert len(result) == 5

    def test_custom_limit_larger_than_nodes(self) -> None:
        """limit > available nodes returns all nodes."""
        data = self._zero_data(
            node_issues={"a": ["undocumented"], "b": ["stale_doc"]}
        )
        result = compute_top_offenders(data, DebtWeights(), limit=50)
        assert len(result) == 2

    # -- Empty / edge cases --

    def test_empty_node_issues_returns_empty(self) -> None:
        """No node issues means no offenders."""
        data = self._zero_data(node_issues={})
        result = compute_top_offenders(data, DebtWeights())
        assert result == []

    def test_node_with_zero_score_excluded(self) -> None:
        """Nodes with no recognized reasons should not appear."""
        data = self._zero_data(
            node_issues={"ghost": ["unknown_reason_xyz"]}
        )
        result = compute_top_offenders(data, DebtWeights())
        assert result == []

    def test_tie_breaking_alphabetical(self) -> None:
        """Nodes with identical scores are ordered alphabetically."""
        data = self._zero_data(
            node_issues={
                "charlie": ["undocumented"],
                "alpha": ["undocumented"],
                "bravo": ["undocumented"],
            }
        )
        result = compute_top_offenders(data, DebtWeights())
        assert len(result) == 3
        assert result[0].ref_id == "alpha"
        assert result[1].ref_id == "bravo"
        assert result[2].ref_id == "charlie"

    def test_custom_weights_affect_ranking(self) -> None:
        """Custom weights change which node ranks highest."""
        data = self._zero_data(
            node_issues={
                "doc-heavy": ["undocumented", "stale_doc"],
                "complex-heavy": ["oversized", "high_fan_out"],
            }
        )
        weights = DebtWeights(
            undocumented_node=10.0, stale_doc=5.0,
            oversized_domain=0.1, high_fan_out=0.1,
        )
        result = compute_top_offenders(data, weights)
        assert result[0].ref_id == "doc-heavy"
        assert result[0].score == 15.0
        assert result[1].ref_id == "complex-heavy"
        assert result[1].score == pytest.approx(0.2)

    def test_returns_node_debt_instances(self) -> None:
        """All returned items are NodeDebt instances."""
        data = self._zero_data(node_issues={"x": ["untested"]})
        result = compute_top_offenders(data, DebtWeights())
        assert all(isinstance(nd, NodeDebt) for nd in result)

    def test_integration_with_compute_debt_score(self) -> None:
        """compute_debt_score uses compute_top_offenders internally."""
        data = self._zero_data(
            node_issues={
                "a": ["undocumented", "oversized"],
                "b": ["stale_doc"],
            }
        )
        report = compute_debt_score(data)
        assert len(report.top_offenders) == 2
        assert report.top_offenders[0].score >= report.top_offenders[1].score


# ===========================================================================
# 8. format_top_offenders_json (BEAD-06) — JSON serialization
# ===========================================================================


class TestFormatTopOffendersJson:
    """Tests for JSON serialization of top offenders list."""

    def test_empty_list(self) -> None:
        result = format_top_offenders_json([])
        assert result == []

    def test_single_offender(self) -> None:
        offenders = [
            NodeDebt(ref_id="alpha", score=5.0, reasons=["undocumented", "oversized"]),
        ]
        result = format_top_offenders_json(offenders)
        assert len(result) == 1
        assert result[0]["ref_id"] == "alpha"
        assert result[0]["score"] == 5.0
        assert result[0]["reasons"] == ["undocumented", "oversized"]

    def test_multiple_offenders_preserve_order(self) -> None:
        offenders = [
            NodeDebt(ref_id="a", score=10.0, reasons=["undocumented"]),
            NodeDebt(ref_id="b", score=5.0, reasons=["stale_doc"]),
            NodeDebt(ref_id="c", score=1.0, reasons=["dormant"]),
        ]
        result = format_top_offenders_json(offenders)
        assert len(result) == 3
        assert [d["ref_id"] for d in result] == ["a", "b", "c"]

    def test_json_serializable(self) -> None:
        """Output must be JSON-serializable (no custom objects)."""
        import json

        offenders = [NodeDebt(ref_id="x", score=3.0, reasons=["oversized"])]
        result = format_top_offenders_json(offenders)
        serialized = json.dumps(result)
        assert isinstance(serialized, str)

    def test_dict_keys(self) -> None:
        """Each dict has exactly ref_id, score, reasons keys."""
        offenders = [NodeDebt(ref_id="n1", score=2.0, reasons=["untested"])]
        result = format_top_offenders_json(offenders)
        assert set(result[0].keys()) == {"ref_id", "score", "reasons"}


# ===========================================================================
# 9. format_debt_report tests (BEAD-02)
# ===========================================================================


class TestFormatDebtReport:
    """Tests for the Rich-formatted human-readable debt report output."""

    def _make_report(
        self,
        *,
        debt_score: float = 23.0,
        severity: str = "medium",
        categories: list[CategoryScore] | None = None,
        top_offenders: list[NodeDebt] | None = None,
        trend: DebtTrend | None = None,
    ) -> DebtReport:
        if categories is None:
            categories = [
                CategoryScore(
                    name="rule_violations", score=9.0,
                    details={"errors": 2, "warnings": 3},
                ),
                CategoryScore(
                    name="doc_gaps", score=8.0,
                    details={"undocumented": 3, "stale": 4, "untracked": 1},
                ),
                CategoryScore(
                    name="complexity", score=5.0,
                    details={"oversized": 2, "high_fan_out": 1, "dormant": 0},
                ),
                CategoryScore(
                    name="test_gaps", score=1.0,
                    details={"untested": 1},
                ),
            ]
        if top_offenders is None:
            top_offenders = [
                NodeDebt(
                    ref_id="SERVICES", score=8.0,
                    reasons=["violation:rule1", "stale_doc", "oversized"],
                ),
                NodeDebt(
                    ref_id="GRAPH", score=4.0,
                    reasons=["stale_doc", "oversized"],
                ),
            ]
        return DebtReport(
            debt_score=debt_score, severity=severity,
            categories=categories, top_offenders=top_offenders,
            trend=trend,
        )

    def test_returns_non_empty_string(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report()
        result = format_debt_report(report)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_header(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report()
        result = format_debt_report(report)
        assert "Architecture Debt Report" in result

    def test_contains_score(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report(debt_score=23.0)
        result = format_debt_report(report)
        assert "23" in result
        assert "100" in result

    def test_contains_severity_indicator_medium(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report(severity="medium")
        result = format_debt_report(report)
        assert "\u25b2" in result  # triangle

    @staticmethod
    def _zero_categories() -> list[CategoryScore]:
        return [
            CategoryScore(
                name="rule_violations", score=0.0,
                details={"errors": 0, "warnings": 0},
            ),
            CategoryScore(
                name="doc_gaps", score=0.0,
                details={"undocumented": 0, "stale": 0, "untracked": 0},
            ),
            CategoryScore(
                name="complexity", score=0.0,
                details={"oversized": 0, "high_fan_out": 0, "dormant": 0},
            ),
            CategoryScore(
                name="test_gaps", score=0.0,
                details={"untested": 0},
            ),
        ]

    def test_contains_severity_indicator_clean(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report(
            debt_score=0.0, severity="clean",
            categories=self._zero_categories(), top_offenders=[],
        )
        result = format_debt_report(report)
        assert "\u2713" in result

    def test_contains_severity_indicator_critical(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report(debt_score=80.0, severity="critical")
        result = format_debt_report(report)
        assert "\u2716" in result

    def test_contains_category_names(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report()
        result = format_debt_report(report)
        assert "Rule Violations" in result
        assert "Doc Gaps" in result or "Documentation Gaps" in result
        assert "Complexity" in result
        assert "Test Gaps" in result

    def test_contains_category_scores(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report()
        result = format_debt_report(report)
        assert "9" in result
        assert "8" in result

    def test_contains_top_offenders(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report()
        result = format_debt_report(report)
        assert "SERVICES" in result
        assert "GRAPH" in result

    def test_no_top_offenders_section_when_empty(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report(
            debt_score=0.0, severity="clean",
            categories=self._zero_categories(), top_offenders=[],
        )
        result = format_debt_report(report)
        assert "Top Offenders" not in result

    def test_category_item_counts_shown(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report()
        result = format_debt_report(report)
        assert "errors" in result.lower() or "2" in result

    def test_severity_low_indicator(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report(debt_score=5.0, severity="low")
        result = format_debt_report(report)
        assert "\u25cf" in result

    def test_severity_high_indicator(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_report

        report = self._make_report(debt_score=30.0, severity="high")
        result = format_debt_report(report)
        assert "\u25c6" in result


# ===========================================================================
# 10. CLI --debt-report integration tests (BEAD-02)
# ===========================================================================


class TestCliDebtReport:
    """Integration tests for `beadloom status --debt-report`."""

    def _setup_project(self, tmp_path: Path) -> Path:
        """Create a minimal project with graph + DB for testing."""
        import yaml as _yaml

        project = tmp_path / "proj"
        project.mkdir()

        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "graph.yml").write_text(
            _yaml.dump(
                {
                    "nodes": [
                        {
                            "ref_id": "alpha",
                            "kind": "domain",
                            "summary": "Alpha domain",
                        },
                        {
                            "ref_id": "beta",
                            "kind": "domain",
                            "summary": "Beta domain",
                        },
                    ],
                    "edges": [
                        {"src": "alpha", "dst": "beta", "kind": "depends_on"},
                    ],
                }
            )
        )

        docs_dir = project / "docs"
        docs_dir.mkdir()
        (docs_dir / "alpha.md").write_text("## Alpha\n\nAlpha docs.\n")

        src_dir = project / "src"
        src_dir.mkdir()

        from beadloom.infrastructure.reindex import reindex

        reindex(project)
        return project

    def test_debt_report_flag_accepted(self, tmp_path: Path) -> None:
        """The --debt-report flag should be accepted without error."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["status", "--debt-report", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output

    def test_debt_report_shows_score(self, tmp_path: Path) -> None:
        """The debt report should show the debt score."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["status", "--debt-report", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert "Architecture Debt Report" in result.output
        assert "100" in result.output

    def test_debt_report_shows_categories(self, tmp_path: Path) -> None:
        """The debt report should show category breakdown."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["status", "--debt-report", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert "Rule Violations" in result.output
        assert "Test Gaps" in result.output

    def test_status_without_debt_report_unchanged(self, tmp_path: Path) -> None:
        """Plain `beadloom status` should NOT show debt report output."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["status", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert "Architecture Debt Report" not in result.output

    def test_status_json_without_debt_report_unchanged(
        self, tmp_path: Path
    ) -> None:
        """Plain `beadloom status --json` should NOT include debt report."""
        import json as _json

        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["status", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        data = _json.loads(result.output)
        assert "debt_score" not in data

    def test_no_db_returns_error(self, tmp_path: Path) -> None:
        """Without a DB, --debt-report should error the same as status."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            main, ["status", "--debt-report", "--project", str(project)]
        )
        assert result.exit_code != 0


# ===========================================================================
# 11. format_debt_json tests (BEAD-03)
# ===========================================================================


class TestFormatDebtJson:
    """Tests for the JSON serialization of a full DebtReport."""

    @staticmethod
    def _make_report(
        *,
        debt_score: float = 25.0,
        severity: str = "medium",
        categories: list[CategoryScore] | None = None,
        top_offenders: list[NodeDebt] | None = None,
        trend: DebtTrend | None = None,
    ) -> DebtReport:
        if categories is None:
            categories = [
                CategoryScore(
                    name="rule_violations", score=10.0,
                    details={"errors": 2, "warnings": 4},
                ),
                CategoryScore(
                    name="doc_gaps", score=8.0,
                    details={"undocumented": 3, "stale": 1, "untracked": 0},
                ),
                CategoryScore(
                    name="complexity", score=5.0,
                    details={"oversized": 2, "high_fan_out": 1, "dormant": 0},
                ),
                CategoryScore(
                    name="test_gaps", score=2.0,
                    details={"untested": 2},
                ),
            ]
        if top_offenders is None:
            top_offenders = [
                NodeDebt(
                    ref_id="graph", score=8.5,
                    reasons=["violation:error:r1", "violation:warning:r2", "stale_doc"],
                ),
                NodeDebt(
                    ref_id="infra", score=4.0,
                    reasons=["undocumented", "oversized"],
                ),
            ]
        return DebtReport(
            debt_score=debt_score, severity=severity,
            categories=categories, top_offenders=top_offenders,
            trend=trend,
        )

    def test_returns_dict(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report()
        result = format_debt_json(report)
        assert isinstance(result, dict)

    def test_top_level_keys(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report()
        result = format_debt_json(report)
        assert set(result.keys()) == {
            "debt_score", "severity", "categories", "top_offenders", "trend",
        }

    def test_debt_score_and_severity(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report(debt_score=25.0, severity="medium")
        result = format_debt_json(report)
        assert result["debt_score"] == 25.0
        assert result["severity"] == "medium"

    def test_categories_structure(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report()
        result = format_debt_json(report)
        cats = result["categories"]
        assert isinstance(cats, list)
        assert len(cats) == 4
        for cat in cats:
            assert "name" in cat
            assert "score" in cat
            assert "details" in cat

    def test_categories_match_report(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report()
        result = format_debt_json(report)
        cat_names = [c["name"] for c in result["categories"]]
        assert cat_names == ["rule_violations", "doc_gaps", "complexity", "test_gaps"]

    def test_top_offenders_structure(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report()
        result = format_debt_json(report)
        offenders = result["top_offenders"]
        assert isinstance(offenders, list)
        assert len(offenders) == 2
        for o in offenders:
            assert "ref_id" in o
            assert "score" in o
            assert "reasons" in o

    def test_trend_none_when_absent(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report(trend=None)
        result = format_debt_json(report)
        assert result["trend"] is None

    def test_trend_present(self) -> None:
        from beadloom.infrastructure.debt_report import format_debt_json

        trend = DebtTrend(
            previous_snapshot="2026-02-15",
            previous_score=30.0,
            delta=-5.0,
            category_deltas={
                "rule_violations": -3.0,
                "doc_gaps": -1.0,
                "complexity": 0.0,
                "test_gaps": -1.0,
            },
        )
        report = self._make_report(trend=trend)
        result = format_debt_json(report)
        assert result["trend"] is not None
        assert result["trend"]["previous_snapshot"] == "2026-02-15"
        assert result["trend"]["previous_score"] == 30.0
        assert result["trend"]["delta"] == -5.0
        assert result["trend"]["category_deltas"]["rule_violations"] == -3.0

    def test_json_serializable(self) -> None:
        """Result must be fully JSON-serializable."""
        import json as _json

        from beadloom.infrastructure.debt_report import format_debt_json

        trend = DebtTrend(
            previous_snapshot="2026-02-15",
            previous_score=30.0,
            delta=-5.0,
            category_deltas={"rule_violations": -3.0},
        )
        report = self._make_report(trend=trend)
        result = format_debt_json(report)
        serialized = _json.dumps(result)
        assert isinstance(serialized, str)

    def test_empty_report(self) -> None:
        """A clean report with no issues serializes correctly."""
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report(
            debt_score=0.0,
            severity="clean",
            categories=[
                CategoryScore(
                    name="rule_violations", score=0.0,
                    details={"errors": 0, "warnings": 0},
                ),
            ],
            top_offenders=[],
        )
        result = format_debt_json(report)
        assert result["debt_score"] == 0.0
        assert result["severity"] == "clean"
        assert result["top_offenders"] == []

    def test_category_filter(self) -> None:
        """format_debt_json with category filter returns only matching category."""
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report()
        result = format_debt_json(report, category="doc_gaps")
        cats = result["categories"]
        assert len(cats) == 1
        assert cats[0]["name"] == "doc_gaps"

    def test_category_filter_none_returns_all(self) -> None:
        """format_debt_json with category=None returns all categories."""
        from beadloom.infrastructure.debt_report import format_debt_json

        report = self._make_report()
        result = format_debt_json(report)
        assert len(result["categories"]) == 4


# ===========================================================================
# 12. CLI --json + --debt-report integration tests (BEAD-03)
# ===========================================================================


class TestCliDebtReportJson:
    """Integration tests for `beadloom status --debt-report --json`."""

    def _setup_project(self, tmp_path: Path) -> Path:
        """Create a minimal project with graph + DB for testing."""
        import yaml as _yaml

        project = tmp_path / "proj"
        project.mkdir()

        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "graph.yml").write_text(
            _yaml.dump(
                {
                    "nodes": [
                        {
                            "ref_id": "alpha",
                            "kind": "domain",
                            "summary": "Alpha domain",
                        },
                        {
                            "ref_id": "beta",
                            "kind": "domain",
                            "summary": "Beta domain",
                        },
                    ],
                    "edges": [
                        {"src": "alpha", "dst": "beta", "kind": "depends_on"},
                    ],
                }
            )
        )

        docs_dir = project / "docs"
        docs_dir.mkdir()
        (docs_dir / "alpha.md").write_text("## Alpha\n\nAlpha docs.\n")

        src_dir = project / "src"
        src_dir.mkdir()

        from beadloom.infrastructure.reindex import reindex

        reindex(project)
        return project

    def test_json_flag_produces_valid_json(self, tmp_path: Path) -> None:
        """--json with --debt-report should produce valid JSON."""
        import json as _json

        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--json", "--project", str(project)],
        )
        assert result.exit_code == 0, result.output
        data = _json.loads(result.output)
        assert "debt_score" in data
        assert "severity" in data
        assert "categories" in data

    def test_json_schema_matches_spec(self, tmp_path: Path) -> None:
        """JSON output should match the spec schema."""
        import json as _json

        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--json", "--project", str(project)],
        )
        assert result.exit_code == 0, result.output
        data = _json.loads(result.output)
        assert isinstance(data["debt_score"], (int, float))
        assert isinstance(data["severity"], str)
        assert isinstance(data["categories"], list)
        assert isinstance(data["top_offenders"], list)
        # trend can be None or dict
        assert data["trend"] is None or isinstance(data["trend"], dict)

    def test_json_without_debt_report_unchanged(self, tmp_path: Path) -> None:
        """--json WITHOUT --debt-report should be the regular status JSON."""
        import json as _json

        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--json", "--project", str(project)],
        )
        assert result.exit_code == 0, result.output
        data = _json.loads(result.output)
        # Regular status JSON has nodes_count, not debt_score
        assert "nodes_count" in data
        assert "debt_score" not in data


# ===========================================================================
# 13. CLI --fail-if tests (BEAD-03)
# ===========================================================================


class TestCliFailIf:
    """Integration tests for --fail-if CI gate flag."""

    def _setup_project_with_debt(self, tmp_path: Path) -> Path:
        """Create a project that will have a non-zero debt score.

        Creates nodes without documentation so undocumented_count > 0.
        """
        import yaml as _yaml

        project = tmp_path / "proj"
        project.mkdir()

        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "graph.yml").write_text(
            _yaml.dump(
                {
                    "nodes": [
                        {"ref_id": f"node-{i}", "kind": "domain", "summary": f"Node {i}"}
                        for i in range(10)
                    ],
                    "edges": [],
                }
            )
        )

        docs_dir = project / "docs"
        docs_dir.mkdir()
        src_dir = project / "src"
        src_dir.mkdir()

        from beadloom.infrastructure.reindex import reindex

        reindex(project)
        return project

    def test_fail_if_score_above_threshold_exits_1(self, tmp_path: Path) -> None:
        """--fail-if=score>0 should exit 1 when there's any debt."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project_with_debt(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--fail-if=score>0",
             "--project", str(project)],
        )
        assert result.exit_code == 1

    def test_fail_if_score_below_threshold_exits_0(self, tmp_path: Path) -> None:
        """--fail-if=score>1000 should exit 0 when score is well below."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project_with_debt(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--fail-if=score>1000",
             "--project", str(project)],
        )
        assert result.exit_code == 0

    def test_fail_if_errors_above_threshold(self, tmp_path: Path) -> None:
        """--fail-if=errors>1000 should exit 0 when no rule violations."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project_with_debt(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--fail-if=errors>1000",
             "--project", str(project)],
        )
        assert result.exit_code == 0

    def test_fail_if_invalid_expression_errors(self, tmp_path: Path) -> None:
        """Invalid --fail-if expression should produce an error."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project_with_debt(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--fail-if=invalid",
             "--project", str(project)],
        )
        assert result.exit_code != 0

    def test_fail_if_works_with_json(self, tmp_path: Path) -> None:
        """--fail-if can be combined with --json."""
        import json as _json

        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project_with_debt(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--json", "--fail-if=score>0",
             "--project", str(project)],
        )
        # Should still produce valid JSON and exit 1
        assert result.exit_code == 1
        data = _json.loads(result.output)
        assert "debt_score" in data

    def test_fail_if_requires_debt_report(self, tmp_path: Path) -> None:
        """--fail-if without --debt-report should be ignored or error."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project_with_debt(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--fail-if=score>0", "--project", str(project)],
        )
        # Should succeed but ignore fail-if since no debt report
        assert result.exit_code == 0


# ===========================================================================
# 14. CLI --category filter tests (BEAD-03)
# ===========================================================================


class TestCliCategoryFilter:
    """Integration tests for --category filter flag."""

    def _setup_project(self, tmp_path: Path) -> Path:
        import yaml as _yaml

        project = tmp_path / "proj"
        project.mkdir()

        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "graph.yml").write_text(
            _yaml.dump(
                {
                    "nodes": [
                        {"ref_id": "alpha", "kind": "domain", "summary": "Alpha"},
                    ],
                    "edges": [],
                }
            )
        )

        docs_dir = project / "docs"
        docs_dir.mkdir()
        src_dir = project / "src"
        src_dir.mkdir()

        from beadloom.infrastructure.reindex import reindex

        reindex(project)
        return project

    def test_category_filter_human_output(self, tmp_path: Path) -> None:
        """--category=rules should filter human output."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--category=rules",
             "--project", str(project)],
        )
        assert result.exit_code == 0, result.output
        assert "Rule Violations" in result.output

    def test_category_filter_json_output(self, tmp_path: Path) -> None:
        """--category=docs with --json should return only docs category."""
        import json as _json

        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--json", "--category=docs",
             "--project", str(project)],
        )
        assert result.exit_code == 0, result.output
        data = _json.loads(result.output)
        assert len(data["categories"]) == 1
        assert data["categories"][0]["name"] == "doc_gaps"

    def test_category_invalid_name_errors(self, tmp_path: Path) -> None:
        """Invalid category name should produce an error."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--category=nonexistent",
             "--project", str(project)],
        )
        assert result.exit_code != 0


# ===========================================================================
# 15. BEAD-07 — Edge case / coverage augmentation tests
# ===========================================================================


class TestLoadDebtWeightsEdgeCases:
    """Edge cases for load_debt_weights: invalid YAML, non-dict data, etc."""

    def test_invalid_yaml_returns_defaults(self, project_root: Path) -> None:
        """Malformed YAML content falls back to defaults."""
        config_path = project_root / "config.yml"
        config_path.write_text(": : : invalid yaml [[[", encoding="utf-8")
        weights = load_debt_weights(project_root)
        assert weights == DebtWeights()

    def test_yaml_with_non_dict_root_returns_defaults(
        self, project_root: Path,
    ) -> None:
        """A YAML list at root level should return defaults."""
        config_path = project_root / "config.yml"
        config_path.write_text("- item1\n- item2\n", encoding="utf-8")
        weights = load_debt_weights(project_root)
        assert weights == DebtWeights()

    def test_debt_section_is_string_returns_defaults(
        self, project_root: Path,
    ) -> None:
        """debt_report set to a string (not dict) returns defaults."""
        config = {"debt_report": "not_a_dict"}
        config_path = project_root / "config.yml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")
        weights = load_debt_weights(project_root)
        assert weights == DebtWeights()

    def test_weights_data_is_non_dict_returns_defaults(
        self, project_root: Path,
    ) -> None:
        """debt_report.weights set to a string falls back to empty dict."""
        config = {"debt_report": {"weights": "not_a_dict"}}
        config_path = project_root / "config.yml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")
        weights = load_debt_weights(project_root)
        # All weights should be defaults since weights_data was invalid
        assert weights.rule_error == 3.0
        assert weights.rule_warning == 1.0

    def test_thresholds_data_is_non_dict_returns_defaults(
        self, project_root: Path,
    ) -> None:
        """debt_report.thresholds set to a list falls back to empty dict."""
        config = {
            "debt_report": {
                "weights": {"rule_error": 5},
                "thresholds": [1, 2, 3],
            }
        }
        config_path = project_root / "config.yml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")
        weights = load_debt_weights(project_root)
        # Custom weight applied, thresholds are defaults
        assert weights.rule_error == 5.0
        assert weights.oversized_symbols == 200
        assert weights.high_fan_out_threshold == 10
        assert weights.dormant_months == 3

    def test_empty_yaml_file_returns_defaults(
        self, project_root: Path,
    ) -> None:
        """An empty config.yml (yaml.safe_load returns None) returns defaults."""
        config_path = project_root / "config.yml"
        config_path.write_text("", encoding="utf-8")
        weights = load_debt_weights(project_root)
        assert weights == DebtWeights()


class TestSeverityLabelEdgeCases:
    """Edge case boundary tests for _severity_label."""

    def test_negative_score_is_clean(self) -> None:
        """Negative scores (theoretically impossible) map to clean."""
        assert _severity_label(-1.0) == "clean"

    def test_score_0_5_is_low(self) -> None:
        """Fractional scores in low range."""
        assert _severity_label(0.5) == "low"

    def test_score_10_5_is_medium(self) -> None:
        """Score 10.5 is in the medium range (11-25)."""
        assert _severity_label(10.5) == "medium"

    def test_score_25_5_is_high(self) -> None:
        """Score 25.5 is in the high range (26-50)."""
        assert _severity_label(25.5) == "high"

    def test_score_above_100_is_critical(self) -> None:
        """Scores above 100 (should be capped, but still critical)."""
        assert _severity_label(150.0) == "critical"


class TestComputeTopOffendersEdgeCases:
    """Edge cases for compute_top_offenders."""

    @staticmethod
    def _zero_data(**overrides: object) -> DebtData:
        defaults: dict[str, object] = {
            "error_count": 0,
            "warning_count": 0,
            "undocumented_count": 0,
            "stale_count": 0,
            "untracked_count": 0,
            "oversized_count": 0,
            "high_fan_out_count": 0,
            "dormant_count": 0,
            "untested_count": 0,
            "node_issues": {},
        }
        defaults.update(overrides)
        return DebtData(**defaults)  # type: ignore[arg-type]

    def test_limit_zero_returns_empty(self) -> None:
        """limit=0 returns empty list."""
        data = self._zero_data(
            node_issues={"a": ["undocumented"], "b": ["stale_doc"]}
        )
        result = compute_top_offenders(data, DebtWeights(), limit=0)
        assert result == []

    def test_node_with_many_reasons_accumulates_score(self) -> None:
        """Node with all issue types gets cumulative score."""
        all_reasons = [
            "undocumented", "stale_doc", "oversized",
            "high_fan_out", "dormant", "untested",
            "violation:error:r1", "violation:warning:r2",
        ]
        data = self._zero_data(node_issues={"mega": all_reasons})
        weights = DebtWeights()
        result = compute_top_offenders(data, weights)
        assert len(result) == 1
        expected = (
            weights.undocumented_node + weights.stale_doc
            + weights.oversized_domain + weights.high_fan_out
            + weights.dormant_domain + weights.untested_domain
            + weights.rule_error + weights.rule_warning
        )
        assert result[0].score == expected


class TestTrendArrow:
    """Tests for _trend_arrow helper."""

    def test_negative_delta_improved(self) -> None:
        arrow, label = _trend_arrow(-5.0)
        assert arrow == "\u2193"
        assert label == "improved"

    def test_positive_delta_regressed(self) -> None:
        arrow, label = _trend_arrow(3.0)
        assert arrow == "\u2191"
        assert label == "regressed"

    def test_zero_delta_unchanged(self) -> None:
        arrow, label = _trend_arrow(0.0)
        assert arrow == "="
        assert label == "unchanged"

    def test_very_small_positive_delta(self) -> None:
        arrow, label = _trend_arrow(0.001)
        assert arrow == "\u2191"
        assert label == "regressed"

    def test_very_small_negative_delta(self) -> None:
        arrow, label = _trend_arrow(-0.001)
        assert arrow == "\u2193"
        assert label == "improved"


class TestComputeSnapshotDebt:
    """Tests for _compute_snapshot_debt (snapshot-based debt calculation)."""

    def test_empty_snapshot_returns_zero(self) -> None:
        """Empty snapshot (no nodes, no edges) -> zero score."""
        total, cats = _compute_snapshot_debt([], [], 0, DebtWeights())
        assert total == 0.0
        assert cats["complexity"] == 0.0
        assert cats["rule_violations"] == 0.0
        assert cats["doc_gaps"] == 0.0
        assert cats["test_gaps"] == 0.0

    def test_high_fan_out_from_edges(self) -> None:
        """Edges with high fan-out should contribute to complexity."""
        nodes = [{"ref_id": "hub"}]
        # 11 outgoing edges from hub -> exceeds default threshold of 10
        edges = [
            {"src_ref_id": "hub", "dst_ref_id": f"target-{i}"}
            for i in range(11)
        ]
        weights = DebtWeights(high_fan_out_threshold=10, high_fan_out=2.0)
        total, cats = _compute_snapshot_debt(nodes, edges, 0, weights)
        assert cats["complexity"] == 2.0  # 1 hub exceeding threshold * 2.0
        assert total == 2.0

    def test_no_fan_out_exceeding_threshold(self) -> None:
        """Edges below threshold should not contribute."""
        nodes = [{"ref_id": "hub"}]
        edges = [
            {"src_ref_id": "hub", "dst_ref_id": f"target-{i}"}
            for i in range(5)
        ]
        weights = DebtWeights(high_fan_out_threshold=10)
        total, cats = _compute_snapshot_debt(nodes, edges, 0, weights)
        assert cats["complexity"] == 0.0
        assert total == 0.0

    def test_multiple_high_fan_out_nodes(self) -> None:
        """Two nodes exceeding threshold doubles score."""
        nodes = [{"ref_id": "hub1"}, {"ref_id": "hub2"}]
        edges = [
            *[{"src_ref_id": "hub1", "dst_ref_id": f"t1-{i}"} for i in range(12)],
            *[{"src_ref_id": "hub2", "dst_ref_id": f"t2-{i}"} for i in range(15)],
        ]
        weights = DebtWeights(high_fan_out_threshold=10, high_fan_out=1.0)
        total, cats = _compute_snapshot_debt(nodes, edges, 0, weights)
        assert cats["complexity"] == 2.0  # 2 nodes * 1.0
        assert total == 2.0

    def test_score_capped_at_100(self) -> None:
        """Snapshot debt score should be capped at 100."""
        nodes = [{"ref_id": f"hub-{i}"} for i in range(200)]
        edges = []
        for i in range(200):
            for j in range(15):
                edges.append({
                    "src_ref_id": f"hub-{i}",
                    "dst_ref_id": f"target-{i}-{j}",
                })
        weights = DebtWeights(high_fan_out_threshold=10, high_fan_out=5.0)
        total, _ = _compute_snapshot_debt(nodes, edges, 0, weights)
        assert total == 100.0

    def test_empty_src_ref_id_ignored(self) -> None:
        """Edges with empty src_ref_id are skipped."""
        edges = [
            {"src_ref_id": "", "dst_ref_id": "target"},
            {"dst_ref_id": "target"},  # missing src_ref_id
        ]
        total, _cats = _compute_snapshot_debt([], edges, 0, DebtWeights())
        assert total == 0.0


class TestFormatTrendSection:
    """Tests for format_trend_section (text rendering of trend data)."""

    def test_none_trend_returns_no_baseline(self) -> None:
        """When trend is None, return 'No baseline snapshot available'."""
        result = format_trend_section(None)
        assert "No baseline snapshot available" in result

    def test_basic_trend_rendering(self) -> None:
        """Trend with deltas renders correctly."""
        trend = DebtTrend(
            previous_snapshot="2026-02-15T10:00:00",
            previous_score=20.0,
            delta=-5.0,
            category_deltas={
                "rule_violations": -3.0,
                "doc_gaps": -1.0,
                "complexity": 0.0,
                "test_gaps": -1.0,
            },
        )
        result = format_trend_section(trend)
        assert "Trend (vs 2026-02-15):" in result
        assert "Overall:" in result
        assert "20" in result  # previous score
        assert "15" in result  # current = 20 + (-5) = 15
        assert "\u2193" in result  # down arrow for improvement
        assert "improved" in result

    def test_trend_with_label_in_snapshot(self) -> None:
        """Snapshot label in date string is stripped for display."""
        trend = DebtTrend(
            previous_snapshot="2026-02-15 [v1.6.0]",
            previous_score=10.0,
            delta=0.0,
            category_deltas={
                "rule_violations": 0.0,
                "doc_gaps": 0.0,
                "complexity": 0.0,
                "test_gaps": 0.0,
            },
        )
        result = format_trend_section(trend)
        assert "2026-02-15" in result
        assert "[v1.6.0]" not in result

    def test_trend_regression_shows_up_arrow(self) -> None:
        """Positive delta shows up arrow and 'regressed'."""
        trend = DebtTrend(
            previous_snapshot="2026-02-10",
            previous_score=5.0,
            delta=10.0,
            category_deltas={
                "rule_violations": 10.0,
                "doc_gaps": 0.0,
                "complexity": 0.0,
                "test_gaps": 0.0,
            },
        )
        result = format_trend_section(trend)
        assert "\u2191" in result  # up arrow
        assert "regressed" in result

    def test_trend_unchanged_shows_equals(self) -> None:
        """Zero delta shows = and 'unchanged'."""
        trend = DebtTrend(
            previous_snapshot="2026-02-10",
            previous_score=10.0,
            delta=0.0,
            category_deltas={
                "rule_violations": 0.0,
                "doc_gaps": 0.0,
                "complexity": 0.0,
                "test_gaps": 0.0,
            },
        )
        result = format_trend_section(trend)
        assert "=" in result
        assert "unchanged" in result

    def test_all_category_names_present(self) -> None:
        """All 4 category short names appear in output."""
        trend = DebtTrend(
            previous_snapshot="2026-02-10",
            previous_score=10.0,
            delta=-2.0,
            category_deltas={
                "rule_violations": -1.0,
                "doc_gaps": 0.0,
                "complexity": -1.0,
                "test_gaps": 0.0,
            },
        )
        result = format_trend_section(trend)
        assert "Rules:" in result
        assert "Docs:" in result
        assert "Complexity:" in result
        assert "Tests:" in result


class TestComputeDebtTrend:
    """Tests for compute_debt_trend with snapshot data."""

    @pytest.fixture()
    def conn_with_snapshot(
        self, conn: sqlite3.Connection, project_root: Path,
    ) -> sqlite3.Connection:
        """Create a DB with a graph snapshot for trend testing."""
        import json as _json

        # Ensure graph_snapshots table exists
        conn.execute(
            "CREATE TABLE IF NOT EXISTS graph_snapshots ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  nodes_json TEXT NOT NULL,"
            "  edges_json TEXT NOT NULL,"
            "  symbols_count INTEGER NOT NULL DEFAULT 0,"
            "  label TEXT,"
            "  created_at TEXT NOT NULL"
            ")"
        )
        nodes_json = _json.dumps([{"ref_id": "alpha"}, {"ref_id": "beta"}])
        edges_json = _json.dumps([
            {"src_ref_id": "alpha", "dst_ref_id": "beta"},
        ])
        conn.execute(
            "INSERT INTO graph_snapshots "
            "(nodes_json, edges_json, symbols_count, label, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (nodes_json, edges_json, 50, "v1.0", "2026-02-15T10:00:00"),
        )
        conn.commit()
        return conn

    def test_no_snapshots_returns_none(
        self, conn: sqlite3.Connection, project_root: Path,
    ) -> None:
        """With no snapshots, trend should be None."""
        report = compute_debt_score(
            DebtData(
                error_count=0, warning_count=0, undocumented_count=0,
                stale_count=0, untracked_count=0, oversized_count=0,
                high_fan_out_count=0, dormant_count=0, untested_count=0,
                node_issues={},
            )
        )
        # Ensure graph_snapshots table exists for the test
        conn.execute(
            "CREATE TABLE IF NOT EXISTS graph_snapshots ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  nodes_json TEXT NOT NULL,"
            "  edges_json TEXT NOT NULL,"
            "  symbols_count INTEGER NOT NULL DEFAULT 0,"
            "  label TEXT,"
            "  created_at TEXT NOT NULL"
            ")"
        )
        conn.commit()
        trend = compute_debt_trend(conn, report, project_root)
        assert trend is None

    def test_trend_with_snapshot_returns_debt_trend(
        self,
        conn_with_snapshot: sqlite3.Connection,
        project_root: Path,
    ) -> None:
        """With a snapshot, trend should return a DebtTrend."""
        report = DebtReport(
            debt_score=10.0,
            severity="low",
            categories=[
                CategoryScore(name="rule_violations", score=5.0, details={}),
                CategoryScore(name="doc_gaps", score=2.0, details={}),
                CategoryScore(name="complexity", score=2.0, details={}),
                CategoryScore(name="test_gaps", score=1.0, details={}),
            ],
            top_offenders=[],
            trend=None,
        )
        trend = compute_debt_trend(
            conn_with_snapshot, report, project_root,
        )
        assert trend is not None
        assert isinstance(trend, DebtTrend)
        assert "2026-02-15" in trend.previous_snapshot
        assert "v1.0" in trend.previous_snapshot
        assert isinstance(trend.delta, float)
        assert "rule_violations" in trend.category_deltas
        assert "doc_gaps" in trend.category_deltas
        assert "complexity" in trend.category_deltas
        assert "test_gaps" in trend.category_deltas


class TestFormatDebtJsonEdgeCases:
    """Additional edge cases for format_debt_json."""

    def test_category_filter_short_name_rules(self) -> None:
        """Short name 'rules' maps to 'rule_violations'."""
        report = DebtReport(
            debt_score=5.0,
            severity="low",
            categories=[
                CategoryScore(
                    name="rule_violations", score=5.0,
                    details={"errors": 1, "warnings": 2},
                ),
                CategoryScore(name="doc_gaps", score=0.0, details={}),
            ],
            top_offenders=[],
            trend=None,
        )
        result = format_debt_json(report, category="rules")
        assert len(result["categories"]) == 1
        assert result["categories"][0]["name"] == "rule_violations"

    def test_category_filter_short_name_tests(self) -> None:
        """Short name 'tests' maps to 'test_gaps'."""
        report = DebtReport(
            debt_score=5.0,
            severity="low",
            categories=[
                CategoryScore(name="rule_violations", score=3.0, details={}),
                CategoryScore(name="test_gaps", score=2.0, details={"untested": 2}),
            ],
            top_offenders=[],
            trend=None,
        )
        result = format_debt_json(report, category="tests")
        assert len(result["categories"]) == 1
        assert result["categories"][0]["name"] == "test_gaps"

    def test_nonexistent_category_filter_returns_empty(self) -> None:
        """Filtering by a name that matches nothing yields empty list."""
        report = DebtReport(
            debt_score=5.0,
            severity="low",
            categories=[
                CategoryScore(name="rule_violations", score=5.0, details={}),
            ],
            top_offenders=[],
            trend=None,
        )
        result = format_debt_json(report, category="nonexistent_xyz")
        assert result["categories"] == []

    def test_json_output_is_valid_json(self) -> None:
        """Full round-trip: format_debt_json -> json.dumps -> json.loads."""
        import json as _json

        trend = DebtTrend(
            previous_snapshot="2026-02-15",
            previous_score=20.0,
            delta=-5.0,
            category_deltas={"rule_violations": -2.0, "doc_gaps": -3.0},
        )
        report = DebtReport(
            debt_score=15.0,
            severity="medium",
            categories=[
                CategoryScore(
                    name="rule_violations", score=8.0,
                    details={"errors": 2, "warnings": 2},
                ),
                CategoryScore(
                    name="doc_gaps", score=4.0,
                    details={"undocumented": 2, "stale": 0, "untracked": 0},
                ),
                CategoryScore(
                    name="complexity", score=2.0,
                    details={"oversized": 1, "high_fan_out": 0, "dormant": 0},
                ),
                CategoryScore(
                    name="test_gaps", score=1.0,
                    details={"untested": 1},
                ),
            ],
            top_offenders=[
                NodeDebt(ref_id="alpha", score=5.0, reasons=["undocumented"]),
            ],
            trend=trend,
        )
        result = format_debt_json(report)
        serialized = _json.dumps(result)
        parsed = _json.loads(serialized)
        assert parsed["debt_score"] == 15.0
        assert parsed["trend"]["delta"] == -5.0


class TestCollectDebtDataEdgeCases:
    """Additional edge cases for collect_debt_data and helper functions."""

    def test_untracked_nodes_counted(
        self, conn: sqlite3.Connection, project_root: Path,
    ) -> None:
        """Nodes with source but no sync_state entry are untracked."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("orphan", "domain", "Orphan domain", "src/orphan/"),
        )
        conn.commit()
        data = collect_debt_data(conn, project_root)
        assert data.untracked_count >= 1

    def test_oversized_below_threshold_not_counted(
        self, conn: sqlite3.Connection, project_root: Path,
    ) -> None:
        """Nodes with fewer symbols than threshold are not oversized."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("small-domain", "domain", "Small", "src/small/"),
        )
        # Insert 5 code symbols — well below threshold of 200
        for i in range(5):
            conn.execute(
                "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                "line_start, line_end, annotations, file_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"src/small/mod{i}.py", f"func_{i}", "function", 1, 10, "{}", "h"),
            )
        conn.commit()
        data = collect_debt_data(conn, project_root)
        assert data.oversized_count == 0

    def test_high_fan_out_at_threshold_not_counted(
        self, conn: sqlite3.Connection, project_root: Path,
    ) -> None:
        """Nodes with exactly threshold edges are NOT high fan-out (> not >=)."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("border-hub", "feature", "Border hub"),
        )
        # Exactly 10 edges (threshold is 10, need >10 to flag)
        for i in range(10):
            target = f"border-target-{i}"
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
                (target, "feature", f"Target {i}"),
            )
            conn.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
                ("border-hub", target, "uses"),
            )
        conn.commit()
        data = collect_debt_data(conn, project_root)
        assert data.high_fan_out_count == 0

    def test_multiple_stale_docs_for_same_ref_counted_once(
        self, conn: sqlite3.Connection, project_root: Path,
    ) -> None:
        """Multiple stale entries for same ref_id count as 1 due to DISTINCT."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("multi-stale", "domain", "Multi"),
        )
        for i in range(3):
            conn.execute(
                "INSERT INTO sync_state (doc_path, code_path, ref_id, "
                "code_hash_at_sync, doc_hash_at_sync, synced_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    f"multi-stale-{i}.md", f"src/multi-stale/f{i}.py",
                    "multi-stale", "h1", "h2", "2026-01-01T00:00:00", "stale",
                ),
            )
        conn.commit()
        data = collect_debt_data(conn, project_root)
        assert data.stale_count == 1  # DISTINCT ref_id

    def test_collect_with_custom_weights(
        self, conn: sqlite3.Connection, project_root: Path,
    ) -> None:
        """Custom weights change oversized threshold."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("custom-thresh", "domain", "Custom", "src/custom/"),
        )
        # Insert 50 symbols
        for i in range(50):
            conn.execute(
                "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                "line_start, line_end, annotations, file_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"src/custom/m{i}.py", f"fn_{i}", "function", 1, 10, "{}", "h"),
            )
        conn.commit()
        # With threshold=30, 50 symbols should be oversized
        low_weights = DebtWeights(oversized_symbols=30)
        data = collect_debt_data(conn, project_root, weights=low_weights)
        assert data.oversized_count == 1


class TestComputeDebtScoreEdgeCases:
    """More edge cases for compute_debt_score."""

    def test_very_high_counts_cap_at_100(self) -> None:
        """Extreme counts should still cap at 100."""
        data = DebtData(
            error_count=1000,
            warning_count=1000,
            undocumented_count=1000,
            stale_count=1000,
            untracked_count=1000,
            oversized_count=1000,
            high_fan_out_count=1000,
            dormant_count=1000,
            untested_count=1000,
            node_issues={},
        )
        report = compute_debt_score(data)
        assert report.debt_score == 100.0
        assert report.severity == "critical"

    def test_only_doc_gaps_category(self) -> None:
        """Only doc-related counts produce doc_gaps category score."""
        data = DebtData(
            error_count=0, warning_count=0,
            undocumented_count=5, stale_count=3, untracked_count=2,
            oversized_count=0, high_fan_out_count=0, dormant_count=0,
            untested_count=0, node_issues={},
        )
        report = compute_debt_score(data)
        doc_cat = next(c for c in report.categories if c.name == "doc_gaps")
        # 5 * 2.0 + 3 * 1.0 + 2 * 0.5 = 10 + 3 + 1 = 14
        assert doc_cat.score == 14.0
        assert doc_cat.details["undocumented"] == 5
        assert doc_cat.details["stale"] == 3
        assert doc_cat.details["untracked"] == 2

    def test_only_complexity_category(self) -> None:
        """Only complexity counts produce complexity category score."""
        data = DebtData(
            error_count=0, warning_count=0,
            undocumented_count=0, stale_count=0, untracked_count=0,
            oversized_count=2, high_fan_out_count=3, dormant_count=4,
            untested_count=0, node_issues={},
        )
        report = compute_debt_score(data)
        cplx_cat = next(c for c in report.categories if c.name == "complexity")
        # 2 * 2.0 + 3 * 1.0 + 4 * 0.5 = 4 + 3 + 2 = 9
        assert cplx_cat.score == 9.0

    def test_only_test_gaps_category(self) -> None:
        """Only untested count produces test_gaps score."""
        data = DebtData(
            error_count=0, warning_count=0,
            undocumented_count=0, stale_count=0, untracked_count=0,
            oversized_count=0, high_fan_out_count=0, dormant_count=0,
            untested_count=7, node_issues={},
        )
        report = compute_debt_score(data)
        test_cat = next(c for c in report.categories if c.name == "test_gaps")
        # 7 * 1.0 = 7
        assert test_cat.score == 7.0

    def test_score_exactly_at_boundary_values(self) -> None:
        """Score exactly at severity boundary thresholds."""
        # Score = 10.0 -> low
        data = DebtData(
            error_count=0, warning_count=10,  # 10 * 1.0 = 10
            undocumented_count=0, stale_count=0, untracked_count=0,
            oversized_count=0, high_fan_out_count=0, dormant_count=0,
            untested_count=0, node_issues={},
        )
        report = compute_debt_score(data)
        assert report.debt_score == 10.0
        assert report.severity == "low"

    def test_report_trend_is_always_none_from_compute(self) -> None:
        """compute_debt_score always sets trend to None."""
        data = DebtData(
            error_count=1, warning_count=0,
            undocumented_count=0, stale_count=0, untracked_count=0,
            oversized_count=0, high_fan_out_count=0, dormant_count=0,
            untested_count=0, node_issues={},
        )
        report = compute_debt_score(data)
        assert report.trend is None


class TestFormatDebtReportEdgeCases:
    """Additional edge cases for format_debt_report Rich rendering."""

    def test_single_point_uses_pt_not_pts(self) -> None:
        """Score of exactly 1.0 should use 'pt' singular label."""
        from beadloom.infrastructure.debt_report import format_debt_report

        report = DebtReport(
            debt_score=1.0,
            severity="low",
            categories=[
                CategoryScore(
                    name="test_gaps", score=1.0,
                    details={"untested": 1},
                ),
            ],
            top_offenders=[
                NodeDebt(ref_id="alpha", score=1.0, reasons=["untested"]),
            ],
            trend=None,
        )
        result = format_debt_report(report)
        assert "1 pt" in result

    def test_unknown_severity_uses_fallback(self) -> None:
        """Unknown severity string uses fallback indicator."""
        from beadloom.infrastructure.debt_report import format_debt_report

        report = DebtReport(
            debt_score=5.0,
            severity="unknown_severity",
            categories=[
                CategoryScore(
                    name="rule_violations", score=5.0,
                    details={"errors": 1, "warnings": 2},
                ),
            ],
            top_offenders=[],
            trend=None,
        )
        # Should not crash, uses fallback "?" indicator
        result = format_debt_report(report)
        assert isinstance(result, str)
        assert len(result) > 0


class TestCliFailIfEdgeCases:
    """Edge cases for --fail-if behavior."""

    def _setup_project_with_debt(self, tmp_path: Path) -> Path:
        """Create a project with known debt (10 undocumented nodes)."""
        import yaml as _yaml

        project = tmp_path / "proj"
        project.mkdir()

        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "graph.yml").write_text(
            _yaml.dump(
                {
                    "nodes": [
                        {"ref_id": f"node-{i}", "kind": "domain", "summary": f"Node {i}"}
                        for i in range(10)
                    ],
                    "edges": [],
                }
            )
        )

        (project / "docs").mkdir()
        (project / "src").mkdir()

        from beadloom.infrastructure.reindex import reindex as do_reindex

        do_reindex(project)
        return project

    def test_fail_if_score_exactly_at_threshold_passes(
        self, tmp_path: Path,
    ) -> None:
        """--fail-if=score>N passes when score == N (strictly greater)."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project_with_debt(tmp_path)

        # First get the actual score
        import json as _json

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--json", "--project", str(project)],
        )
        score = _json.loads(result.output)["debt_score"]

        # Now test with threshold exactly at score
        threshold = int(score)
        result = runner.invoke(
            main,
            ["status", "--debt-report", f"--fail-if=score>{threshold}",
             "--project", str(project)],
        )
        # score > threshold should fail if score is a float above threshold
        # If score == threshold exactly, exit_code should be 0
        if score > threshold:
            assert result.exit_code == 1
        else:
            assert result.exit_code == 0

    def test_fail_if_errors_zero_with_no_violations(
        self, tmp_path: Path,
    ) -> None:
        """--fail-if=errors>0 passes when no rule violations exist."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project_with_debt(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["status", "--debt-report", "--fail-if=errors>0",
             "--project", str(project)],
        )
        # No rules.yml means no violations -> errors=0 -> 0 > 0 is false -> exit 0
        assert result.exit_code == 0


class TestMcpDebtReport:
    """Tests for the MCP get_debt_report handler."""

    def _setup_project(self, tmp_path: Path) -> Path:
        """Create a minimal project for MCP testing."""
        import yaml as _yaml

        project = tmp_path / "proj"
        project.mkdir()

        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "graph.yml").write_text(
            _yaml.dump(
                {
                    "nodes": [
                        {"ref_id": "alpha", "kind": "domain", "summary": "Alpha"},
                    ],
                    "edges": [],
                }
            )
        )

        (project / "docs").mkdir()
        (project / "src").mkdir()

        from beadloom.infrastructure.reindex import reindex as do_reindex

        do_reindex(project)
        return project

    def test_mcp_get_debt_report_basic(self, tmp_path: Path) -> None:
        """MCP handler returns valid debt report dict."""
        from beadloom.infrastructure.db import open_db
        from beadloom.services.mcp_server import handle_get_debt_report

        project = self._setup_project(tmp_path)
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)

        result = handle_get_debt_report(conn, project)
        conn.close()

        assert "debt_score" in result
        assert "severity" in result
        assert "categories" in result
        assert "top_offenders" in result
        assert "trend" in result
        assert result["trend"] is None  # no snapshots

    def test_mcp_get_debt_report_with_category_filter(
        self, tmp_path: Path,
    ) -> None:
        """MCP handler with category filter returns filtered categories."""
        from beadloom.infrastructure.db import open_db
        from beadloom.services.mcp_server import handle_get_debt_report

        project = self._setup_project(tmp_path)
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)

        result = handle_get_debt_report(conn, project, category="docs")
        conn.close()

        cats = result["categories"]
        assert len(cats) == 1
        assert cats[0]["name"] == "doc_gaps"

    def test_mcp_dispatch_get_debt_report(self, tmp_path: Path) -> None:
        """_dispatch_tool routes get_debt_report correctly."""
        from beadloom.infrastructure.db import open_db
        from beadloom.services.mcp_server import _dispatch_tool

        project = self._setup_project(tmp_path)
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)

        result = _dispatch_tool(
            conn, "get_debt_report", {}, project_root=project,
        )
        conn.close()

        assert "debt_score" in result
        assert "severity" in result

    def test_mcp_dispatch_get_debt_report_requires_project_root(
        self, tmp_path: Path,
    ) -> None:
        """get_debt_report without project_root raises ValueError."""
        from beadloom.infrastructure.db import open_db
        from beadloom.services.mcp_server import _dispatch_tool

        project = self._setup_project(tmp_path)
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)

        with pytest.raises(ValueError, match="get_debt_report requires project_root"):
            _dispatch_tool(conn, "get_debt_report", {}, project_root=None)
        conn.close()


# ===========================================================================
# BDL-027 BEAD-03: Issue #39 — _count_untracked returns tuple
# ===========================================================================


class TestCountUntrackedReturnsTuple:
    """#39: _count_untracked should return (count, list[str]) not just int."""

    def test_returns_tuple_with_ref_ids(
        self, conn: sqlite3.Connection,
    ) -> None:
        """Untracked nodes are returned as (count, [ref_ids])."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("orphan-a", "domain", "A", "src/a/"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("orphan-b", "feature", "B", "src/b/"),
        )
        conn.commit()
        count, ref_ids = _count_untracked(conn)
        assert count == 2
        assert set(ref_ids) == {"orphan-a", "orphan-b"}

    def test_empty_returns_zero_and_empty_list(
        self, conn: sqlite3.Connection,
    ) -> None:
        """No untracked nodes -> (0, [])."""
        count, ref_ids = _count_untracked(conn)
        assert count == 0
        assert ref_ids == []

    def test_tracked_node_excluded(
        self, conn: sqlite3.Connection,
    ) -> None:
        """Nodes with sync_state entries are not untracked."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tracked", "domain", "Tracked", "src/tracked/"),
        )
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, "
            "code_hash_at_sync, doc_hash_at_sync, synced_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("tracked.md", "src/tracked/main.py", "tracked", "h1", "h2",
             "2026-01-01T00:00:00", "ok"),
        )
        conn.commit()
        count, ref_ids = _count_untracked(conn)
        assert count == 0
        assert ref_ids == []

    def test_untracked_refs_in_collect_debt_data_node_issues(
        self, conn: sqlite3.Connection, project_root: Path,
    ) -> None:
        """collect_debt_data records untracked refs in node_issues."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("untracked-x", "domain", "X", "src/x/"),
        )
        conn.commit()
        data = collect_debt_data(conn, project_root)
        assert "untracked" in data.node_issues.get("untracked-x", [])


# ===========================================================================
# BDL-027 BEAD-03: Issue #40 — _count_oversized excludes child node symbols
# ===========================================================================


class TestCountOversizedExcludesChildren:
    """#40: _count_oversized should not count symbols owned by child nodes."""

    def test_parent_excludes_child_symbols(
        self, conn: sqlite3.Connection,
    ) -> None:
        """Parent node should not count symbols from child node's source prefix."""
        # Parent: source=src/beadloom/
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("parent", "service", "Parent", "src/beadloom/"),
        )
        # Child: source=src/beadloom/graph/
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("child", "domain", "Child", "src/beadloom/graph/"),
        )
        # Edge: child part_of parent
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("child", "parent", "part_of"),
        )
        # 150 symbols in parent's own files (src/beadloom/*.py)
        for i in range(150):
            conn.execute(
                "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                "line_start, line_end, annotations, file_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"src/beadloom/mod{i}.py", f"func_{i}", "function", 1, 10, "{}", "h"),
            )
        # 100 symbols in child's files (src/beadloom/graph/*.py)
        for i in range(100):
            conn.execute(
                "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                "line_start, line_end, annotations, file_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"src/beadloom/graph/g{i}.py", f"gfunc_{i}", "function", 1, 10, "{}", "h"),
            )
        conn.commit()

        # Threshold 200: parent has 150 own + 100 child = 250 total
        # Without fix: parent counted as oversized (250 > 200)
        # With fix: parent has only 150 own symbols, not oversized
        _count, refs = _count_oversized(conn, threshold=200)
        assert "parent" not in refs

    def test_leaf_node_counts_all_its_symbols(
        self, conn: sqlite3.Connection,
    ) -> None:
        """Leaf node (no children) counts all its symbols."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("leaf", "feature", "Leaf", "src/leaf/"),
        )
        for i in range(250):
            conn.execute(
                "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                "line_start, line_end, annotations, file_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"src/leaf/f{i}.py", f"func_{i}", "function", 1, 10, "{}", "h"),
            )
        conn.commit()
        _count, refs = _count_oversized(conn, threshold=200)
        assert "leaf" in refs

    def test_child_node_independently_oversized(
        self, conn: sqlite3.Connection,
    ) -> None:
        """A child node with too many symbols is flagged independently."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("root", "service", "Root", "src/root/"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("big-child", "domain", "Big", "src/root/big/"),
        )
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("big-child", "root", "part_of"),
        )
        for i in range(250):
            conn.execute(
                "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                "line_start, line_end, annotations, file_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"src/root/big/m{i}.py", f"func_{i}", "function", 1, 10, "{}", "h"),
            )
        conn.commit()
        _count, refs = _count_oversized(conn, threshold=200)
        assert "big-child" in refs
        assert "root" not in refs  # root has 0 own symbols
