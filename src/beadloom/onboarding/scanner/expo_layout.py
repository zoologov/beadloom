"""Local Expo modules, read as a module and its native parts for ``init`` (BDL-080 S3b).

A folder holding ``expo-module.config.json`` (``modules/<name>/`` in an Expo app) is one
Expo module: TypeScript that calls ``requireNativeModule``, and the native code that
answers, Swift in ``ios/`` and Kotlin in ``android/``. So the units a graph is written from
are:

- **the module**: one component for the folder, whose own code is everything outside the
  two native folders (``index.ts``, ``src/``);
- **a native part** for each of ``ios/`` and ``android/`` that holds native code: one
  component, part of its module.

The bridge between them is no import, and ``init`` does not write it: the reindex derives
a ``uses`` edge from the module to each part its config links
(``beadloom.graph.expo_modules``), on every run, so a platform the config stops linking
stops being drawn.

What this layout *claims* leaves the directory clustering and the JVM walk, the way an
FSD root does: until BDL-080 the JVM walk took ``android/`` as a Gradle module with a
node per package, part of the root rather than of the module, and Swift outside a
``Package.swift`` target was read by nothing.

Not read: a repository that is itself one Expo module (its config at the root), and native
code an ``apple.podspecPath`` or ``android.path`` moves out of the two folders.
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from beadloom.onboarding.scanner.constants import (
    _CLUSTER_SKIP,
    _CODE_EXTENSIONS,
    _RECURSIVE_SKIP,
    _SKIP_DIRS,
    _sanitize_ref_id,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterator
    from pathlib import Path

    from beadloom.onboarding.scanner.ref_ids import RefIdAllocator

#: The file that makes a folder an Expo module.
EXPO_MODULE_CONFIG = "expo-module.config.json"

#: Each native folder of a module and the extensions of the code it holds.
NATIVE_FOLDERS: dict[str, frozenset[str]] = {
    "ios": frozenset({".swift", ".m", ".mm"}),
    "android": frozenset({".kt", ".java"}),
}

#: Build output and installed code inside a native folder, at any depth.
_NATIVE_SKIP = frozenset({"Pods", "build", ".gradle", ".cxx"})

#: The kind every unit of an Expo module is written as.
EXPO_NODE_KIND = "component"


@dataclass(frozen=True)
class NativePart:
    """One native folder of a module: *platform* is its name, ``ios`` or ``android``."""

    platform: str
    directory: str
    files: tuple[str, ...]


@dataclass(frozen=True)
class ExpoModuleUnit:
    """One Expo module: its folder, its own code files, and its native parts."""

    name: str
    directory: str
    files: tuple[str, ...]
    parts: tuple[NativePart, ...]


@dataclass(frozen=True)
class ExpoLayout:
    """The local Expo modules of a project; empty when it has none."""

    modules: tuple[ExpoModuleUnit, ...] = ()

    @property
    def claimed(self) -> frozenset[str]:
        """The module folders, which the directory clustering and the JVM walk leave alone."""
        return frozenset(module.directory for module in self.modules)

    @property
    def scan_paths(self) -> tuple[str, ...]:
        """Each module folder, sorted: the scan paths its code is indexed through."""
        return tuple(sorted(self.claimed))

    @property
    def languages(self) -> frozenset[str]:
        """The extensions of every file the modules hold."""
        return frozenset(
            path[path.rfind(".") :]
            for module in self.modules
            for path in (*module.files, *(f for part in module.parts for f in part.files))
        )


def _files(
    project_root: Path, folder: Path, extensions: Collection[str], skip: Collection[str]
) -> tuple[str, ...]:
    """The project-relative files below *folder* with *extensions*, *skip* folders left out."""
    return tuple(
        sorted(
            path.relative_to(project_root).as_posix()
            for path in folder.rglob("*")
            if path.is_file()
            and path.suffix in extensions
            and not any(part in skip for part in path.relative_to(folder).parts[:-1])
        )
    )


def _module(project_root: Path, folder: Path) -> ExpoModuleUnit | None:
    """The module in *folder*, or ``None`` when it holds no code at all."""
    parts = tuple(
        NativePart(platform, f"{_rel(project_root, folder)}/{platform}", files)
        for platform, extensions in NATIVE_FOLDERS.items()
        if (native := folder / platform).is_dir()
        and (files := _files(project_root, native, extensions, _NATIVE_SKIP | _RECURSIVE_SKIP))
    )
    native_prefixes = tuple(f"{_rel(project_root, folder)}/{p}/" for p in NATIVE_FOLDERS)
    own = tuple(
        path
        for path in _files(project_root, folder, _CODE_EXTENSIONS, _RECURSIVE_SKIP)
        if not path.startswith(native_prefixes)
    )
    if not own and not parts:
        return None
    return ExpoModuleUnit(_sanitize_ref_id(folder.name), _rel(project_root, folder), own, parts)


def _rel(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()


def _is_walked(folder: Path, *, top_level: bool, skip: Collection[str]) -> bool:
    name = folder.name
    if not folder.is_dir() or folder.is_symlink() or name.startswith((".", "_")):
        return False
    if name in _RECURSIVE_SKIP or name in _CLUSTER_SKIP or name in _NATIVE_SKIP:
        return False
    return not (top_level and (name in _SKIP_DIRS or name in skip))


def _module_folders(project_root: Path, skip: Collection[str]) -> Iterator[Path]:
    """Every folder below the root holding a config, not entering a module once found."""
    pending = [
        child
        for child in sorted(project_root.iterdir(), reverse=True)
        if _is_walked(child, top_level=True, skip=skip)
    ]
    while pending:
        folder = pending.pop()
        if (folder / EXPO_MODULE_CONFIG).is_file():
            yield folder
            continue
        pending.extend(
            child
            for child in sorted(folder.iterdir(), reverse=True)
            if _is_walked(child, top_level=False, skip=skip)
        )


def read_expo_layout(project_root: Path, *, skip: Collection[str] = ()) -> ExpoLayout:
    """Read the local Expo modules of *project_root*.

    *skip* names top-level folders another reading accounts for (an FSD root, a portal
    ``docs site`` wrote); no module below one is read here.
    """
    modules = (_module(project_root, folder) for folder in _module_folders(project_root, skip))
    return ExpoLayout(
        tuple(sorted((m for m in modules if m is not None), key=lambda m: m.directory))
    )


@dataclass(frozen=True)
class ExpoGraph:
    """What :func:`expo_nodes` writes: the nodes and their ``part_of`` edges."""

    nodes: tuple[dict[str, Any], ...]
    edges: tuple[dict[str, str], ...]


def _node(ref_id: str, directory: str, summary: str) -> dict[str, Any]:
    return {
        "ref_id": ref_id,
        "kind": EXPO_NODE_KIND,
        "summary": summary,
        "confidence": "high",
        "source": f"{directory}/",
    }


def expo_nodes(
    layout: ExpoLayout,
    ref_ids: RefIdAllocator,
    parent: str,
    summarise: Callable[[ExpoModuleUnit | NativePart], str],
) -> ExpoGraph:
    """The nodes of *layout*: each module ``part_of`` *parent*, each part ``part_of`` its module.

    A part is named after the ref_id its module was written under, so the two read as one
    family even when the module's own name was taken.
    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for module in layout.modules:
        module_ref = ref_ids.take(module.name, qualifier=EXPO_NODE_KIND)
        nodes.append(_node(module_ref, module.directory, summarise(module)))
        edges.append({"src": module_ref, "dst": parent, "kind": "part_of"})
        for part in module.parts:
            part_ref = ref_ids.take(f"{module_ref}-{part.platform}", qualifier=EXPO_NODE_KIND)
            nodes.append(_node(part_ref, part.directory, summarise(part)))
            edges.append({"src": part_ref, "dst": module_ref, "kind": "part_of"})
    return ExpoGraph(nodes=tuple(nodes), edges=tuple(edges))
