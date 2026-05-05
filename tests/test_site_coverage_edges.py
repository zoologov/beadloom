"""Edge/error-path coverage for the `docs site` generator surface (BDL-040 BEAD-06).

Closes the remaining branch gaps in the F4 modules (``site.py`` / ``site_pages.py``
/ ``site_dashboard.py`` / ``site_landscape.py`` / ``site_published.py``) by
exercising the defensive and degenerate paths the happy-path suites skip:

- a node whose kind is none of domain/service/feature (nav-config + page dir
  fallback to ``other``);
- a self-edge dropped on a node page;
- a node with no symbols / no diagram children;
- ``site_published``: a node with a directory source (real coverage counting),
  an empty ``ref_id`` (0.0 coverage), a non-Markdown asset copied verbatim, and
  ``build_published_docs`` with no source ``docs/`` dir;
- ``site_landscape``: a malformed federated.json (read error -> empty map), a
  self-edge / empty-endpoint federated edge dropped, a ``@``-only id passed
  through, and an edge referencing a node not in the node set;
- ``site_dashboard``: an unreadable federated artifact, a non-dict payload, an
  edge with an empty verdict skipped, and the debt-trend attach branch.

Behaviour-focused: assertions are on the public output (emitted files / returned
data dicts), never on private attributes. Deterministic; no wall-clock asserts.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site import generate_site
from beadloom.application.site_dashboard import (
    _federated_metrics,
    _read_federated_payload,
    build_dashboard_data,
)
from beadloom.application.site_landscape import (
    _strip_namespace,
    build_landscape_data,
    render_landscape_md,
)
from beadloom.application.site_published import (
    build_published_docs,
    publish_docs,
)
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    return db


def _add_node(
    conn: sqlite3.Connection,
    ref_id: str,
    kind: str,
    summary: str = "",
    source: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        (ref_id, kind, summary, source),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# site.py: a node whose kind is not domain/service/feature
# ---------------------------------------------------------------------------


def test_nav_config_skips_unknown_kind(conn: sqlite3.Connection, tmp_path: Path) -> None:
    """A node of an unrecognised kind is skipped in the nav sidebar (no crash)."""
    # Arrange: a node whose kind has no nav sub-directory mapping.
    _add_node(conn, "beadloom", "service", "CLI service.")
    _add_node(conn, "weird", "external", "An external/unmapped node.")

    # Act
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)

    # Assert: the index still generates; the unknown-kind node is absent from nav.
    cfg = (out / ".vitepress" / "config.generated.mjs").read_text(encoding="utf-8")
    assert '"beadloom"' in cfg
    assert "/services/beadloom" in cfg
    assert "/weird" not in cfg  # no sub-dir -> skipped from the architecture nav


def test_unknown_kind_page_goes_to_other_dir(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """An unrecognised-kind node renders into the ``other/`` directory."""
    _add_node(conn, "weird", "external", "An external node.")
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    assert (out / "other" / "weird.md").exists()


# ---------------------------------------------------------------------------
# site_pages.py: self-edge dropped, node with no symbols / no diagram children
# ---------------------------------------------------------------------------


def test_self_edge_not_rendered_on_page(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """A self-referential edge is dropped from the node-page edge list."""
    _add_node(conn, "beadloom", "service", "CLI service.")
    _add_node(conn, "application", "domain", "Use cases.")
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("application", "beadloom", "part_of"),
    )
    # A self-edge (application -> application) must NOT produce a self link.
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("application", "application", "depends_on"),
    )
    conn.commit()

    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    # The self-edge target page is not linked.
    assert "](../domains/application.md)" not in text
    # The real part_of edge IS linked.
    assert "](../services/beadloom.md)" in text


def test_node_with_no_symbols_or_children_still_renders(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """A leaf node with no symbols and no graph children renders without error."""
    _add_node(conn, "lonely", "feature", "An isolated feature, no source.")
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    page = (out / "features" / "lonely.md")
    assert page.exists()
    text = page.read_text(encoding="utf-8")
    assert "An isolated feature" in text
    # A diagram block is still emitted (container fallback).
    assert "```mermaid" in text


# ---------------------------------------------------------------------------
# site_published.py: directory-source coverage, empty ref_id, non-md asset,
# missing docs/ dir
# ---------------------------------------------------------------------------


def test_published_directory_source_coverage_counted(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """A node with a directory source gets a real tracked/total coverage %."""
    # Arrange: a domain whose source is a directory with two .py files, one of
    # which is tracked by a sync pair -> 50% coverage.
    _add_node(conn, "application", "domain", "Use cases.", "src/beadloom/application/")
    src_dir = tmp_path / "src" / "beadloom" / "application"
    src_dir.mkdir(parents=True)
    (src_dir / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (src_dir / "b.py").write_text("def b():\n    return 2\n", encoding="utf-8")
    # __init__.py is excluded from the denominator.
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("domains/application/README.md", "domain", "application", "dh"),
    )
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        " synced_at, status, symbols_hash, doc_hash_at_last_edit) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "domains/application/README.md",
            "src/beadloom/application/a.py",
            "application",
            "ch",
            "dh",
            "2026-06-01T00:00:00+00:00",
            "ok",
            "",
            "dh",
        ),
    )
    conn.commit()
    docs = tmp_path / "docs" / "domains" / "application"
    docs.mkdir(parents=True)
    (docs / "README.md").write_text("# App\n", encoding="utf-8")

    # Act
    published = build_published_docs(conn, project_root=tmp_path)

    # Assert: 1 tracked of 2 counted files -> 50.0%.
    by_path = {d.doc_path: d for d in published}
    assert by_path["domains/application/README.md"].coverage_pct == 50.0


def test_published_untracked_doc_with_no_ref_zero_coverage(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """A doc tracked by no node gets ``untracked`` status and 0.0 coverage."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "orphan.md").write_text("# Orphan\n", encoding="utf-8")
    published = build_published_docs(conn, project_root=tmp_path)
    by_path = {d.doc_path: d for d in published}
    assert by_path["orphan.md"].status == "untracked"
    assert by_path["orphan.md"].coverage_pct == 0.0
    assert by_path["orphan.md"].ref_id == ""


