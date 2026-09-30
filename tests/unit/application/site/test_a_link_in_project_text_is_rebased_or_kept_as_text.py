"""A link in text the generator copies from the project's files, on the portal page it lands on.

BDL-076 (``beadloom-ujzb.11``). ``beadloom init`` takes the root service's
summary from the README's first paragraph, and the node page wrote it as it was:
``See [license](LICENSE).`` became a link to ``./LICENSE`` beside the service's
page, a file the portal does not publish, and ``vitepress build`` failed. The link
was correct where its author wrote it; the generator moved the text.

:func:`rebase_links` is the one rule every page that carries project text uses:

- a link to a file the portal publishes goes to that file's page;
- a link to any other file in the repository goes to the declared repository,
  or becomes its own text when none is declared (an image becomes its alt text);
- a link that leaves the repository becomes its text;
- an absolute address, a protocol-relative one and an anchor stay as written;
- a page that mirrors a directory (the published ``docs/``) keeps a link that
  stays inside it, because the relative path still resolves there;
- nothing inside a code span or a fenced block changes.
"""

from __future__ import annotations

import pytest

from beadloom.application.site.markdown_links import PortalLinks, rebase_links
from beadloom.application.site.repository_link import RepositoryLink

_REPO = "https://gitlab.com/acme/orders"
#: The commit the site was generated from (BDL-076 B4: links are at it, not at `main`).
_REF = "fedcba9876543210fedcba9876543210fedcba98"

#: What the portal publishes in these tests: two documents and the README pair.
_PUBLISHED = PortalLinks(
    doc_slugs=frozenset({"guide", "domains/orders"}),
    page_routes={"readme.md": "/", "readme.ru.md": "/ru/"},
)
_WITH_REPO = PortalLinks(
    doc_slugs=_PUBLISHED.doc_slugs,
    page_routes=_PUBLISHED.page_routes,
    repository=RepositoryLink(url=_REPO, ref=_REF),
)


# -- a relative link to a file the portal does not publish --------------------


@pytest.mark.parametrize("target", ["LICENSE", "./LICENSE", "src/../LICENSE", "/LICENSE"])
def test_a_link_to_an_unpublished_file_becomes_its_text(target: str) -> None:
    assert rebase_links(f"See [license]({target}).", _PUBLISHED) == "See license."


@pytest.mark.parametrize("target", ["LICENSE", "./LICENSE", "/LICENSE"])
def test_a_link_to_an_unpublished_file_goes_to_the_declared_repository(target: str) -> None:
    out = rebase_links(f"See [license]({target}).", _WITH_REPO)
    assert out == f"See [license]({_REPO}/-/blob/{_REF}/LICENSE)."


def test_a_link_that_leaves_the_repository_becomes_its_text_even_with_a_repository() -> None:
    assert rebase_links("[up](../other/README.md)", _WITH_REPO) == "up"


def test_a_link_keeps_its_fragment_when_it_goes_to_the_repository() -> None:
    out = rebase_links("[line](src/app.js#L10)", _WITH_REPO)
    assert out == f"[line]({_REPO}/-/blob/{_REF}/src/app.js#L10)"


def test_a_link_keeps_its_title() -> None:
    out = rebase_links('[license](LICENSE "The licence")', _WITH_REPO)
    assert out == f'[license]({_REPO}/-/blob/{_REF}/LICENSE "The licence")'


def test_an_angle_bracketed_target_is_read_without_its_brackets() -> None:
    assert rebase_links("[notes](<docs/guide.md>)", _PUBLISHED) == "[notes](/docs/guide)"


# -- a relative link to a file the portal publishes ---------------------------


@pytest.mark.parametrize(
    "target", ["docs/guide.md", "./docs/guide.md", "docs/guide", "/docs/guide.md"]
)
def test_a_link_to_a_published_document_goes_to_its_page(target: str) -> None:
    assert rebase_links(f"[the guide]({target})", _PUBLISHED) == "[the guide](/docs/guide)"


def test_a_link_to_a_published_document_keeps_its_anchor() -> None:
    out = rebase_links("[setup](docs/guide.md#setup)", _PUBLISHED)
    assert out == "[setup](/docs/guide#setup)"


def test_a_link_to_the_readme_pair_goes_to_its_about_page() -> None:
    out = rebase_links("[en](README.md), [ru](./README.ru.md)", _PUBLISHED)
    assert out == "[en](/), [ru](/ru/)"


def test_a_readme_the_portal_does_not_publish_is_not_a_page() -> None:
    portal = PortalLinks(page_routes={"readme.md": "/"})
    assert rebase_links("[ru](README.ru.md)", portal) == "ru"


