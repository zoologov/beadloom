"""A link written as raw HTML in project text, and a link to a file missing from ``docs/``.

BDL-076 (``beadloom-ujzb.12``). Measured on VitePress 1.6.4: a raw
``<a href="../LICENSE">`` or ``<a href="./other.md">`` in a published document
builds and leads nowhere, because VitePress neither checks nor rewrites raw HTML
and does not put the portal's base path in front of it. A raw
``<img src="missing.png">`` and a Markdown ``![](./missing.png)`` inside ``docs/``
fail the build: Vite cannot resolve the file.

:func:`raw_html_destination` gives a raw attribute the rule a Markdown link has
(``beadloom-ujzb.11``), with two differences a raw attribute needs: a page's
route carries the base path and the file name VitePress writes, and a file inside
the mirrored directory is kept only when the portal publishes it. The second
difference holds for Markdown links too, once the portal says which files it
publishes.
"""

from __future__ import annotations

import pytest

from beadloom.application.site.markdown_links import (
    PortalLinks,
    raw_html_destination,
    rebase_links,
)
from beadloom.application.site.repository_link import RepositoryLink

_REPO = "https://gitlab.com/acme/orders"
#: The commit the site was generated from (BDL-076 B4: links are at it, not at `main`).
_REF = "fedcba9876543210fedcba9876543210fedcba98"
_BASE = "/orders/"

_PORTAL = PortalLinks(
    doc_slugs=frozenset({"guide", "other", "sub/index"}),
    page_routes={"readme.md": "/", "readme.ru.md": "/ru/"},
    base=_BASE,
    mirrored_files=frozenset(
        {"docs/guide.md", "docs/other.md", "docs/sub/index.md", "docs/logo.png"}
    ),
)
_WITH_REPO = PortalLinks(
    doc_slugs=_PORTAL.doc_slugs,
    page_routes=_PORTAL.page_routes,
    repository=RepositoryLink(url=_REPO, ref=_REF),
    base=_BASE,
    mirrored_files=_PORTAL.mirrored_files,
)

#: Where a published document sits, and the directory its page mirrors.
_IN_DOCS = {"source_dir": "docs", "mirrored_dir": "docs"}


def _href(url: str, portal: PortalLinks = _PORTAL, **where: str) -> str | None:
    return raw_html_destination(url, portal, **where)


def _src(url: str, portal: PortalLinks = _PORTAL, **where: str) -> str | None:
    return raw_html_destination(url, portal, asset=True, **where)


# -- a raw link to a page the portal publishes --------------------------------


@pytest.mark.parametrize("target", ["./other.md", "other.md", "other", "../docs/other.md"])
def test_a_raw_link_to_a_published_document_goes_to_its_page_under_the_base(
    target: str,
) -> None:
    assert _href(target, **_IN_DOCS) == "/orders/docs/other.html"


def test_a_raw_link_to_a_published_document_keeps_its_anchor() -> None:
    assert _href("docs/guide.md#setup") == "/orders/docs/guide.html#setup"


def test_a_raw_link_to_the_readme_pair_goes_to_its_about_page_under_the_base() -> None:
    assert _href("README.md") == "/orders/"
    assert _href("../README.ru.md", **_IN_DOCS) == "/orders/ru/"


def test_a_raw_link_to_a_directory_index_goes_to_its_page() -> None:
    assert _href("docs/sub/index.md") == "/orders/docs/sub/index.html"


# -- a raw link to anything else ----------------------------------------------


def test_a_raw_link_to_a_repository_file_goes_to_the_declared_repository() -> None:
    assert _href("../LICENSE", _WITH_REPO, **_IN_DOCS) == f"{_REPO}/-/blob/{_REF}/LICENSE"


def test_a_raw_link_to_a_repository_file_has_nowhere_to_go_without_a_repository() -> None:
    assert _href("../LICENSE", **_IN_DOCS) is None


