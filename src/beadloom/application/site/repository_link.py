# beadloom:domain=application
# beadloom:feature=site-generation
"""Where a node's source can be read on the web: the repository the site links to.

The node card links a node's ``source`` to its repository (BDL-076 A3). The
address comes from the project's own ``origin`` remote, never from a constant,
because the same generator writes an adopter's portal; and the revision is the
commit the site was generated from, so a link shows the source the page
describes rather than whatever the branch holds later.

A remote git can reach but a browser cannot (a path on disk, ``file://``) gives
no address, and the card then shows the source without a link. A credential
written into an HTTPS remote is dropped: the data file is published.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from beadloom.graph.federation import current_commit_sha

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_WEB_SCHEMES = frozenset({"http", "https"})
_SSH_SCHEME = "ssh"
_GIT_SUFFIX = ".git"


@dataclass(frozen=True)
class RepositoryLink:
    """The repository's web address and the revision the site was generated from.

    Both are empty when nothing states them: a project outside git, or one whose
    ``origin`` has no web address.
    """

    url: str = ""
    ref: str = ""

    def as_dict(self) -> dict[str, str]:
        """The data file's ``repository`` block."""
        return {"url": self.url, "ref": self.ref}


def _strip_suffix(path: str) -> str:
    path = path.strip("/")
    return path[: -len(_GIT_SUFFIX)] if path.endswith(_GIT_SUFFIX) else path


def _scp_like(remote: str) -> tuple[str, str] | None:
    """``user@host:path`` (git's scp-like syntax) as ``(host, path)``, or None."""
    if "://" in remote or ":" not in remote:
        return None
    host_part, path = remote.split(":", 1)
    host = host_part.rsplit("@", 1)[-1]
    # A one-letter "host" is a Windows drive (``C:\\repo``), which git reads as a path.
    if len(host) < 2 or "/" in host or not path:
        return None
    return host, path


def web_url_of_remote(remote: str) -> str:
    """The web address of a git remote, or ``""`` when a browser cannot open it.

    HTTP(S) keeps its scheme; SSH, in either spelling, becomes HTTPS on the same
    host without the port. User names and credentials are dropped, and so is a
    trailing ``.git``.
    """
    remote = remote.strip()
    if not remote:
        return ""
    scp = _scp_like(remote)
    if scp is not None:
        host, path = scp
        return f"https://{host}/{_strip_suffix(path)}"
    parts = urlsplit(remote)
    host = parts.hostname or ""
    path = _strip_suffix(parts.path)
    if not host or not path:
        return ""
    if parts.scheme in _WEB_SCHEMES:
        port = f":{parts.port}" if parts.port else ""
        return f"{parts.scheme}://{host}{port}/{path}"
    if parts.scheme == _SSH_SCHEME:
        return f"https://{host}/{path}"
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
