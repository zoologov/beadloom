# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Feature-Sliced Design's ``@x`` notation: where an import lands, and the edge fact it makes.

BDL-082 (RFC D1). feature-sliced.design, *Public API for cross-imports*: "entity A can
declare a separate public API just for entity B" — the file ``entities/A/@x/B.ts``, or a
folder ``entities/A/@x/B/`` entered through its ``index`` — "and only use this notation on
the Entities layer, where eliminating cross-imports is often unreasonable".

Two rules read the notation, and they read it through this one module so that they cannot
read one import two ways:

- ``slice_public_api`` (:mod:`.slices`, S1b) asks :func:`located` which file of a slice an
  import reaches and :func:`cross_import_name` whether that file is an ``@x`` API, and if so
  which slice it is opened to;
- the layer rule (:mod:`.layer_crossings`, S1a) reads the **edge fact** the reindex records
  from the same two answers (:func:`edge_cross_import`, called by
  :func:`beadloom.graph.import_resolver.create_import_edges`). An import is *via* ``@x``
  when it lands on ``<target's folder>/@x/<importer's folder name>`` (a file, or that folder's
  ``index``). On a derived ``depends_on`` edge the reindex writes into ``extra``:

  - ``"via": "@x"`` when every import behind the edge is via ``@x``;
  - ``"partly_via": "@x"`` and ``"not_via": "<file>:<line>"`` when some are and one is not,
    naming the first that is not (by file, then line);
  - nothing when none is.

  The layer rule reads the fact with :func:`read_cross_import_facts` and never reads
  ``code_imports``, so it stays a rule over the graph.

**What is read.** Only an import whose specifier names an ``@x`` path segment is located; any
other import is not via ``@x``. An alias that maps a name with no ``@x`` in it straight onto
an ``@x`` folder is therefore read as an ordinary import, and the layer rule reports the edge
as an ordinary crossing — the conservative side of the two.
"""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.graph.exact_case import first_existing_file
from beadloom.graph.js_specifiers import (
    MODULE_EXTENSIONS,
    PLATFORM_SUFFIXES,
    is_relative_specifier,
    module_file_candidates,
    relative_import_candidates,
)
from beadloom.graph.rules.slice_units import INDEX, inside, stem

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterable
    from pathlib import Path

#: The folder a slice's cross-import APIs live in.
CROSS_IMPORT_FOLDER = "@x"

#: The edge attribute naming the notation every import behind an edge goes through.
VIA_KEY = "via"
#: The edge attribute naming the notation SOME imports behind an edge go through.
PARTLY_VIA_KEY = "partly_via"
#: The edge attribute naming the first import of a mixed edge that does not, ``<file>:<line>``.
NOT_VIA_KEY = "not_via"
#: The value of :data:`VIA_KEY` and :data:`PARTLY_VIA_KEY`.
VIA_CROSS_IMPORT = "@x"

#: The specification's note a finding quotes (``/docs/reference/public-api``).
ENTITIES_ONLY_NOTE = (
    "only use this notation on the Entities layer, where eliminating cross-imports is "
    "often unreasonable"
)


def located(specifier: str, importer: str, folder: str, project_root: Path) -> str | None:
    """The file inside *folder* that *specifier*, imported by *importer*, names; or ``None``.

    A relative specifier is completed from the importing file's folder, as the resolver
    completes it. Any other went through an alias this module does not read, so it is
    matched by its longest trailing path that names a file inside *folder*.
    """
    if is_relative_specifier(specifier):
        found = first_existing_file(relative_import_candidates(specifier, importer), project_root)
        return found if found is not None and inside(found, folder) else None
    segments = [segment for segment in specifier.split("/") if segment]
    for start in range(len(segments) + 1):
        target = posixpath.normpath(posixpath.join(folder, *segments[start:]))
        if not inside(target, folder):
            continue
        found = first_existing_file(module_file_candidates(target), project_root)
        if found is not None:
            return found if inside(found, folder) else None
    return None


def _module_name(file_name: str) -> str:
    """*file_name* without its code extension and a platform suffix, if it has them.

    ``artist.ios.tsx`` names ``artist``; ``artist.test.ts`` names ``artist.test``, which is no
    API opened to the slice ``artist``.
    """
    name, extension = posixpath.splitext(file_name)
    if extension not in MODULE_EXTENSIONS:
        return file_name
    base, platform = posixpath.splitext(name)
    return base if platform in PLATFORM_SUFFIXES else name


def cross_import_name(path: str, folder: str) -> str | None:
    """The slice name ``B`` when *path* is ``<folder>/@x/B.*`` or ``<folder>/@x/B/index.*``.

    ``B.*`` is a code extension, with a platform suffix before it or not.
    """
    if not inside(path, folder):
        return None
    match path[len(folder) + 1 :].split("/"):
        case [head, file_name] if head == CROSS_IMPORT_FOLDER:
            return _module_name(file_name)
        case [head, slice_name, file_name] if head == CROSS_IMPORT_FOLDER and (
            stem(file_name) == INDEX
        ):
            return slice_name
        case _:
            return None


def names_cross_import(specifier: str) -> bool:
    """Whether *specifier* has an ``@x`` path segment, the only imports located for the fact."""
    return CROSS_IMPORT_FOLDER in specifier.split("/")


@dataclass(frozen=True)
class CrossImportFact:
    """What a derived edge records about its imports going through ``@x``.

    *every* is ``True`` when each import behind the edge does; otherwise some do and
    *not_via* is ``<file>:<line>`` of the first that does not.
    """

    every: bool
    not_via: str | None

    def as_extra(self) -> dict[str, str]:
        """The keys this fact adds to the edge's ``extra``."""
        if self.every:
            return {VIA_KEY: VIA_CROSS_IMPORT}
        return {PARTLY_VIA_KEY: VIA_CROSS_IMPORT, NOT_VIA_KEY: self.not_via or ""}

    def not_via_location(self) -> tuple[str, int] | None:
        """``(file, line)`` of :attr:`not_via`, or ``None`` when there is none to name."""
        if self.not_via is None:
            return None
        path, _, line = self.not_via.rpartition(":")
        return (path, int(line)) if path and line.isdigit() else None


