# beadloom:domain=graph
# beadloom:feature=rule-engine
"""The two Feature-Sliced Design slice rules: entered through its index, shaped by segments.

BDL-080 S3c, RFC D4. A *slice* is a node carrying one of a rule's ``tags`` whose
``source`` is a folder on disk. Both rules are judged per slice and read the folder; the
layer order between slices is the ``layers`` rule's, not theirs.

- :func:`evaluate_slice_public_api_rules` — ``slice_public_api``
  (:class:`~beadloom.graph.rules.types.SlicePublicApiRule`). For each row of
  ``code_imports`` that the reindex resolved to a node inside a slice, from a file
  outside that slice: the imported file is located inside the slice's folder, and a file
  other than the slice's ``index`` is a finding. A relative specifier is completed from
  the importing file's folder by :func:`~beadloom.graph.js_specifiers.relative_import_candidates`,
  the completion the resolver itself uses. Any other specifier went through an alias the
  rule does not read (tsconfig ``paths``, ``imports.aliases``), so it is matched against
  the slice's folder by its longest trailing path that names a file there:
  ``@/features/auth/model/session`` names ``model/session.ts`` inside
  ``src/features/auth``, and ``@/features/auth`` names nothing deeper, so the folder
  itself, so its ``index``. Either way a candidate is the file only when its path is
  named in its exact case (:func:`~beadloom.graph.exact_case.first_existing_file`, the
  resolver's own completion): on macOS ``app.vue`` answers ``is_file()`` for ``App.vue``,
  and until BDL-080 S3f the rule judged a file the resolver had not reached. An import
  into a slice that has no ``index`` is a finding too: there is no public API to enter it
  through. An import whose file cannot be located in a slice that has one is not judged.
- :func:`evaluate_slice_shape_rules` — ``slice_shape``
  (:class:`~beadloom.graph.rules.types.SliceShapeRule`). A folder at a slice's top that
  is not one of the rule's ``segments``, and a code file there that is not its
  ``index``, are findings.

:func:`slice_rule_inert_reason` says why either rule cannot fire, for
:mod:`.liveness`: no node carries any of its tags, or no such node's source is a folder.
"""

from __future__ import annotations

import posixpath
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.graph.exact_case import first_existing_file
from beadloom.graph.js_specifiers import (
    MODULE_EXTENSIONS,
    is_relative_specifier,
    module_file_candidates,
    relative_import_candidates,
)
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import SlicePublicApiRule, SliceShapeRule, Violation
from beadloom.infrastructure.repository import most_specific_owner

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence

SLICE_PUBLIC_API_RULE_TYPE = "slice_public_api"
SLICE_SHAPE_RULE_TYPE = "slice_shape"

#: The stem of a slice's public API file: ``index.ts``, ``index.vue``, ``index.ios.tsx``.
_INDEX = "index"


def _stem(file_name: str) -> str:
    """The name before its first dot: ``index`` for ``index.ios.tsx``."""
    return file_name.split(".", 1)[0]


def _node_sources(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """``(ref_id, source)`` of every node that declares a source."""
    rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source != '' "
        "ORDER BY ref_id"
    ).fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


def _carriers(conn: sqlite3.Connection, tags: Sequence[str]) -> list[str]:
    """The nodes carrying one of *tags*, sorted."""
    wanted = set(tags)
    return sorted(ref for ref, carried in node_tags(conn).as_mapping().items() if carried & wanted)


def _slice_folders(
    conn: sqlite3.Connection, tags: Sequence[str], project_root: Path
) -> dict[str, str]:
    """Each slice's ref_id, mapped to its project-relative folder (no trailing slash)."""
    carriers = set(_carriers(conn, tags))
    return {
        ref_id: source.rstrip("/")
        for ref_id, source in _node_sources(conn)
        if ref_id in carriers and (project_root / source).is_dir()
    }


def _inside(path: str, folder: str) -> bool:
    return path == folder or path.startswith(f"{folder}/")


def _located(specifier: str, importer: str, folder: str, project_root: Path) -> str | None:
    """The file inside *folder* that *specifier*, imported by *importer*, names; or ``None``."""
    if is_relative_specifier(specifier):
        found = first_existing_file(relative_import_candidates(specifier, importer), project_root)
        return found if found is not None and _inside(found, folder) else None
    segments = [segment for segment in specifier.split("/") if segment]
    for start in range(len(segments) + 1):
        target = posixpath.normpath(posixpath.join(folder, *segments[start:]))
        if not _inside(target, folder):
            continue
        found = first_existing_file(module_file_candidates(target), project_root)
        if found is not None:
            return found if _inside(found, folder) else None
    return None


def _slice_holding(source: str, folders: dict[str, str]) -> str | None:
    """The slice whose folder holds the node *source* (a file or a folder), deepest first."""
    path = source.rstrip("/")
    holding = [ref for ref, folder in folders.items() if path and _inside(path, folder)]
    return max(holding, key=lambda ref: len(folders[ref])) if holding else None


def _is_the_index_of(path: str, folder: str) -> bool:
    """Whether the file *path* is the ``index`` at the top of *folder*."""
    return posixpath.dirname(path) == folder and _stem(posixpath.basename(path)) == _INDEX


