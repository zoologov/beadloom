# beadloom:domain=application
# beadloom:feature=site-generation
"""The portal's identity: the ``site:`` block of ``.beadloom/config.yml``.

BDL-076 B1 (``beadloom-dfwt``). ``beadloom docs site`` writes an adopter's
portal, so nothing about the portal's identity can be a constant of this
package: its title, its description, the base path it is served under and the
repository it links to are the project's, declared as::

    site:
      title: Acme Orders
      description: Orders, payments and stock
      base: /orders/
      repo_url: https://git.acme.example/sales/orders
      repo_icon: gitlab
      forges:
        git.acme.example: gitlab
      logo: docs/assets/orders-logo.svg
      powered_by: true

Every key is optional. The title defaults to the project directory's name and
the base to ``/``. The repository link has no default, by the owner's ruling
(BDL-076 CONTEXT, 2026-09-30): a project's name comes from its configuration and
never from its git remote, and nothing from the remote is published except each
node's ``source_url``. A project that declares no ``repo_url`` gets no link.

The nav and the footer (BDL-080 S4d, ``beadloom-af99.7``, the owner's rulings of
2026-10-09): ``logo`` is the project's own logo, an SVG or a PNG named relative to
the project root and copied into the portal
(:mod:`beadloom.application.site.site_logo`); without it the nav shows no logo.
``powered_by`` switches the footer that says "Powered by Beadloom", on unless it
is ``false``. ``repo_icon`` names the icon beside the repository link where the
host of ``repo_url`` says nothing
(:mod:`beadloom.application.site.repository_icon`).

``forges`` maps a host to the forge that serves it (``beadloom-ujzb.8``): a kind
— ``github``, ``gitlab``, ``gitea``, ``bitbucket``, ``azure`` — whose routes are
reused, or a mapping of URL templates over ``{url}``, ``{ref}`` and ``{path}``,
``source:`` for the page of a path and ``raw:`` for the file itself, for a forge
no kind describes. It is keyed by host because the forge is a property of the
server: one entry covers every repository on it and every form of remote,
HTTPS or SSH, with or without a port. Without it, a host is recognised only when
it is a public forge's own, as before. The routes and the reading of one value
are :mod:`beadloom.application.site.forge_routes`.

A value the portal cannot use is refused where it was written — ``site.base`` —
and a key the block does not read is refused by name, with the keys it does
read. The refusals are the shape :mod:`beadloom.doc_sync.declarations` gives
every declaration of this file, and they reach three readers: ``docs site``,
which stops before it writes anything; ``beadloom config-check``; and the Gate's
``config-check`` step. The keys are one table, :data:`_FIELDS`, so a key added
later is one row and its reader, beside these; ``forges`` is such a row.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from beadloom.application.site.favicon import favicons_of
from beadloom.application.site.forge_routes import (
    KNOWN_FORGES,
    PLACEHOLDERS,
    Forge,
    forge_for,
    read_forge,
    runs_past_repository,
    stops_before_repository,
)
from beadloom.application.site.repository_icon import REPO_ICONS, repo_icon_of
from beadloom.application.site.site_logo import (
    is_monochrome,
    logo_problem,
    logo_site_path,
    read_logo,
)
from beadloom.doc_sync.declarations import (
    Refusal,
    describe_value,
    mapping_of,
    read_declaration,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

#: The key of ``.beadloom/config.yml`` this module reads.
SITE_KEY = "site"

_WEB_SCHEMES = frozenset({"http", "https"})

#: A host name as ``site.forges`` is keyed by: labels of letters, digits and
#: hyphens, no scheme, port, user or path.
_HOST_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_HOST_RE = re.compile(rf"^{_HOST_LABEL}(?:\.{_HOST_LABEL})*$")


class SiteConfigError(ValueError):
    """The ``site:`` block holds something the portal cannot use.

    Raised by :func:`site_config_of`, before ``docs site`` writes a file: a
    portal generated with a default in place of a mistyped value deploys under
    the wrong path and says nothing.
    """

    def __init__(self, refusals: tuple[Refusal, ...]) -> None:
        detail = "; ".join(f"{refusal.where}: {refusal.why}" for refusal in refusals)
        super().__init__(f"the `site:` block of .beadloom/config.yml cannot be used: {detail}")
        self.refusals = refusals


@dataclass(frozen=True)
class SiteConfig:
    """The portal's identity, with every default applied.

    ``repo_url`` is ``""`` when the project declares none; ``forges`` maps each
    host the project declares a forge for, lower-case, to that forge. ``logo``
    is the project's logo relative to its root, ``""`` without one;
    ``powered_by`` switches the footer; ``repo_icon`` is the declared icon,
    ``""`` when the host decides it.
    """

    title: str
    description: str
    base: str
    repo_url: str
    forges: Mapping[str, Forge] = field(default_factory=dict, hash=False)
    logo: str = ""
    powered_by: bool = True
    repo_icon: str = ""


def _text(value: object, where: str) -> Refusal | None:
    """A non-empty string, or the refusal that says what was written instead."""
    if isinstance(value, str) and value.strip():
        return None
    shown = "an empty string" if isinstance(value, str) else describe_value(value)
    return Refusal(
        where=where,
        why=f"`{where}` is {shown}",
        remediation=f"write `{where.rsplit('.', 1)[-1]}:` as a non-empty string",
    )


#: What GitHub Actions evaluates wherever it stands in a workflow, quoted or not.
_ACTIONS_EXPRESSION = "${{"


def _base(value: object, where: str) -> Refusal | None:
    """A base path VitePress accepts, starting and ending with ``/``, that a workflow can carry.

    The Pages workflow (:mod:`beadloom.application.site.pages_workflow`) writes
    the base into a workflow file, where ``${{`` opens an expression however the
    value is quoted, so such a base is refused here, where it was written.
    """
    remediation = "write `base:` as the path the portal is served under, e.g. `/orders/`"
    if not (isinstance(value, str) and value.startswith("/") and value.endswith("/")):
        shown = f"`{value}`" if isinstance(value, str) else describe_value(value)
        return Refusal(
            where=where,
            why=f"`{where}` is {shown}, and a base path starts and ends with `/`",
            remediation=remediation,
        )
    if _ACTIONS_EXPRESSION in value:
        return Refusal(
            where=where,
            why=(
                f"`{where}` holds `{_ACTIONS_EXPRESSION}`, which GitHub Actions evaluates as "
                "an expression in any workflow that carries the base"
            ),
            remediation=remediation,
        )
    return None


_REPO_URL_REMEDIATION = (
    "write `repo_url:` as the repository's own address, e.g. "
    "`https://gitlab.com/acme/orders`, with no credential, query or fragment"
)
_GIT_SUFFIX = ".git"


def _repo_url(value: object, where: str) -> tuple[object, tuple[Refusal, ...]]:
    """A web address a reader can open, in one spelling, holding nothing unpublishable.

    The spelling is :func:`canonical_repo_url`'s, so a link the generator builds
    from it is the forge's route whichever way the address was copied.
    """
    why = _repo_url_problem(value)
    if why is None and isinstance(value, str):
        return canonical_repo_url(value), ()
    # The value itself is never repeated: it may hold a credential.
    return None, (
        Refusal(where=where, why=f"`{where}` {why}", remediation=_REPO_URL_REMEDIATION),
    )


def canonical_repo_url(url: str) -> str:
    """*url* without what does not change the repository it names.

    The scheme and the host are lower-cased (RFC 3986 makes them
    case-insensitive) and the port is kept; trailing ``/`` and one ``.git`` are
    removed: an address bar adds the first, a forge's clone address carries the
    second, and the forge's routes are appended after neither. The path keeps
    its case, because a forge may serve two repositories that differ by it.
    """
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    if path.endswith(_GIT_SUFFIX):
        path = path[: -len(_GIT_SUFFIX)].rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def _past_repository(repo_url: str, forges: Mapping[str, Forge], where: str) -> Refusal | None:
    """A refusal when *repo_url* is not a repository's own address on its forge.

    Only on a host whose forge is known: a page inside the repository, by the
    routes and the address shape that forge has, or an address that stops
    before a repository (``beadloom-ujzb.23``, n2). On any other host nothing
    says which segment of the path is a route.
    """
    forge = forge_for(repo_url, forges)
    if forge is None:
        return None
    shape = stops_before_repository(repo_url, forge)
    if shape is not None:
        why = (
            f"`{where}` stops before a repository: its forge writes a repository's "
            f"address as `{shape}`, and every link the portal builds would miss it"
        )
    elif runs_past_repository(repo_url, forge):
        why = (
            f"`{where}` runs past the repository into a page of it, a route its forge "
            "serves, and every link the portal builds would be appended to that page"
        )
    else:
        return None
    return Refusal(where=where, why=why, remediation=_REPO_URL_REMEDIATION)


def _repo_url_problem(value: object) -> str | None:
    """What makes *value* unusable as the portal's repository link, or ``None``."""
    if not isinstance(value, str):
        return f"is {describe_value(value)}"
    try:
        parts = urlsplit(value)
        host = parts.hostname
    except ValueError:
        return "is not a web address"
    if parts.scheme not in _WEB_SCHEMES or not host:
        return "is not an http(s) address with a host"
    if parts.username is not None or parts.password is not None:
        return "carries a credential, which the portal would publish"
    if parts.query or parts.fragment:
        return "carries a query or a fragment, which the portal would publish"
    return None


def _forges(value: object, where: str) -> tuple[object, tuple[Refusal, ...]]:
    """The forge each host is declared to be, and one refusal per host that names none."""
    if not isinstance(value, dict):
        return None, (
            Refusal(
                where=where,
                why=f"`{where}` is {describe_value(value)}, not a mapping of host to forge",
                remediation="write `forges:` as `<host>: <kind>`, e.g. `git.acme.example: gitlab`",
            ),
        )
    forges: dict[str, Forge] = {}
    refusals: list[Refusal] = []
    for host, setting in value.items():
        forge, problems = read_forge(setting)
        remediations = [_FORGE_REMEDIATION] if problems else []
        if not _is_host(host):
            problems = ("is not keyed by a host name", *problems)
            remediations.insert(0, _HOST_REMEDIATION)
        entry = f"{where}[{host}]"
        if problems:
            refusals.append(
                Refusal(
                    where=entry,
                    why=f"`{entry}` " + "; ".join(problems),
                    remediation="; ".join(remediations),
                )
            )
        elif forge is not None:
            forges[str(host).lower()] = forge
    return forges, tuple(refusals)


_FORGE_REMEDIATION = (
    "name the forge as one of "
    + ", ".join(f"`{kind}`" for kind in sorted(KNOWN_FORGES))
    + ", or write `source:` (and optionally `raw:`) as templates over "
    + ", ".join(f"`{{{name}}}`" for name in PLACEHOLDERS)
)
_HOST_REMEDIATION = (
    "key the entry by the host name alone, e.g. `git.acme.example`, with no scheme, "
    "port or path"
)


def _is_host(host: object) -> bool:
    return isinstance(host, str) and _HOST_RE.match(host) is not None


def _powered_by(value: object, where: str) -> Refusal | None:
    """``true`` or ``false``, or the refusal that says what was written instead."""
    if isinstance(value, bool):
        return None
    return Refusal(
        where=where,
        why=f"`{where}` is {describe_value(value)}, not `true` or `false`",
        remediation="write `powered_by: false` to remove the footer, or leave the key out",
    )


def _repo_icon(value: object, where: str) -> Refusal | None:
    """One icon of :data:`REPO_ICONS`, or the refusal that lists them."""
    if isinstance(value, str) and value in REPO_ICONS:
        return None
    shown = f"`{value}`" if isinstance(value, str) else describe_value(value)
    icons = ", ".join(f"`{icon}`" for icon in sorted(REPO_ICONS))
    return Refusal(
        where=where,
        why=f"`{where}` is {shown}, which is not an icon the portal draws; the icons are {icons}",
        remediation=f"write `repo_icon:` as one of {icons}, or leave it out to read the host",
    )


def _checked(
    check: Callable[[object, str], Refusal | None],
) -> Callable[[object, str], tuple[object, tuple[Refusal, ...]]]:
    """A reader that keeps the value when *check* refuses nothing."""

    def read(value: object, where: str) -> tuple[object, tuple[Refusal, ...]]:
        refusal = check(value, where)
        return (None, (refusal,)) if refusal is not None else (value, ())

    return read


#: Every key the block reads, with the reader that returns the usable value (or
#: ``None``) and every refusal.
_FIELDS: dict[str, Callable[[object, str], tuple[object, tuple[Refusal, ...]]]] = {
    "title": _checked(_text),
    "description": _checked(_text),
    "base": _checked(_base),
    "repo_url": _repo_url,
    "forges": _forges,
    "logo": read_logo,
    "powered_by": _checked(_powered_by),
    "repo_icon": _checked(_repo_icon),
}


def _unknown_key(key: str) -> Refusal:
    known = ", ".join(f"`{name}:`" for name in sorted(_FIELDS))
    return Refusal(
        where=f"{SITE_KEY}.{key}",
        why=f"`{key}:` is not a key of `{SITE_KEY}:`; the block reads {known}",
        remediation=f"rename `{key}:` to the key it was meant to be, or remove it",
    )


def _defaults(project_root: Path) -> SiteConfig:
    title = project_root.resolve().name
    return SiteConfig(
        title=title,
        description=f"The architecture of {title}: its graph, its documentation and its health",
        base="/",
        repo_url="",
    )


def read_site_config(project_root: Path) -> tuple[SiteConfig, tuple[Refusal, ...]]:
    """The portal identity *project_root* declares, and every value that could not be used.

    A refused value is replaced by its default in the returned config, so a
    caller that only reports can still describe the rest; :func:`site_config_of`
    is the reader that refuses to go on.
    """
    defaults = _defaults(project_root)
    declaration = read_declaration(project_root, SITE_KEY)
    if declaration.undetermined:
        return defaults, declaration.refusals
    if not declaration.present:
        return defaults, ()
    block, refusals = mapping_of(declaration, "the keys " + ", ".join(sorted(_FIELDS)))
    if block is None:
        return defaults, refusals
    found: list[Refusal] = []
    usable: dict[str, object] = {}
    for key, value in block.items():
        reader = _FIELDS.get(str(key))
        if reader is None:
            found.append(_unknown_key(str(key)))
            continue
        read, refusals = reader(value, f"{SITE_KEY}.{key}")
        found.extend(refusals)
        if read is not None:
            usable[str(key)] = read
    forges = usable.get("forges")
    declared_forges = forges if isinstance(forges, dict) else {}
    repo_url = usable.get("repo_url")
    if isinstance(repo_url, str):
        past = _past_repository(repo_url, declared_forges, f"{SITE_KEY}.repo_url")
        if past is not None:
            found.append(past)
            del usable["repo_url"]
    logo = usable.get("logo")
    if isinstance(logo, str):
        missing = logo_problem(project_root, logo, f"{SITE_KEY}.logo")
        if missing is not None:
            found.append(missing)
            del usable["logo"]
    config = SiteConfig(
        title=_text_of(usable, "title", defaults.title),
        description=_text_of(usable, "description", defaults.description),
        base=_text_of(usable, "base", defaults.base),
        repo_url=_text_of(usable, "repo_url", defaults.repo_url),
        forges=declared_forges,
        logo=_text_of(usable, "logo", defaults.logo),
        powered_by=usable.get("powered_by") is not False,
        repo_icon=_text_of(usable, "repo_icon", defaults.repo_icon),
    )
    return config, tuple(found)


def _text_of(usable: Mapping[str, object], key: str, default: str) -> str:
    value = usable.get(key)
    return value if isinstance(value, str) else default


def site_config_of(project_root: Path) -> SiteConfig:
    """The portal identity *project_root* declares.

    Raises :class:`SiteConfigError` when any value of the block is refused.
    """
    config, refusals = read_site_config(project_root)
    if refusals:
        raise SiteConfigError(refusals)
    return config


def unlinked_repository(project_root: Path) -> str:
    """Why a declared portal's header has no repository link, or ``""``.

    ``""`` too when the project declares no ``site:`` block, or one that is not
    a mapping, which is refused elsewhere. Not a refusal itself: a portal without
    the link is a portal ``docs site`` can write. ``config-check`` prints it so
    the absence is a statement rather than a silence (the owner's ruling of
    2026-10-09).
    """
    declaration = read_declaration(project_root, SITE_KEY)
    block = declaration.value if declaration.present else None
    if not isinstance(block, dict) or "repo_url" in block:
        return ""
    unused = (
        f"; `{SITE_KEY}.repo_icon` is declared and nothing draws it"
        if "repo_icon" in block
        else ""
    )
    return (
        f"`{SITE_KEY}.repo_url` is not declared, so the portal's header has no repository "
        f"link{unused}"
    )


def render_site_module(config: SiteConfig, project_root: Path) -> str:
    """``.vitepress/site.generated.mjs``: the identity the shipped ``config.mjs`` reads.

    *project_root* is where ``config.logo`` is read from: the favicons and the
    logo's colour follow the file (BDL-080 S4e). JSON is a JavaScript
    expression, so the values reach the config quoted by the same encoder
    whatever they hold.
    """
    identity = {
        "title": config.title,
        "description": config.description,
        "base": config.base,
        "repoUrl": config.repo_url,
        "repoIcon": repo_icon_of(config.repo_url, config.forges, config.repo_icon),
        "logo": logo_site_path(config.logo),
        "logoMonochrome": is_monochrome(project_root, config.logo),
        "favicons": favicons_of(project_root, config.logo),
        "poweredBy": config.powered_by,
    }
    return (
        "// GENERATED by `beadloom docs site` from the `site:` block of .beadloom/config.yml.\n"
        "// Imported by .vitepress/config.mjs and by the browser tests; do not edit by hand.\n"
        f"export const site = {json.dumps(identity, ensure_ascii=False)};\n"
    )
