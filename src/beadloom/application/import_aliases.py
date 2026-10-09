# beadloom:domain=application
# beadloom:feature=reindex
"""The ``imports:`` block of ``.beadloom/config.yml``: the aliases a project's imports go through.

BDL-080 S3a (``beadloom-cwzc``), RFC D5 (b). A JavaScript or TypeScript project names its
own modules through aliases its tooling applies: tsconfig ``paths``, which the resolver
reads itself, and Babel ``module-resolver`` or Vite ``resolve.alias``, which live in a
program (``babel.config.js``, ``vite.config.ts``) the resolver does not run. The second
kind is declared here, and ``beadloom init`` writes what a text scan of those files found::

    imports:
      aliases:
        "@shared": src/shared   # @shared/api -> src/shared/api
        "~": src                # ~/features/auth -> src/features/auth

An alias is a string the specifier is, or starts with followed by ``/``; its value is a
folder or a file relative to the project root (``.`` for the root). A trailing ``/`` on
the alias is dropped, so ``"@/"`` declares ``@``.

A key the block does not read, an ``aliases:`` that is not a mapping, an alias that is a
pattern or a relative path, and a value that is not a path to something in the project
are each refused by name, in the shape :mod:`beadloom.doc_sync.declarations` gives every
declaration of this file; a refused entry is dropped and the usable ones are kept. The
refusals reach ``beadloom config-check`` and the Gate's ``config-check`` step, which block
on them: a mistyped folder would otherwise leave every import under the alias unresolved
without a word, and no project declared this block before it existed.

It belongs to the reindex, which hands the aliases to the import resolver: the graph
domain does not read this file's blocks itself.
"""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING

from beadloom.doc_sync.declarations import (
    Refusal,
    describe_value,
    inside_project,
    mapping_of,
    read_declaration,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The key of ``.beadloom/config.yml`` this module reads.
IMPORTS_KEY = "imports"

#: The keys the block reads.
_ALIASES = "aliases"
_KEYS = (_ALIASES,)

#: What an alias may not hold: a pattern is tsconfig's form, not a string alias.
_WILDCARD = "*"
_ROOT = "."

Alias = tuple[str, str]


def read_import_aliases(project_root: Path) -> tuple[tuple[Alias, ...], tuple[Refusal, ...]]:
    """The ``(alias, folder)`` pairs *project_root* declares, and every entry refused."""
    declaration = read_declaration(project_root, IMPORTS_KEY)
    if declaration.undetermined:
        return (), declaration.refusals
    if not declaration.present:
        return (), ()
    block, refusals = mapping_of(declaration, "the key `aliases:`")
    if block is None:
        return (), refusals
    found = [_unknown_key(str(key)) for key in block if str(key) not in _KEYS]
    aliases: tuple[Alias, ...] = ()
    if block.get(_ALIASES) is not None:
        aliases, refused = _aliases(project_root, block[_ALIASES])
        found.extend(refused)
    return aliases, tuple(found)


def import_aliases(project_root: Path) -> tuple[Alias, ...]:
    """The usable aliases only: what the resolver applies, refusals aside."""
    return read_import_aliases(project_root)[0]


def _aliases(project_root: Path, value: object) -> tuple[tuple[Alias, ...], list[Refusal]]:
    where = f"{IMPORTS_KEY}.{_ALIASES}"
    if not isinstance(value, dict):
        return (), [
            Refusal(
                where=where,
                why=f"`{_ALIASES}:` is {describe_value(value)}, not a mapping of alias to folder",
                remediation=f'write `{_ALIASES}:` as a mapping such as `"@shared": src/shared`',
            )
        ]
    aliases: list[Alias] = []
    refusals: list[Refusal] = []
    for key, folder in value.items():
        alias, refusal = _entry(project_root, key, folder)
        if alias is not None:
            aliases.append(alias)
        if refusal is not None:
            refusals.append(refusal)
    return tuple(aliases), refusals


def _entry(project_root: Path, key: object, value: object) -> tuple[Alias | None, Refusal | None]:
    """One declared alias, or the refusal that names what about it cannot be used."""
    where = f"{IMPORTS_KEY}.{_ALIASES}.{key}"
    alias = str(key).rstrip("/")
    if not alias or _WILDCARD in alias:
        return None, _refused(
            where,
            f"the alias `{key}` is a pattern or empty; an alias is the string a specifier"
            " starts with, and a pattern is tsconfig's `paths` form",
            "write the alias without `*` (`@/*` is `@`), or declare it in tsconfig `paths`",
        )
    if alias.startswith((".", "/")):
        return None, _refused(
            where,
            f"the alias `{key}` is a relative or absolute path, which is never aliased",
            "write the string the imports start with, such as `@shared`",
        )
    folder, why = _folder(project_root, value, where)
    if folder is None:
        return None, _refused(
            where, why, "point it at a folder or file of the project, relative to its root"
        )
    return (alias, folder), None


def _folder(project_root: Path, value: object, where: str) -> tuple[str | None, str]:
    """*value* as a project-relative folder, or why it is not one."""
    if not isinstance(value, str) or not value.strip():
        shown = "an empty string" if isinstance(value, str) else describe_value(value)
        return None, f"the folder is {shown}, not a path"
    declared = value.strip()
    if _WILDCARD in declared:
        return None, f"the folder `{declared}` is a pattern, not a path"
    if declared.startswith("/"):
        return None, f"`{declared}` resolves outside the project root"
    resolved, refusal = inside_project(project_root, declared, where=where, field=where)
    if resolved is None:
        return None, refusal.why if refusal is not None else ""
    if not resolved.exists():
        return None, f"`{declared}` names nothing in the project"
    normal = posixpath.normpath(declared)
    return ("" if normal == _ROOT else normal), ""


def _refused(where: str, why: str, remediation: str) -> Refusal:
    return Refusal(where=where, why=why, remediation=remediation)


def _unknown_key(key: str) -> Refusal:
    known = ", ".join(f"`{name}:`" for name in _KEYS)
    return Refusal(
        where=f"{IMPORTS_KEY}.{key}",
        why=f"`{key}:` is not a key of `{IMPORTS_KEY}:`; the block reads {known}",
        remediation=f"rename or remove `{key}:`",
    )
