"""A Feature-Sliced Design tree, read slice by slice for ``init`` (BDL-080 S3c, RFC D4).

FSD names six layers (:data:`~beadloom.onboarding.presets.FSD_LAYERS`), and the
architecture lives one level below them: a layer is a folder of slices, a slice is one
business entity or feature, and ``app`` and ``shared`` hold segments rather than slices.
So the units a graph is written from are:

- **a slice** of ``pages``, ``widgets``, ``features`` or ``entities``: one unit per
  folder, named ``<layer>-<slice>``. The layer folder itself is no unit, because a node
  per layer would be a tagged container shared by every slice in it, and the layer rule
  reads two ends inside one tagged container as internal: two widgets importing each
  other would pass.
- **a slice of a group** (BDL-082 S2a, RFC D2): a folder of a sliced layer is a slice
  when it holds a standard segment or an ``index`` at its top; a folder that holds
  neither and has a slice below it is a *group*, which the specification gives "no code
  sharing". The group has no unit; each folder in it
  is one slice, named ``<layer>-<group>-<slice>``, so ``register`` importing ``login`` is
  an edge between two slices of one layer. Groups are read at any depth: a group inside
  a group is read as its slices too, named ``<layer>-<group>-<group>-<slice>``. A folder
  holding code at its top is a group only when a folder in it holds a standard segment,
  and otherwise one slice (the owner's ruling of 2026-10-13): a slice not yet split into
  segments stays one unit with all its files, while the code at a group's top belongs to
  no unit, and the shape rule reports both.
- **a container** for ``app`` and for ``shared``, and **a segment** for each folder in
  them, the segment a part of its container. Two segments of one layer import each other
  freely in FSD, which the tagged container says to the layer rule.
- **a legacy unit** for each folder beside the layers that holds code (``components``,
  ``hooks``, ``stores`` …), outside every layer. A graph that ignores half the code says
  by omission that it is not there; Steiger's config ignores such folders, and a graph
  is not a linter.

- **the routes** of Expo Router, when the layers are under ``src/`` and the project
  depends on the router (:mod:`~beadloom.onboarding.scanner.expo_router`): ``app/`` at the
  root is ONE segment of the ``app`` layer, ``app-routes``, part of the ``app`` container
  (of the root when the layer has none). FSD's guidance for Expo Router reads the routes
  as the top layer, so the layer rule judges them; until BDL-080 S3e the clustering made a
  node of each route folder (``app/trail/`` as ``trail``, outside every layer) and left
  ``app/_layout.tsx`` to the root. One node, not one per route: routes as nodes is
  ``beadloom-mnuu``.

What the layout *claims* leaves the directory clustering, the way a JVM module or a
Swift target does: the whole ``src/`` and the routes folder when the layers are under
``src/``, else the layer and legacy folders at the root. Code elsewhere is clustered as
before.

Not read: an FSD tree inside one package of a monorepo.
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from beadloom.graph.rules import DEFAULT_SLICE_SEGMENTS, is_index_file
from beadloom.onboarding.presets import FSD_LAYERS, fsd_root
from beadloom.onboarding.scanner.constants import (
    _CLUSTER_SKIP,
    _CODE_EXTENSIONS,
    _RECURSIVE_SKIP,
    _SKIP_DIRS,
    _is_in_skip_dir,
    _sanitize_ref_id,
)
from beadloom.onboarding.scanner.expo_router import expo_router_routes

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from pathlib import Path

    from beadloom.onboarding.scanner.ref_ids import RefIdAllocator

#: The two layers that hold segments instead of slices.
SEGMENTED_LAYERS: frozenset[str] = frozenset({"app", "shared"})

#: The layer Expo Router's routes belong to, and the name their one unit asks for.
ROUTES_LAYER = "app"
ROUTES_UNIT = "app-routes"

#: The tag a folder beside the layers is written with: outside every layer of the rule.
FSD_LEGACY_TAG = "fsd-legacy"

#: The kind every FSD node is written as: a slice, a segment, a container, a legacy folder.
FSD_NODE_KIND = "component"

SLICE = "slice"
CONTAINER = "container"
SEGMENT = "segment"
LEGACY = "legacy"


@dataclass(frozen=True)
class FsdUnit:
    """One folder of an FSD tree that ``init`` writes as a node.

    *name* is the ref_id the node asks for; *layer* is ``None`` for a legacy folder;
    *role* is one of :data:`SLICE`, :data:`CONTAINER`, :data:`SEGMENT`, :data:`LEGACY`;
    *parent* is the container's *name* for a segment, else ``None``. *files* are the
    project-relative code files below *directory*, sorted; a container's are the ones
    none of its segments holds.
    """

    name: str
    directory: str
    layer: str | None
    role: str
    parent: str | None
    files: tuple[str, ...]


@dataclass(frozen=True)
class FsdLayout:
    """The FSD tree of a project: where its layers are, and the units it is written from.

    *root* is the project-relative folder holding the layers, ``""`` for the project
    root, ``None`` when the project is not in the FSD layout. *routes* is Expo Router's
    routes folder beside the root, written as one unit of the ``app`` layer, else ``None``.
    """

    root: str | None = None
    units: tuple[FsdUnit, ...] = ()
    routes: str | None = None

    @property
    def claimed(self) -> frozenset[str]:
        """The folders the directory clustering leaves to this layout."""
        if self.root is None:
            return frozenset()
        if self.root:
            return frozenset({self.root, *([self.routes] if self.routes else [])})
        return frozenset(unit.directory.split("/", 1)[0] for unit in self.units)


def _is_architecture_folder(folder: Path, skip: Collection[str]) -> bool:
    """Whether *folder* can be part of the architecture: not hidden, vendored or an asset."""
    name = folder.name
    return (
        folder.is_dir()
        and not name.startswith((".", "_"))
        and name not in _RECURSIVE_SKIP
        and name not in _CLUSTER_SKIP
        and name not in skip
    )


def _code_files(project_root: Path, folder: Path) -> tuple[str, ...]:
    """The project-relative code files below *folder*, skipped folders left out, sorted."""
    return tuple(
        sorted(
            path.relative_to(project_root).as_posix()
            for path in folder.rglob("*")
            if path.is_file()
            and path.suffix in _CODE_EXTENSIONS
            and not _is_in_skip_dir(path, folder)
        )
    )


def _subfolders(folder: Path, skip: Collection[str] = ()) -> list[Path]:
    return [child for child in sorted(folder.iterdir()) if _is_architecture_folder(child, skip)]


def _layer_units(project_root: Path, layer_folder: Path) -> list[FsdUnit]:
    """The units of one layer folder: slices, or a container and its segments."""
    layer = layer_folder.name
    rel = layer_folder.relative_to(project_root).as_posix()
    if layer not in SEGMENTED_LAYERS:
        return [
            unit
            for folder in _subfolders(layer_folder)
            for unit in _slices_of(project_root, [folder], layer)
        ]
    segments = [
        FsdUnit(
            f"{layer}-{_sanitize_ref_id(segment.name)}",
            f"{rel}/{segment.name}",
            layer,
            SEGMENT,
            layer,
            segment_files,
        )
        for segment in _subfolders(layer_folder)
        if (segment_files := _code_files(project_root, segment))
    ]
    # The container holds what no segment does: its entry files, for one.
    in_segments = {path for segment in segments for path in segment.files}
    own = tuple(
        path for path in _code_files(project_root, layer_folder) if path not in in_segments
    )
    if not own and not segments:
        return []
    return [FsdUnit(layer, rel, layer, CONTAINER, None, own), *segments]


def _holds_a_segment(folder: Path) -> bool:
    """Whether *folder* holds a standard segment at its top: Steiger's own slice test."""
    return any(
        child.is_dir() and child.name in DEFAULT_SLICE_SEGMENTS for child in folder.iterdir()
    )


