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
        generate_site(conn, out, project_root=project)
        conn2 = _open(project)
        try:
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
        generate_site(conn, out, project_root=project)
        first = (out / "dashboard.data.json").read_bytes()
        first_md = (out / "dashboard.md").read_bytes()
        generate_site(conn, out, project_root=project)
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
    assert raw == json.dumps(reparsed, sort_keys=True, indent=2) + "\n"
