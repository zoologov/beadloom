"""A declared ``site.repo_url`` is read in one spelling, so a link built from it is the forge's.

BDL-076 ``beadloom-ujzb.20`` (R2 finding F9). The address was used as written,
and the forge's route was appended to it, so three ordinary spellings built
links no forge serves::

    https://github.com/o/r/           -> https://github.com/o/r//tree/<ref>/<path>
    https://github.com/o/r.git        -> https://github.com/o/r.git/tree/<ref>/<path>
    https://github.com/o/r/tree/main  -> https://github.com/o/r/tree/main/tree/<ref>/<path>

The first two name the same repository as the address without them: a trailing
``/`` is what a browser's address bar gives, and ``.git`` is the clone address a
forge prints. They are read away, together with the case of the scheme and the
host, which RFC 3986 makes case-insensitive. The path keeps its case: a forge may
serve ``Team/Orders`` and ``team/orders`` as two repositories.

The third is not a spelling of the repository: it is a page inside it, and no
reading recovers which part of the path is the repository on every forge. It is
refused by name, where it was written, when the path holds a route the forge
serving the host appends — read from that forge's own route templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.repository_link import RepositoryLink
from beadloom.application.site.site_config import read_site_config, render_site_module

if TYPE_CHECKING:
    from pathlib import Path


def _declared(tmp_path: Path, repo_url: str, forges: str = "") -> Path:
    root = tmp_path / "orders"
    (root / ".beadloom").mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(
        f"site:\n  repo_url: '{repo_url}'\n{forges}", encoding="utf-8"
    )
    return root


@pytest.mark.parametrize(
    ("written", "read"),
    [
        ("https://github.com/o/r/", "https://github.com/o/r"),
        ("https://github.com/o/r//", "https://github.com/o/r"),
        ("https://github.com/o/r.git", "https://github.com/o/r"),
        ("https://github.com/o/r.git/", "https://github.com/o/r"),
        ("https://GitHub.COM/o/r", "https://github.com/o/r"),
        ("HTTPS://github.com/o/r", "https://github.com/o/r"),
        (
            "https://Git.Acme.Example:8443/Team/Orders/",
            "https://git.acme.example:8443/Team/Orders",
        ),
        ("https://gitlab.com/acme/platform/orders.git", "https://gitlab.com/acme/platform/orders"),
        ("https://github.com/o/r", "https://github.com/o/r"),
    ],
)
def test_a_spelling_of_the_repository_is_read_as_its_address(
    tmp_path: Path, written: str, read: str
) -> None:
    config, refusals = read_site_config(_declared(tmp_path, written))
    assert refusals == ()
    assert config.repo_url == read


@pytest.mark.parametrize(
    "written", ["https://github.com/o/r/", "https://github.com/o/r.git", "https://GITHUB.com/o/r"]
)
def test_a_link_from_any_spelling_is_the_forges_route(tmp_path: Path, written: str) -> None:
    config, _ = read_site_config(_declared(tmp_path, written))
    link = RepositoryLink(url=config.repo_url, ref="abc")
    assert link.source_url("src/x") == "https://github.com/o/r/tree/abc/src/x"
    assert link.file_url("README.md") == "https://github.com/o/r/blob/abc/README.md"


def test_the_generated_module_carries_the_address_as_read(tmp_path: Path) -> None:
    config, _ = read_site_config(_declared(tmp_path, "https://github.com/o/r.git/"))
    module = render_site_module(config, tmp_path)
    assert '"repoUrl": "https://github.com/o/r"' in module


@pytest.mark.parametrize(
    ("written", "forges"),
    [
        ("https://github.com/o/r/tree/main", ""),
        ("https://github.com/o/r/blob/main/README.md", ""),
        ("https://gitlab.com/acme/platform/orders/-/tree/main", ""),
        ("https://bitbucket.org/acme/orders/src/main/", ""),
        ("https://codeberg.org/acme/orders/src/branch/main", ""),
        (
            "https://git.acme.example/team/orders/-/tree/main",
            "  forges:\n    git.acme.example: gitlab\n",
        ),
        (
            "https://code.acme.example/team/orders/browse/main",
            "  forges:\n    code.acme.example:\n      source: '{url}/browse/{ref}/{path}'\n",
        ),
    ],
)
def test_a_page_inside_the_repository_is_refused_by_name(
    tmp_path: Path, written: str, forges: str
) -> None:
    config, refusals = read_site_config(_declared(tmp_path, written, forges))
    assert [refusal.where for refusal in refusals] == ["site.repo_url"]
    why = refusals[0].why
    assert "past the repository" in why
    assert written not in why, "the value is never repeated: it may hold a credential"
    assert "repository's own address" in refusals[0].remediation
    assert config.repo_url == ""


@pytest.mark.parametrize(
    ("written", "forges"),
    [
        # A repository whose name is a route word is still a repository.
        ("https://github.com/o/tree", ""),
        ("https://github.com/tree/r", ""),
        ("https://bitbucket.org/acme/src", ""),
        # A group whose name is a route word, on a forge with nested groups.
        ("https://gitlab.com/acme/tree/orders", ""),
        # A host no forge is known for: nothing says which segment is a route.
        ("https://git.acme.example/team/orders/tree/x", ""),
        # Azure's route is a query, which is refused on its own.
        ("https://dev.azure.com/acme/shop/_git/orders", ""),
    ],
)
def test_an_address_holding_no_route_of_its_forge_is_kept(
    tmp_path: Path, written: str, forges: str
) -> None:
    config, refusals = read_site_config(_declared(tmp_path, written, forges))
    assert refusals == ()
    assert config.repo_url == written


# -- the re-review (``beadloom-ujzb.23``, n2) ---------------------------------------

#: The ``forges:`` entry declaring ``git.acme.example`` a forge of one kind.
_DECLARED = "  forges:\n    git.acme.example: {kind}\n"


@pytest.mark.parametrize(
    ("written", "forges"),
    [
        # A page of the repository a known forge serves at its own host's root.
        ("https://github.com/o/r/pulls", ""),
        ("https://github.com/o/r/issues", ""),
        ("https://github.com/o/r/wiki", ""),
        ("https://github.com/o/r/issues/12", ""),
        ("https://bitbucket.org/acme/orders/pull-requests", ""),
        ("https://codeberg.org/acme/orders/issues", ""),
        ("https://git.acme.example/o/r/pulls", _DECLARED.format(kind="github")),
        # A GitHub route on a GitLab host: GitLab reserves the word for its own routes.
        ("https://gitlab.com/acme/orders/tree/main", ""),
        ("https://gitlab.com/acme/orders/blob/main/README.md", ""),
        ("https://gitlab.com/acme/platform/orders/raw/main/x", ""),
        # Past the repository on Azure DevOps, whose repository ends at `_git/<name>`.
        ("https://dev.azure.com/acme/shop/_git/orders/pullrequests", ""),
    ],
)
def test_a_page_of_the_repository_is_refused_by_name(
    tmp_path: Path, written: str, forges: str
) -> None:
    config, refusals = read_site_config(_declared(tmp_path, written, forges))
    assert [refusal.where for refusal in refusals] == ["site.repo_url"]
    assert "past the repository" in refusals[0].why
    assert written not in refusals[0].why
    assert config.repo_url == ""


@pytest.mark.parametrize(
    ("written", "forges", "shape"),
    [
        ("https://github.com/o", "", "/<owner>/<repository>"),
        ("https://github.com", "", "/<owner>/<repository>"),
        ("https://gitlab.com/acme", "", "/<group>/<project>"),
        ("https://bitbucket.org/acme", "", "/<workspace>/<repository>"),
        ("https://codeberg.org/acme", "", "/<owner>/<repository>"),
        ("https://dev.azure.com/acme/shop", "", "/<organisation>/<project>/_git/<repository>"),
        (
            "https://git.acme.example/team",
            _DECLARED.format(kind="gitlab"),
            "/<group>/<project>",
        ),
    ],
)
def test_an_address_that_stops_before_a_repository_is_refused_by_name(
    tmp_path: Path, written: str, forges: str, shape: str
) -> None:
    config, refusals = read_site_config(_declared(tmp_path, written, forges))
    assert [refusal.where for refusal in refusals] == ["site.repo_url"]
    why = refusals[0].why
    assert "stops before a repository" in why
    assert shape in why
    assert written not in why
    assert config.repo_url == ""


@pytest.mark.parametrize(
    ("written", "forges"),
    [
        # GitLab nests groups, and a group may be named like a page.
        ("https://gitlab.com/acme/platform/team/orders", ""),
        ("https://gitlab.com/acme/orders/issues", ""),
        # A self-hosted Gitea or GitLab may live under a path of its host.
        ("https://git.acme.example/gitea/acme/orders", _DECLARED.format(kind="gitea")),
        ("https://git.acme.example/gitlab/acme/orders", _DECLARED.format(kind="gitlab")),
        # Azure DevOps Server keeps a collection in front of the project.
        ("https://git.acme.example/tfs/Main/shop/_git/orders", _DECLARED.format(kind="azure")),
        # A template forge says nothing about the shape of its addresses.
        (
            "https://code.acme.example",
            "  forges:\n    code.acme.example:\n      source: '{url}/browse/{ref}/{path}'\n",
        ),
    ],
)
def test_a_repository_address_whose_shape_the_forge_allows_is_kept(
    tmp_path: Path, written: str, forges: str
) -> None:
    config, refusals = read_site_config(_declared(tmp_path, written, forges))
    assert refusals == ()
    assert config.repo_url == written