def _is_slice(folder: Path) -> bool:
    """Whether *folder* holds a standard segment or an ``index`` code file at its top.

    The ``index`` is read by the public-API rule's own reader, so ``init`` and
    ``fsd-public-api`` agree on which folders have a public API.
    """
    return _holds_a_segment(folder) or any(is_index_file(child) for child in folder.iterdir())


def _holds_code_at_top(folder: Path) -> bool:
    """Whether *folder* holds a code file directly, not only in its folders."""
    return any(child.is_file() and child.suffix in _CODE_EXTENSIONS for child in folder.iterdir())


def _is_group(folder: Path) -> bool:
    """Whether *folder*, no slice itself, is a group of the slices below it.

    The owner's ruling 3 as refined on 2026-10-13: a folder with no code at its top is a
    group when a folder in it is a slice or a group, at any depth; a folder with code at its
    top is a group only when a folder in it holds a standard segment, and otherwise a slice,
    so a slice not yet split into segments stays whole while a group with a shared file in it
    keeps its slices. A linked folder is not looked into: a link back up the tree would
    never end.
    """
    if folder.is_symlink():
        return False
    children = _subfolders(folder)
    if _holds_code_at_top(folder):
        return any(_holds_a_segment(child) for child in children)
    return any(_is_slice(child) or _is_group(child) for child in children)


