"""Which project files a JS/TS module specifier may name, in the order they are tried.

A relative specifier is read from the importing file's folder; an aliased one from the
folder an alias names (``tsconfig`` ``paths``, or ``imports.aliases:`` in
``.beadloom/config.yml``). Either way the path is completed the same way, which is this
module's one rule: the path as written, the TypeScript source of an emitted ``.js``, each
extension, then each extension on ``<path>/index``. Whether a candidate exists, and which
node owns it, is :mod:`beadloom.graph.import_resolver`'s question.

**Platform suffixes** (BDL-080 ``beadloom-cwzc``). React Native's bundler completes
``./Button`` to ``Button.ios.tsx`` on iOS, ``Button.android.tsx`` on Android and
``Button.web.tsx`` on the web, with ``.native`` for both phones. A module that exists only
in those forms was named by no candidate and every import of it was unresolved. The
suffixes are tried before the plain extension, as the bundler does; this index is not built
for one platform, so all four are tried, iOS first. The files of one module sit in one
folder, so the node an import resolves to does not depend on which of them answers.

Not handled, each named so its absence reads as a decision: a folder's ``package.json``
``main``/``exports``, ``.mts``/``.cts`` and ``.d.ts`` targets, query suffixes
(``./x.vue?raw``), CommonJS ``require()``, Babel ``module-resolver``'s ``root:`` folders and
regular-expression aliases.
"""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

#: The extensions a JS/TS specifier is completed with, in order (BDL-076 J1). A file
#: therefore beats a folder of the same name, as it does for Node and for the bundlers.
#: ``.vue`` need not be parseable here: the target only has to exist for its owning node
#: to be named.
MODULE_EXTENSIONS: tuple[str, ...] = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue")

#: React Native's platform suffixes, tried before the plain extension.
PLATFORM_SUFFIXES: tuple[str, ...] = (".ios", ".android", ".native", ".web")

#: TypeScript's ESM convention: a specifier carries the extension the file will have
#: AFTER compilation, so ``./a.js`` in a source tree names ``a.ts``. Tried right after the
#: path as written.
_TS_SOURCES_OF_EMITTED: dict[str, tuple[str, ...]] = {
    ".js": (".ts", ".tsx"),
    ".jsx": (".tsx",),
}

_INDEX = "index"


def is_relative_specifier(specifier: str) -> bool:
    """Whether a JS/TS module specifier is relative to the importing file."""
    return specifier in (".", "..") or specifier.startswith(("./", "../"))


def _completed(path: str) -> list[str]:
    """*path* with each extension, each preceded by every platform suffix."""
    return [
        f"{path}{platform}{ext}"
        for ext in MODULE_EXTENSIONS
        for platform in (*PLATFORM_SUFFIXES, "")
    ]


def module_file_candidates(target: str) -> list[str]:
    """The project-relative files a specifier mapped to *target* may name, in order."""
    stem, suffix = posixpath.splitext(target)
    return [
        target,
        *(stem + ext for ext in _TS_SOURCES_OF_EMITTED.get(suffix, ())),
        *_completed(target),
        *_completed(posixpath.join(target, _INDEX)),
    ]


def relative_import_candidates(specifier: str, importer: str) -> list[str]:
    """The project-relative files a relative *specifier* may name, in resolution order.

    *importer* is the importing file's project-relative POSIX path. A specifier that
    climbs above the project root names nothing and yields ``[]``.
    """
    target = posixpath.normpath(posixpath.join(posixpath.dirname(importer), specifier))
    if target == ".." or target.startswith("../"):
        return []
    return module_file_candidates(target)


def aliased_targets(specifier: str, aliases: Sequence[tuple[str, str]]) -> tuple[str, ...]:
    """The project-relative path *specifier* names through the one alias it is written under.

    An alias matches the specifier that IS the alias or starts with it and a ``/``, as
    Babel's ``module-resolver`` and Vite's ``resolve.alias`` read a string key: ``@shared``
    matches ``@shared/api`` and not ``@sharedx``. The longest alias that matches wins, so
    the order the project declared them in decides nothing. *aliases* are ``(alias,
    folder)`` pairs, the folder relative to the project root (``""`` for the root).
    """
    for alias, folder in sorted(aliases, key=lambda pair: -len(pair[0])):
        if specifier == alias:
            return (folder,)
        if specifier.startswith(f"{alias}/"):
            target = posixpath.normpath(posixpath.join(folder, specifier[len(alias) + 1 :]))
            return () if target == ".." or target.startswith("../") else (target,)
    return ()
