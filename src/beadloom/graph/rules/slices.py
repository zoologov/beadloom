# beadloom:domain=graph
# beadloom:feature=rule-engine
"""The two Feature-Sliced Design slice rules: entered through a public API, shaped by purpose.

BDL-080 S3c, RFC D4; read as feature-sliced.design 2.1 writes it since BDL-082 S1b (RFC D1,
D4, D5). The units a rule judges — slices, the segments of ``shared`` and ``app`` and their
containers, slice groups — are read by :mod:`.slice_units`; the layer order between them is
the ``layers`` rule's, not theirs.

- :func:`evaluate_slice_public_api_rules` — ``slice_public_api``
  (:class:`~beadloom.graph.rules.types.SlicePublicApiRule`). For each row of
  ``code_imports`` that the reindex resolved to a node inside a unit, from a file outside
  that unit: the imported file is located inside the unit's folder
  (:func:`~beadloom.graph.rules.cross_imports.located`, the reading the reindex's ``@x``
  edge fact is taken through as well), and a file that is no public API entry is a
  finding. The entries are the unit's ``index``; ``@x/<B>`` (or
  ``@x/<B>/index``), the cross-import API a slice opens to the slice ``B`` of its own layer
  alone; and, in a segment ``ui`` or ``lib`` of ``shared``, a per-component index
  (``shared/ui/button/index``). Two segments of one container import each other freely, and
  an import into a container itself is not judged. A relative specifier is completed from
  the importing file's folder by :func:`~beadloom.graph.js_specifiers.relative_import_candidates`,
  the completion the resolver itself uses. Any other specifier went through an alias the
  rule does not read (tsconfig ``paths``, ``imports.aliases``), so it is matched against
  the unit's folder by its longest trailing path that names a file there:
  ``@/features/auth/model/session`` names ``model/session.ts`` inside
  ``src/features/auth``, and ``@/features/auth`` names nothing deeper, so the folder
  itself, so its ``index``. Either way a candidate is the file only when its path is
  named in its exact case (:func:`~beadloom.graph.exact_case.first_existing_file`, the
  resolver's own completion): on macOS ``app.vue`` answers ``is_file()`` for ``App.vue``,
  and until BDL-080 S3f the rule judged a file the resolver had not reached. An import
  into a unit that has no ``index`` is a finding too, unless it lands on another entry:
  there is no public API to enter it through. An import whose file cannot be located in a
  unit that has one is not judged.
- :func:`evaluate_slice_shape_rules` — ``slice_shape``
  (:class:`~beadloom.graph.rules.types.SliceShapeRule`). A folder at a slice's top named in
  the rule's ``discouraged`` and not in its ``segments``, a code file there that is not its
  ``index``, and a code file at the top of a slice group are findings.

:func:`slice_rule_inert_reason` says why either rule cannot fire, for
:mod:`.liveness`: no node carries any of its tags, or no such node's source is a folder.
"""

from __future__ import annotations

import posixpath
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.graph.js_specifiers import MODULE_EXTENSIONS
from beadloom.graph.rules.cross_imports import cross_import_name, located
from beadloom.graph.rules.slice_units import (
    INDEX,
    SliceUnits,
    carriers,
    has_index,
    inside,
    node_sources,
    read_units,
    stem,
)
from beadloom.graph.rules.types import SlicePublicApiRule, SliceShapeRule, Violation
from beadloom.infrastructure.repository import most_specific_owner

if TYPE_CHECKING:
    import sqlite3

SLICE_PUBLIC_API_RULE_TYPE = "slice_public_api"
SLICE_SHAPE_RULE_TYPE = "slice_shape"

#: The specification's sentence a cross-import finding quotes (``/docs/reference/public-api``).
_CROSS_IMPORT_SPEC = "entity A can declare a separate public API just for entity B"

#: The segments of ``shared`` whose components each carry an index of their own
#: (``/docs/reference/public-api``, *Large bundles … in Shared*).
_PER_COMPONENT_SEGMENTS = frozenset({"ui", "lib"})
_SHARED_LAYER_FOLDER = "shared"


def _is_the_index_of(path: str, folder: str) -> bool:
    """Whether the file *path* is the ``index`` at the top of *folder*."""
    return posixpath.dirname(path) == folder and stem(posixpath.basename(path)) == INDEX


def _has_per_component_indexes(folder: str) -> bool:
    """Whether *folder* is ``shared/ui`` or ``shared/lib``, whose components carry indexes."""
    return (
        posixpath.basename(folder) in _PER_COMPONENT_SEGMENTS
        and posixpath.basename(posixpath.dirname(folder)) == _SHARED_LAYER_FOLDER
    )


