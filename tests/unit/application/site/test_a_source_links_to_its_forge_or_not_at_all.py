"""A node's source links to the page its forge serves, or to nothing (BDL-076 R1 finding M1).

Each forge serves a path at a revision under its own route, and the viewer used
GitHub's for every remote, so a Bitbucket, Gitea or Azure DevOps adopter got a
dead link on every card. The generator knows the remote, so it decides the link
and writes it finished into the data file. A host it does not recognise gets no
link: the card then shows the source as plain text, which is true, where a
guessed route would be a 404 that looks like a link.
"""

from __future__ import annotations

import pytest

from beadloom.application.site.repository_link import RepositoryLink

#: The commit the site was generated from, as `repository_of` records it.
_REF = "0123456789abcdef0123456789abcdef01234567"


@pytest.mark.parametrize(
    ("url", "link"),
    [
        ("https://github.com/team/shop", f"https://github.com/team/shop/tree/{_REF}/src/a.py"),
        ("https://gitlab.com/team/shop", f"https://gitlab.com/team/shop/-/tree/{_REF}/src/a.py"),
        (
            "https://gitlab.com/group/sub/shop",
            f"https://gitlab.com/group/sub/shop/-/tree/{_REF}/src/a.py",
        ),
        (
            "https://bitbucket.org/team/shop",
            f"https://bitbucket.org/team/shop/src/{_REF}/src/a.py",
        ),
        (
            "https://codeberg.org/team/shop",
            f"https://codeberg.org/team/shop/src/commit/{_REF}/src/a.py",
        ),
        ("https://gitea.com/team/shop", f"https://gitea.com/team/shop/src/commit/{_REF}/src/a.py"),
        (
            "https://dev.azure.com/org/project/_git/shop",
            f"https://dev.azure.com/org/project/_git/shop?path=/src/a.py&version=GC{_REF}",
        ),
        (
            "https://org.visualstudio.com/project/_git/shop",
            f"https://org.visualstudio.com/project/_git/shop?path=/src/a.py&version=GC{_REF}",
        ),
    ],
    ids=["github", "gitlab", "gitlab-subgroup", "bitbucket", "codeberg", "gitea", "azure", "vsts"],
)
def test_a_public_forge_links_the_source_at_the_commit(url: str, link: str) -> None:
    assert RepositoryLink(url=url, ref=_REF).source_url("src/a.py") == link


@pytest.mark.parametrize(
    "url",
    [
        "https://git.example/team/shop",
        "https://intranet.example/owner/repo",
        # A self-hosted forge is not recognised by its host, even when the host
        # names the product: it is declared in the project's configuration
        # (the owner's ruling, `beadloom-ujzb.8`). Until then it gets no link.
        "https://gitlab.corp.example/team/shop",
        "https://github.corp.example/team/shop",
        "https://bitbucket.corp.example/team/shop",
        "https://tfs.corp.example/collection/project/_git/shop",
        # A host that merely contains a forge's name is not that forge.
        "https://notgithub.com/team/shop",
        "https://github.com.example/team/shop",
        # Azure DevOps' SSH host serves no web pages (re-review finding m1).
        "https://vs-ssh.visualstudio.com/DefaultCollection/sales/_ssh/shop",
        # An address no parser can read gives no link rather than an error.
        "https://[2001/db8::1]:team/shop",
    ],
)
def test_a_host_the_generator_does_not_recognise_gets_no_link(url: str) -> None:
    assert RepositoryLink(url=url, ref=_REF).source_url("src/a.py") == ""


@pytest.mark.parametrize(
    ("source", "encoded"),
    [
        ("src/my module/a b.py", "src/my%20module/a%20b.py"),
        ("src/c#/x.py", "src/c%23/x.py"),
        ("src/q?/x&y.py", "src/q%3F/x%26y.py"),
        ("src/pkg/", "src/pkg"),
        ("docs/ü.md", "docs/%C3%BC.md"),
    ],
)
def test_the_path_is_url_encoded(source: str, encoded: str) -> None:
    link = RepositoryLink(url="https://github.com/team/shop", ref=_REF).source_url(source)

    assert link == f"https://github.com/team/shop/tree/{_REF}/{encoded}"


def test_the_azure_path_is_encoded_inside_its_query() -> None:
    azure = RepositoryLink(url="https://dev.azure.com/o/p/_git/r", ref=_REF)

    link = azure.source_url("a b/c&d.py")

    assert link == f"https://dev.azure.com/o/p/_git/r?path=/a%20b/c%26d.py&version=GC{_REF}"


@pytest.mark.parametrize(
    ("url", "ref", "source"),
    [
        ("", _REF, "src/a.py"),
        ("https://github.com/team/shop", "", "src/a.py"),
        ("https://github.com/team/shop", _REF, ""),
        ("https://github.com/team/shop", _REF, "/"),
    ],
    ids=["no-repository", "no-commit", "no-source", "root-only"],
)
def test_nothing_to_link_gives_no_link(url: str, ref: str, source: str) -> None:
    assert RepositoryLink(url=url, ref=ref).source_url(source) == ""