def _has_index(folder: str, project_root: Path) -> bool:
    return any(
        path.is_file() and _stem(path.name) == _INDEX and path.suffix in MODULE_EXTENSIONS
        for path in (project_root / folder).iterdir()
    )


def _public_api_finding(
    rule: SlicePublicApiRule,
    row: tuple[str, int, str],
    owner: str | None,
    slice_ref: str,
    message: str,
) -> Violation:
    importer, line, _ = row
    return Violation(
        rule_name=rule.name,
        rule_description=rule.description,
        rule_type=SLICE_PUBLIC_API_RULE_TYPE,
        severity=rule.severity,
        file_path=importer,
        line_number=line,
        from_ref_id=owner,
        to_ref_id=slice_ref,
        message=message,
    )


def _judge_import(
    rule: SlicePublicApiRule,
    row: tuple[str, int, str],
    slice_ref: str,
    folder: str,
    project_root: Path,
    owner: str | None,
) -> Violation | None:
    """The finding one import into the slice *slice_ref* earns, or ``None``."""
    importer, line, specifier = row
    if not _has_index(folder, project_root):
        return _public_api_finding(
            rule,
            row,
            owner,
            slice_ref,
            f"{importer}:{line} imports '{specifier}' into slice '{slice_ref}', which has no "
            f"index: a slice without a public API cannot be entered from outside it",
        )
    found = _located(specifier, importer, folder, project_root)
    if found is None or _is_the_index_of(found, folder):
        return None
    return _public_api_finding(
        rule,
        row,
        owner,
        slice_ref,
        f"{importer}:{line} imports '{specifier}', which reaches past the public API of "
        f"slice '{slice_ref}' ({folder}/index) into {found}",
    )


def evaluate_slice_public_api_rules(
    conn: sqlite3.Connection,
    rules: list[SlicePublicApiRule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Every import into a slice, from outside it, that does not land on its ``index``.

    *project_root* (default: cwd) is where the slices' folders are read.
    """
    if not rules:
        return []
    root = project_root if project_root is not None else Path.cwd()
    sources = _node_sources(conn)
    rows = conn.execute(
        "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports "
        "WHERE resolved_ref_id IS NOT NULL ORDER BY file_path, line_number, import_path"
    ).fetchall()
    resolved_source = dict(sources)
    violations: list[Violation] = []
    for rule in rules:
        folders = _slice_folders(conn, rule.tags, root)
        for importer, line, specifier, resolved in rows:
            slice_ref = _slice_holding(resolved_source.get(str(resolved), ""), folders)
            if slice_ref is None or _inside(str(importer), folders[slice_ref]):
                continue
            row = (str(importer), int(line), str(specifier))
            owner = most_specific_owner(sources, str(importer))
            finding = _judge_import(rule, row, slice_ref, folders[slice_ref], root, owner)
            if finding is not None:
                violations.append(finding)
    return violations


def _shape_findings(rule: SliceShapeRule, slice_ref: str, folder: Path) -> list[Violation]:
    """What stands at the top of one slice's *folder* that the rule's shape does not allow."""
    found: list[str] = []
    segments = ", ".join(rule.segments)
    for entry in sorted(folder.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir() and entry.name not in rule.segments:
            found.append(
                f"Slice '{slice_ref}' holds the folder '{entry.name}/' at its top, which is "
                f"not one of its segments ({segments})"
            )
        elif entry.is_file() and entry.suffix in MODULE_EXTENSIONS and _stem(entry.name) != _INDEX:
            found.append(
                f"Slice '{slice_ref}' holds the code file '{entry.name}' at its top, beside "
                f"its segments ({segments}): only its public API, the index, belongs there"
            )
    return [
        Violation(
            rule_name=rule.name,
            rule_description=rule.description,
            rule_type=SLICE_SHAPE_RULE_TYPE,
            severity=rule.severity,
            file_path=None,
            line_number=None,
            from_ref_id=slice_ref,
            to_ref_id=None,
            message=message,
        )
        for message in found
    ]


def evaluate_slice_shape_rules(
    conn: sqlite3.Connection,
    rules: list[SliceShapeRule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Every folder and code file at a slice's top that is neither a segment nor its index."""
    root = project_root if project_root is not None else Path.cwd()
    violations: list[Violation] = []
    for rule in rules:
        for slice_ref, folder in sorted(_slice_folders(conn, rule.tags, root).items()):
            violations.extend(_shape_findings(rule, slice_ref, root / folder))
    return violations


def slice_rule_inert_reason(
    rule: SlicePublicApiRule | SliceShapeRule,
    conn: sqlite3.Connection,
    project_root: Path | None,
) -> str | None:
    """Why *rule* cannot fire, or ``None`` when it has a slice to judge."""
    listed = ", ".join(rule.tags)
    if not _carriers(conn, rule.tags):
        return f"no node carries any of its tags ({listed})"
    root = project_root if project_root is not None else Path.cwd()
    if not _slice_folders(conn, rule.tags, root):
        return (
            f"no slice to judge: no node carrying one of its tags ({listed}) has a source "
            "folder on disk"
        )
    return None
