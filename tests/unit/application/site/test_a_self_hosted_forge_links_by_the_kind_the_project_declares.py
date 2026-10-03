"""A self-hosted forge gets the links of the forge kind the project declares for its host.

BDL-076 B4 (``beadloom-ujzb.8``). The owner's team keeps its repositories on its
own GitLab. The generator recognises a forge by its public host only, because a
guessed route is a 404 that looks like a link, so a self-hosted host got no
source link at all. The project now names the forge that serves a host in the
``site.forges`` setting, and that forge's routes are reused; a forge no kind
describes is given as a URL template.

One object decides every repository link, per forge, at the commit the site was
generated from: the page for a path (``tree``, the card's source link; ``blob``,
a link in the project's own text) and the file itself (``raw``, an image in that
text), because a forge serves an image's page as HTML and not as the image.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.forge_routes import KNOWN_FORGES, read_forge
from beadloom.application.site.repository_link import RepositoryLink, web_url_of_remote

if TYPE_CHECKING:
    from collections.abc import Mapping

    from beadloom.application.site.forge_routes import Forge

#: The commit the site was generated from, as ``repository_of`` records it.
_REF = "0123456789abcdef0123456789abcdef01234567"

#: The team's own GitLab, by the host the project declares it for.
_HOST = "git.acme.example"
_SELF_HOSTED_GITLAB = {_HOST: KNOWN_FORGES["gitlab"]}

#: The repository, three groups deep, as its web address.
_WEB = f"https://{_HOST}/platform/team/shop"


def _link(url: str, forges: Mapping[str, Forge] | None = None) -> RepositoryLink:
    return RepositoryLink(url=url, ref=_REF, forges=forges or {})


# -- a self-hosted GitLab, in every remote form git accepts ----------------------


@pytest.mark.parametrize(
    ("remote", "web"),
    [
        (f"https://{_HOST}/platform/team/shop.git", _WEB),
        (f"https://{_HOST}/platform/team/shop", _WEB),
        (f"git@{_HOST}:platform/team/shop.git", _WEB),
        (f"ssh://git@{_HOST}/platform/team/shop.git", _WEB),
        # An SSH port is the SSH server's, not the web server's: it is dropped.
        (f"ssh://git@{_HOST}:2222/platform/team/shop.git", _WEB),
        # An HTTPS port is the web server's: it is kept.
        (
            f"https://{_HOST}:8443/platform/team/shop.git",
            f"https://{_HOST}:8443/platform/team/shop",
        ),
        # A token in the remote never reaches the link.
        (f"https://oauth2:SECRET@{_HOST}/platform/team/shop.git", _WEB),
    ],
    ids=["https", "https-no-suffix", "scp", "ssh", "ssh-port", "https-port", "https-token"],
)
def test_a_self_hosted_gitlab_remote_links_by_gitlabs_routes(remote: str, web: str) -> None:
    repository = _link(web_url_of_remote(remote), _SELF_HOSTED_GITLAB)

    assert repository.source_url("src/a.py") == f"{web}/-/tree/{_REF}/src/a.py"
    assert repository.file_url("LICENSE") == f"{web}/-/blob/{_REF}/LICENSE"
    assert repository.raw_url("art/logo.png") == f"{web}/-/raw/{_REF}/art/logo.png"
    assert "SECRET" not in repository.source_url("src/a.py")


def test_a_gitlab_served_under_a_path_prefix_keeps_the_prefix_before_its_routes() -> None:
    web = web_url_of_remote("https://acme.example/gitlab/platform/shop.git")
    repository = _link(web, {"acme.example": KNOWN_FORGES["gitlab"]})

    prefix = "https://acme.example/gitlab/platform/shop"
    assert repository.source_url("src") == f"{prefix}/-/tree/{_REF}/src"
    assert repository.raw_url("a.png") == f"{prefix}/-/raw/{_REF}/a.png"


def test_the_declared_host_is_matched_whatever_its_case() -> None:
    repository = _link("https://GIT.Acme.Example/platform/team/shop", _SELF_HOSTED_GITLAB)

    assert "/-/tree/" in repository.source_url("src/a.py")


def test_a_declared_host_leaves_every_other_host_as_it_was() -> None:
    github = _link("https://github.com/team/shop", _SELF_HOSTED_GITLAB)
    unknown = _link("https://git.other.example/team/shop", _SELF_HOSTED_GITLAB)

    assert github.source_url("a.py") == f"https://github.com/team/shop/tree/{_REF}/a.py"
    assert unknown.source_url("a.py") == ""


def test_without_a_declaration_a_self_hosted_host_still_gets_no_link() -> None:
    repository = _link(_WEB)

    assert repository.source_url("src/a.py") == ""
    assert repository.file_url("LICENSE") == ""
    assert repository.raw_url("art/logo.png") == ""


# -- every forge kind: the page for a path, and the file itself ------------------


@pytest.mark.parametrize(
    ("kind", "url", "tree", "blob", "raw"),
    [
        (
            "github",
            "https://github.com/team/shop",
            "https://github.com/team/shop/tree/{ref}/{path}",
            "https://github.com/team/shop/blob/{ref}/{path}",
            "https://github.com/team/shop/raw/{ref}/{path}",
        ),
        (
            "gitlab",
            "https://gitlab.com/group/sub/shop",
            "https://gitlab.com/group/sub/shop/-/tree/{ref}/{path}",
            "https://gitlab.com/group/sub/shop/-/blob/{ref}/{path}",
            "https://gitlab.com/group/sub/shop/-/raw/{ref}/{path}",
        ),
        (
            "gitea",
            "https://codeberg.org/team/shop",
            "https://codeberg.org/team/shop/src/commit/{ref}/{path}",
            "https://codeberg.org/team/shop/src/commit/{ref}/{path}",
            "https://codeberg.org/team/shop/raw/commit/{ref}/{path}",
        ),
        (
            "bitbucket",
            "https://bitbucket.org/team/shop",
            "https://bitbucket.org/team/shop/src/{ref}/{path}",
            "https://bitbucket.org/team/shop/src/{ref}/{path}",
            "https://bitbucket.org/team/shop/raw/{ref}/{path}",
        ),
        (
            "azure",
            "https://dev.azure.com/org/sales/_git/shop",
            "https://dev.azure.com/org/sales/_git/shop?path=/{path}&version=GC{ref}",
            "https://dev.azure.com/org/sales/_git/shop?path=/{path}&version=GC{ref}",
            "https://dev.azure.com/org/sales/_apis/git/repositories/shop/items"
            "?path=/{path}&versionDescriptor.version={ref}"
            "&versionDescriptor.versionType=commit&%24format=octetStream&download=false"
            "&api-version=7.1",
        ),
    ],
    ids=["github", "gitlab", "gitea", "bitbucket", "azure"],
)
def test_each_forge_serves_a_path_and_its_file_under_its_own_routes(
    kind: str, url: str, tree: str, blob: str, raw: str
) -> None:
    # Declared for the host, so the kind is what decides, not the public host table.
    host = url.split("/")[2]
    repository = _link(url, {host: KNOWN_FORGES[kind]})
    path = "docs/a b.png"
    encoded = "docs/a%20b.png"

    assert repository.source_url(path) == tree.format(ref=_REF, path=encoded)
    assert repository.file_url(path) == blob.format(ref=_REF, path=encoded)
    assert repository.raw_url(path) == raw.format(ref=_REF, path=encoded)


def test_an_azure_address_without_its_git_segment_serves_no_raw_file() -> None:
    forges = {"dev.azure.com": KNOWN_FORGES["azure"]}
    repository = _link("https://dev.azure.com/org/sales", forges)

    assert repository.raw_url("a.png") == ""


# -- a forge no kind describes: a URL template -----------------------------------


def test_a_template_gives_the_page_and_the_file_it_describes() -> None:
    forge, problems = read_forge(
        {"source": "{url}/browse/{path}?at={ref}", "raw": "{url}/raw/{path}?at={ref}"}
    )
    assert problems == ()
    assert forge is not None
    base = "https://code.acme.example/projects/SHOP/repos/shop"
    repository = _link(base, {"code.acme.example": forge})

    assert repository.source_url("src/a b.py") == f"{base}/browse/src/a%20b.py?at={_REF}"
    assert repository.file_url("LICENSE") == f"{base}/browse/LICENSE?at={_REF}"
    assert repository.raw_url("art/logo.png") == f"{base}/raw/art/logo.png?at={_REF}"


def test_a_template_without_a_raw_route_serves_no_image() -> None:
    forge, problems = read_forge({"source": "{url}/browse/{path}?at={ref}"})
    assert problems == ()
    assert forge is not None
    repository = _link("https://code.acme.example/shop", {"code.acme.example": forge})

    link = repository.file_url("LICENSE")
    assert link == f"https://code.acme.example/shop/browse/LICENSE?at={_REF}"
    assert repository.raw_url("art/logo.png") == ""


@pytest.mark.parametrize("kind", sorted(KNOWN_FORGES))
def test_a_kind_name_is_read_as_that_forge(kind: str) -> None:
    assert read_forge(kind) == (KNOWN_FORGES[kind], ())


@pytest.mark.parametrize(
    ("setting", "said"),
    [
        ("gitlab-ce", "`gitlab-ce`, which is not a forge kind"),
        ("", "not a forge kind"),
        (42, "a number"),
        (["gitlab"], "a list"),
        ({"raw": "{url}/raw/{ref}/{path}"}, "no `source:`"),
        ({"source": "{url}/{path}", "row": "{url}/raw/{path}"}, "`row:`"),
        ({"source": "{url}/src/{branch}/{path}"}, "`{branch}`"),
        ({"source": "{url}/src/{ref}"}, "`{path}`"),
        ({"source": "{url}/src/{ref}/{path"}, "brace"),
        ({"source": "{url}/src/}{ref}/{path}"}, "brace"),
        ({"source": "{url}/src/{path!r}"}, "`{path!r}`"),
        ({"source": "{url}/src/{path:>9}"}, "`{path:>9}`"),
        ({"source": "/src/{ref}/{path}"}, "http(s)"),
        ({"source": "ftp://code.acme.example/{path}"}, "http(s)"),
        ({"source": "https://user:pw@code.acme.example/{path}"}, "credential"),
        ({"source": "{url}/src/{path}", "raw": 7}, "`raw:` is a number"),
        ({"source": "{gitlab}/{path}"}, "`{gitlab}`"),
        ({"source": "{}/{path}"}, "`{}`"),
    ],
    ids=[
        "unknown-kind",
        "empty-kind",
        "a-number",
        "a-list",
        "no-source",
        "unknown-template-key",
        "unknown-placeholder",
        "no-path",
        "unclosed-brace",
        "stray-brace",
        "conversion",
        "format-spec",
        "no-scheme",
        "not-web",
        "credential",
        "raw-a-number",
        "kind-as-placeholder",
        "positional",
    ],
)
def test_a_setting_that_names_no_forge_is_refused_with_its_reason(
    setting: object, said: str
) -> None:
    forge, problems = read_forge(setting)

    assert forge is None
    assert problems, "a refused setting says why"
    assert any(said in problem for problem in problems), problems


def test_an_unknown_kind_is_refused_with_the_kinds_there_are() -> None:
    _, problems = read_forge("gitlab-ce")

    for kind in KNOWN_FORGES:
        assert f"`{kind}`" in problems[0]