def test_a_raw_link_out_of_the_repository_has_nowhere_to_go() -> None:
    assert _href("../../elsewhere.md", _WITH_REPO, **_IN_DOCS) is None


@pytest.mark.parametrize(
    "target",
    ["https://acme.test/x", "mailto:team@acme.test", "//cdn.acme.test/a.js", "#usage", ""],
)
def test_an_absolute_raw_address_or_an_anchor_is_left_as_written(target: str) -> None:
    assert _href(target, **_IN_DOCS) == target
    assert _src(target, **_IN_DOCS) == target


# -- a raw image --------------------------------------------------------------


def test_a_raw_image_the_mirrored_directory_publishes_is_left_as_written() -> None:
    assert _src("./logo.png", **_IN_DOCS) == "./logo.png"


def test_a_raw_image_missing_from_the_mirrored_directory_has_nowhere_to_go() -> None:
    assert _src("missing.png", _WITH_REPO, **_IN_DOCS) is None


def test_a_raw_image_outside_the_mirrored_directory_follows_the_markdown_image_rule() -> None:
    assert _src("assets/logo.png") is None
    assert _src("assets/logo.png", _WITH_REPO) == f"{_REPO}/-/raw/{_REF}/assets/logo.png"


# -- a Markdown link to a file missing from the mirrored directory ------------


def test_a_markdown_image_missing_from_the_mirrored_directory_becomes_its_alt_text() -> None:
    out = rebase_links("![a diagram](./missing.png)", _WITH_REPO, **_IN_DOCS)
    assert out == "a diagram"


def test_a_markdown_link_to_a_missing_document_becomes_its_text() -> None:
    assert rebase_links("[gone](./gone.md)", _PORTAL, **_IN_DOCS) == "gone"


@pytest.mark.parametrize(
    "text",
    [
        "![logo](./logo.png)",
        "[other](./other.md)",
        "[other](other)",
        "[other](./other.html#top)",
        "[sub](./sub/)",
        "[index](./)",
    ],
)
def test_a_markdown_link_to_a_file_the_mirrored_directory_publishes_is_left_as_written(
    text: str,
) -> None:
    assert rebase_links(text, _PORTAL, **_IN_DOCS) == text


def test_a_portal_that_names_no_published_files_trusts_a_link_inside_the_mirror() -> None:
    portal = PortalLinks(doc_slugs=_PORTAL.doc_slugs)
    assert rebase_links("![x](./missing.png)", portal, **_IN_DOCS) == "![x](./missing.png)"


# -- an image the portal publishes, on a page outside the mirrored directory --
#
# The portal copies every file under docs/ beside the published documents, so an
# image there is reachable from any page. On the code before this bead a README's
# raw <img src="docs/logo.png"> built and showed the logo on the About page, since
# the About page sits where the README does; the link rule must not lose that.


@pytest.mark.parametrize(
    ("page_dir", "expected"),
    [("", "./docs/logo.png"), ("ru", "../docs/logo.png"), ("services", "../docs/logo.png")],
)
def test_a_raw_image_the_portal_publishes_is_referenced_from_where_the_page_sits(
    page_dir: str, expected: str
) -> None:
    assert _src("docs/logo.png", _WITH_REPO, page_dir=page_dir) == expected


def test_a_markdown_image_the_portal_publishes_is_referenced_from_where_the_page_sits() -> None:
    out = rebase_links("![logo](./docs/logo.png)", _PORTAL, page_dir="ru")
    assert out == "![logo](../docs/logo.png)"


def test_a_link_to_a_published_file_that_is_not_an_image_is_not_rebased_as_one() -> None:
    link = _href("docs/logo.png", _WITH_REPO, page_dir="")
    assert link == f"{_REPO}/-/blob/{_REF}/docs/logo.png"


def test_with_no_page_location_a_published_image_follows_the_markdown_image_rule() -> None:
    assert _src("docs/logo.png") is None
