"""Every landscape node links to its page, ``other/`` included (BDL-076 A4).

Every node has a page, and a kind with no directory of its own writes it under
``other/``. The landscape used to link only the three kinds with a directory,
because the Mermaid click targets on ``landscape-diagram.md`` reach the page
through the diagram viewer's base-path rewrite, and that rewrite did not know
``/other/``. The rewrite now covers it, so a component or a site that takes
part in a contract links to its page on the interactive map and on the Mermaid
fallback alike.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.generate import generate_site
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


def _contract(direction: str) -> str:
    return json.dumps({"contract": {"direction": direction, "schema": "bundle"}})


@pytest.fixture()
def conn() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    for ref_id, kind in [("shop", "service"), ("storefront", "site")]:
        db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, f"The {ref_id}.", None),
        )
    for src, dst, kind in [("shop", "storefront", "produces"), ("storefront", "shop", "consumes")]:
        db.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key, extra) "
            "VALUES (?, ?, ?, ?, ?)",
            (src, dst, kind, "data:bundle", _contract(kind)),
        )
    db.commit()
    return db


def test_the_interactive_map_links_a_site_to_its_page_under_other(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)

    data = json.loads((out / "public" / "landscape.data.json").read_text(encoding="utf-8"))
    urls = {node["id"]: node["url"] for node in data["nodes"]}
    assert urls == {"shop": "/services/shop", "storefront": "/other/storefront"}
    assert (out / "other" / "storefront.md").exists()


def test_the_mermaid_fallback_links_it_too(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)

    diagram = (out / "landscape-diagram.md").read_text(encoding="utf-8")
    assert 'click n_storefront "/other/storefront"' in diagram
    assert 'click n_shop "/services/shop"' in diagram


def test_the_landscape_page_describes_the_map_it_mounts(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """The map runs on the graph viewer: a node's card lists its contracts, an edge has none."""
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)

    page = (out / "landscape.md").read_text(encoding="utf-8")
    assert "<LandscapeMap />" in page
    assert "click a node or edge" not in page
    assert "Select a service" in page
    assert "every contract it produces or consumes" in page
