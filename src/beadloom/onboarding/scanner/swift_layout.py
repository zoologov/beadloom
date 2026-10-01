"""The Swift Package Manager layout of a project: its targets, test targets and their code.

BDL-076 B7 (``beadloom-ujzb.16``). On a Swift package ``init`` wrote 0 nodes,
``languages: [python]`` and ``scan_paths: [src]``: ``Package.swift`` was no manifest
it knew, ``Sources/`` no source folder and ``.swift`` no extension the project scan
counts. What a manifest declares is read by :mod:`beadloom.graph.swift_packages`,
the same reading the reindex resolves a Swift ``import`` through; this module turns
it into what ``init`` writes.

- **A target is a node** when it is a library, an executable, a macro or a plugin
  target and its folder holds a ``.swift`` file. A binary target is a prebuilt
  artifact and a system library a module map over a C library: neither holds Swift
  source, and neither is a node. A target holding no Swift — a C, C++ or
  Objective-C target — is no node either, because ``init`` reads Swift only.
- **The targets' folders are the scan paths**, each as the manifest places it
  (``Sources/<Target>`` by default, or its ``path:``).
- **A test target is never a node and never a scan path.** Its folder is mirrored
  to the target it tests, so its tests bind there: the target it is named after
  (``<Target>Tests``), else the one target of its package among its dependencies;
  a test target of several targets, or of none, mirrors nothing.
- **A package at the root** gives one cluster per target. **A package below the
  root** (``Packages/Kit/Package.swift``) is one cluster, named by its path, with
  its targets as children — the shape the JVM layout gives a module.
- **The packages read** are those the project scan would read: none under a top
  folder it skips (``tests``, ``docs``, ``build`` ...) and none under a fixtures or
  other skipped folder at any depth.

Edges are not taken from the manifest's ``dependencies:`` lists: a dependency
declared and not imported draws no edge, and the quick scan and the reindex both
read the ``import`` statements, so the two stay the same set.
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.graph.swift_packages import (
    KIND_EXECUTABLE,
    KIND_MACRO,
    KIND_PLUGIN,
    KIND_TARGET,
    SwiftPackages,
)
from beadloom.onboarding.scanner.constants import _CLUSTER_SKIP, _RECURSIVE_SKIP, _SKIP_DIRS
from beadloom.onboarding.scanner.ref_ids import RefIdAllocator

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from pathlib import Path

    from beadloom.graph.swift_packages import SwiftPackage, SwiftTarget
    from beadloom.onboarding.scanner.types import ClusterEntry

#: The extension of the code ``init`` reads in a target.
SWIFT_EXTENSION = ".swift"
#: The kinds of target that are nodes.
_NODE_KINDS = frozenset({KIND_TARGET, KIND_EXECUTABLE, KIND_MACRO, KIND_PLUGIN})
#: SwiftPM names a test target after the target it tests, plus this suffix.
_TEST_TARGET_SUFFIX = "Tests"
#: What a cluster name is qualified with when it is taken.
_TARGET_QUALIFIER = "target"
_PACKAGE_QUALIFIER = "package"


@dataclass(frozen=True)
class TargetRoot:
    """One target of one package, with the Swift files of its folder."""

    package: str
    target: SwiftTarget
    files: tuple[str, ...]

    @property
    def directory(self) -> str:
        return self.target.directory or ""


@dataclass(frozen=True)
class SwiftLayout:
    """Every Swift target of a project with code in its folder; empty when it has none."""

    roots: tuple[TargetRoot, ...] = ()
    packages: SwiftPackages | None = field(default=None, compare=False)

    @property
    def production(self) -> tuple[TargetRoot, ...]:
        return tuple(root for root in self.roots if not root.target.is_test)

    @property
    def production_roots(self) -> tuple[str, ...]:
        """The node targets' folders, sorted: the project's Swift scan paths."""
        return tuple(sorted(root.directory for root in self.production))

    @property
    def languages(self) -> tuple[str, ...]:
        return (SWIFT_EXTENSION,) if self.production else ()

    @property
    def territory(self) -> frozenset[str]:
        """The top folders the layout accounts for, taken out of the directory clustering."""
        return frozenset(
            PurePosixPath(root.package or root.directory).parts[0]
            for root in self.roots
            if root.package or root.directory
        )

    @property
    def mirrors(self) -> dict[str, str]:
        """Each test target's folder mapped to the folder of the target it tests."""
        mapped: dict[str, str] = {}
        for test in sorted(self.roots, key=lambda root: root.directory):
            if not test.target.is_test:
                continue
            tested = self._tested_by(test)
            if tested is not None:
                mapped[test.directory] = tested.directory
        return mapped

    def _tested_by(self, test: TargetRoot) -> TargetRoot | None:
        """The target *test* tests (see the module docstring)."""
        own = {root.target.name: root for root in self.production if root.package == test.package}
        name = test.target.name
        if name.endswith(_TEST_TARGET_SUFFIX) and name[: -len(_TEST_TARGET_SUFFIX)] in own:
            return own[name[: -len(_TEST_TARGET_SUFFIX)]]
        depended = {own[dep].directory: own[dep] for dep in test.target.dependencies if dep in own}
        return next(iter(depended.values())) if len(depended) == 1 else None


