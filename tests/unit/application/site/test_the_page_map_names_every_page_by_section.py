"""The dashboard names the pages the site run wrote (BDL-080 S4a, `beadloom-5pxv`).

Owner, 2026-10-09: the dashboard shows how many and which pages `docs site`
generated — by section, by language, the node pages among them — as a population
beside lint and debt. The generator states each page's section as it writes it;
this module turns that into the data file's ``pages``.
"""

from __future__ import annotations

from pathlib import Path

from beadloom.application.site.page_map import PAGE_SECTIONS, page_map_of

_OUT = Path("/portal")


def test_every_section_is_named_in_the_sidebars_order_with_its_pages_sorted() -> None:
    written = {
        "nodes": [_OUT / "services/shop.md", _OUT / "domains/orders.md"],
        "about": [_OUT / "index.md"],
        "docs": [_OUT / "docs/index.md", _OUT / "docs/guide.md"],
    }

    pages = page_map_of(_OUT, written, languages={"en": _OUT / "index.md"})

    assert PAGE_SECTIONS == ("about", "dashboard", "architecture", "nodes", "landscape", "docs")
    assert pages == {
        "count": 5,
        "sections": [
            {"name": "about", "count": 1, "pages": ["index.md"]},
            {"name": "dashboard", "count": 0, "pages": []},
            {"name": "architecture", "count": 0, "pages": []},
            {"name": "nodes", "count": 2, "pages": ["domains/orders.md", "services/shop.md"]},
            {"name": "landscape", "count": 0, "pages": []},
            {"name": "docs", "count": 2, "pages": ["docs/guide.md", "docs/index.md"]},
        ],
        "languages": [{"language": "en", "page": "index.md"}],
    }


def test_only_markdown_pages_are_counted_and_a_page_listed_twice_once() -> None:
    written = {"docs": [_OUT / "docs/a.md", _OUT / "docs/img.png", _OUT / "docs/a.md"]}

    pages = page_map_of(_OUT, written, languages={})

    (docs,) = [section for section in pages["sections"] if section["name"] == "docs"]
    assert docs == {"name": "docs", "count": 1, "pages": ["docs/a.md"]}
    assert pages["count"] == 1


def test_the_languages_are_listed_by_code() -> None:
    pages = page_map_of(_OUT, {}, languages={"ru": _OUT / "ru/index.md", "en": _OUT / "index.md"})

    assert pages["languages"] == [
        {"language": "en", "page": "index.md"},
        {"language": "ru", "page": "ru/index.md"},
    ]
