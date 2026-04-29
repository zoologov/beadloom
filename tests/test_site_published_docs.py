"""Tests for Showcase C — published validated docs + per-doc badges (BDL-040 BEAD-04).

The generator publishes the REAL ``docs/`` tree into ``site/docs/…`` preserving
structure (the source is the truth, rendered as-is) and injects a per-doc
**validation badge** derived from the ``doc_sync`` engine (the SAME source as
``beadloom sync-check``):

- a fresh doc badges ``fresh``;
- a stale doc badges ``stale`` with the matching reason
  (``hash_changed`` / ``symbols_changed`` / ``untracked_files``);
- a doc tracked by no pair badges ``untracked`` honestly;
- the badge status EQUALS the ``check_sync`` status for the same doc;
- the source ``docs/`` files are byte-unchanged after generation;
- regeneration overwrites ONLY the marker-delimited badge region, never prose;
- output is deterministic (no wall-clock; ``last synced`` from ``sync_state``).
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site import generate_site
from beadloom.application.site_published import (
    BADGE_END,
    BADGE_START,
    build_published_docs,
    inject_badge,
)
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures: a project tree with real docs + a seeded graph + sync_state.
# ---------------------------------------------------------------------------


def _seed_graph(conn: sqlite3.Connection) -> None:
    nodes = [
        ("beadloom", "service", "Beadloom CLI service.", None),
        ("application", "domain", "Use-case orchestration.", "src/beadloom/application"),
        ("graph", "domain", "YAML graph format.", "src/beadloom/graph"),
    ]
    for ref_id, kind, summary, source in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, source),
        )
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("application", "beadloom", "part_of"),
    )
    conn.commit()


def _seed_docs_table(conn: sqlite3.Connection) -> None:
    rows = [
        ("getting-started.md", "other", "beadloom", "h1"),
        ("domains/application/README.md", "domain", "application", "h2"),
        ("orphan.md", "other", None, "h3"),  # tracked by no node -> untracked
    ]
    for path, kind, ref_id, doc_hash in rows:
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            (path, kind, ref_id, doc_hash),
        )
    conn.commit()


def _seed_sync_pair(
    conn: sqlite3.Connection,
    *,
    doc_path: str,
    code_path: str,
    ref_id: str,
    status: str,
    synced_at: str,
    doc_hash: str,
    code_hash: str,
    symbols_hash: str = "",
) -> None:
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        " synced_at, status, symbols_hash, doc_hash_at_last_edit) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            doc_path,
            code_path,
            ref_id,
            code_hash,
            doc_hash,
            synced_at,
            status,
            symbols_hash,
            doc_hash,
        ),
    )
    conn.commit()


def _hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A project root with a real docs/ tree on disk."""
    docs = tmp_path / "docs"
    (docs / "domains" / "application").mkdir(parents=True)
    (docs / "getting-started.md").write_text(
        "# Getting started\n\nWelcome.\n", encoding="utf-8"
    )
    (docs / "domains" / "application" / "README.md").write_text(
        "# Application\n\nUse-case orchestration.\n", encoding="utf-8"
    )
    (docs / "orphan.md").write_text("# Orphan\n\nNobody tracks me.\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def conn(project: Path) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    _seed_graph(db)
    _seed_docs_table(db)
    # A code file the application doc is paired with (fresh).
    code = project / "src" / "beadloom" / "application"
    code.mkdir(parents=True)
    code_file = code / "x.py"
    code_file.write_text("def f():\n    return 1\n", encoding="utf-8")
    doc_text = (project / "docs" / "domains" / "application" / "README.md").read_text()
    _seed_sync_pair(
        db,
        doc_path="domains/application/README.md",
        code_path="src/beadloom/application/x.py",
        ref_id="application",
        status="ok",
        synced_at="2026-06-01T00:00:00+00:00",
        doc_hash=_hash(doc_text),
        code_hash=_hash(code_file.read_text()),
    )
    return db


# ---------------------------------------------------------------------------
# Publishing: the docs/ tree is copied under site/docs/ preserving structure.
# ---------------------------------------------------------------------------


def test_publishes_docs_tree_preserving_structure(
    conn: sqlite3.Connection, project: Path
) -> None:
    out = project / "site"
    generate_site(conn, out, project_root=project)
    assert (out / "docs" / "getting-started.md").exists()
    assert (out / "docs" / "domains" / "application" / "README.md").exists()
    assert (out / "docs" / "orphan.md").exists()


def test_published_doc_contains_original_prose(
    conn: sqlite3.Connection, project: Path
) -> None:
    out = project / "site"
    generate_site(conn, out, project_root=project)
    text = (out / "docs" / "getting-started.md").read_text(encoding="utf-8")
    assert "Welcome." in text  # authored prose preserved


# ---------------------------------------------------------------------------
# Badges: fresh / stale(reason) / untracked — equal to sync-check.
# ---------------------------------------------------------------------------


def test_fresh_doc_badges_fresh(conn: sqlite3.Connection, project: Path) -> None:
    out = project / "site"
    generate_site(conn, out, project_root=project)
    text = (out / "docs" / "domains" / "application" / "README.md").read_text(
        encoding="utf-8"
    )
    assert BADGE_START in text
    assert BADGE_END in text
    assert "fresh" in text.lower()
    assert "last synced" in text.lower()
    assert "2026-06-01" in text  # synced_at, a stored value


def test_stale_doc_badges_stale_with_reason(
    conn: sqlite3.Connection, project: Path
) -> None:
    # Mutate the code file on disk so check_sync reports hash_changed.
    code_file = project / "src" / "beadloom" / "application" / "x.py"
    code_file.write_text("def f():\n    return 999\n", encoding="utf-8")
    out = project / "site"
    generate_site(conn, out, project_root=project)
    text = (out / "docs" / "domains" / "application" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "stale" in text.lower()
    assert "hash_changed" in text


def test_untracked_doc_badges_untracked(
    conn: sqlite3.Connection, project: Path
) -> None:
    out = project / "site"
    generate_site(conn, out, project_root=project)
    text = (out / "docs" / "orphan.md").read_text(encoding="utf-8")
    assert "untracked" in text.lower()


def test_badge_status_equals_sync_check(
    conn: sqlite3.Connection, project: Path
) -> None:
    """The badge status for a doc EQUALS check_sync's status for the same doc."""
    from beadloom.doc_sync.engine import check_sync

    # Make the application doc stale via code drift.
    code_file = project / "src" / "beadloom" / "application" / "x.py"
    code_file.write_text("def f():\n    return 2\n", encoding="utf-8")

    docs = build_published_docs(conn, project_root=project)
    by_path = {d.doc_path: d for d in docs}

    # check_sync is the literal sync-check code path.
    results = check_sync(conn, project_root=project)
    sync_status = {r["doc_path"]: r["status"] for r in results}

    badge = by_path["domains/application/README.md"]
    assert badge.status == sync_status["domains/application/README.md"]
    assert badge.status == "stale"


def test_node_coverage_in_badge(conn: sqlite3.Connection, project: Path) -> None:
    out = project / "site"
    generate_site(conn, out, project_root=project)
    text = (out / "docs" / "domains" / "application" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "coverage" in text.lower()
    assert "%" in text


# ---------------------------------------------------------------------------
# Source docs/ NEVER mutated.
# ---------------------------------------------------------------------------


def test_source_docs_byte_unchanged(conn: sqlite3.Connection, project: Path) -> None:
    docs = project / "docs"
    before = {
        p.relative_to(docs): p.read_bytes()
        for p in sorted(docs.rglob("*"))
        if p.is_file()
    }
    out = project / "site"
    generate_site(conn, out, project_root=project)
    after = {
        p.relative_to(docs): p.read_bytes()
        for p in sorted(docs.rglob("*"))
        if p.is_file()
    }
    assert before == after


# ---------------------------------------------------------------------------
# Badge injection is a stable marker-delimited prefix.
# ---------------------------------------------------------------------------


def test_inject_badge_overwrites_only_badge_region() -> None:
    prose = "# Title\n\nAuthored prose stays.\n"
    once = inject_badge(prose, "OLD BADGE")
    assert "Authored prose stays." in once
    assert "OLD BADGE" in once
    # Re-injecting a new badge replaces only the badge region.
    twice = inject_badge(once, "NEW BADGE")
    assert "NEW BADGE" in twice
    assert "OLD BADGE" not in twice
    assert "Authored prose stays." in twice
    # Exactly one badge block remains.
    assert twice.count(BADGE_START) == 1
    assert twice.count(BADGE_END) == 1


def test_inject_badge_preserves_prose_byte_for_byte() -> None:
    prose = "# Title\n\nLine one.\nLine two.\n"
    injected = inject_badge(prose, "BADGE")
    # The original prose appears verbatim after the badge region.
    tail = injected.split(BADGE_END, 1)[1]
    assert tail.endswith(prose)


# ---------------------------------------------------------------------------
# Determinism: regenerate -> byte-identical (incl. the published docs).
# ---------------------------------------------------------------------------


def test_regenerate_published_docs_byte_identical(
    conn: sqlite3.Connection, project: Path
) -> None:
    out = project / "site"
    generate_site(conn, out, project_root=project)
    first = {
        p.relative_to(out): p.read_bytes()
        for p in sorted((out / "docs").rglob("*"))
        if p.is_file()
    }
    generate_site(conn, out, project_root=project)
    second = {
        p.relative_to(out): p.read_bytes()
        for p in sorted((out / "docs").rglob("*"))
        if p.is_file()
    }
    assert first == second
