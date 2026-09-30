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


@pytest.mark.parametrize(
    "remote",
    [
        # Azure DevOps' legacy SSH remotes name a collection and an `_ssh` segment
        # where the web address has neither in that form. Only the `v3` form is
        # mapped; any other SSH remote on an Azure host gets no address rather
        # than one on the SSH host that looks right (re-review finding m1).
        "ssh://org@vs-ssh.visualstudio.com:22/DefaultCollection/sales/_ssh/shop",
        "ssh://org@vs-ssh.visualstudio.com:22/sales/_ssh/shop",
        "ssh://org@org.visualstudio.com:22/DefaultCollection/sales/_ssh/shop",
        "git@ssh.dev.azure.com:org/sales/shop",
        "ssh://git@ssh.dev.azure.com/org/sales/shop",
    ],
)
def test_an_azure_ssh_remote_other_than_v3_gives_none(remote: str) -> None:
    assert web_url_of_remote(remote) == ""


@pytest.mark.parametrize(
    "remote",
    [
        # git reads each of these; the parser cannot. A remote that cannot be read
        # gives no address, and never stops the site (re-review finding m2).
        "git@[2001:db8::1]:team/shop.git",
        "git@[2001:db8::1]:22:team/shop.git",
        # An IPv6 address is no forge's host, and git's other spellings of it
        # parse into an address with its brackets lost.
        "ssh://git@[2001:db8::1]:22/team/shop.git",
        "https://[::1]:8080/team/shop.git",
        "https://github.com:https/team/shop.git",
        "https://github.com:99999/team/shop.git",
        "https://[2001:db8::1/team/shop.git",
    ],
)
def test_a_remote_that_cannot_be_parsed_gives_none(remote: str) -> None:
    assert web_url_of_remote(remote) == ""