def _is_a_per_component_index(path: str, folder: str) -> bool:
    """Whether *path* is ``<folder>/<component>/index.*``."""
    return _is_the_index_of(path, posixpath.dirname(path)) and (
        posixpath.dirname(posixpath.dirname(path)) == folder
    )


def _public_api_finding(
    rule: SlicePublicApiRule,
    row: tuple[str, int, str],
    owner: str | None,
    unit: str,
    message: str,
    remediation: str | None = None,
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
        to_ref_id=unit,
        message=message,
        remediation=remediation,
    )


def _judge_cross_import(
    rule: SlicePublicApiRule,
    row: tuple[str, int, str],
    owner: str | None,
    units: SliceUnits,
    target: tuple[str, str, str],
) -> Violation | None:
    """An import of ``@x/<B>`` of *unit*: clean from slice B of its layer, else a finding.

    *target* is ``(unit, B, the file reached)``.
    """
    unit, opened_to, found = target
    importer, line, specifier = row
    importer_unit = units.holding(importer)
    if (
        importer_unit is not None
        and units.same_layer(importer_unit, unit)
        and posixpath.basename(units.folders[importer_unit]) == opened_to
    ):
        return None
    whence = f"slice '{importer_unit}'" if importer_unit else "outside every slice"
    return _public_api_finding(
        rule,
        row,
        owner,
        unit,
        f"{importer}:{line} imports '{specifier}', the cross-import API slice '{unit}' opens "
        f"to its sibling slice '{opened_to}' alone ({found}), from {whence}: a cross-import "
        f'API is open to the one slice it names ("{_CROSS_IMPORT_SPEC}")',
        f"import `{unit}` through its index, or have `{unit}` open a cross-import API of "
        f"its own to this slice, `@x/<this slice's folder>`",
    )


def _judge_import(
    rule: SlicePublicApiRule,
    row: tuple[str, int, str],
    unit: str,
    units: SliceUnits,
    project_root: Path,
    owner: str | None,
) -> Violation | None:
    """The finding one import into the unit *unit* earns, or ``None``."""
    importer, line, specifier = row
    folder = units.folders[unit]
    noun = units.noun(unit)
    per_component = _has_per_component_indexes(folder)
    found = located(specifier, importer, folder, project_root)
    if found is not None:
        opened_to = cross_import_name(found, folder)
        if opened_to is not None:
            return _judge_cross_import(rule, row, owner, units, (unit, opened_to, found))
        if per_component and _is_a_per_component_index(found, folder):
            return None
    if not has_index(folder, project_root) and not (per_component and found is not None):
        return _public_api_finding(
            rule,
            row,
            owner,
            unit,
            f"{importer}:{line} imports '{specifier}' into {noun} '{unit}', which has no "
            f"index: a {noun} without a public API cannot be entered from outside it",
        )
    if found is None or _is_the_index_of(found, folder):
        return None
    entries = f"{folder}/index"
    if per_component:
        entries += f", or a per-component index {folder}/<component>/index"
    return _public_api_finding(
        rule,
        row,
        owner,
        unit,
        f"{importer}:{line} imports '{specifier}', which reaches past the public API of "
        f"{noun} '{unit}' ({entries}) into {found}",
    )


def _not_judged(importer: str, unit: str, units: SliceUnits) -> bool:
    """Whether an import from *importer* into *unit* is the unit's own business.

    An import from inside the unit; an import into a container, which FSD gives no public
    API; and an import between two segments of one container, which import each other
    freely.
    """
    if inside(importer, units.folders[unit]) or units.is_container(unit):
        return True
    container = units.container_of.get(unit)
    return container is not None and inside(importer, units.folders[container])


