"""Tests for BDL-057 Layer 2 reference surface-drift in the sync engine.

Covers baseline (reindex), drift detection (sync-check), and clearing
(sync-update) of reference docs that declare a ``watches:`` surface — plus the
guarantee that this is additive and never touches the symbol-pair sync_state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import (
    build_reference_state,
    check_reference_drift,
    mark_reference_synced,
)
from beadloom.doc_sync.surface import aggregate_hash
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    (proj / ".beadloom").mkdir(parents=True)
    return proj


@pytest.fixture()
def conn(project: Path) -> sqlite3.Connection:
    db_path = project / ".beadloom" / "beadloom.db"
    c = open_db(db_path)
    create_schema(c)
    return c


def _add_node(conn: sqlite3.Connection, ref_id: str, kind: str = "feature") -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, '')",
        (ref_id, kind),
    )
    conn.commit()


def _write_doc(project: Path, rel: str, watches: str | None = "graph") -> None:
    anno = f"<!-- beadloom:watches={watches} -->\n" if watches else ""
    (project / "docs" / rel).write_text(f"{anno}# Overview\nSome prose.\n")


# --------------------------------------------------------------------------
# build_reference_state — baseline on reindex
# --------------------------------------------------------------------------


def test_baseline_records_watched_doc(conn: sqlite3.Connection, project: Path) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)

    row = conn.execute(
        "SELECT doc_path, watches, status FROM reference_state"
    ).fetchone()
    assert row["doc_path"] == "docs/architecture.md"
    assert row["watches"] == "graph"
    assert row["status"] == "ok"


def test_baseline_noop_without_annotation(conn: sqlite3.Connection, project: Path) -> None:
    _add_node(conn, "a")
    _write_doc(project, "plain.md", watches=None)
    build_reference_state(conn, project)
    assert conn.execute("SELECT COUNT(*) FROM reference_state").fetchone()[0] == 0


def test_baseline_records_multiple_surfaces_in_order(
    conn: sqlite3.Connection, project: Path
) -> None:
    _add_node(conn, "a")
    _write_doc(project, "readme.md", watches="cli,graph,flow.yml")
    build_reference_state(conn, project)
    row = conn.execute("SELECT watches FROM reference_state").fetchone()
    assert row["watches"] == "cli,graph,flow.yml"


def test_baseline_is_idempotent(conn: sqlite3.Connection, project: Path) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    build_reference_state(conn, project)
    assert conn.execute("SELECT COUNT(*) FROM reference_state").fetchone()[0] == 1


def test_baseline_preserved_across_reindex_so_drift_survives(
    conn: sqlite3.Connection, project: Path
) -> None:
    # A routine reindex must NOT silently re-baseline away accrued drift.
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    _add_node(conn, "b")  # surface drifts after the baseline
    build_reference_state(conn, project)  # simulate another reindex
    assert check_reference_drift(conn, project)[0]["status"] == "surface_drift"


def test_baseline_rebaselines_when_watches_set_changes(
    conn: sqlite3.Connection, project: Path
) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    # Author broadens the watched surfaces -> old baseline no longer applies.
    _write_doc(project, "architecture.md", watches="graph,flow.yml")
    build_reference_state(conn, project)
    row = conn.execute("SELECT watches, status FROM reference_state").fetchone()
    assert row["watches"] == "graph,flow.yml"
    assert row["status"] == "ok"
    assert check_reference_drift(conn, project)[0]["status"] == "ok"


def test_baseline_drops_doc_when_annotation_removed(
    conn: sqlite3.Connection, project: Path
) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    # Annotation removed -> next baseline forgets it.
    _write_doc(project, "architecture.md", watches=None)
    build_reference_state(conn, project)
    assert conn.execute("SELECT COUNT(*) FROM reference_state").fetchone()[0] == 0


# --------------------------------------------------------------------------
# check_reference_drift — sync-check warning
# --------------------------------------------------------------------------


def test_check_clean_when_no_drift(conn: sqlite3.Connection, project: Path) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    results = check_reference_drift(conn, project)
    assert len(results) == 1
    assert results[0]["status"] == "ok"
    assert results[0]["reason"] == "ok"
    assert results[0]["severity"] == "warning"


def test_check_reports_surface_drift_on_graph_change(
    conn: sqlite3.Connection, project: Path
) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    # Graph changes after baseline -> drift.
    _add_node(conn, "b")
    results = check_reference_drift(conn, project)
    assert results[0]["status"] == "surface_drift"
    assert results[0]["reason"] == "surface_drift"
    assert results[0]["severity"] == "warning"


def test_check_persists_drift_status(conn: sqlite3.Connection, project: Path) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    _add_node(conn, "b")
    check_reference_drift(conn, project)
    row = conn.execute("SELECT status FROM reference_state").fetchone()
    assert row["status"] == "surface_drift"


def test_check_drift_on_flow_change(conn: sqlite3.Connection, project: Path) -> None:
    flow = project / ".beadloom" / "flow.yml"
    flow.write_text("methodology: ddd\n")
    _write_doc(project, "getting-started.md", watches="flow.yml")
    build_reference_state(conn, project)
    flow.write_text("methodology: fsd\n")
    results = check_reference_drift(conn, project)
    assert results[0]["status"] == "surface_drift"


def test_check_empty_when_no_reference_docs(conn: sqlite3.Connection, project: Path) -> None:
    assert check_reference_drift(conn, project) == []


# --------------------------------------------------------------------------
# mark_reference_synced — clear the warning
# --------------------------------------------------------------------------


def test_mark_synced_clears_drift(conn: sqlite3.Connection, project: Path) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    _add_node(conn, "b")
    assert check_reference_drift(conn, project)[0]["status"] == "surface_drift"

    updated = mark_reference_synced(conn, "docs/architecture.md", project)
    assert updated == 1
    # New baseline = current; drift cleared.
    assert check_reference_drift(conn, project)[0]["status"] == "ok"


def test_mark_synced_rebaselines_hash(conn: sqlite3.Connection, project: Path) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    build_reference_state(conn, project)
    _add_node(conn, "b")
    mark_reference_synced(conn, "docs/architecture.md", project)
    row = conn.execute(
        "SELECT aggregate_hash FROM reference_state WHERE doc_path = 'docs/architecture.md'"
    ).fetchone()
    assert row["aggregate_hash"] == aggregate_hash(["graph"], conn, project)


def test_mark_synced_unknown_doc_returns_zero(
    conn: sqlite3.Connection, project: Path
) -> None:
    assert mark_reference_synced(conn, "nope.md", project) == 0


def test_mark_synced_all_clears_every_drift(
    conn: sqlite3.Connection, project: Path
) -> None:
    _add_node(conn, "a")
    _write_doc(project, "architecture.md", watches="graph")
    _write_doc(project, "readme.md", watches="graph")
    build_reference_state(conn, project)
    _add_node(conn, "b")
    assert all(r["status"] == "surface_drift" for r in check_reference_drift(conn, project))

    count = mark_reference_synced(conn, None, project, all_docs=True)
    assert count == 2
    assert all(r["status"] == "ok" for r in check_reference_drift(conn, project))
