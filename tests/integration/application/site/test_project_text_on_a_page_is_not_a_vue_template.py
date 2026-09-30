"""Every page carrying a project's own text shows it as written (BDL-076, ``beadloom-ujzb.12``).

VitePress compiles each page as a Vue template, and a Helm value, ``List<String>``
or an unclosed ``<details>`` in project text failed ``vitepress build`` on the
fixture measured for this bead. The About pages, the node summaries and the
published documents now go through one path, ``project_text.render_project_text``;
these tests pin that each page takes it, with the portal the generator describes:
its base path, its repository and the files it publishes under ``docs/``. The
generator's own components on those pages stay as they were.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.generate import generate_site
from beadloom.application.site.markdown_links import PortalLinks
from beadloom.application.site.node_pages import NodeRow, render_node_page
from beadloom.infrastructure.db import create_schema
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

_HELM = "{{ .Values.image.tag }}"
_SUMMARY = f"Deploys with {_HELM} and `{_HELM}`; returns List<String>."
_NOW = "2026-09-30T00:00:00+00:00"
_REPO = "https://gitlab.com/acme/shop"


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


def test_a_node_summary_is_shown_as_written_and_the_viewer_still_mounts(
    conn: sqlite3.Connection,
) -> None:
    node = NodeRow(ref_id="shop", kind="service", summary=_SUMMARY, source=None)
    body = render_node_page(conn, node, {"shop": "service"}, PortalLinks()).body
    assert (
        f"Deploys with <span v-pre>{_HELM}</span> and <code v-pre>{_HELM}</code>; "
        "returns List&lt;String>."
    ) in body
    assert '<ArchitectureMap focus="shop" :depth="1" height="60vh" />' in body
    assert "v-pre" not in body.split("## Graph", 1)[1]


def _project(root: Path) -> Path:
    (root / ".beadloom").mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(
        f"site:\n  base: /shop/\n  repo_url: {_REPO}\n", encoding="utf-8"
    )
    (root / "docs").mkdir(parents=True)
    (root / "README.md").write_text(
        f'# Shop\n\nSet {_HELM}. <a href="docs/guide.md">The guide</a>.\n', encoding="utf-8"
    )
    (root / "README.ru.md").write_text(f"# Магазин\n\n`{_HELM}`\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text(
        "# Guide\n\n"
        "<details><summary>More</summary>\n\n"
        f"Hidden {_HELM}.\n\n"
        '<img src="./logo.png" alt="logo"> <img src="./gone.png" alt="gone">\n\n'
        '<a href="../LICENSE">licence</a>\n\n'
        "```mermaid\ngraph LR\n  A --> B\n```\n",
        encoding="utf-8",
    )
    (root / "docs" / "logo.png").write_bytes(b"\x89PNG\r\n")
    return root


def test_the_generated_portal_shows_project_text_as_written(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    root = _project(tmp_path / "shop")
    # Committed, so a repository path has a commit to be linked at (BDL-076 B4).
    ref = commit_project(root)
    out = tmp_path / "site"
    generate_site(conn, out, project_root=root, now_ts=_NOW)

    about = (out / "index.md").read_text(encoding="utf-8")
    assert f"Set <span v-pre>{_HELM}</span>." in about
    assert '<a href="/shop/docs/guide.html">The guide</a>' in about
    about_ru = (out / "ru" / "index.md").read_text(encoding="utf-8")
    assert f"<code v-pre>{_HELM}</code>" in about_ru

    guide = (out / "docs" / "guide.md").read_text(encoding="utf-8")
    assert "&lt;details><summary>More</summary>" in guide
    assert f"Hidden <span v-pre>{_HELM}</span>." in guide
    assert '<img src="./logo.png" alt="logo"> gone' in guide
    assert f'<a href="{_REPO}/-/blob/{ref}/LICENSE">licence</a>' in guide
    assert "```mermaid\ngraph LR\n  A --> B\n```" in guide

    service = (out / "services" / "shop.md").read_text(encoding="utf-8")
    assert f"Deploys with <span v-pre>{_HELM}</span>" in service


def test_an_image_the_portal_publishes_is_found_from_every_page_that_shows_it(
    tmp_path: Path,
) -> None:
    """A README's ``<img src="docs/logo.png">`` built and showed the logo before this bead.

    The About page sits where the README does, so the relative path resolved; the
    root service's page, one directory down, did not. Every page now references the
    copy the portal publishes from where that page sits.
    """
    root = _project(tmp_path / "shop")
    readme = '# Shop\n\n<img src="docs/logo.png" alt="Shop logo"> Takes orders.\n'
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "README.ru.md").write_text(readme, encoding="utf-8")
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    summary = '<img src="docs/logo.png" alt="Shop logo"> Takes orders.'
    db.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("shop", "service", summary, None),
    )
    out = tmp_path / "site"
    generate_site(db, out, project_root=root, now_ts=_NOW)

    logo = '<img src="{}" alt="Shop logo">'
    assert logo.format("./docs/logo.png") in (out / "index.md").read_text(encoding="utf-8")
    ru = (out / "ru" / "index.md").read_text(encoding="utf-8")
    assert logo.format("../docs/logo.png") in ru
    service = (out / "services" / "shop.md").read_text(encoding="utf-8")
    assert logo.format("../docs/logo.png") in service