def evaluate_slice_public_api_rules(
    conn: sqlite3.Connection,
    rules: list[SlicePublicApiRule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Every import into a slice or a segment, from outside it, that lands on no entry.

    *project_root* (default: cwd) is where the units' folders are read.
    """
    if not rules:
        return []
    root = project_root if project_root is not None else Path.cwd()
    sources = node_sources(conn)
    rows = conn.execute(
        "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports "
        "WHERE resolved_ref_id IS NOT NULL ORDER BY file_path, line_number, import_path"
    ).fetchall()
    resolved_source = dict(sources)
    violations: list[Violation] = []
    for rule in rules:
        units = read_units(conn, rule.tags, root)
        for importer, line, specifier, resolved in rows:
            unit = units.holding(resolved_source.get(str(resolved), ""))
            if unit is None or _not_judged(str(importer), unit, units):
                continue
            row = (str(importer), int(line), str(specifier))
            owner = most_specific_owner(sources, str(importer))
            finding = _judge_import(rule, row, unit, units, root, owner)
            if finding is not None:
                violations.append(finding)
    return violations


def _discouraged_finding(rule: SliceShapeRule, slice_ref: str, name: str) -> tuple[str, str]:
    """The message and the remediation for the discouraged folder *name* of a slice."""
    count = len(rule.discouraged)
    listed = (
        "the name this rule discourages"
        if count == 1
        else (f"one of the {count} names this rule discourages")
    )
    return (
        f"Slice '{slice_ref}' holds the folder '{name}/' at its top, {listed}: name by "
        f'purpose, not essence ("the name of these segments describes the purpose of the '
        f'content, not its essence"; its known segments: {", ".join(rule.segments)})',
        f"rename `{name}/` after what its code is for, or list it under the rule's "
        f"`segments:` when the name is this project's decision",
    )


def _shape_messages(rule: SliceShapeRule, slice_ref: str, folder: Path) -> list[tuple[str, str]]:
    """What stands at the top of one slice's *folder* that the rule's shape does not allow."""
    found: list[tuple[str, str]] = []
    segments = ", ".join(rule.segments)
    for entry in sorted(folder.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            if entry.name in rule.discouraged and entry.name not in rule.segments:
                found.append(_discouraged_finding(rule, slice_ref, entry.name))
        elif entry.suffix in MODULE_EXTENSIONS and stem(entry.name) != INDEX:
            found.append(
                (
                    f"Slice '{slice_ref}' holds the code file '{entry.name}' at its top, "
                    f"beside its segments ({segments}): only its public API, the index, "
                    f"belongs there",
                    f"move `{entry.name}` into one of `{slice_ref}`'s segments, or into a "
                    f"slice of its own when it is a business entity or feature of its own",
                )
            )
    return found


def _shape_violation(
    rule: SliceShapeRule,
    message: tuple[str, str],
    *,
    slice_ref: str | None = None,
    file_path: str | None = None,
) -> Violation:
    return Violation(
        rule_name=rule.name,
        rule_description=rule.description,
        rule_type=SLICE_SHAPE_RULE_TYPE,
        severity=rule.severity,
        file_path=file_path,
        line_number=None,
        from_ref_id=slice_ref,
        to_ref_id=None,
        message=message[0],
        remediation=message[1],
    )


def _group_findings(rule: SliceShapeRule, units: SliceUnits, root: Path) -> list[Violation]:
    """A code file at the top of a slice group, a folder that shares no code."""
    violations: list[Violation] = []
    for group, members in units.groups().items():
        for entry in sorted((root / group).iterdir()):
            if entry.name.startswith(".") or not entry.is_file():
                continue
            if entry.suffix not in MODULE_EXTENSIONS:
                continue
            message = (
                f"Group folder '{group}/' holds the code file '{entry.name}' at its top: a "
                f'group shares no code (its slices: {", ".join(members)}; "there should be '
                f'no code sharing in that folder")',
                f"move `{entry.name}` into the one slice of the group that uses it, or into "
                f"a lower layer when several slices do",
            )
            violations.append(_shape_violation(rule, message, file_path=f"{group}/{entry.name}"))
    return violations


def evaluate_slice_shape_rules(
    conn: sqlite3.Connection,
    rules: list[SliceShapeRule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Every discouraged folder and stray code file at a slice's top, and code in a group.

    A segment of ``shared`` or ``app`` is not judged: its top is its content.
    """
    root = project_root if project_root is not None else Path.cwd()
    violations: list[Violation] = []
    for rule in rules:
        units = read_units(conn, rule.tags, root)
        for slice_ref in sorted(units.folders):
            if units.is_segment(slice_ref):
                continue
            for message in _shape_messages(rule, slice_ref, root / units.folders[slice_ref]):
                violations.append(_shape_violation(rule, message, slice_ref=slice_ref))
        violations.extend(_group_findings(rule, units, root))
    return violations


def slice_rule_inert_reason(
    rule: SlicePublicApiRule | SliceShapeRule,
    conn: sqlite3.Connection,
    project_root: Path | None,
) -> str | None:
    """Why *rule* cannot fire, or ``None`` when it has a slice to judge."""
    listed = ", ".join(rule.tags)
    if not carriers(conn, rule.tags):
        return f"no node carries any of its tags ({listed})"
    root = project_root if project_root is not None else Path.cwd()
    if not read_units(conn, rule.tags, root).folders:
        return (
            f"no slice to judge: no node carrying one of its tags ({listed}) has a source "
            "folder on disk"
        )
    return None
