"""The JVM source-set layout of a project: its modules, source roots, test trees and packages.

BDL-076 B6 (``beadloom-ujzb.15``). Maven and Gradle keep code in
``<module>/src/<set>/<language>/<package path>/``. Until this module ``init`` read
that tree as plain folders: it made nodes of ``src/main``, ``src/main/java`` and
``src/test``, wrote ``scan_paths: [src]`` — under which a dotted import is looked
up at ``src/org/...``, where no code is — and made no node of any package. The
rules below are what replaced that reading.

- **A module** is a folder — the project root or one below it — holding
  ``src/<set>/<language>/`` with a Java or Kotlin file in it. ``<language>`` is
  ``java`` or ``kotlin``, the two JVM languages the indexer parses; a Scala or
  Groovy tree holds nothing it reads and is no source root. Modules are found by
  walking the tree, not by parsing ``settings.gradle(.kts)`` ``include`` or a parent
  ``pom.xml``'s ``<modules>``: a declared module in the standard layout is found
  whether or not its declaration can be parsed (a Groovy closure, a ``projectDir``
  override). The walk skips the top-level folders the project scan skips
  (``tests``, ``docs``, ``build`` ...), hidden folders, build outputs and fixtures
  at any depth, and never enters a ``src`` folder.
- **A source set is a test set** when a word of its camel-case name is ``test``
  or ``tests`` (``test``, ``integrationTest``, ``testFixtures``, ``androidTest``)
  or it is Failsafe's ``it``. Every other set (``main``, ``commonMain``, ``debug``)
  is production. Production roots are the project's scan paths; a test root is
  never a node and never a scan path. It is mirrored to its module's production
  root of the same language, else to the module's ``main`` set, else to its first
  production root, so its tests bind to the package they test; a module with test
  sources only has nothing to mirror.
- **The base package** of a module is where its packages part: from the source
  roots down, the folder that holds code itself or does not have exactly one
  subfolder, read over the union of the module's production roots. A shared
  ``org/example/<project>/`` prefix is therefore no node per segment.
- **Packages are clustered two levels below the root**, the depth the directory
  clustering of every other stack keeps. In the root module the top-level
  packages (the base package's subpackages) are the clusters and their own
  subpackages the children, deeper ones folded into those; when the base package
  holds code it is the one cluster and the top-level packages its children. A
  single-package project is that one package. A module below the root is one
  cluster, named by its path, and its top-level packages — with the base package
  when that holds code — are its children.
- **A package split across two roots** of one module (``java`` and ``kotlin``) is
  one cluster per root; the first root by precedence (the ``main`` set, then the
  others; ``java`` before ``kotlin``) keeps the package's name, and the next is
  qualified by its set and language (``shared-main-kotlin``).

Pure apart from :func:`read_jvm_layout`, which walks the tree once and records
every code file, so the clustering and the import mapping read no file.
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.constants import _CLUSTER_SKIP, _RECURSIVE_SKIP, _SKIP_DIRS

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from pathlib import Path

    from beadloom.onboarding.scanner.types import ClusterEntry

#: The language folders of a source set whose code the indexer parses.
JVM_LANGUAGES = ("java", "kotlin")
#: The file extensions of that code.
JVM_EXTENSIONS = frozenset({".java", ".kt"})

#: The folder every source set lives in, below its module.
_SOURCE_FOLDER = "src"
#: The production set Maven and Gradle create by default.
_MAIN_SET = "main"
#: The words of a set name that make it a test set, and Failsafe's own set name.
_TEST_WORDS = frozenset({"test", "tests"})
_FAILSAFE_SET = "it"
_CAMEL_WORD = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])")


def is_test_set(name: str) -> bool:
    """Whether the source set *name* holds test code (see the module docstring)."""
    words = {word.lower() for word in _CAMEL_WORD.findall(name)}
    return name == _FAILSAFE_SET or bool(words & _TEST_WORDS)


@dataclass(frozen=True)
class SourceRoot:
    """One ``<module>/src/<set>/<language>`` folder and the code files under it."""

    module: str
    source_set: str
    language: str
    files: tuple[str, ...]

    @property
    def path(self) -> str:
        """The root's project-relative path."""
        parts = (self.module, _SOURCE_FOLDER, self.source_set, self.language)
        return "/".join(part for part in parts if part)

    @property
    def is_test(self) -> bool:
        return is_test_set(self.source_set)

    @property
    def qualifier(self) -> str:
        """What tells this root apart from another of its module: ``<set>-<language>``."""
        return f"{self.source_set}-{self.language}"

    @property
    def precedence(self) -> tuple[bool, str, str]:
        """The order roots of one module are read in: ``main`` first, ``java`` first."""
        return (self.source_set != _MAIN_SET, self.source_set, self.language)


