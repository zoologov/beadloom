"""A node page beadloom wrote under a section the node's page has left is removed.

BDL-081 R2 (``beadloom-ehts``), RFC D4. A node declared ``kind: site`` has its page
under ``services/`` since BDL-080 S1a, and 8.0.0 wrote it under ``other/``: a portal
8.0.0 wrote and the tree rewrote kept both. Node pages carry no generated marker, so a
page is told as beadloom's by the front matter every version writes on it (``title:``
the node's ref, then ``kind:``) and its ``# <ref>`` heading; anything else at that path,
and any path the project provides under ``.beadloom/site/``, stays. The portal is a
temporary directory and the function reads nothing else, so unit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.site.moved_pages import RetiredPages, retire_moved_pages
from beadloom.application.site.node_pages import NodePage

if TYPE_CHECKING:
    from pathlib import Path


def _page(ref: str, kind: str) -> str:
    return f"---\ntitle: {ref}\nkind: {kind}\n---\n\n# {ref}\n\n**Kind:** {kind}\n"


def _written(*refs: str) -> list[NodePage]:
    """The node pages this run wrote, each as ``<section>:<ref>``."""
    pages = []
    for entry in refs:
        section, ref = entry.split(":", 1)
        pages.append(NodePage(rel_path=f"{section}/{ref}.md", body="", ref_id=ref))
    return pages


def _write(site: Path, rel: str, body: str) -> Path:
    path = site / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_the_page_under_the_section_the_node_left_is_removed(tmp_path: Path) -> None:
    _write(tmp_path, "services/portal.md", _page("portal", "service"))
    _write(tmp_path, "other/portal.md", _page("portal", "site"))
    _write(tmp_path, "other/widget.md", _page("widget", "component"))

    retired = retire_moved_pages(tmp_path, _written("services:portal", "other:widget"))

    assert retired == RetiredPages(pages=("other/portal.md",))
    assert not (tmp_path / "other" / "portal.md").exists()
    assert (tmp_path / "services" / "portal.md").is_file()
    assert (tmp_path / "other" / "widget.md").is_file()


def test_every_section_is_looked_in(tmp_path: Path) -> None:
    for section in ("domains", "features", "other"):
        _write(tmp_path, f"{section}/orders.md", _page("orders", "feature"))
    _write(tmp_path, "services/orders.md", _page("orders", "service"))

    retired = retire_moved_pages(tmp_path, _written("services:orders"))

    assert retired.pages == ("domains/orders.md", "features/orders.md", "other/orders.md")


def test_a_file_beadloom_did_not_write_stays(tmp_path: Path) -> None:
    _write(tmp_path, "services/portal.md", _page("portal", "service"))
    notes = _write(tmp_path, "other/portal.md", "# Notes on the portal\n")
    other_title = _write(tmp_path, "domains/portal.md", _page("portal-v1", "domain"))

    retired = retire_moved_pages(tmp_path, _written("services:portal"))

    assert retired == RetiredPages()
    assert notes.is_file()
    assert other_title.is_file()


def test_a_path_the_project_provides_stays(tmp_path: Path) -> None:
    _write(tmp_path, "services/portal.md", _page("portal", "service"))
    own = _write(tmp_path, "other/portal.md", _page("portal", "site"))

    retired = retire_moved_pages(tmp_path, _written("services:portal"), keep={"other/portal.md"})

    assert retired == RetiredPages()
    assert own.is_file()


def test_a_page_whose_node_has_none_this_run_stays(tmp_path: Path) -> None:
    gone = _write(tmp_path, "other/removed-node.md", _page("removed-node", "component"))

    assert retire_moved_pages(tmp_path, []) == RetiredPages()
    assert gone.is_file()


def test_a_section_the_retired_page_leaves_empty_is_removed(tmp_path: Path) -> None:
    _write(tmp_path, "services/portal.md", _page("portal", "service"))
    _write(tmp_path, "other/portal.md", _page("portal", "site"))

    retired = retire_moved_pages(tmp_path, _written("services:portal"))

    assert retired == RetiredPages(pages=("other/portal.md",), folders=("other",))
    assert not (tmp_path / "other").exists()


def test_a_page_outside_the_sections_is_not_read(tmp_path: Path) -> None:
    published = _write(tmp_path, "docs/portal.md", _page("portal", "site"))
    _write(tmp_path, "services/portal.md", _page("portal", "service"))

    assert retire_moved_pages(tmp_path, _written("services:portal")) == RetiredPages()
    assert published.is_file()


def test_a_node_id_holding_a_slash_never_costs_another_node_its_page(tmp_path: Path) -> None:
    """Release review (``beadloom-g0a0``), major 1: nodes ``b`` and ``x/b`` on a fresh portal.

    The id was taken from the file name and the section from the folder, so the page
    of ``x/b`` under ``services/x/`` read as having left ``services/``, and the page
    of ``b`` the same run had just written was removed.
    """
    plain = _write(tmp_path, "services/b.md", _page("b", "service"))
    nested = _write(tmp_path, "services/x/b.md", _page("x/b", "service"))

    retired = retire_moved_pages(tmp_path, _written("services:b", "services:x/b"))

    assert retired == RetiredPages()
    assert plain.is_file()
    assert nested.is_file()


def test_the_old_page_of_a_node_id_holding_a_slash_is_found_where_it_was(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "services/b.md", _page("b", "service"))
    _write(tmp_path, "services/x/b.md", _page("x/b", "service"))
    _write(tmp_path, "other/x/b.md", _page("x/b", "site"))
    unrelated = _write(tmp_path, "other/b.md", _page("b", "site"))

    retired = retire_moved_pages(tmp_path, _written("services:x/b"))

    assert retired == RetiredPages(pages=("other/x/b.md",), folders=("other/x",))
    assert unrelated.is_file()


def test_a_path_this_run_wrote_is_never_removed(tmp_path: Path) -> None:
    page = _write(tmp_path, "other/b.md", _page("b", "component"))

    retired = retire_moved_pages(tmp_path, [*_written("services:b"), *_written("other:b")])

    assert retired == RetiredPages()
    assert page.is_file()
