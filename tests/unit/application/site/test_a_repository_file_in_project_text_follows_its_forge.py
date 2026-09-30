"""A link from project text to a repository file goes to its forge's route at the commit.

BDL-076 B4 (``beadloom-ujzb.8``). A link in the README, a node summary or a
published document to a file the portal does not publish went to
``<repo_url>/blob/main/<path>``: GitHub's route, on every forge, at a branch
assumed to be ``main``. An image went to the same page, which a forge serves as
HTML and not as the image, so it drew as a broken image.

The link is now the declared repository's own route at the commit the site was
generated from: a file goes to the page its forge shows it on, an image to the
file itself. With no commit to link at, a path has no true address and the link
becomes its text, as it does with no repository.
"""

from __future__ import annotations

from beadloom.application.site.forge_routes import KNOWN_FORGES, read_forge
from beadloom.application.site.markdown_links import (
    PortalLinks,
    raw_html_destination,
    rebase_links,
)
from beadloom.application.site.repository_link import RepositoryLink

_REF = "89abcdef0123456789abcdef0123456789abcdef"
_GITLAB = "https://git.acme.example/platform/shop"
_SELF_HOSTED = RepositoryLink(
    url=_GITLAB, ref=_REF, forges={"git.acme.example": KNOWN_FORGES["gitlab"]}
)
_PORTAL = PortalLinks(repository=_SELF_HOSTED)


def test_a_link_to_a_file_goes_to_the_forges_page_for_it_at_the_commit() -> None:
    out = rebase_links("See [license](LICENSE).", _PORTAL)

    assert out == f"See [license]({_GITLAB}/-/blob/{_REF}/LICENSE)."


def test_an_image_goes_to_the_file_itself() -> None:
    out = rebase_links("![logo](art/logo.png)", _PORTAL)

    assert out == f"![logo]({_GITLAB}/-/raw/{_REF}/art/logo.png)"


def test_a_badge_links_its_image_to_the_file_and_its_target_to_the_page() -> None:
    out = rebase_links("[![ci](art/ci.svg)](ci/README.txt)", _PORTAL)

    assert out == (
        f"[![ci]({_GITLAB}/-/raw/{_REF}/art/ci.svg)]({_GITLAB}/-/blob/{_REF}/ci/README.txt)"
    )


def test_a_raw_html_image_goes_to_the_file_and_a_raw_link_to_the_page() -> None:
    assert raw_html_destination("art/logo.png", _PORTAL, asset=True) == (
        f"{_GITLAB}/-/raw/{_REF}/art/logo.png"
    )
    assert raw_html_destination("LICENSE", _PORTAL) == f"{_GITLAB}/-/blob/{_REF}/LICENSE"


def test_a_link_to_the_repository_root_is_the_repository() -> None:
    assert rebase_links("[repo](/)", _PORTAL) == f"[repo]({_GITLAB})"


def test_github_keeps_its_own_routes_at_the_commit() -> None:
    github = PortalLinks(repository=RepositoryLink(url="https://github.com/team/shop", ref=_REF))

    assert rebase_links("[l](LICENSE)", github) == (
        f"[l](https://github.com/team/shop/blob/{_REF}/LICENSE)"
    )
    assert rebase_links("![a](a.png)", github) == (
        f"![a](https://github.com/team/shop/raw/{_REF}/a.png)"
    )


def test_a_query_on_the_link_joins_a_route_that_already_has_one() -> None:
    azure = PortalLinks(
        repository=RepositoryLink(url="https://dev.azure.com/org/sales/_git/shop", ref=_REF)
    )

    out = rebase_links("[l](src/a.py?plain=1)", azure)

    assert out == (
        f"[l](https://dev.azure.com/org/sales/_git/shop?path=/src/a.py&version=GC{_REF}&plain=1)"
    )


def test_without_a_commit_a_path_has_no_address_and_becomes_text() -> None:
    no_commit = PortalLinks(repository=RepositoryLink(url=_GITLAB, forges=_SELF_HOSTED.forges))

    assert rebase_links("See [license](LICENSE).", no_commit) == "See license."
    assert rebase_links("![logo](art/logo.png)", no_commit) == "logo"


def test_a_host_no_forge_is_declared_for_links_no_file() -> None:
    unknown = PortalLinks(repository=RepositoryLink(url=_GITLAB, ref=_REF))

    assert rebase_links("See [license](LICENSE).", unknown) == "See license."


def test_a_template_forge_without_a_raw_route_shows_an_image_as_its_text() -> None:
    forge, _ = read_forge({"source": "{url}/browse/{path}?at={ref}"})
    assert forge is not None
    portal = PortalLinks(
        repository=RepositoryLink(
            url="https://code.acme.example/shop", ref=_REF, forges={"code.acme.example": forge}
        )
    )

    assert rebase_links("![logo](art/logo.png)", portal) == "logo"
    assert rebase_links("[l](LICENSE)", portal) == (
        f"[l](https://code.acme.example/shop/browse/LICENSE?at={_REF})"
    )