def _slices_of(project_root: Path, path: list[Path], layer: str) -> list[FsdUnit]:
    """The slices the folder at the end of *path*, in a sliced layer, is read as.

    A folder that is no slice but a group (:func:`_is_group`, RFC D2) has no unit, and
    every folder in it is read the same way: a slice, a group in its turn, or one slice of
    the group whether slice-shaped or not, since a group shares no code and a folder read as
    a slice makes an import of it from a sibling a same-layer crossing. Each slice is named
    by the whole *path*, ``<layer>-<group>-...-<slice>``.
    """
    folder = path[-1]
    if _is_slice(folder) or not _is_group(folder):
        return _slice_unit(project_root, path, layer)
    return [
        unit
        for child in _subfolders(folder)
        for unit in _slices_of(project_root, [*path, child], layer)
    ]


def _slice_unit(project_root: Path, path: list[Path], layer: str) -> list[FsdUnit]:
    """One slice unit for the folder at the end of *path*, or none when it holds no code."""
    folder = path[-1]
    files = _code_files(project_root, folder)
    if not files:
        return []
    name = "-".join([layer, *(_sanitize_ref_id(part.name) for part in path)])
    directory = folder.relative_to(project_root).as_posix()
    return [FsdUnit(name, directory, layer, SLICE, None, files)]


def read_fsd_layout(project_root: Path, *, skip: Collection[str] = ()) -> FsdLayout:
    """Read the FSD tree of *project_root*; an empty layout when it is not in that layout.

    *skip* names top-level folders that are not the project's code (a portal
    ``docs site`` wrote), so none of them becomes a legacy unit.
    """
    root = fsd_root(project_root)
    if root is None:
        return FsdLayout()
    base = project_root / root if root else project_root
    units: list[FsdUnit] = []
    for folder in _subfolders(base, skip if not root else ()):
        if folder.name in FSD_LAYERS:
            units.extend(_layer_units(project_root, folder))
            continue
        if not root and folder.name in _SKIP_DIRS:
            continue
        files = _code_files(project_root, folder)
        if files:
            directory = folder.relative_to(project_root).as_posix()
            units.append(
                FsdUnit(_sanitize_ref_id(folder.name), directory, None, LEGACY, None, files)
            )
    routes = _routes_unit(project_root, units) if root else None
    if routes is None:
        return FsdLayout(root=root, units=tuple(units))
    return FsdLayout(root=root, units=(*units, routes), routes=routes.directory)


def _routes_unit(project_root: Path, units: list[FsdUnit]) -> FsdUnit | None:
    """Expo Router's routes as one segment of the ``app`` layer, or ``None``.

    Called only when the layers are under a folder: with the layers at the root,
    ``app/`` IS the ``app`` layer and its folders are its segments.
    """
    folder = expo_router_routes(project_root)
    files = _code_files(project_root, project_root / folder) if folder is not None else ()
    if folder is None or not files:
        return None
    has_container = any(u.role == CONTAINER and u.layer == ROUTES_LAYER for u in units)
    parent = ROUTES_LAYER if has_container else None
    return FsdUnit(ROUTES_UNIT, folder, ROUTES_LAYER, SEGMENT, parent, files)


def fsd_tag(unit: FsdUnit) -> str:
    """The tag *unit* is written with: ``fsd-<layer>``, or :data:`FSD_LEGACY_TAG`."""
    return f"fsd-{unit.layer}" if unit.layer is not None else FSD_LEGACY_TAG


@dataclass(frozen=True)
class FsdGraph:
    """What :func:`fsd_nodes` writes: the nodes and their ``part_of`` edges.

    No ``depends_on`` edge: the reindex derives those from the code (see
    ``bootstrap_project``), so none is frozen into the YAML.
    """

    nodes: tuple[dict[str, Any], ...]
    edges: tuple[dict[str, str], ...]


def fsd_nodes(
    layout: FsdLayout,
    ref_ids: RefIdAllocator,
    frontend: str,
    summarise: Callable[[FsdUnit], str],
) -> FsdGraph:
    """The nodes and ``part_of`` edges of *layout*, each node ``part_of`` *frontend*.

    *frontend* is the service the slices stratify: the root node of a single-app
    repository. A segment is ``part_of`` its container instead. *ref_ids* hands out
    the names, so no FSD node takes a ref_id another node of the graph holds.
    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    refs: dict[str, str] = {}
    for unit in layout.units:
        ref_id = ref_ids.take(unit.name, qualifier=FSD_NODE_KIND)
        refs[unit.name] = ref_id
        nodes.append(
            {
                "ref_id": ref_id,
                "kind": FSD_NODE_KIND,
                "summary": summarise(unit),
                "confidence": "high",
                "source": f"{unit.directory}/",
                "tags": [fsd_tag(unit)],
            }
        )
        parent = refs[unit.parent] if unit.parent is not None else frontend
        edges.append({"src": ref_id, "dst": parent, "kind": "part_of"})
    return FsdGraph(nodes=tuple(nodes), edges=tuple(edges))