@dataclass(frozen=True)
class JvmLayout:
    """Every JVM source root of a project, test and production; empty when it has none."""

    roots: tuple[SourceRoot, ...] = ()

    @property
    def production_roots(self) -> tuple[str, ...]:
        """The production roots' paths, sorted: the project's JVM scan paths."""
        return tuple(sorted(root.path for root in self.production))

    @property
    def test_roots(self) -> tuple[str, ...]:
        return tuple(sorted(root.path for root in self.roots if root.is_test))

    @property
    def modules(self) -> tuple[str, ...]:
        """Every module with a source root, ``""`` for the project root, sorted."""
        return tuple(sorted({root.module for root in self.roots}))

    @property
    def territory(self) -> frozenset[str]:
        """The top-level folders the layout accounts for: ``src`` for the root module."""
        return frozenset(
            PurePosixPath(module).parts[0] if module else _SOURCE_FOLDER for module in self.modules
        )

    @property
    def mirrors(self) -> dict[str, str]:
        """Each test root mapped to the production root its tests bind to."""
        mapped: dict[str, str] = {}
        for test_root in sorted(self.roots, key=lambda root: root.path):
            if not test_root.is_test:
                continue
            code_root = _mirrored_root(test_root, self.production_of(test_root.module))
            if code_root is not None:
                mapped[test_root.path] = code_root.path
        return mapped

    def production_of(self, module: str) -> tuple[SourceRoot, ...]:
        """*module*'s production roots in precedence order."""
        return tuple(
            sorted(
                (root for root in self.production if root.module == module),
                key=lambda root: root.precedence,
            )
        )

    @property
    def production(self) -> tuple[SourceRoot, ...]:
        """The production roots themselves, in path order."""
        return tuple(root for root in self.roots if not root.is_test)

    @cached_property
    def package_directories(self) -> frozenset[str]:
        """Every folder under a production root that holds code itself."""
        return frozenset(
            PurePosixPath(file).parent.as_posix()
            for root in self.production
            for file in root.files
        )


def _mirrored_root(test_root: SourceRoot, production: tuple[SourceRoot, ...]) -> SourceRoot | None:
    """The production root *test_root*'s tests bind to (see the module docstring)."""
    same_language = [root for root in production if root.language == test_root.language]
    main_set = [root for root in production if root.source_set == _MAIN_SET]
    for candidates in (same_language, main_set, list(production)):
        if candidates:
            return candidates[0]
    return None


# --- Reading the tree --------------------------------------------------------


def read_jvm_layout(project_root: Path) -> JvmLayout:
    """Walk *project_root* for JVM modules and record every source root and its code."""
    roots: list[SourceRoot] = []
    pending = [project_root]
    while pending:
        folder = pending.pop()
        module = "" if folder == project_root else folder.relative_to(project_root).as_posix()
        roots.extend(_source_roots(project_root, module, folder / _SOURCE_FOLDER))
        pending.extend(
            child
            for child in sorted(folder.iterdir(), reverse=True)
            if _is_walked(child, top_level=folder == project_root)
        )
    return JvmLayout(tuple(sorted(roots, key=lambda root: root.path)))