def edge_cross_import(
    imports: Iterable[tuple[str, int, str]],
    importer_folder: str,
    target_folder: str,
    project_root: Path,
) -> CrossImportFact | None:
    """The fact the imports behind one edge make, or ``None`` when none is via ``@x``.

    *imports* are ``(file, line, specifier)``; *importer_folder* and *target_folder* are the
    two ends' sources, without a trailing slash.
    """
    opened_to = posixpath.basename(importer_folder)
    via = 0
    not_via: list[tuple[str, int]] = []
    for importer, line, specifier in imports:
        found = (
            located(specifier, importer, target_folder, project_root)
            if names_cross_import(specifier)
            else None
        )
        if found is not None and cross_import_name(found, target_folder) == opened_to:
            via += 1
        else:
            not_via.append((importer, line))
    if via == 0:
        return None
    if not not_via:
        return CrossImportFact(every=True, not_via=None)
    first, line = min(not_via)
    return CrossImportFact(every=False, not_via=f"{first}:{line}")


def read_cross_import_facts(
    conn: sqlite3.Connection, edge_kind: str
) -> dict[tuple[str, str], CrossImportFact]:
    """The ``@x`` fact of every edge of *edge_kind* that carries one, by ``(src, dst)``."""
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, json_extract(extra, '$.' || ?), "
        "json_extract(extra, '$.' || ?), json_extract(extra, '$.' || ?) FROM edges "
        "WHERE kind = ? AND json_valid(extra)",
        (VIA_KEY, PARTLY_VIA_KEY, NOT_VIA_KEY, edge_kind),
    ).fetchall()
    facts: dict[tuple[str, str], CrossImportFact] = {}
    for src, dst, via, partly_via, not_via in rows:
        if via == VIA_CROSS_IMPORT:
            facts[(str(src), str(dst))] = CrossImportFact(every=True, not_via=None)
        elif partly_via == VIA_CROSS_IMPORT:
            where = str(not_via) if isinstance(not_via, str) and not_via else None
            facts[(str(src), str(dst))] = CrossImportFact(every=False, not_via=where)
    return facts


def edge_extra(derived_by: str, fact: CrossImportFact | None) -> str:
    """The ``extra`` JSON of a derived edge: its provenance, and its ``@x`` fact if any."""
    extra: dict[str, str] = {"derived": derived_by}
    if fact is not None:
        extra.update(fact.as_extra())
    return json.dumps(extra, ensure_ascii=False)
