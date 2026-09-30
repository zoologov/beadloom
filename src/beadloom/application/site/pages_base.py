# beadloom:domain=application
# beadloom:feature=site-generation
"""Whether the portal's base can match the path GitHub Pages serves the project under.

BDL-076 ``beadloom-ujzb.13`` (the owner's ruling after B2). GitHub serves a
project repository's Pages site under ``/<repo>/``, and a user or organisation
repository, named ``<owner>.github.io``, at ``/``. A portal built for the base
``/`` loads none of its assets under ``/<repo>/``. The Pages workflow
``--pages-workflow`` writes fails its build on that, in CI; this module lets
``docs site`` say it on the adopter's machine first.

The ``origin`` remote is read only to warn. Nothing read from it is written:
the warning goes to stderr and names the repository only, never its owner or a
credential the remote may carry. Only ``github.com`` is recognised, because the
``/<repo>/`` rule is GitHub's; another host, a project with no remote, and a
base the project declared get no warning, since nothing says they are wrong. A
project repository served from a custom domain is at ``/`` and is warned about
all the same, which the warning says.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from beadloom.application.site.repository_link import web_url_of_remote

#: The one host whose project Pages path this module knows.
_GITHUB_HOST = "github.com"

#: The suffix of a user or organisation Pages repository, ``<owner>.github.io``.
_USER_SITE_SUFFIX = ".github.io"

#: The base ``site:`` defaults to, and the only one this module second-guesses.
_DEFAULT_BASE = "/"

#: A repository's web path on GitHub: owner, then repository.
_OWNER_AND_REPO = 2


def project_pages_base(remote: str) -> str | None:
    """The path GitHub Pages serves *remote*'s project site under, or ``None``.

    ``None`` for anything that is not a GitHub project repository: another
    host, a user or organisation site, a path on disk, or a remote that cannot
    be read.
    """
    url = web_url_of_remote(remote)
    parts = urlsplit(url)
    if (parts.hostname or "").lower() != _GITHUB_HOST:
        return None
    segments = parts.path.strip("/").split("/")
    if len(segments) != _OWNER_AND_REPO or not all(segments):
        return None
    owner, repo = segments
    if repo.lower() == f"{owner.lower()}{_USER_SITE_SUFFIX}":
        return None
    return f"/{repo}/"


def base_warning(base: str, remote: str) -> str | None:
    """The warning for a portal built for *base* in the repository at *remote*, if any.

    Only the default base is second-guessed: a base the project declared is its
    decision, and the Pages workflow checks it against the real path in CI.
    """
    if base != _DEFAULT_BASE:
        return None
    served = project_pages_base(remote)
    if served is None:
        return None
    return (
        f"Warning: the portal is built for the base {_DEFAULT_BASE}, and GitHub Pages "
        f"serves this project repository under {served}, where the portal loads none "
        f"of its assets. Set `site.base: {served}` in .beadloom/config.yml, unless the "
        "site is served from a custom domain."
    )