# -- a text that sits below the project root ----------------------------------


def test_a_parent_link_from_a_document_resolves_against_the_document() -> None:
    out = rebase_links(
        "[readme](../../README.md) and [code](../../src/app.js)",
        _PUBLISHED,
        source_dir="docs/guides",
        mirrored_dir="docs",
    )
    assert out == "[readme](/) and code"


def test_a_link_that_stays_in_the_mirrored_directory_is_left_as_written() -> None:
    text = "[orders](../domains/orders.md) and ![flow](img/flow.png)"
    out = rebase_links(text, _PUBLISHED, source_dir="docs/guides", mirrored_dir="docs")
    assert out == text


# -- images -------------------------------------------------------------------


def test_a_relative_image_becomes_its_alt_text() -> None:
    assert rebase_links("![the flow](assets/flow.png)", _PUBLISHED) == "the flow"


def test_a_relative_image_goes_to_the_declared_repository() -> None:
    out = rebase_links("![the flow](assets/flow.png)", _WITH_REPO)
    assert out == f"![the flow]({_REPO}/-/raw/{_REF}/assets/flow.png)"


def test_a_badge_link_keeps_its_badge_when_its_target_is_dropped() -> None:
    out = rebase_links("[![ci](https://img.shields.io/badge/ci-green)](LICENSE)", _PUBLISHED)
    assert out == "![ci](https://img.shields.io/badge/ci-green)"


# -- reference-style links ----------------------------------------------------


def test_a_reference_definition_to_a_published_document_is_rebased() -> None:
    text = "See [the guide][gs].\n\n[gs]: docs/guide.md\n"
    assert rebase_links(text, _PUBLISHED) == "See [the guide][gs].\n\n[gs]: /docs/guide\n"


def test_a_reference_definition_goes_to_the_declared_repository_with_its_title() -> None:
    text = 'See [the licence][lic].\n\n[lic]: ./LICENSE "MIT"\n'
    out = rebase_links(text, _WITH_REPO)
    assert out == f'See [the licence][lic].\n\n[lic]: {_REPO}/-/blob/{_REF}/LICENSE "MIT"\n'


def test_a_withdrawn_reference_becomes_its_text_in_every_form() -> None:
    text = (
        "Read [the licence][Lic], [lic][] and [lic]; ![logo][art].\n"
        "\n"
        "[lic]: LICENSE\n"
        "[art]: assets/logo.png\n"
    )
    assert rebase_links(text, _PUBLISHED) == "Read the licence, lic and lic; logo.\n\n"


def test_a_bracketed_word_that_names_no_withdrawn_reference_is_left_alone() -> None:
    text = "An [aside] and [a link][home].\n\n[lic]: LICENSE\n[home]: https://acme.test\n"
    out = rebase_links(text, _PUBLISHED)
    assert out == "An [aside] and [a link][home].\n\n[home]: https://acme.test\n"


# -- what never changes -------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "[site](https://acme.test/orders)",
        "[site](http://acme.test)",
        "[mail](mailto:team@acme.test)",
        "[cdn](//cdn.acme.test/x.js)",
        "[usage](#usage)",
        "![badge](https://img.shields.io/badge/build-passing-green)",
        "[nothing]()",
    ],
)
def test_an_absolute_address_or_an_anchor_is_left_as_written(text: str) -> None:
    assert rebase_links(text, _PUBLISHED) == text


@pytest.mark.parametrize(
    "text",
    [
        "Run `[x](LICENSE)` to see it.",
        "Use ``[x](LICENSE)`` literally.",
        "```\n[x](LICENSE)\n[y]: LICENSE\n```\n",
        "`[lic]: LICENSE`",
    ],
)
def test_a_link_inside_code_is_left_as_written(text: str) -> None:
    assert rebase_links(text, _PUBLISHED) == text


def test_a_link_beside_a_code_span_is_still_rebased() -> None:
    out = rebase_links("Run `[x](LICENSE)`, then read [license](LICENSE).", _PUBLISHED)
    assert out == "Run `[x](LICENSE)`, then read license."


def test_prose_with_no_link_is_unchanged() -> None:
    text = "# Title\n\nJust prose, a (parenthetical), and [unclosed bracket.\n"
    assert rebase_links(text, _PUBLISHED) == text


def test_the_repository_form_is_stable_under_a_second_pass() -> None:
    once = rebase_links("[license](LICENSE) and [site](https://acme.test)", _WITH_REPO)
    assert rebase_links(once, _WITH_REPO) == once
