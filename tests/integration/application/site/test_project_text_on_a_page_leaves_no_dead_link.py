"""The pages that carry a project's own text rebase its links (BDL-076, ``beadloom-ujzb.11``).

A node's summary was written onto its node page as it was, so a README that
opened with ``See [license](LICENSE).`` gave the root service's page a dead link
and ``vitepress build`` failed. The summary, the About page and every published
document now go through one rule, ``markdown_links.rebase_links``; these tests pin
that each page applies it, with the portal the generator describes.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.generate import generate_site
from beadloom.application.site.markdown_links import PortalLinks
from beadloom.application.site.node_pages import NodeRow, render_all_pages, render_node_page
from beadloom.infrastructure.db import create_schema
from tests.support.site_links import dead_links

if TYPE_CHECKING:
    from pathlib import Path

_SUMMARY = "See [license](LICENSE) and [the guide](docs/guide.md)."
_NOW = "2026-09-30T00:00:00+00:00"


@pytest.fixture()
def conn() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    db.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("shop", "service", _SUMMARY, None),
    )
    db.commit()
    return db


def _shop() -> NodeRow:
    return NodeRow(ref_id="shop", kind="service", summary=_SUMMARY, source=None)


def test_a_summary_link_to_a_published_document_goes_to_its_page(
    conn: sqlite3.Connection,
) -> None:
    portal = PortalLinks(doc_slugs=frozenset({"guide"}))
    body = render_node_page(conn, _shop(), {"shop": "service"}, portal).body
    assert "See license and [the guide](/docs/guide)." in body


def test_a_summary_link_goes_to_the_declared_repository(conn: sqlite3.Connection) -> None:
    portal = PortalLinks(repo_url="https://gitlab.com/acme/shop")
    body = render_node_page(conn, _shop(), {"shop": "service"}, portal).body
    assert "See [license](https://gitlab.com/acme/shop/blob/main/LICENSE) and" in body


def test_with_no_portal_described_every_relative_summary_link_is_text(
    conn: sqlite3.Connection,
) -> None:
    body = render_node_page(conn, _shop(), {"shop": "service"}).body
    assert "See license and the guide." in body


def test_every_page_is_rendered_with_the_portal_it_is_given(conn: sqlite3.Connection) -> None:
    portal = PortalLinks(doc_slugs=frozenset({"guide"}))
    (page,) = render_all_pages(conn, portal)
    assert "[the guide](/docs/guide)" in page.body


def _project(root: Path) -> Path:
    (root / ".beadloom").mkdir(parents=True)
    (root / "docs" / "guides").mkdir(parents=True)
    (root / "README.md").write_text(
        "# Shop\n\nRead it [in Russian](README.ru.md), see [license](LICENSE).\n",
        encoding="utf-8",
    )
    (root / "docs" / "guides" / "setup.md").write_text(
        "# Setup\n\nStart from [the readme](../../README.md), the [code](../../src/app.js)"
        " and [the index](../index-notes.md).\n",
        encoding="utf-8",
    )
    (root / "docs" / "index-notes.md").write_text("# Notes\n", encoding="utf-8")
    return root


def test_the_generated_portal_holds_no_dead_link_from_project_text(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    root = _project(tmp_path / "shop")
    out = tmp_path / "site"
    generate_site(conn, out, project_root=root, now_ts=_NOW)

    about = (out / "index.md").read_text(encoding="utf-8")
    # README.ru.md is absent, so there is no /ru/ page to send the toggle to.
    assert "Read it in Russian, see license." in about
    setup = (out / "docs" / "guides" / "setup.md").read_text(encoding="utf-8")
    assert "Start from [the readme](/), the code and [the index](../index-notes.md)." in setup
    service = (out / "services" / "shop.md").read_text(encoding="utf-8")
    assert "See license and the guide." in service
    assert dead_links(out) == []