def test_published_skips_hidden_doc_in_build(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """A doc under a hidden path is skipped by build_published_docs."""
    docs = tmp_path / "docs"
    (docs / ".hidden").mkdir(parents=True)
    (docs / ".hidden" / "secret.md").write_text("# Secret\n", encoding="utf-8")
    (docs / "visible.md").write_text("# Visible\n", encoding="utf-8")
    published = build_published_docs(conn, project_root=tmp_path)
    paths = {d.doc_path for d in published}
    assert "visible.md" in paths
    assert all(".hidden" not in p for p in paths)


def test_publish_copies_non_markdown_asset_verbatim(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """A non-Markdown asset under docs/ is copied byte-for-byte (no badge)."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "page.md").write_text("# Page\n", encoding="utf-8")
    asset = docs / "diagram.png"
    raw = b"\x89PNG\r\n\x1a\nfake-bytes"
    asset.write_bytes(raw)
    out = tmp_path / "site"
    publish_docs(conn, out, project_root=tmp_path)
    copied = out / "docs" / "diagram.png"
    assert copied.exists()
    assert copied.read_bytes() == raw  # verbatim, no badge injection


def test_publish_no_docs_dir_returns_empty(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """With no source docs/ dir, build + publish both yield nothing (no crash)."""
    assert build_published_docs(conn, project_root=tmp_path) == []
    assert publish_docs(conn, tmp_path / "site", project_root=tmp_path) == []


# ---------------------------------------------------------------------------
# site_landscape.py: read error, dropped edges, namespace strip, foreign edge
# ---------------------------------------------------------------------------


def test_landscape_malformed_federated_yields_empty_map(tmp_path: Path) -> None:
    """A malformed federated.json is read as an empty map (degenerate, no crash)."""
    fed = tmp_path / "federated.json"
    fed.write_text("{ this is not json", encoding="utf-8")
    data = build_landscape_data(federated=fed)
    assert data["nodes"] == []
    assert data["edges"] == []


def test_landscape_drops_self_and_empty_edges(tmp_path: Path) -> None:
    """Federated edges that are self-links or have an empty endpoint are dropped."""
    payload = {
        "repos": [{"repo": "svc-a"}, {"repo": "svc-b"}],
        "edges": [
            # self-edge (same repo both ends) -> dropped
            {"src": "@svc-a:x", "dst": "@svc-a:y", "verdict": "ok"},
            # empty dst -> dropped
            {"src": "@svc-a:x", "dst": "", "verdict": "ok"},
            # valid cross-repo edge -> kept
            {"src": "@svc-a:x", "dst": "@svc-b:y", "verdict": "drift"},
        ],
    }
    fed = tmp_path / "federated.json"
    fed.write_text(json.dumps(payload), encoding="utf-8")
    data = build_landscape_data(federated=fed)
    edges = data["edges"]
    assert isinstance(edges, list)
    assert len(edges) == 1
    assert edges[0] == {"src": "svc-a", "dst": "svc-b", "verdict": "drift"}


def test_strip_namespace_passes_through_at_without_colon() -> None:
    """An ``@`` id with no ``:`` separator is returned unchanged."""
    assert _strip_namespace("@plainname") == "@plainname"
    assert _strip_namespace("plain") == "plain"
    assert _strip_namespace("@svc-a:plans") == "svc-a"


def test_landscape_render_ignores_edge_to_unknown_node() -> None:
    """An edge referencing a node absent from the node set does not crash render."""
    data: dict[str, object] = {
        "scope": "company",
        "nodes": [{"id": "svc-a"}],
        "edges": [{"src": "svc-a", "dst": "ghost", "verdict": "drift"}],
    }
    md = render_landscape_md(data)
    # svc-a is present and rendered; the ghost endpoint is simply not classed.
    assert "svc_a[svc-a]" in md
    assert "DRIFT" in md
    assert "graph LR" in md


# ---------------------------------------------------------------------------
# site_dashboard.py: federated read-error / non-dict / empty-verdict / trend
# ---------------------------------------------------------------------------


def test_dashboard_federated_unreadable_returns_none(tmp_path: Path) -> None:
    """An unreadable federated artifact yields a None payload (no crash)."""
    missing = tmp_path / "does-not-exist.json"
    assert _read_federated_payload(missing) is None


def test_dashboard_federated_non_dict_returns_none(tmp_path: Path) -> None:
    """A federated.json whose top-level value is not a dict yields None."""
    fed = tmp_path / "federated.json"
    fed.write_text("[1, 2, 3]", encoding="utf-8")
    assert _read_federated_payload(fed) is None


def test_dashboard_federated_skips_empty_verdict(tmp_path: Path) -> None:
    """An edge/contract with an empty verdict is excluded from the counts."""
    payload = {
        "repos": [{"repo": "svc-a"}],
        "edges": [
            {"src": "@svc-a:x", "dst": "@svc-b:y", "repo": "svc-a", "verdict": ""},
            {"src": "@svc-a:p", "dst": "@svc-b:q", "repo": "svc-a", "verdict": "ok"},
        ],
        "contracts": [
            {"contract_key": "k1", "verdict": ""},
            {"contract_key": "k2", "verdict": "confirmed"},
        ],
    }
    fed = tmp_path / "federated.json"
    fed.write_text(json.dumps(payload), encoding="utf-8")
    loaded = _read_federated_payload(fed)
    assert loaded is not None
    rollup = _federated_metrics(loaded)
    assert rollup is not None
    # The empty-verdict contract is not counted.
    assert rollup["contract_verdicts"] == {"confirmed": 1}
    services = {s["repo"]: s for s in rollup["services"]}  # type: ignore[union-attr]
    # The empty-verdict edge is not counted in the per-repo verdict tally.
    assert services["svc-a"]["verdicts"] == {"ok": 1}


def test_dashboard_debt_trend_attached_when_snapshot_exists(tmp_path: Path) -> None:
    """When a debt snapshot exists, the dashboard attaches the computed trend."""
    import yaml

    from beadloom.application.reindex import reindex
    from beadloom.infrastructure.db import open_db

    project = tmp_path / "proj"
    project.mkdir()
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "beadloom", "kind": "service", "summary": "CLI."},
                    {"ref_id": "application", "kind": "domain", "summary": "Uses."},
                ],
                "edges": [
                    {"src": "application", "dst": "beadloom", "kind": "part_of"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (project / "docs").mkdir()
    (project / "src").mkdir()
    reindex(project)

    # Save a graph snapshot so compute_debt_trend returns a non-None trend.
    from beadloom.graph.snapshot import save_snapshot

    conn = open_db(project / ".beadloom" / "beadloom.db")
    try:
        save_snapshot(conn, "baseline")
        data = build_dashboard_data(conn, project_root=project)
    finally:
        conn.close()

    debt = data["debt"]
    assert isinstance(debt, dict)
    # The trend was attached (a snapshot existed) rather than left None.
    assert debt.get("trend") is not None
