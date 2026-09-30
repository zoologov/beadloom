# beadloom:domain=application
# beadloom:feature=site-generation
"""Where a node's source can be read on the web: the repository the site links to.

The node card links a node's ``source`` to its repository (BDL-076 A3). The
address comes from the project's own ``origin`` remote, never from a constant,
because the same generator writes an adopter's portal; and the revision is the
commit the site was generated from, so a link shows the source the page
describes rather than whatever the branch holds later.

A remote git can reach but a browser cannot (a path on disk, ``file://``) gives
no address, and the card then shows the source without a link; so does a remote
this module cannot parse (an IPv6 host in git's scp-like form, a port that is not
a number), which never stops the site. A credential written into a remote is
dropped. The address itself is not published: the data file carries only each
node's finished link, because no screen reads the address and a remote git
cannot use can still hold a credential in a place no parser expects (BDL-076
re-review finding m3).

The link to one path is decided here, per forge, and written finished into the
data file (BDL-076 R1 finding M1): each forge serves a path at a revision under
its own route, and only the generator knows which forge the remote is. The
forge is recognised from the host, and only a public forge's own host is
recognised. Any other host — a self-hosted forge included — gets no link,
because a guessed route is a 404 that looks like a link, and the card's
plain-text source is true. A self-hosted forge is declared in the project's
configuration instead (the owner's ruling, `beadloom-ujzb.8`, slice 2).
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote, urlsplit

from beadloom.graph.federation import current_commit_sha

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_WEB_SCHEMES = frozenset({"http", "https"})

#: An IPv6 host, written in brackets. No forge is recognised on an address, and
#: the parser loses the brackets, so such a remote gives no web address.
_IPV6_OPEN = "["
_NO_IPV6 = "an IPv6 host is no forge's host"
_SSH_SCHEME = "ssh"
_GIT_SUFFIX = ".git"

#: Azure DevOps serves SSH from these hosts, under ``v3/<org>/<project>/<repo>``,
#: and its web pages from another host and another path. Its legacy SSH remotes
#: (``<collection>/<project>/_ssh/<repo>``) are not mapped: they get no address
#: rather than one on the SSH host that looks right (re-review finding m1).
_AZURE_SSH_HOST = "ssh.dev.azure.com"
_VSTS_SSH_HOST = "vs-ssh.visualstudio.com"
_AZURE_SSH_PREFIX = "v3"
_AZURE_SSH_PARTS = 4  # v3, organisation, project, repository

_GITHUB = "github"
_GITLAB = "gitlab"
_BITBUCKET = "bitbucket"
_GITEA = "gitea"
_AZURE = "azure"

#: Each forge's route to a path at a revision, over the repository's web address.
#: The path and the revision arrive URL-encoded.
_ROUTES = {
    _GITHUB: "{base}/tree/{ref}/{path}",
    _GITLAB: "{base}/-/tree/{ref}/{path}",
    _BITBUCKET: "{base}/src/{ref}/{path}",
    _GITEA: "{base}/src/commit/{ref}/{path}",
    _AZURE: "{base}?path=/{path}&version=GC{ref}",
}

#: The public forges, by the host they serve from.
_PUBLIC_HOSTS = {
    "github.com": _GITHUB,
    "gitlab.com": _GITLAB,
    "bitbucket.org": _BITBUCKET,
    "codeberg.org": _GITEA,
    "gitea.com": _GITEA,
    "dev.azure.com": _AZURE,
}

#: Azure DevOps' older hosts, ``<organisation>.visualstudio.com``.
_VSTS_SUFFIX = ".visualstudio.com"

#: Azure DevOps' other hosts, web and SSH.
_AZURE_HOSTS = frozenset({"dev.azure.com", _AZURE_SSH_HOST})


@dataclass(frozen=True)
class RepositoryLink:
    """The repository's web address and the revision the site was generated from.

    Both are empty when nothing states them: a project outside git, or one whose
    ``origin`` has no web address.
    """

    url: str = ""
    ref: str = ""

    def source_url(self, source: str) -> str:
        """The page the forge serves for *source* at the recorded commit, or ``""``.

        ``""`` when there is no repository, no commit or no path, and when the
        host is not a forge this module recognises.
        """
        path = source.strip("/")
        route = _ROUTES.get(forge_of(self.url) or "")
        if route is None or not self.ref or not path:
            return ""
        return route.format(
            base=self.url, ref=quote(self.ref, safe=""), path=quote(path, safe="/")
        )


def forge_of(web_url: str) -> str | None:
    """Which forge serves *web_url*, by its host; ``None`` when none is recognised."""
    try:
        host = (urlsplit(web_url).hostname or "").lower()
    except ValueError:
        return None
    if host.endswith(_VSTS_SUFFIX) and host != _VSTS_SSH_HOST:
        return _AZURE
    return _PUBLIC_HOSTS.get(host)


def _is_azure_host(host: str) -> bool:
    """Whether Azure DevOps serves *host* (lower-case), on the web or over SSH."""
    return host in _AZURE_HOSTS or host.endswith(_VSTS_SUFFIX)


def _strip_suffix(path: str) -> str:
    path = path.strip("/")
    return path[: -len(_GIT_SUFFIX)] if path.endswith(_GIT_SUFFIX) else path


def _scp_like(remote: str) -> tuple[str, str] | None:
    """``user@host:path`` (git's scp-like syntax) as ``(host, path)``, or None."""
    if "://" in remote or ":" not in remote:
        return None
    host_part, path = remote.split(":", 1)
    if _IPV6_OPEN in host_part:
        raise ValueError(_NO_IPV6)
    host = host_part.rsplit("@", 1)[-1]
    # A one-letter "host" is a Windows drive (``C:\\repo``), which git reads as a path.
    if len(host) < 2 or "/" in host or not path:
        return None
    return host, path


def _ssh_web_url(host: str, path: str) -> str:
    """The web address of an SSH remote on *host* at *path*.

    HTTPS on the same host, except for Azure DevOps, whose SSH host and path
    (``ssh.dev.azure.com:v3/<org>/<project>/<repo>``) are not its web ones.
    Any other SSH remote on an Azure host gives ``""``.
    """
    lowered = host.lower()
    if not _is_azure_host(lowered):
        return f"https://{host}/{path}"
    parts = path.split("/")
    if len(parts) != _AZURE_SSH_PARTS or parts[0] != _AZURE_SSH_PREFIX:
        return ""
    _, org, project, repo = parts
    if lowered == _AZURE_SSH_HOST:
        return f"https://dev.azure.com/{org}/{project}/_git/{repo}"
    if lowered == _VSTS_SSH_HOST:
        return f"https://{org}{_VSTS_SUFFIX}/{project}/_git/{repo}"
    return ""


def web_url_of_remote(remote: str) -> str:
    """The web address of a git remote, or ``""`` when a browser cannot open it.

    HTTP(S) keeps its scheme; SSH, in either spelling, becomes HTTPS on the same
    host without the port, or Azure DevOps' web address for its SSH remotes.
    User names and credentials are dropped, and so is a trailing ``.git``. A
    remote that cannot be parsed gives ``""`` rather than an error, because the
    link is an extra of the site and never a reason to stop it.
    """
    try:
        return _web_url(remote.strip())
    except ValueError as exc:
        # The remote is not logged: it can hold a credential.
        logger.debug("the origin remote is not a readable address (%s)", type(exc).__name__)
        return ""


def _web_url(remote: str) -> str:
    if not remote:
        return ""
    scp = _scp_like(remote)
    if scp is not None:
        host, path = scp
        return _ssh_web_url(host, _strip_suffix(path))
    parts = urlsplit(remote)
    host = parts.hostname or ""
    path = _strip_suffix(parts.path)
    if not host or not path:
        return ""
    if ":" in host:
        raise ValueError(_NO_IPV6)
    if parts.scheme in _WEB_SCHEMES:
        port = f":{parts.port}" if parts.port else ""
        return f"{parts.scheme}://{host}{port}/{path}"
    if parts.scheme == _SSH_SCHEME:
        return _ssh_web_url(host, path)
    return ""


def _origin_remote(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],  # noqa: S607 - the git on PATH, as every git read here
            cwd=project_root,
            capture_output=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )
    except OSError as exc:
        logger.debug("git is not available to read the origin remote: %s", exc)
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def repository_of(project_root: Path) -> RepositoryLink:
    """The repository link of the project at ``project_root``.

    Empty unless ``project_root`` is the top of its own git repository: a
    project nested in another repository must not link to that one, which is
    the guard :func:`~beadloom.graph.federation.current_commit_sha` applies.
    """
    ref = current_commit_sha(project_root)
    if ref is None:
        return RepositoryLink()
    url = web_url_of_remote(_origin_remote(project_root))
    return RepositoryLink(url=url, ref=ref if url else "")