def _is_walked(folder: Path, *, top_level: bool) -> bool:
    """Whether the module walk enters *folder*."""
    name = folder.name
    if not folder.is_dir() or folder.is_symlink() or name.startswith("."):
        return False
    if name == _SOURCE_FOLDER or name in _RECURSIVE_SKIP or name in _CLUSTER_SKIP:
        return False
    return not (top_level and name in _SKIP_DIRS)


def _source_roots(project_root: Path, module: str, source: Path) -> Iterable[SourceRoot]:
    if not source.is_dir():
        return
    for source_set in sorted(source.iterdir()):
        if not source_set.is_dir() or source_set.name.startswith("."):
            continue
        for language in JVM_LANGUAGES:
            files = _code_files(project_root, source_set / language)
            if files:
                yield SourceRoot(module, source_set.name, language, files)


def _code_files(project_root: Path, folder: Path) -> tuple[str, ...]:
    if not folder.is_dir():
        return ()
    return tuple(
        sorted(
            path.relative_to(project_root).as_posix()
            for path in folder.rglob("*")
            if path.suffix in JVM_EXTENSIONS
            and path.is_file()
            and not _RECURSIVE_SKIP.intersection(path.relative_to(folder).parts)
        )
    )


# --- Packages ----------------------------------------------------------------


def _package_of(root: SourceRoot, file: str) -> str:
    """The package folder of *file* relative to *root*, ``""`` for the default package."""
    relative = PurePosixPath(file).parent.relative_to(root.path).as_posix()
    return "" if relative == "." else relative


def _join(*parts: str) -> str:
    return "/".join(part for part in parts if part)


def _below(path: str, folder: str) -> str | None:
    """*path* relative to *folder* when it lies strictly below it, else ``None``."""
    if not folder:
        return path or None
    return path[len(folder) + 1 :] if path.startswith(f"{folder}/") else None


def _base_package(roots: tuple[SourceRoot, ...]) -> str:
    """Where the packages of *roots* part (see the module docstring)."""
    packages = {_package_of(root, file) for root in roots for file in root.files}
    base = ""
    while base not in packages:
        subfolders = {
            rest.split("/", 1)[0]
            for rest in (_below(package, base) for package in packages)
            if rest is not None
        }
        if len(subfolders) != 1:
            break
        base = _join(base, subfolders.pop())
    return base


@dataclass(frozen=True)
class _Package:
    """One package folder under one source root, with every code file at or below it."""

    root: SourceRoot
    path: str
    files: tuple[str, ...]

    @property
    def directory(self) -> str:
        return _join(self.root.path, self.path)

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).name if self.path else self.root.qualifier

    @property
    def own_files(self) -> list[str]:
        """The files of this package itself, without those of its subpackages."""
        return [file for file in self.files if _package_of(self.root, file) == self.path]

    def holds_code_itself(self) -> bool:
        return bool(self.own_files)

    def subpackages(self) -> list[_Package]:
        """The packages one level below this one, each with the files at or below it."""
        names = sorted(
            {
                rest.split("/", 1)[0]
                for rest in (_below(_package_of(self.root, f), self.path) for f in self.files)
                if rest is not None
            }
        )
        return [self._narrowed(_join(self.path, name)) for name in names]

    def _narrowed(self, path: str) -> _Package:
        prefix = f"{_join(self.root.path, path)}/"
        return _Package(self.root, path, tuple(f for f in self.files if f.startswith(prefix)))


def _base_packages(roots: tuple[SourceRoot, ...]) -> list[_Package]:
    """Each root's base package that holds any code, in the roots' precedence order."""
    base = _base_package(roots)
    found = [root_package._narrowed(base) for root_package in _whole(roots)]
    return [package for package in found if package.files]


def _whole(roots: tuple[SourceRoot, ...]) -> list[_Package]:
    return [_Package(root, "", root.files) for root in roots]


def _claim(preferred: str, qualifier: str, names: set[str]) -> str:
    """*preferred*, or a qualified form of it no earlier claim holds."""
    candidate = preferred if preferred not in names else f"{preferred}-{qualifier}"
    suffix = 2
    while candidate in names:
        candidate = f"{preferred}-{qualifier}-{suffix}"
        suffix += 1
    names.add(candidate)
    return candidate


