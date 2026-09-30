"""A node page mounts the architecture viewer focused on its node (BDL-076 A4, US-4).

Before A4 a node page carried a scoped Mermaid C4 diagram of its own, with its
own pan and zoom and none of the viewer's navigation, filters or card. The page
now mounts the architecture page's viewer, focused on the page's node, so the
reader lands on that node's neighbourhood and can walk away from it. The
Mermaid C4 view stays on ``architecture-diagram.md``, the page a reader without
JavaScript is sent to.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.generate import generate_site
from beadloom.application.site.node_pages import NodeRow, render_node_page
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def conn() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    for ref_id, kind in [
        ("shop", "service"),
        ("orders", "domain"),
        ("checkout", "feature"),
        ("cart-widget", "component"),
    ]:
        db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, f"The {ref_id}.", None),
        )
    for src, dst, kind in [
        ("orders", "shop", "part_of"),
        ("checkout", "orders", "part_of"),
        ("cart-widget", "shop", "part_of"),
        ("checkout", "cart-widget", "depends_on"),
    ]:
        db.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )
    db.commit()
    return db


def _page(conn: sqlite3.Connection, ref_id: str) -> str:
    row = conn.execute(
        "SELECT ref_id, kind, summary, source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    node = NodeRow(ref_id=row["ref_id"], kind=row["kind"], summary=row["summary"], source=None)
    kinds = {r["ref_id"]: r["kind"] for r in conn.execute("SELECT ref_id, kind FROM nodes")}
    return render_node_page(conn, node, kinds).body


def _graph_section(body: str) -> list[str]:
    lines = body.splitlines()
    start = lines.index("## Graph")
    rest = lines[start + 1 :]
    end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return [line.strip() for line in rest[:end] if line.strip()]


def test_the_page_mounts_the_viewer_focused_on_its_node(conn: sqlite3.Connection) -> None:
    section = _graph_section(_page(conn, "checkout"))

    assert section == [
        "<ClientOnly>",
        '<ArchitectureMap focus="checkout" :depth="1" height="60vh" />',
        "</ClientOnly>",
    ]


def test_the_scoped_mermaid_diagram_is_gone(conn: sqlite3.Connection) -> None:
    body = _page(conn, "orders")

    assert "## Diagram" not in body
    assert "```mermaid" not in body


def test_a_node_of_a_kind_without_a_directory_is_focused_the_same_way(
    conn: sqlite3.Connection,
) -> None:
    section = _graph_section(_page(conn, "cart-widget"))

    assert '<ArchitectureMap focus="cart-widget" :depth="1" height="60vh" />' in section


def test_the_graph_takes_the_place_the_diagram_had(conn: sqlite3.Connection) -> None:
    """The viewer sits where the Mermaid diagram was: after the page's text sections."""
    body = _page(conn, "checkout")

    headings = ("## Relationships", "## Documentation", "## Graph")
    order = [body.index(heading) for heading in headings]
    assert order == sorted(order)
    assert "](../domains/orders.md)" in body


def test_the_c4_view_stays_on_the_architecture_diagram_page(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)

    fallback = (out / "architecture-diagram.md").read_text(encoding="utf-8")
    assert "```mermaid" in fallback
    assert "C4" in fallback
    page = (out / "features" / "checkout.md").read_text(encoding="utf-8")
    assert "```mermaid" not in page
    assert '<ArchitectureMap focus="checkout"' in page
