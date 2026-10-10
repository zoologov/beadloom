"""The icon beside the portal's repository link: the host's forge, or ``site.repo_icon``.

BDL-080 S4d (``beadloom-af99.7``), the owner's ruling of 2026-10-09: github.com
draws GitHub, a ``gitlab.*`` host GitLab, bitbucket.org Bitbucket, codeberg.org
Codeberg, a ``gitea.*`` host Gitea, anything else git's own mark; the declared
icon wins over the host; no repository, no icon.
"""

from __future__ import annotations

import pytest

from beadloom.application.site.forge_routes import KNOWN_FORGES, Forge
from beadloom.application.site.repository_icon import GENERIC_ICON, REPO_ICONS, repo_icon_of


@pytest.mark.parametrize(
    ("url", "icon"),
    [
        ("https://github.com/acme/orders", "github"),
        ("https://gitlab.com/acme/orders", "gitlab"),
        ("https://gitlab.acme.example/sales/orders", "gitlab"),
        ("https://GitLab.Acme.Example/sales/orders", "gitlab"),
        ("https://bitbucket.org/acme/orders", "bitbucket"),
        ("https://codeberg.org/acme/orders", "codeberg"),
        ("https://gitea.com/acme/orders", "gitea"),
        ("https://gitea.acme.example/sales/orders", "gitea"),
        ("https://dev.azure.com/acme/orders/_git/orders", "azuredevops"),
        ("https://acme.visualstudio.com/orders/_git/orders", "azuredevops"),
        ("https://git.acme.example/sales/orders", GENERIC_ICON),
        ("https://code.gitlab-mirror.example/sales/orders", GENERIC_ICON),
    ],
)
def test_the_host_names_the_icon(url: str, icon: str) -> None:
    assert repo_icon_of(url) == icon


@pytest.mark.parametrize("icon", REPO_ICONS)
def test_a_declared_icon_wins_over_the_host(icon: str) -> None:
    assert repo_icon_of("https://github.com/acme/orders", declared=icon) == icon


def test_no_repository_draws_no_icon_whatever_is_declared() -> None:
    assert repo_icon_of("", declared="gitlab") == ""


def test_a_declared_forge_kind_names_the_icon_of_its_host() -> None:
    forges = {"git.acme.example": KNOWN_FORGES["gitlab"]}
    assert repo_icon_of("https://git.acme.example/sales/orders", forges) == "gitlab"


def test_a_forge_declared_by_template_is_read_by_its_host() -> None:
    template = Forge(kind="", tree="{url}/b/{path}", blob="{url}/b/{path}", raw="")
    assert repo_icon_of("https://git.acme.example/o/r", {"git.acme.example": template}) == "git"
    assert repo_icon_of("https://gitea.acme.example/o/r", {"gitea.acme.example": template}) == (
        "gitea"
    )


def test_the_vocabulary_is_the_six_icons_the_ruling_names_and_azure_devops() -> None:
    # Azure DevOps joined in BDL-080 S4e (`beadloom-af99.9`), by the owner's look.
    assert sorted(REPO_ICONS) == [
        "azuredevops",
        "bitbucket",
        "codeberg",
        "git",
        "gitea",
        "github",
        "gitlab",
    ]
