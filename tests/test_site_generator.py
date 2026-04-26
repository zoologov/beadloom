"""Tests for beadloom.application.site — the `docs site` generator (BDL-040 BEAD-01).

Asserts the generator emits the expected files deterministically (re-generate ->
byte-identical), node pages contain summary/symbols/edges-as-links + an embedded
diagram, and nothing is written outside ``--out``.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site import generate_site
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed(conn: sqlite3.Connection) -> None:
    """Insert a small but representative graph (service/domain/feature + edges)."""
    nodes = [
        ("beadloom", "service", "Beadloom CLI service.", None),
        ("application", "domain", "Use-case orchestration.", "src/beadloom/application"),
        ("graph", "domain", "YAML graph format and loader.", "src/beadloom/graph"),
        ("reindex", "feature", "Full reindex pipeline.", "src/beadloom/application/reindex.py"),
    ]
    for ref_id, kind, summary, source in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, source),
        )
    edges = [
        ("application", "beadloom", "part_of"),
        ("graph", "beadloom", "part_of"),
        ("reindex", "application", "part_of"),
        ("application", "graph", "depends_on"),
        ("application", "graph", "uses"),
    ]
    for src, dst, kind in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )
    # A public symbol attached to the application source dir.
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("src/beadloom/application/reindex.py", "do_reindex", "function", 1, 10, "h"),
    )
    # A linked hand-written doc for the application node.
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("docs/domains/application/README.md", "domain", "application", "dh"),
    )
    conn.commit()


@pytest.fixture()
def conn() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    _seed(db)
    return db


# ---------------------------------------------------------------------------
# Structure / emitted files
# ---------------------------------------------------------------------------


def test_emits_index_and_per_node_pages(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    result = generate_site(conn, out, project_root=tmp_path)

    assert (out / "index.md").exists()
    assert (out / "services" / "beadloom.md").exists()
    assert (out / "domains" / "application.md").exists()
    assert (out / "domains" / "graph.md").exists()
    assert (out / "features" / "reindex.md").exists()
    # The result reports every written path.
    assert (out / "index.md") in result.written
    assert (out / "domains" / "application.md") in result.written


def test_emits_vitepress_config(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    cfg = out / ".vitepress" / "config.generated.mjs"
    assert cfg.exists()
    text = cfg.read_text(encoding="utf-8")
    # nav/sidebar sections present (later beads fill Dashboard/Landscape/Documentation).
    assert "Dashboard" in text
    assert "Architecture" in text
    assert "Landscape" in text
    assert "Documentation" in text


def test_index_has_counts_and_diagram_and_health(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "index.md").read_text(encoding="utf-8")
    assert "1 service" in text or "1 services" in text
    assert "2 domains" in text
    assert "1 feature" in text or "1 features" in text
    # Embedded top-level diagram (mermaid C4).
    assert "```mermaid" in text
    assert "C4Container" in text
    # Health summary line (coverage).
    assert "coverage" in text.lower()


# ---------------------------------------------------------------------------
# Node-page content: summary / symbols / edges-as-links / diagram
# ---------------------------------------------------------------------------


def test_node_page_has_summary_source_symbols(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    assert "Use-case orchestration." in text
    assert "src/beadloom/application" in text


def test_node_page_symbols_listed(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "features" / "reindex.md").read_text(encoding="utf-8")
    assert "do_reindex" in text


def test_node_page_edges_as_links(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    # depends_on / uses / part_of edges rendered as markdown links to other pages.
    assert "depends_on" in text
    assert "](../domains/graph.md)" in text  # link to the graph domain page
    assert "](../services/beadloom.md)" in text  # part_of -> beadloom service page


def test_node_page_embedded_diagram(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    assert "```mermaid" in text


def test_node_page_linked_docs_as_links(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    assert "docs/domains/application/README.md" in text


# ---------------------------------------------------------------------------
# Determinism + no source mutation
# ---------------------------------------------------------------------------


def test_regenerate_is_byte_identical(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    first = {
        p.relative_to(out): p.read_bytes()
        for p in sorted(out.rglob("*"))
        if p.is_file()
    }
    # Regenerate into the same dir; output must be byte-identical.
    generate_site(conn, out, project_root=tmp_path)
    second = {
        p.relative_to(out): p.read_bytes()
        for p in sorted(out.rglob("*"))
        if p.is_file()
    }
    assert first == second


def test_no_wall_clock_in_output(conn: sqlite3.Connection, tmp_path: Path) -> None:
    """Two generations of the same graph produce identical bytes (no timestamps)."""
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    generate_site(conn, out_a, project_root=tmp_path)
    generate_site(conn, out_b, project_root=tmp_path)
    a = {p.relative_to(out_a): p.read_bytes() for p in sorted(out_a.rglob("*")) if p.is_file()}
    b = {p.relative_to(out_b): p.read_bytes() for p in sorted(out_b.rglob("*")) if p.is_file()}
    assert a == b


def test_never_writes_into_source_docs(conn: sqlite3.Connection, tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    sentinel = docs / "README.md"
    sentinel.write_text("ORIGINAL", encoding="utf-8")
    out = tmp_path / "site"
    result = generate_site(conn, out, project_root=tmp_path)
    # Source docs untouched.
    assert sentinel.read_text(encoding="utf-8") == "ORIGINAL"
    # Every written path is under out/.
    for p in result.written:
        assert out in p.parents or p == out


def test_empty_graph_still_emits_index(tmp_path: Path) -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    out = tmp_path / "site"
    generate_site(db, out, project_root=tmp_path)
    assert (out / "index.md").exists()


# ---------------------------------------------------------------------------
# CLI: `beadloom docs site`
# ---------------------------------------------------------------------------


def _cli_project(tmp_path: Path) -> Path:
    import yaml

    from beadloom.application.reindex import reindex

    project = tmp_path / "proj"
    project.mkdir()
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "api-gw", "kind": "service", "summary": "API Gateway"},
                    {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
                    {"ref_id": "FEAT-1", "kind": "feature", "summary": "Feature one"},
                ],
                "edges": [
                    {"src": "routing", "dst": "api-gw", "kind": "part_of"},
                    {"src": "FEAT-1", "dst": "routing", "kind": "part_of"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (project / "docs").mkdir()
    (project / "src").mkdir()
    reindex(project)
    return project


def test_cli_docs_site_default_out(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from beadloom.services.cli import main

    project = _cli_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["docs", "site", "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert (project / "site" / "index.md").exists()
    assert (project / "site" / "services" / "api-gw.md").exists()


def test_cli_docs_site_custom_out(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from beadloom.services.cli import main

    project = _cli_project(tmp_path)
    out = tmp_path / "custom-site"
    runner = CliRunner()
    result = runner.invoke(
        main, ["docs", "site", "--project", str(project), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert (out / "index.md").exists()


def test_cli_docs_site_no_db(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from beadloom.services.cli import main

    project = tmp_path / "empty"
    project.mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["docs", "site", "--project", str(project)])
    assert result.exit_code == 1
    assert "database not found" in result.output
