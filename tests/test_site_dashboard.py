"""Tests for beadloom.application.site_dashboard — Showcase A (BDL-040 BEAD-02).

The dashboard MUST be honest by construction: every number it shows equals the
value produced by the SAME code path as the corresponding CLI gate
(``lint`` / ``status --debt-report`` / ``sync-check`` / ``doctor`` / ``federate``).
These tests assert that equality directly — the dashboard never reimplements a
metric — plus determinism (re-generate -> byte-identical) and that the dashboard
files are written only under ``--out``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.application.debt_report import (
    collect_debt_data,
    compute_debt_score,
    format_debt_json,
    load_debt_weights,
)
from beadloom.application.doctor import Severity, run_checks
from beadloom.application.site import generate_site
from beadloom.application.site_dashboard import build_dashboard_data, render_dashboard_md
from beadloom.graph.linter import lint

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# ---------------------------------------------------------------------------
# Project fixtures (real on-disk project so the reused gate paths run as in CLI)
# ---------------------------------------------------------------------------


_RULES = {
    "version": 3,
    "rules": [
        {
            "name": "domain-needs-parent",
            "description": "Every domain must be part_of the beadloom service.",
            "severity": "error",
            "require": {
                "for": {"kind": "domain"},
                "has_edge_to": {"ref_id": "beadloom"},
                "edge_kind": "part_of",
            },
        }
    ],
}


def _make_project(tmp_path: Path, *, with_violation: bool) -> Path:
    """Build a real indexed project (graph.yml + rules.yml) on disk."""
    from beadloom.application.reindex import reindex

    project = tmp_path / "proj"
    project.mkdir()
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)

    nodes = [
        {"ref_id": "beadloom", "kind": "service", "summary": "CLI service."},
        {
            "ref_id": "application",
            "kind": "domain",
            "summary": "Use cases.",
            "source": "src/beadloom/application/",
        },
        {
            "ref_id": "graph",
            "kind": "domain",
            "summary": "Graph format.",
            "source": "src/beadloom/graph/",
        },
    ]
    edges = [
        {"src": "application", "dst": "beadloom", "kind": "part_of"},
        {"src": "graph", "dst": "beadloom", "kind": "part_of"},
    ]
    if with_violation:
        # A domain with NO part_of edge to beadloom -> violates the require rule
        # (domain-needs-parent) -> 1 error.
        nodes.append(
            {"ref_id": "rogue", "kind": "domain", "summary": "Rogue domain."}
        )

    (graph_dir / "graph.yml").write_text(
        yaml.dump({"nodes": nodes, "edges": edges}),
        encoding="utf-8",
    )
    (graph_dir / "rules.yml").write_text(yaml.dump(_RULES), encoding="utf-8")
    (project / "docs").mkdir()
    (project / "src").mkdir()
    reindex(project)
    return project


def _open(project: Path) -> sqlite3.Connection:
    from beadloom.infrastructure.db import open_db

    return open_db(project / ".beadloom" / "beadloom.db")


# ---------------------------------------------------------------------------
# Honest-by-construction: each metric EQUALS its underlying gate path
# ---------------------------------------------------------------------------


def test_lint_count_matches_linter(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    expected = lint(project, reindex_before=False)
    assert data["lint"]["violations"] == len(expected.violations)
    assert data["lint"]["errors"] == expected.error_count
    assert data["lint"]["warnings"] == expected.warning_count
    # A real error was produced (proves the path is exercised, not a stub of 0).
    assert data["lint"]["errors"] >= 1


def test_lint_severity_breakdown_present(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    assert data["lint"]["by_severity"]["error"] == 0
    assert data["lint"]["violations"] == 0


def test_debt_matches_debt_report(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
        weights = load_debt_weights(project)
        report = compute_debt_score(collect_debt_data(conn, project, weights), weights)
    finally:
        conn.close()
    expected = format_debt_json(report)
    assert data["debt"]["debt_score"] == expected["debt_score"]
    assert data["debt"]["severity"] == expected["severity"]
    assert data["debt"]["categories"] == expected["categories"]
    assert data["debt"]["top_offenders"] == expected["top_offenders"]


def test_docs_freshness_and_coverage(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
        nodes = int(conn.execute("SELECT count(*) FROM nodes").fetchone()[0])
        covered = int(
            conn.execute(
                "SELECT count(DISTINCT n.ref_id) FROM nodes n "
                "JOIN docs d ON d.ref_id = n.ref_id"
            ).fetchone()[0]
        )
        stale = int(
            conn.execute(
                "SELECT count(*) FROM sync_state WHERE status = 'stale'"
            ).fetchone()[0]
        )
    finally:
        conn.close()
    assert data["docs"]["nodes"] == nodes
    assert data["docs"]["stale"] == stale
    expected_cov = round(covered / nodes * 100.0, 1) if nodes else 0.0
    assert data["docs"]["coverage_pct"] == expected_cov


def test_doctor_matches_run_checks(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
        checks = run_checks(conn, project_root=project)
    finally:
        conn.close()
    errors = sum(1 for c in checks if c.severity is Severity.ERROR)
    warnings = sum(1 for c in checks if c.severity is Severity.WARNING)
    assert data["doctor"]["total"] == len(checks)
    assert data["doctor"]["errors"] == errors
    assert data["doctor"]["warnings"] == warnings
    assert data["doctor"]["passed"] == (errors == 0)


# ---------------------------------------------------------------------------
# Federated rollup (only when --federated is given)
# ---------------------------------------------------------------------------


def _federated_json(tmp_path: Path) -> Path:
    payload = {
        "schema_version": 2,
        "repos": [
            {"repo": "svc-a", "landscape": "shop", "commit_sha": "abc", "age_seconds": 60},
            {"repo": "svc-b", "landscape": "shop", "commit_sha": "def", "age_seconds": 120},
        ],
        "nodes": [],
        "edges": [
            {"src": "@svc-a:x", "dst": "@svc-b:y", "kind": "uses", "repo": "svc-a",
             "verdict": "ok"},
            {"src": "@svc-a:p", "dst": "@svc-c:q", "kind": "uses", "repo": "svc-a",
             "verdict": "drift"},
            {"src": "@svc-b:m", "dst": "@svc-a:n", "kind": "uses", "repo": "svc-b",
             "verdict": "ok"},
        ],
        "contracts": [
            {"contract_key": "k1", "verdict": "confirmed"},
            {"contract_key": "k2", "verdict": "breaking"},
            {"contract_key": "k3", "verdict": "confirmed"},
        ],
        "unresolved_refs": [],
    }
    path = tmp_path / "federated.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return path


def test_no_federated_section_when_not_given(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    assert data["federated"] is None


def test_federated_rollup_counts(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    rollup = data["federated"]
    assert rollup is not None
    # Contract-verdict counts (sorted keys).
    assert rollup["contract_verdicts"] == {"breaking": 1, "confirmed": 2}
    # Per-service edge-verdict health.
    services = {s["repo"]: s for s in rollup["services"]}
    assert services["svc-a"]["verdicts"] == {"drift": 1, "ok": 1}
    assert services["svc-b"]["verdicts"] == {"ok": 1}
    # Healthy = no drift/breaking edges.
    assert services["svc-a"]["healthy"] is False
    assert services["svc-b"]["healthy"] is True


# ---------------------------------------------------------------------------
# Wiring into the generator: dashboard.md + dashboard.data.json under --out
# ---------------------------------------------------------------------------


def test_generator_emits_dashboard_files(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    out = tmp_path / "site"
    conn = _open(project)
    try:
        result = generate_site(conn, out, project_root=project)
    finally:
        conn.close()
    assert (out / "dashboard.md").exists()
    assert (out / "dashboard.data.json").exists()
    assert (out / "dashboard.md") in result.written
    assert (out / "dashboard.data.json") in result.written


def test_dashboard_data_json_matches_build(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    out = tmp_path / "site"
    conn = _open(project)
    try:
        generate_site(conn, out, project_root=project, now_ts="2026-06-05T00:00:00+00:00")
        conn2 = _open(project)
        try:
            # build is pure-read of the now-recorded history -> equal to the file.
            expected = build_dashboard_data(conn2, project_root=project)
        finally:
            conn2.close()
    finally:
        conn.close()
    written = json.loads((out / "dashboard.data.json").read_text(encoding="utf-8"))
    assert written == expected


def test_dashboard_md_renders_numbers_from_data(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    md = render_dashboard_md(data)
    assert "# Metrics dashboard" in md
    assert "Lint" in md
    assert "Debt" in md
    assert "Documentation" in md
    assert "Doctor" in md
    # The lint error count is rendered verbatim from the data.
    assert str(data["lint"]["errors"]) in md


# ---------------------------------------------------------------------------
# Widget mounting (BEAD-04): the page mounts the ECharts widgets AND still
# carries the honest textual values (graceful when JS is disabled).
# ---------------------------------------------------------------------------


def test_dashboard_md_mounts_echarts_widgets(tmp_path: Path) -> None:
    """The dashboard page mounts the four committed Vue/ECharts widgets."""
    project = _make_project(tmp_path, with_violation=True)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    md = render_dashboard_md(data)
    for tag in ("<HealthGauges", "<CategoryChart", "<TrendCharts", "<Recommendations"):
        assert tag in md, f"dashboard.md must mount {tag} ... />"


def test_dashboard_md_keeps_honest_values_alongside_widgets(tmp_path: Path) -> None:
    """The honest textual summary survives — numbers come from the data, not JS."""
    project = _make_project(tmp_path, with_violation=True)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    md = render_dashboard_md(data)
    # Widgets mounted...
    assert "<HealthGauges" in md
    # ...and the verbatim gate figures are STILL present (JS-disabled fallback).
    lint_data = data["lint"]
    docs_data = data["docs"]
    assert isinstance(lint_data, dict)
    assert isinstance(docs_data, dict)
    assert str(lint_data["violations"]) in md
    assert f"{docs_data['coverage_pct']}%" in md


def test_dashboard_md_is_deterministic(tmp_path: Path) -> None:
    """render_dashboard_md is a pure function of its data (byte-stable)."""
    project = _make_project(tmp_path, with_violation=True)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    assert render_dashboard_md(data) == render_dashboard_md(data)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_dashboard_data_is_deterministic(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        first = build_dashboard_data(conn, project_root=project, federated=fed)
        second = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_dashboard_files_byte_identical_on_regenerate(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    out = tmp_path / "site"
    conn = _open(project)
    try:
        # Same injected ts both runs -> dedup-by-ts keeps the history (and thus
        # the diffed file) byte-identical.
        generate_site(conn, out, project_root=project, now_ts="2026-06-05T00:00:00+00:00")
        first = (out / "dashboard.data.json").read_bytes()
        first_md = (out / "dashboard.md").read_bytes()
        generate_site(conn, out, project_root=project, now_ts="2026-06-05T00:00:00+00:00")
        second = (out / "dashboard.data.json").read_bytes()
        second_md = (out / "dashboard.md").read_bytes()
    finally:
        conn.close()
    assert first == second
    assert first_md == second_md


def test_dashboard_written_only_under_out(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    docs = project / "docs"
    sentinel = docs / "keep.md"
    sentinel.write_text("ORIGINAL", encoding="utf-8")
    out = tmp_path / "site"
    conn = _open(project)
    try:
        result = generate_site(conn, out, project_root=project)
    finally:
        conn.close()
    assert sentinel.read_text(encoding="utf-8") == "ORIGINAL"
    for p in result.written:
        assert out in p.parents or p == out


@pytest.mark.parametrize("with_violation", [True, False])
def test_data_json_is_sorted_keys(tmp_path: Path, with_violation: bool) -> None:
    project = _make_project(tmp_path, with_violation=with_violation)
    out = tmp_path / "site"
    conn = _open(project)
    try:
        generate_site(conn, out, project_root=project)
    finally:
        conn.close()
    raw = (out / "dashboard.data.json").read_text(encoding="utf-8")
    # Re-serialize with sorted keys; the file is already sorted -> identical.
    reparsed = json.loads(raw)
    assert raw == json.dumps(reparsed, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Trends — honest time-series from the metrics-history store only (G5)
# ---------------------------------------------------------------------------


def test_trends_empty_when_no_history(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    # No recorded points yet -> an empty (but present) series, never fabricated.
    assert data["trends"] == []


def test_trends_are_exactly_recorded_points_sorted(tmp_path: Path) -> None:
    from beadloom.application.site_metrics_history import (
        MetricsPoint,
        append_metrics_point,
    )

    project = _make_project(tmp_path, with_violation=False)

    def _pt(ts: str, lint: int) -> MetricsPoint:
        return MetricsPoint(
            ts=ts,
            lint_violations=lint,
            debt_score=1.0,
            coverage_pct=50.0,
            sync_pct=100.0,
            nodes=3,
            edges=2,
            symbols=0,
        )

    append_metrics_point(project, _pt("2026-06-03T00:00:00+00:00", 3))
    append_metrics_point(project, _pt("2026-06-01T00:00:00+00:00", 1))
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    trends = data["trends"]
    assert isinstance(trends, list)
    # Exactly the two recorded points, sorted by ts, no interpolation.
    assert [p["ts"] for p in trends] == [
        "2026-06-01T00:00:00+00:00",
        "2026-06-03T00:00:00+00:00",
    ]
    assert [p["lint_violations"] for p in trends] == [1, 3]


def test_generate_site_appends_current_point_with_injected_ts(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    out = tmp_path / "site"
    conn = _open(project)
    try:
        generate_site(conn, out, project_root=project, now_ts="2026-06-05T12:00:00+00:00")
    finally:
        conn.close()
    written = json.loads((out / "dashboard.data.json").read_text(encoding="utf-8"))
    trends = written["trends"]
    # The current run's point is recorded with the INJECTED ts (never now()).
    assert any(p["ts"] == "2026-06-05T12:00:00+00:00" for p in trends)


# ---------------------------------------------------------------------------
# Recommendations — prioritized, honest, from the existing gate data (G6)
# ---------------------------------------------------------------------------


def test_recommendations_present_and_severity_ordered(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    recs = data["recommendations"]
    assert isinstance(recs, list)
    assert recs, "with a violation + federated risks there must be recommendations"
    # Every item carries the documented shape.
    for item in recs:
        assert set(item) == {"kind", "severity", "target", "message", "link"}
    # Severity-ordered: error/critical before warn/info.
    rank = {"error": 0, "critical": 0, "warn": 1, "info": 2}
    severities = [rank.get(str(i["severity"]), 9) for i in recs]
    assert severities == sorted(severities)


def test_lint_recommendations_match_linter(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    expected = lint(project, reindex_before=False)
    lint_recs = [r for r in data["recommendations"] if r["kind"] == "lint"]
    # One lint recommendation per real violation — honest, no invented hotspots.
    assert len(lint_recs) == len(expected.violations)
    messages = [str(r["message"]) for r in lint_recs]
    # Each gate violation's own message is carried verbatim (remediation may be
    # appended) — the recommendation never invents or drops a violation.
    for v in expected.violations:
        assert any(v.message in m for m in messages)


def test_contract_risk_recommendations_from_federated(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=False)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    contract_recs = [r for r in data["recommendations"] if r["kind"] == "contract"]
    # The fixture has exactly one BREAKING contract -> exactly one contract risk.
    assert len(contract_recs) == 1
    assert contract_recs[0]["target"] == "k2"
    assert contract_recs[0]["severity"] == "error"


def test_recommendations_deterministic(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        first = build_dashboard_data(conn, project_root=project, federated=fed)
        second = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    assert json.dumps(first["recommendations"], sort_keys=True) == json.dumps(
        second["recommendations"], sort_keys=True
    )


# ---------------------------------------------------------------------------
# Attention / alerts — critical-first problem signalling (BEAD-10)
# ---------------------------------------------------------------------------


def test_alerts_present_iff_problems_exist(tmp_path: Path) -> None:
    """`alerts` is non-empty IFF there are real problems; empty when clean."""
    (tmp_path / "clean").mkdir()
    clean = _make_project(tmp_path / "clean", with_violation=False)
    conn = _open(clean)
    try:
        clean_data = build_dashboard_data(conn, project_root=clean)
    finally:
        conn.close()
    # A clean project (no lint errors / stale docs / doctor errors / high debt /
    # no federated contracts) -> all-clear -> empty alerts list (present key).
    assert clean_data["alerts"] == []

    (tmp_path / "dirty").mkdir()
    dirty = _make_project(tmp_path / "dirty", with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(dirty)
    try:
        dirty_data = build_dashboard_data(conn, project_root=dirty, federated=fed)
    finally:
        conn.close()
    alerts = dirty_data["alerts"]
    assert isinstance(alerts, list)
    assert alerts, "with a lint error + BREAKING contract there must be alerts"


def test_alerts_list_exactly_the_real_problems(tmp_path: Path) -> None:
    """Each alert maps to a real gate problem — no invented or dropped alerts."""
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    alerts = data["alerts"]
    assert isinstance(alerts, list)
    kinds = {str(a["kind"]) for a in alerts}
    # The fixture has a lint error AND one BREAKING contract.
    assert "lint" in kinds
    assert "contract" in kinds
    # No stale docs / no doctor errors in this fixture -> not alerted.
    assert "stale_doc" not in kinds
    assert "doctor" not in kinds
    for a in alerts:
        assert set(a) == {"kind", "severity", "message"}


def test_alerts_severity_ordered_breaking_first(tmp_path: Path) -> None:
    """Alerts are severity-ordered: BREAKING contracts lead, then errors."""
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    alerts = data["alerts"]
    rank = {"critical": 0, "error": 1, "warn": 2, "info": 3}
    ranks = [rank.get(str(a["severity"]), 9) for a in alerts]
    assert ranks == sorted(ranks)
    # The BREAKING contract is the single most severe -> leads the banner.
    assert alerts[0]["kind"] == "contract"
    assert alerts[0]["severity"] == "critical"


def test_alerts_deterministic(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        first = build_dashboard_data(conn, project_root=project, federated=fed)
        second = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    assert json.dumps(first["alerts"], sort_keys=True) == json.dumps(
        second["alerts"], sort_keys=True
    )


# ---------------------------------------------------------------------------
# Status cards — threshold-colored per metric group (BEAD-10)
# ---------------------------------------------------------------------------


def test_status_cards_cover_all_metric_groups(tmp_path: Path) -> None:
    """A card per group: lint, debt, docs, doctor (+ federated when present)."""
    project = _make_project(tmp_path, with_violation=False)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    cards = data["status_cards"]
    assert isinstance(cards, list)
    groups = {str(c["group"]) for c in cards}
    assert {"lint", "debt", "docs", "doctor"} <= groups
    # No federated artifact -> no federated card.
    assert "federated" not in groups
    for c in cards:
        assert set(c) == {"group", "label", "status", "value", "detail"}
        assert c["status"] in {"ok", "warn", "error"}


def test_status_cards_clean_project_all_ok(tmp_path: Path) -> None:
    """A clean project -> every status card is green (ok)."""
    project = _make_project(tmp_path, with_violation=False)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    cards = data["status_cards"]
    statuses = {str(c["group"]): str(c["status"]) for c in cards}
    # No violations -> lint card is green; no card is red (no error-level problem).
    assert statuses["lint"] == "ok"
    assert "error" not in statuses.values()


def test_status_cards_thresholds_red_on_errors(tmp_path: Path) -> None:
    """Lint errors -> red lint card; BREAKING contract -> red federated card."""
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    cards = {str(c["group"]): c for c in data["status_cards"]}
    assert cards["lint"]["status"] == "error"
    assert "federated" in cards
    assert cards["federated"]["status"] == "error"


def test_status_cards_deterministic(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        first = build_dashboard_data(conn, project_root=project, federated=fed)
        second = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    assert json.dumps(first["status_cards"], sort_keys=True) == json.dumps(
        second["status_cards"], sort_keys=True
    )


# ---------------------------------------------------------------------------
# Critical-first MD rendering — Attention banner + status cards (BEAD-10)
# ---------------------------------------------------------------------------


def test_dashboard_md_mounts_alert_banner(tmp_path: Path) -> None:
    project = _make_project(tmp_path, with_violation=True)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    md = render_dashboard_md(data)
    assert "<AlertBanner" in md
    assert "<StatusCards" in md


def test_dashboard_md_all_clear_text_when_clean(tmp_path: Path) -> None:
    """The honest text fallback shows an all-clear line when there are no alerts."""
    project = _make_project(tmp_path, with_violation=False)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()
    md = render_dashboard_md(data)
    assert "All clear" in md


def test_dashboard_md_lists_alerts_in_text_fallback(tmp_path: Path) -> None:
    """When problems exist, the honest text fallback names each alert."""
    project = _make_project(tmp_path, with_violation=True)
    fed = _federated_json(tmp_path)
    conn = _open(project)
    try:
        data = build_dashboard_data(conn, project_root=project, federated=fed)
    finally:
        conn.close()
    md = render_dashboard_md(data)
    alerts = data["alerts"]
    assert isinstance(alerts, list)
    assert "Attention" in md
    for a in alerts:
        assert str(a["message"]) in md


# ---------------------------------------------------------------------------
# Helper-level unit tests — defensive + threshold branches (pure, no DB/node)
# ---------------------------------------------------------------------------


def test_contract_alerts_handles_malformed_payload() -> None:
    """A non-dict payload, a missing/non-list ``contracts``, and non-dict items
    all degrade to no alerts (honest: only real verdicts count)."""
    from beadloom.application.site_dashboard import _contract_alerts

    assert _contract_alerts(None) == []
    assert _contract_alerts({"contracts": "nope"}) == []
    assert _contract_alerts({}) == []
    # Non-dict items are skipped; only the recognised verdict produces an alert.
    payload: dict[str, object] = {"contracts": ["x", 1, {"verdict": "drift"}]}
    alerts = _contract_alerts(payload)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "error"
    assert "DRIFT" in str(alerts[0]["message"])


def test_contract_alerts_drift_only_has_no_breaking() -> None:
    from beadloom.application.site_dashboard import _contract_alerts

    alerts = _contract_alerts({"contracts": [{"verdict": "drift"}, {"verdict": "drift"}]})
    # Only a DRIFT alert (no BREAKING) — the breaking branch is skipped.
    assert [a["kind"] for a in alerts] == ["contract"]
    assert "2 DRIFT" in str(alerts[0]["message"])


def test_build_alerts_each_problem_class_emits_one_alert() -> None:
    from beadloom.application.site_dashboard import _build_alerts

    alerts = _build_alerts(
        lint_data={"errors": 0},
        debt_data={"severity": "critical", "debt_score": 91},
        docs_data={"stale": 3},
        doctor_data={"errors": 2},
        federated_payload=None,
    )
    kinds = {str(a["kind"]) for a in alerts}
    # doctor error, stale doc, and critical debt each surface exactly once.
    assert kinds == {"doctor", "stale_doc", "debt"}
    # Severity-ordered: critical debt leads over error doctor over warn stale.
    rank = {"critical": 0, "error": 1, "warn": 2}
    severities = [str(a["severity"]) for a in alerts]
    assert severities == sorted(severities, key=lambda s: rank.get(s, 9))


def test_build_alerts_low_debt_is_not_alerted() -> None:
    from beadloom.application.site_dashboard import _build_alerts

    alerts = _build_alerts(
        lint_data={"errors": 0},
        debt_data={"severity": "medium", "debt_score": 40},
        docs_data={"stale": 0},
        doctor_data={"errors": 0},
        federated_payload=None,
    )
    # medium debt is below the alert threshold -> all-clear.
    assert alerts == []


@pytest.mark.parametrize(
    ("severity", "expected"),
    [("critical", "error"), ("high", "error"), ("medium", "warn"), ("low", "ok"), ("", "ok")],
)
def test_debt_card_threshold_status(severity: str, expected: str) -> None:
    from beadloom.application.site_dashboard import _debt_card

    card = _debt_card({"severity": severity, "debt_score": 10})
    assert card["status"] == expected
    assert card["group"] == "debt"


@pytest.mark.parametrize(
    ("stale", "coverage", "expected"),
    [(2, 95.0, "warn"), (0, 50.0, "warn"), (0, 80.0, "ok"), (0, 100.0, "ok")],
)
def test_docs_card_threshold_status(stale: int, coverage: float, expected: str) -> None:
    from beadloom.application.site_dashboard import _docs_card

    card = _docs_card({"stale": stale, "coverage_pct": coverage, "tracked_pairs": 5})
    assert card["status"] == expected


@pytest.mark.parametrize(
    ("errors", "warnings", "expected"),
    [(1, 0, "error"), (0, 2, "warn"), (0, 0, "ok")],
)
def test_doctor_card_threshold_status(errors: int, warnings: int, expected: str) -> None:
    from beadloom.application.site_dashboard import _doctor_card

    card = _doctor_card({"errors": errors, "warnings": warnings, "passed": errors == 0})
    assert card["status"] == expected


@pytest.mark.parametrize(
    ("breaking", "drift", "expected"),
    [(1, 0, "error"), (0, 3, "warn"), (0, 0, "ok")],
)
def test_federated_card_threshold_status(
    breaking: int, drift: int, expected: str
) -> None:
    from beadloom.application.site_dashboard import _federated_card

    card = _federated_card(
        {"contract_verdicts": {"breaking": breaking, "drift": drift}, "contract_count": 4}
    )
    assert card["status"] == expected


def test_node_link_falls_back_to_dashboard_for_empty_ref() -> None:
    from beadloom.application.site_dashboard import _node_link

    assert _node_link(None) == "/dashboard"
    assert _node_link("") == "/dashboard"
    assert _node_link("graph") == "/dashboard#graph"


def test_contract_recommendations_handles_malformed_payload() -> None:
    from beadloom.application.site_dashboard import _contract_recommendations

    assert _contract_recommendations(None) == []
    assert _contract_recommendations({"contracts": "nope"}) == []
    # Non-dict item + healthy verdict are skipped; only the unhealthy one stays.
    recs = _contract_recommendations(
        {
            "contracts": [
                "skip-me",
                {"verdict": "confirmed", "contract_key": "ok"},
                {"verdict": "breaking", "contract_key": "amqp:X"},
            ]
        }
    )
    assert len(recs) == 1
    assert recs[0]["severity"] == "error"
    assert recs[0]["target"] == "amqp:X"
    assert recs[0]["link"] == "/landscape"
