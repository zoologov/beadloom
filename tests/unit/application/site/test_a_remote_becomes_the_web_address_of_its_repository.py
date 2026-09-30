"""The node card links a node's source to its repository (BDL-076 A3).

The repository's web address is derived from the project's own ``origin``
remote, never from a constant: an adopter's portal must link to the adopter's
repository. A remote in any of git's spellings becomes one web address, and a
credential written into the remote never reaches a page that is published. The
link to one source path, per forge, is ``test_a_source_links_to_its_forge_or_not_at_all``.
"""

from __future__ import annotations

import pytest

from beadloom.application.site.repository_link import web_url_of_remote


@pytest.mark.parametrize(
    ("remote", "web_url"),
    [
        ("https://github.com/owner/repo.git", "https://github.com/owner/repo"),
        ("https://github.com/owner/repo", "https://github.com/owner/repo"),
        ("https://github.com/owner/repo/", "https://github.com/owner/repo"),
        ("git@github.com:owner/repo.git", "https://github.com/owner/repo"),
        ("git@gitlab.example.com:group/sub/repo.git", "https://gitlab.example.com/group/sub/repo"),
        ("ssh://git@host.example:2222/owner/repo.git", "https://host.example/owner/repo"),
        ("http://intranet.example/owner/repo.git", "http://intranet.example/owner/repo"),
        # Azure DevOps serves its SSH remotes from another host and another path
        # than its web pages (BDL-076 R1 finding M1).
        (
            "git@ssh.dev.azure.com:v3/org/project/repo",
            "https://dev.azure.com/org/project/_git/repo",
        ),
        (
            "ssh://git@ssh.dev.azure.com/v3/org/project/repo",
            "https://dev.azure.com/org/project/_git/repo",
        ),
        (
            "https://org@dev.azure.com/org/project/_git/repo",
            "https://dev.azure.com/org/project/_git/repo",
        ),
        (
            "org@vs-ssh.visualstudio.com:v3/org/project/repo",
            "https://org.visualstudio.com/project/_git/repo",
        ),
    ],
)
def test_each_spelling_of_a_remote_becomes_one_web_address(remote: str, web_url: str) -> None:
    assert web_url_of_remote(remote) == web_url


@pytest.mark.parametrize(
    "remote",
    [
        "https://user:secret-token@github.com/owner/repo.git",
        "https://oauth2:secret-token@gitlab.example.com/group/repo",
    ],
)
def test_a_credential_in_the_remote_is_dropped(remote: str) -> None:
    web_url = web_url_of_remote(remote)

    assert "secret-token" not in web_url
    assert "@" not in web_url
    assert web_url.startswith("https://")


@pytest.mark.parametrize(
    "remote",
    ["", "   ", "/srv/git/repo.git", "file:///srv/git/repo.git", "../sibling-repo"],
)
def test_a_remote_with_no_web_address_gives_none(remote: str) -> None:
    assert web_url_of_remote(remote) == ""