def _entry(
    directory: str, source_dir: str, files: Iterable[str], children: Iterable[tuple[str, _Package]]
) -> ClusterEntry:
    kept = list(children)
    return {
        "files": sorted(files),
        "children": {name: list(package.files) for name, package in kept},
        "source_dir": source_dir,
        "directory": directory,
        "child_directories": {name: package.directory for name, package in kept},
    }


def _named(packages: Iterable[_Package]) -> list[tuple[str, _Package]]:
    """*packages* under unique names, the first by precedence keeping the plain one."""
    names: set[str] = set()
    return [(_claim(package.name, package.root.qualifier, names), package) for package in packages]


def _root_module_clusters(
    roots: tuple[SourceRoot, ...], names: set[str]
) -> dict[str, ClusterEntry]:
    """The root module's clusters: its top-level packages, or its base package over them."""
    bases = _base_packages(roots)
    tops = [sub for base in bases for sub in base.subpackages()]
    holding = [base for base in bases if base.holds_code_itself()]
    clusters: dict[str, ClusterEntry] = {}
    if not holding:
        for top in tops:
            name = _claim(top.name, top.root.qualifier, names)
            clusters[name] = _entry(
                top.directory, top.root.path, top.files, _named(top.subpackages())
            )
        return clusters
    # The base package holds code, so it is the cluster and the top-level packages
    # its children. A second root holding code in the same package keeps that code.
    first, *others = holding
    files = [*first.own_files, *(file for top in tops for file in top.files)]
    name = _claim(first.name, first.root.qualifier, names)
    clusters[name] = _entry(first.directory, first.root.path, files, _named(tops))
    for other in others:
        name = _claim(other.name, other.root.qualifier, names)
        clusters[name] = _entry(other.directory, other.root.path, other.own_files, ())
    return clusters


def _module_cluster(module: str, roots: tuple[SourceRoot, ...]) -> ClusterEntry:
    """A module below the root as one cluster, its top-level packages the children."""
    bases = _base_packages(roots)
    children = [
        *(base for base in bases if base.holds_code_itself()),
        *(sub for base in bases for sub in base.subpackages()),
    ]
    files = [f for root in roots for f in root.files]
    parent = PurePosixPath(module).parent.as_posix()
    return _entry(module, "" if parent == "." else parent, files, _named(children))


def cluster_packages(layout: JvmLayout, taken: Collection[str] = ()) -> dict[str, ClusterEntry]:
    """The clusters *layout*'s packages make, named apart from every name in *taken*."""
    names = set(taken)
    clusters: dict[str, ClusterEntry] = {}
    for module in layout.modules:
        roots = layout.production_of(module)
        if not roots:
            continue
        if not module:
            clusters.update(_root_module_clusters(roots, names))
            continue
        name = _claim(module.replace("/", "-"), "module", names)
        clusters[name] = _module_cluster(module, roots)
    return clusters


# --- Imports -----------------------------------------------------------------


def jvm_package_directory(import_path: str, layout: JvmLayout) -> str | None:
    """The project folder of the package a Java or Kotlin import names, if the project has it.

    The import is read as a package path under every production root, and the
    longest prefix of it that is a folder holding code is the package: a class,
    a member of a static import and a wildcard all sit below it. A third-party
    import names no such folder, even where a segment of it names one of the
    project's packages (``org.springframework.web`` beside a package ``web``).
    Where two roots hold the package, the deeper match wins, then the root read first.
    """
    segments = [part for part in import_path.split(".") if part and part != "*"]
    best: tuple[int, str] | None = None
    for root in sorted(layout.production, key=lambda r: (r.module, r.precedence)):
        for depth in range(len(segments), 0, -1):
            candidate = _join(root.path, *segments[:depth])
            if candidate in layout.package_directories:
                if best is None or depth > best[0]:
                    best = (depth, candidate)
                break
    return None if best is None else best[1]
