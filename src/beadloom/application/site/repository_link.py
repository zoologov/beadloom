# beadloom:domain=application
# beadloom:feature=site-generation
"""Where a node's source can be read on the web: the repository the site links to.

The node card links a node's ``source`` to its repository (BDL-076 A3). The
address comes from the project's declaration or its own ``origin`` remote, never
from a constant, because the same generator writes an adopter's portal; and the
revision is the commit the site was generated from, so a link shows the source
the page describes rather than whatever the branch holds later.

A remote git can reach but a browser cannot (a path on disk, ``file://``) gives
no address, and the card then shows the source without a link; so does a remote
this module cannot parse (an IPv6 host in git's scp-like form, a port that is not
a number), which never stops the site. A credential written into a remote is
dropped. The address itself is not published: the data file carries only each
node's finished link, because no screen reads the address and a remote git
cannot use can still hold a credential in a place no parser expects (BDL-076
re-review finding m3).

The link to one path is decided here, per forge, and written finished wherever
it goes (BDL-076 R1 finding M1): the node card's source, and every link from a
project's own text to a file of its repository, an image included. The routes
are :mod:`beadloom.application.site.forge_routes`; the forge is recognised from
the host, a public forge's by this package and any other by the project's
``site.forges`` setting (``beadloom-ujzb.8``). A host neither names gets no
link, because a guessed route is a 404 that looks like a link, and the plain
text it leaves is true.

Which repository (``beadloom-ujzb.8``): the one the project declares in
``site.repo_url`` wins over the ``origin`` remote. The declaration is the
project's own statement, checked by ``config-check`` for a credential, a query
and a fragment; the remote is whatever this clone was made from — a mirror, a
fork, a CI clone with a token — and an SSH remote of a forge served under a path
prefix cannot name the web address at all. The remote is read only when nothing
is declared, and only for the card's links, as before.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from beadloom.application.site.forge_routes import VSTS_SSH_HOST, VSTS_SUFFIX, forge_for
from beadloom.graph.federation import current_commit_sha

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from beadloom.application.site.forge_routes import Forge, Route

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
_AZURE_SSH_PREFIX = "v3"
_AZURE_SSH_PARTS = 4  # v3, organisation, project, repository

#: Azure DevOps' hosts, web and SSH, besides ``<organisation>.visualstudio.com``.
_AZURE_HOSTS = frozenset({"dev.azure.com", _AZURE_SSH_HOST})


@dataclass(frozen=True)
class RepositoryLink:
    """The repository's web address, the revision the site was generated from, and its forges.

    ``url`` and ``ref`` are empty when nothing states them: a project outside
    git, or one whose ``origin`` has no web address and that declares none.
    ``forges`` are the hosts the project declares a forge for (``site.forges``),
    keyed lower-case.
    """

    url: str = ""
    ref: str = ""
    forges: Mapping[str, Forge] = field(default_factory=dict, hash=False)

    def source_url(self, source: str) -> str:
        """The page the forge serves for *source*, a directory or a file, or ``""``.

        ``""`` when there is no repository, no commit or no path, and when no
        forge is known for the host.
        """
        return self._link("tree", source)

    def file_url(self, path: str) -> str:
        """The page the forge serves for the file *path*, or ``""`` (as :meth:`source_url`)."""
        return self._link("blob", path)

    def raw_url(self, path: str) -> str:
        """The file *path* itself, as an image is drawn from, or ``""``.

        Also ``""`` when the forge serves no raw file the generator can name.
        """
        return self._link("raw", path)

    def _link(self, route: Route, source: str) -> str:
        path = source.strip("/")
        forge = forge_for(self.url, self.forges)
        if forge is None or not self.ref or not path:
            return ""
        return forge.link(route, self.url, self.ref, path)


def _is_azure_host(host: str) -> bool:
    """Whether Azure DevOps serves *host* (lower-case), on the web or over SSH."""
    return host in _AZURE_HOSTS or host.endswith(VSTS_SUFFIX)


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
    if lowered == VSTS_SSH_HOST:
        return f"https://{org}{VSTS_SUFFIX}/{project}/_git/{repo}"
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


def origin_remote(project_root: Path) -> str:
    """The ``origin`` remote as git reports it, or ``""`` without git or a remote.

    Never logged or published as it is: it can hold a credential.
    """
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


def repository_of(
    project_root: Path,
    *,
    declared_url: str = "",
    forges: Mapping[str, Forge] | None = None,
) -> RepositoryLink:
    """The repository link of the project at ``project_root``.

    *declared_url* is ``site.repo_url``, and wins over the ``origin`` remote,
    which is read only when nothing is declared. The revision is empty unless
    ``project_root`` is the top of its own git repository: a project nested in
    another repository must not link to that one, which is the guard
    :func:`~beadloom.graph.federation.current_commit_sha` applies. A declared
    repository without a revision keeps its address, so a link to the
    repository itself still goes somewhere true, and links no path.
    """
    declared = dict(forges or {})
    ref = current_commit_sha(project_root)
    if ref is None:
        return RepositoryLink(url=declared_url, forges=declared)
    url = declared_url or web_url_of_remote(origin_remote(project_root))
    return RepositoryLink(url=url, ref=ref if url else "", forges=declared)
