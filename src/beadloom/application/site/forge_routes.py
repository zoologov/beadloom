# beadloom:domain=application
# beadloom:feature=site-generation
"""The routes a forge serves a repository path under, and which forge serves a host.

A forge shows a path at a revision under its own route, and serves the file
itself under another one; an image in a project's text needs the second,
because the first is an HTML page. Three routes, over the repository's web
address ``{url}``, the revision ``{ref}`` and the path ``{path}``:

``tree``
    the page for a path, a directory or a file (the node card's source link);
``blob``
    the page for a file (a link in the project's own text);
``raw``
    the file itself (an image in that text); empty when the forge serves none
    the generator can name.

Each known kind carries its routes below. None was opened against a live forge
when they were written (no network was used): they are the URL forms the forges
publish for GitHub, GitLab, Gitea and Bitbucket Cloud. The least certain is the
Azure DevOps ``raw`` route, a call to its Items REST API, followed by what a
forge does with a directory under ``blob`` (GitHub and GitLab redirect to
``tree``). ``bitbucket`` is Bitbucket Cloud; Bitbucket Data Center serves other
routes and is described by a template.

A forge is recognised from the host of the web address. A public forge's own
host is recognised by this module; any other host is recognised only when the
project declares the forge that serves it (``site.forges``, BDL-076
``beadloom-ujzb.8``), by kind or by a URL template, because a guessed route is a
404 that looks like a link.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from urllib.parse import quote, urlsplit

from beadloom.doc_sync.declarations import describe_value

if TYPE_CHECKING:
    from collections.abc import Mapping

#: The three routes a forge serves a path under.
Route = Literal["tree", "blob", "raw"]


@dataclass(frozen=True)
class Forge:
    """How one forge serves a repository's paths: three URL templates.

    ``kind`` is the name of a known forge, ``""`` for one a project described by
    a template. A route is ``""`` when the forge serves nothing under it.
    """

    kind: str
    tree: str
    blob: str
    raw: str

    def link(self, route: Route, url: str, ref: str, path: str) -> str:
        """The address of *path* at *ref* under *route* (``tree``/``blob``/``raw``), or ``""``.

        The revision and the path are URL-encoded here; ``url`` is taken as the
        web address it already is.
        """
        template = {"tree": self.tree, "blob": self.blob, "raw": self.raw}[route]
        if not template:
            return ""
        values = {"url": url, "ref": quote(ref, safe=""), "path": quote(path, safe="/")}
        if _ITEMS in template:
            items = _azure_items(url)
            if not items:
                return ""
            values[_ITEMS_FIELD] = items
        return template.format(**values)


_GITHUB = "github"
_GITLAB = "gitlab"
_BITBUCKET = "bitbucket"
_GITEA = "gitea"
_AZURE = "azure"

#: Azure DevOps serves a file's content through its REST API, under the
#: project, not the repository's web page. The generator derives that address
#: from the web address; a project's own template cannot name it.
_ITEMS_FIELD = "items"
_ITEMS = "{" + _ITEMS_FIELD + "}"
_AZURE_WEB_SEGMENT = "/_git/"
_AZURE_ITEMS_ROUTE = "/_apis/git/repositories/{repo}/items"
#: The Items API version the route names; a GET without one is refused.
_AZURE_API_VERSION = "7.1"

#: Every known forge, by kind.
KNOWN_FORGES: Mapping[str, Forge] = {
    _GITHUB: Forge(
        kind=_GITHUB,
        tree="{url}/tree/{ref}/{path}",
        blob="{url}/blob/{ref}/{path}",
        raw="{url}/raw/{ref}/{path}",
    ),
    _GITLAB: Forge(
        kind=_GITLAB,
        tree="{url}/-/tree/{ref}/{path}",
        blob="{url}/-/blob/{ref}/{path}",
        raw="{url}/-/raw/{ref}/{path}",
    ),
    _GITEA: Forge(
        kind=_GITEA,
        tree="{url}/src/commit/{ref}/{path}",
        blob="{url}/src/commit/{ref}/{path}",
        raw="{url}/raw/commit/{ref}/{path}",
    ),
    _BITBUCKET: Forge(
        kind=_BITBUCKET,
        tree="{url}/src/{ref}/{path}",
        blob="{url}/src/{ref}/{path}",
        raw="{url}/raw/{ref}/{path}",
    ),
    _AZURE: Forge(
        kind=_AZURE,
        tree="{url}?path=/{path}&version=GC{ref}",
        blob="{url}?path=/{path}&version=GC{ref}",
        raw=(
            _ITEMS + "?path=/{path}&versionDescriptor.version={ref}"
            "&versionDescriptor.versionType=commit&%24format=octetStream&download=false"
            f"&api-version={_AZURE_API_VERSION}"
        ),
    ),
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

#: Azure DevOps' older hosts, ``<organisation>.visualstudio.com``, and the one
#: among them that serves SSH and no web page.
VSTS_SUFFIX = ".visualstudio.com"
VSTS_SSH_HOST = "vs-ssh.visualstudio.com"


def forge_for(web_url: str, declared: Mapping[str, Forge] | None = None) -> Forge | None:
    """The forge that serves *web_url*, by its host; ``None`` when none is known.

    A host the project declares (keys lower-case) is looked up first, so a
    declaration is never overruled by this module's table.
    """
    try:
        host = (urlsplit(web_url).hostname or "").lower()
    except ValueError:
        return None
    if not host:
        return None
    if declared and host in declared:
        return declared[host]
    if host.endswith(VSTS_SUFFIX) and host != VSTS_SSH_HOST:
        return KNOWN_FORGES[_AZURE]
    kind = _PUBLIC_HOSTS.get(host)
    return None if kind is None else KNOWN_FORGES[kind]


def _azure_items(url: str) -> str:
    """The Items API address of the Azure DevOps repository at *url*, or ``""``."""
    head, found, repo = url.rpartition(_AZURE_WEB_SEGMENT)
    if not found or not repo or "/" in repo:
        return ""
    return head + _AZURE_ITEMS_ROUTE.format(repo=repo)


# -- a project's own declaration ------------------------------------------------

#: The routes a project's template gives: the page for a path, and the file.
_SOURCE = "source"
_RAW = "raw"
_TEMPLATE_KEYS = (_SOURCE, _RAW)
#: The placeholders a template may use.
PLACEHOLDERS = ("url", "ref", "path")
_REQUIRED_PLACEHOLDER = "path"
_WEB_SCHEMES = frozenset({"http", "https"})

#: Values the placeholders are replaced with to check what a template yields.
_SAMPLE = {"url": "https://forge.example/team/repo", "ref": "0" * 40, "path": "a/b"}


def read_forge(setting: object) -> tuple[Forge | None, tuple[str, ...]]:
    """The forge a ``site.forges`` value names, or what makes it name none.

    A string is a kind; a mapping is a template: ``source:`` (required), the
    page for a path, and ``raw:``, the file itself. Every problem is returned,
    not only the first, so an author repairs the entry in one pass.
    """
    if isinstance(setting, str):
        forge = KNOWN_FORGES.get(setting)
        return (forge, ()) if forge else (None, (_unknown_kind(setting),))
    if not isinstance(setting, dict):
        return None, (f"is {describe_value(setting)}, not a forge kind or a mapping of templates",)
    problems = [
        f"has `{key}:`, which is not a template key; the keys are `source:` and `raw:`"
        for key in setting
        if key not in _TEMPLATE_KEYS
    ]
    if _SOURCE not in setting:
        problems.append("has no `source:` template")
    templates: dict[str, str] = {}
    for key in _TEMPLATE_KEYS:
        if key not in setting:
            continue
        value = setting[key]
        problem = template_problem(value)
        if problem is not None:
            problems.append(f"`{key}:` {problem}")
        elif isinstance(value, str):
            templates[key] = value
    if problems:
        return None, tuple(problems)
    source = templates[_SOURCE]
    return Forge(kind="", tree=source, blob=source, raw=templates.get(_RAW, "")), ()


def template_problem(template: object) -> str | None:
    """What makes *template* unusable as a route, or ``None``."""
    if not isinstance(template, str):
        return f"is {describe_value(template)}, not a template"
    try:
        fields = [
            (name, conversion, spec)
            for _, name, spec, conversion in string.Formatter().parse(template)
            if name is not None
        ]
    except ValueError:
        return "has an unmatched brace; write a placeholder as `{path}`"
    names: list[str] = []
    for name, conversion, spec in fields:
        written = (
            "{"
            + name
            + (f"!{conversion}" if conversion else "")
            + (f":{spec}" if spec else "")
            + "}"
        )
        if name not in PLACEHOLDERS:
            return f"names `{written}`; the placeholders are {_placeholders()}"
        if conversion or spec:
            return f"writes `{written}`; a placeholder is written bare, as `{{{name}}}`"
        names.append(name)
    if _REQUIRED_PLACEHOLDER not in names:
        return "has no `{path}`, so every path would get one address"
    return _yield_problem(template)


def _yield_problem(template: str) -> str | None:
    """What is wrong with the address *template* yields, or ``None``."""
    try:
        parts = urlsplit(template.format(**_SAMPLE))
        host = parts.hostname
    except ValueError:
        return "does not yield a web address"
    if parts.scheme not in _WEB_SCHEMES or not host:
        return "does not yield an http(s) address; start it with `{url}` or `https://`"
    if parts.username is not None or parts.password is not None:
        return "carries a credential, which the portal would publish"
    return None


def _unknown_kind(name: str) -> str:
    kinds = ", ".join(f"`{kind}`" for kind in sorted(KNOWN_FORGES))
    return (
        f"names `{name}`, which is not a forge kind; the kinds are {kinds}, "
        "or a mapping with a `source:` template"
    )


def _placeholders() -> str:
    return ", ".join(f"`{{{name}}}`" for name in PLACEHOLDERS)
