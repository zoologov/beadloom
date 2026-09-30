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
      repo_url: https://gitlab.com/acme/orders

Every key is optional. The title defaults to the project directory's name and
the base to ``/``. The repository link has no default, by the owner's ruling
(BDL-076 CONTEXT, 2026-09-30): a project's name comes from its configuration and
never from its git remote, and nothing from the remote is published except each
node's ``source_url``. A project that declares no ``repo_url`` gets no link.

A value the portal cannot use is refused where it was written — ``site.base`` —
and a key the block does not read is refused by name, with the keys it does
read. The refusals are the shape :mod:`beadloom.doc_sync.declarations` gives
every declaration of this file, and they reach three readers: ``docs site``,
which stops before it writes anything; ``beadloom config-check``; and the Gate's
``config-check`` step. The keys are one table, :data:`_FIELDS`, so a key added
later (a forge per self-hosted host, ``beadloom-ujzb.8``) is one row and its
reader, beside these.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from beadloom.application.site.repository_link import forge_of
from beadloom.doc_sync.declarations import (
    Refusal,
    describe_value,
    mapping_of,
    read_declaration,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: The key of ``.beadloom/config.yml`` this module reads.
SITE_KEY = "site"

_WEB_SCHEMES = frozenset({"http", "https"})

#: The simple-icons name VitePress draws for each forge ``forge_of`` recognises;
#: any other host gets git's own mark.
_FORGE_ICONS = {
    "github": "github",
    "gitlab": "gitlab",
    "bitbucket": "bitbucket",
    "gitea": "gitea",
    "azure": "azuredevops",
}
_GENERIC_ICON = "git"


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

    ``repo_url`` is ``""`` when the project declares none.
    """

    title: str
    description: str
    base: str
    repo_url: str


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


def _base(value: object, where: str) -> Refusal | None:
    """A base path VitePress accepts: it starts and ends with ``/``."""
    if isinstance(value, str) and value.startswith("/") and value.endswith("/"):
        return None
    shown = f"`{value}`" if isinstance(value, str) else describe_value(value)
    return Refusal(
        where=where,
        why=f"`{where}` is {shown}, and a base path starts and ends with `/`",
        remediation="write `base:` as the path the portal is served under, e.g. `/orders/`",
    )


def _repo_url(value: object, where: str) -> Refusal | None:
    """A web address a reader can open, holding nothing that must not be published."""
    remediation = (
        "write `repo_url:` as the repository's web address, e.g. "
        "`https://gitlab.com/acme/orders`, with no credential, query or fragment"
    )
    why = _repo_url_problem(value)
    if why is None:
        return None
    # The value itself is never repeated: it may hold a credential.
    return Refusal(where=where, why=f"`{where}` {why}", remediation=remediation)


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


#: Every key the block reads, with the reader that decides whether a value is usable.
_FIELDS: dict[str, Callable[[object, str], Refusal | None]] = {
    "title": _text,
    "description": _text,
    "base": _base,
    "repo_url": _repo_url,
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
    usable: dict[str, str] = {}
    for key, value in block.items():
        reader = _FIELDS.get(str(key))
        if reader is None:
            found.append(_unknown_key(str(key)))
            continue
        refusal = reader(value, f"{SITE_KEY}.{key}")
        if refusal is not None:
            found.append(refusal)
        elif isinstance(value, str):
            usable[str(key)] = value
    config = SiteConfig(
        title=usable.get("title", defaults.title),
        description=usable.get("description", defaults.description),
        base=usable.get("base", defaults.base),
        repo_url=usable.get("repo_url", defaults.repo_url),
    )
    return config, tuple(found)


def site_config_of(project_root: Path) -> SiteConfig:
    """The portal identity *project_root* declares.

    Raises :class:`SiteConfigError` when any value of the block is refused.
    """
    config, refusals = read_site_config(project_root)
    if refusals:
        raise SiteConfigError(refusals)
    return config


def repo_icon_of(repo_url: str) -> str:
    """The icon the portal draws beside its repository link; ``""`` when there is no link."""
    if not repo_url:
        return ""
    return _FORGE_ICONS.get(forge_of(repo_url) or "", _GENERIC_ICON)


def render_site_module(config: SiteConfig) -> str:
    """``.vitepress/site.generated.mjs``: the identity the shipped ``config.mjs`` reads.

    JSON is a JavaScript expression, so the values reach the config quoted by
    the same encoder whatever they hold.
    """
    identity = {
        "title": config.title,
        "description": config.description,
        "base": config.base,
        "repoUrl": config.repo_url,
        "repoIcon": repo_icon_of(config.repo_url),
    }
    return (
        "// GENERATED by `beadloom docs site` from the `site:` block of .beadloom/config.yml.\n"
        "// Imported by .vitepress/config.mjs and by the browser tests; do not edit by hand.\n"
        f"export const site = {json.dumps(identity, ensure_ascii=False)};\n"
    )