# --- Reading the tree --------------------------------------------------------


def _is_read(package: str) -> bool:
    """Whether the package in folder *package* is the project's own (see the docstring)."""
    parts = PurePosixPath(package).parts
    if parts and parts[0] in _SKIP_DIRS:
        return False
    return not any(part in _CLUSTER_SKIP or part in _RECURSIVE_SKIP for part in parts)


def _swift_files(project_root: Path, directory: str) -> tuple[str, ...]:
    folder = project_root / directory
    if not directory or not folder.is_dir():
        return ()
    return tuple(
        sorted(
            path.relative_to(project_root).as_posix()
            for path in folder.rglob(f"*{SWIFT_EXTENSION}")
            if path.is_file()
            and not any(
                part in _RECURSIVE_SKIP or part.startswith(".")
                for part in path.relative_to(folder).parts[:-1]
            )
        )
    )


def _roots(project_root: Path, package: SwiftPackage) -> Iterable[TargetRoot]:
    for target in package.targets:
        if target.directory is None or not (target.is_test or target.kind in _NODE_KINDS):
            continue
        files = _swift_files(project_root, target.directory)
        if files:
            yield TargetRoot(package.directory, target, files)


def read_swift_layout(project_root: Path) -> SwiftLayout:
    """Read every ``Package.swift`` of *project_root* and record each target's Swift files."""
    packages = SwiftPackages(project_root)
    roots = [
        root
        for package in packages.packages
        if _is_read(package.directory)
        for root in _roots(project_root, package)
    ]
    return SwiftLayout(tuple(roots), packages)


# --- Clusters ----------------------------------------------------------------


def _parent(directory: str) -> str:
    parent = PurePosixPath(directory).parent.as_posix()
    return "" if parent == "." else parent


def _entry(directory: str, roots: Iterable[TargetRoot], children: bool) -> ClusterEntry:
    kept = list(roots)
    return {
        "files": sorted(file for root in kept for file in root.files),
        "children": {root.target.name: list(root.files) for root in kept} if children else {},
        "source_dir": _parent(directory),
        "directory": directory,
        "child_directories": (
            {root.target.name: root.directory for root in kept} if children else {}
        ),
    }


def cluster_targets(layout: SwiftLayout, taken: Collection[str] = ()) -> dict[str, ClusterEntry]:
    """The clusters *layout*'s targets make, named apart from every name in *taken*."""
    names = RefIdAllocator(taken)
    clusters: dict[str, ClusterEntry] = {}
    by_package: dict[str, list[TargetRoot]] = {}
    for root in sorted(layout.production, key=lambda r: (r.package, r.directory)):
        by_package.setdefault(root.package, []).append(root)
    for package, roots in sorted(by_package.items()):
        if not package:
            for root in roots:
                name = names.take(root.target.name, qualifier=_TARGET_QUALIFIER)
                clusters[name] = _entry(root.directory, [root], children=False)
            continue
        name = names.take(package.replace("/", "-"), qualifier=_PACKAGE_QUALIFIER)
        clusters[name] = _entry(package, roots, children=True)
    return clusters
