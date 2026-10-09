# beadloom:domain=application
# beadloom:feature=site-generation
"""The icon beside the portal's repository link in the header.

BDL-080 S4d (``beadloom-af99.7``), the owner's ruling of 2026-10-09. The link is
the adopter's own (``site.repo_url``), so its icon is the adopter's forge, read
from the host: ``github.com`` draws GitHub's mark, a ``gitlab.*`` host GitLab's,
``bitbucket.org`` Bitbucket's, ``codeberg.org`` Codeberg's, a ``gitea.*`` host
Gitea's, and any other host git's own. A self-hosted instance whose host says
nothing names its icon with ``site.repo_icon``, which takes one value of
:data:`REPO_ICONS` and wins over the host.

A host the project declares a forge kind for under ``site.forges`` draws that
kind's icon, as it did before this bead, and so do the Azure DevOps hosts, which
the ruling's list does not name and whose mark the portal drew since BDL-076.

The values are simple-icons names, the set VitePress draws a social link from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from beadloom.application.site.forge_routes import VSTS_SUFFIX

if TYPE_CHECKING:
    from collections.abc import Mapping

    from beadloom.application.site.forge_routes import Forge

#: Git's own mark, for a host nothing else names.
GENERIC_ICON = "git"

#: Every icon ``site.repo_icon`` may name.
REPO_ICONS = ("github", "gitlab", "bitbucket", "codeberg", "gitea", GENERIC_ICON)

#: The icon Azure DevOps' hosts draw; derived only, never declared.
_AZURE_ICON = "azuredevops"

#: The icon each forge kind of ``site.forges`` draws.
_KIND_ICONS = {
    "github": "github",
    "gitlab": "gitlab",
    "bitbucket": "bitbucket",
    "gitea": "gitea",
    "azure": _AZURE_ICON,
}

#: A public forge's own host, and its icon.
_HOST_ICONS = {
    "github.com": "github",
    "gitlab.com": "gitlab",
    "bitbucket.org": "bitbucket",
    "codeberg.org": "codeberg",
    "gitea.com": "gitea",
    "dev.azure.com": _AZURE_ICON,
}

#: The first label of a self-hosted instance's host that names its forge.
_FIRST_LABEL_ICONS = {"gitlab": "gitlab", "gitea": "gitea"}


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def repo_icon_of(
    repo_url: str, forges: Mapping[str, Forge] | None = None, declared: str = ""
) -> str:
    """The icon the portal draws beside its repository link; ``""`` when there is no link.

    *declared* is ``site.repo_icon`` and wins over the host. *forges* are the
    hosts the project declares a forge for, keyed lower-case; a host declared by
    template is read by its name, like any other host.
    """
    if not repo_url:
        return ""
    if declared:
        return declared
    host = _host(repo_url)
    forge = (forges or {}).get(host)
    if forge is not None and forge.kind in _KIND_ICONS:
        return _KIND_ICONS[forge.kind]
    if host in _HOST_ICONS:
        return _HOST_ICONS[host]
    if host.endswith(VSTS_SUFFIX):
        return _AZURE_ICON
    return _FIRST_LABEL_ICONS.get(host.split(".", 1)[0], GENERIC_ICON)
