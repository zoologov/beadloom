"""Project structure discovery: dirs, manifests, clusters, project name."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.constants import (
    _CLUSTER_SKIP,
    _CODE_EXTENSIONS,
    _MANIFESTS,
    _RECURSIVE_SKIP,
    _SKIP_DIRS,
    _SOURCE_DIRS,
    _is_in_skip_dir,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from pathlib import Path

    from beadloom.onboarding.scanner.types import ClusterEntry, ScanResult


def generated_portals(project_root: Path, is_portal: Callable[[Path], bool]) -> tuple[str, ...]:
    """The top-level folders of *project_root* holding the portal ``docs site`` wrote, sorted.

    *is_portal* decides, and is the scaffold's own marker test in production (the
    re-review's finding m4): this domain cannot read the scaffold, which lives in
    the application layer. A portal written below a top-level folder is not looked
    for.
    """
    return tuple(
        item.name
        for item in sorted(project_root.iterdir())
        if item.is_dir() and not item.name.startswith(".") and is_portal(item)
    )


def unscanned_portals_sentence(portals: Collection[str]) -> str:
    """What ``init`` says about the *portals* it did not scan; ``""`` when there are none."""
    if not portals:
        return ""
    named = ", ".join(f"{portal}/" for portal in portals)
    return (
        f"Not scanned: {named} - holds the portal `beadloom docs site` wrote (its files "
        "carry the generated marker), which is output, not the project's code"
    )


def scan_project(project_root: Path, *, skip: Collection[str] = ()) -> ScanResult:
    """Scan project structure and return summary.

    Returns dict with manifests, source_dirs, file_count, languages.

    A top-level folder named in *skip* is not read at all: a portal ``beadloom docs
    site`` wrote is output, not the project's code (:func:`generated_portals`).

    Discovery strategy (both passes always run, results merged):
    1. **Pass 1:** directories matching ``_SOURCE_DIRS`` (known names).
    2. **Pass 2:** all non-hidden, non-vendor, non-test directories that
       contain code files — catches ``components/``, ``hooks/``, etc.
    """
    manifests: list[str] = []
    file_count = 0
    extensions: set[str] = set()

    # Pass 1: known source dirs.
    known_dirs: list[str] = []
    # Pass 2 candidates: non-hidden, non-skip, non-known dirs.
    other_dirs: list[str] = []

    for item in sorted(project_root.iterdir()):
        if item.name.startswith(".") or item.name in skip:
            continue
        if item.is_file() and item.name in _MANIFESTS:
            manifests.append(item.name)
        if item.is_dir():
            if item.name in _SOURCE_DIRS:
                known_dirs.append(item.name)
                for f in item.rglob("*"):
                    if (
                        f.is_file()
                        and f.suffix in _CODE_EXTENSIONS
                        and not _is_in_skip_dir(f, item)
                    ):
                        file_count += 1
                        extensions.add(f.suffix)
            elif item.name not in _SKIP_DIRS:
                other_dirs.append(item.name)

    # Pass 2: always scan non-known dirs for code files (not just as fallback).
    code_dirs: list[str] = []
    for dir_name in other_dirs:
        dir_path = project_root / dir_name
        count = 0
        for f in dir_path.rglob("*"):
            if f.is_file() and f.suffix in _CODE_EXTENSIONS and not _is_in_skip_dir(f, dir_path):
                count += 1
                extensions.add(f.suffix)
        if count > 0:
            code_dirs.append(dir_name)
            file_count += count

    # Merge + deduplicate (sorted for deterministic output).
    source_dirs = sorted(set(known_dirs + code_dirs))

    return {
        "manifests": manifests,
        "source_dirs": source_dirs,
        "file_count": file_count,
        "languages": sorted(extensions),
    }


def _cluster_by_dirs(
    project_root: Path,
    source_dirs: list[str] | None = None,
) -> dict[str, list[str]]:
    """Cluster source files by top-level subdirectories.

    Parameters
    ----------
    project_root:
        Root of the project.
    source_dirs:
        Discovered source directories.  When *None*, falls back to
        ``_SOURCE_DIRS`` for backwards compatibility.

    Returns dict of dir_name -> list of code file paths (relative).
    """
    clusters: dict[str, list[str]] = {}
    dirs_to_scan = source_dirs if source_dirs is not None else list(_SOURCE_DIRS)

    for src_dir_name in dirs_to_scan:
        src_dir = project_root / src_dir_name
        if not src_dir.is_dir():
            continue

        for sub in sorted(src_dir.iterdir()):
            if (
                sub.is_dir()
                and not sub.name.startswith("_")
                and sub.name not in _RECURSIVE_SKIP
                and sub.name not in _CLUSTER_SKIP
            ):
                files = []
                for f in sub.rglob("*"):
                    if (
                        f.is_file()
                        and f.suffix in _CODE_EXTENSIONS
                        and not _is_in_skip_dir(f, sub)
                    ):
                        files.append(str(f.relative_to(project_root)))
                if files:
                    clusters[sub.name] = files

    return clusters


def is_claimed(path: str, claimed: Collection[str]) -> bool:
    """Whether the project-relative *path* is one of the *claimed* folders or lies below one."""
    return any(path == folder or path.startswith(f"{folder}/") for folder in claimed)


def _holds_code(folder: Path) -> bool:
    """Whether *folder* holds a code file the project scan counts."""
    return any(
        f.is_file() and f.suffix in _CODE_EXTENSIONS and not _is_in_skip_dir(f, folder)
        for f in folder.rglob("*")
    )


@dataclass(frozen=True)
class UnclaimedCode:
    """The scan paths left around the claimed folders, and the code no scan path can hold.

    ``loose_files`` are code files lying directly in a folder that was split around a
    claimed one: a scan path is a folder, and that folder would hold the claim too.
    """

    folders: tuple[str, ...] = ()
    loose_files: tuple[str, ...] = ()


def unclaimed_code(
    project_root: Path, folders: list[str], claimed: Collection[str]
) -> UnclaimedCode:
    """*folders* without the *claimed* ones, as scan paths that never overlap.

    A folder with no claimed folder below it is kept whole. One that holds a
    claimed folder is replaced by its subfolders that hold code, each read the
    same way, so a Python service beside a Maven module in ``services/`` is
    scanned and the module — whose production roots are scan paths of their
    own, and whose test tree must stay out — is not scanned a second time. A
    code file lying directly in such a folder, beside the module, can be in no
    scan path, and is returned as a loose file so that ``init`` names it
    (the re-review's finding m3) instead of dropping it in silence.
    """
    kept: list[str] = []
    loose: list[str] = []
    for folder in folders:
        if is_claimed(folder, claimed):
            continue
        if not any(other.startswith(f"{folder}/") for other in claimed):
            kept.append(folder)
            continue
        children = sorted((project_root / folder).iterdir())
        loose.extend(
            f"{folder}/{child.name}"
            for child in children
            if child.is_file() and child.suffix in _CODE_EXTENSIONS
        )
        subfolders = [
            f"{folder}/{child.name}"
            for child in children
            if child.is_dir()
            and not child.name.startswith(".")
            and child.name not in _RECURSIVE_SKIP
            and _holds_code(child)
        ]
        below = unclaimed_code(project_root, subfolders, claimed)
        kept.extend(below.folders)
        loose.extend(below.loose_files)
    return UnclaimedCode(tuple(kept), tuple(loose))


def unclaimed_folders(
    project_root: Path, folders: list[str], claimed: Collection[str]
) -> list[str]:
    """The scan paths of :func:`unclaimed_code`."""
    return list(unclaimed_code(project_root, folders, claimed).folders)


#: How many unread files ``init`` names before it only counts the rest.
_NAMED_FILES = 5


@dataclass(frozen=True)
class CodeBesideModules:
    """The code beside a module's or a package's source roots, and what ``init`` says of it.

    ``scanned`` are folders inside a module's own folder and outside the folders its
    layout reads (``backend/scripts`` beside ``backend/src``): each is a scan path,
    and its files belong to the module's node, the deepest node whose folder holds
    them. ``unread`` are the loose files of :class:`UnclaimedCode`.
    """

    scanned: tuple[str, ...] = ()
    unread: tuple[str, ...] = ()

    def sentences(self) -> list[str]:
        """What ``init`` says about this code: nothing when there is none."""
        said: list[str] = []
        if self.scanned:
            said.append(
                f"Also scanned: {', '.join(self.scanned)} - code in a module's folder outside "
                "its source roots; its files belong to that module's node"
            )
        if self.unread:
            said.append(self._unread_sentence())
        return said

    def _unread_sentence(self) -> str:
        count = len(self.unread)
        if count == 1:
            return (
                f"Not read: {self.unread[0]} - a code file lying directly in a folder that "
                "holds a module; a scan path is a folder, and that one would scan the "
                "module's test tree too, so move the file into a folder of its own to have "
                "it read"
            )
        named = ", ".join(self.unread[:_NAMED_FILES])
        rest = count - _NAMED_FILES
        more = f" and {rest} more" if rest > 0 else ""
        return (
            f"Not read: {count} code files lying directly in folders that hold a module "
            f"({named}{more}) - a scan path is a folder, and those would scan the module's "
            "test tree too, so move the files into a folder of their own to have them read"
        )


def _cluster_with_children(
    project_root: Path,
    source_dirs: list[str] | None = None,
    *,
    claimed: Collection[str] = (),
) -> dict[str, ClusterEntry]:
    """Two-level directory scan for preset-aware bootstrap.

    Parameters
    ----------
    project_root:
        Root of the project.
    source_dirs:
        Discovered source directories.  When *None*, falls back to
        ``_SOURCE_DIRS`` for backwards compatibility.
    claimed:
        Project-relative folders another reading accounts for (a JVM module, a
        Swift package or target). None of them, and no file below one, is part
        of a cluster here; their siblings are.

    Returns dict of dir_name -> {files, children, source_dir} where
    children is a dict of child_name -> {files}.
    """
    result: dict[str, ClusterEntry] = {}
    dirs_to_scan = source_dirs if source_dirs is not None else list(_SOURCE_DIRS)

    def _rel(path: Path) -> str:
        return path.relative_to(project_root).as_posix()

    for src_dir_name in dirs_to_scan:
        src_dir = project_root / src_dir_name
        if not src_dir.is_dir():
            continue

        for sub in sorted(src_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("_"):
                continue
            if sub.name in _RECURSIVE_SKIP or sub.name in _CLUSTER_SKIP:
                continue
            if claimed and is_claimed(_rel(sub), claimed):
                continue

            files: list[str] = []
            children: dict[str, list[str]] = {}

            for item in sorted(sub.iterdir()):
                if item.is_file() and item.suffix in _CODE_EXTENSIONS:
                    files.append(str(item.relative_to(project_root)))
                elif item.is_dir() and not item.name.startswith("_"):
                    if item.name in _RECURSIVE_SKIP or item.name in _CLUSTER_SKIP:
                        continue
                    child_files = []
                    for f in item.rglob("*"):
                        if (
                            f.is_file()
                            and f.suffix in _CODE_EXTENSIONS
                            and not _is_in_skip_dir(f, item)
                            and not (claimed and is_claimed(_rel(f), claimed))
                        ):
                            child_files.append(str(f.relative_to(project_root)))
                    if child_files:
                        children[item.name] = child_files
                        files.extend(child_files)

            if files:
                result[sub.name] = {
                    "files": files,
                    "children": children,
                    "source_dir": src_dir_name,
                }

    return result


def _read_manifest_deps(package_dir: Path) -> list[str]:
    """Read internal dependency names from a package manifest.

    Supports package.json workspace/file/link dependencies.
    Returns only names that look like local/workspace packages.
    """
    deps: list[str] = []

    pkg_json = package_dir / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            for key in ("dependencies", "devDependencies"):
                for dep_name, ver in (data.get(key) or {}).items():
                    if isinstance(ver, str) and (
                        ver.startswith("workspace:")
                        or ver.startswith("file:")
                        or ver.startswith("link:")
                    ):
                        clean = dep_name.split("/")[-1]
                        deps.append(clean)
        except (json.JSONDecodeError, KeyError):
            pass

    return deps


def _detect_project_name(project_root: Path) -> str:
    """Detect project name from manifest files or directory name.

    Checks (in order): pyproject.toml, package.json, go.mod, Cargo.toml.
    Falls back to the directory name.
    """
    # pyproject.toml — [project] or [tool.poetry] name.
    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if match:
            return match.group(1)

    # package.json.
    pkg_json = project_root / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            name = data.get("name", "")
            if name:
                # Handle scoped packages: @org/name → name.
                return str(name).split("/")[-1]
        except (json.JSONDecodeError, KeyError):
            pass

    # go.mod.
    go_mod = project_root / "go.mod"
    if go_mod.is_file():
        text = go_mod.read_text(encoding="utf-8")
        match = re.search(r"^module\s+(\S+)", text, re.MULTILINE)
        if match:
            # Handle full paths: github.com/org/name → name.
            return match.group(1).split("/")[-1]

    # Cargo.toml.
    cargo = project_root / "Cargo.toml"
    if cargo.is_file():
        text = cargo.read_text(encoding="utf-8")
        match = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if match:
            return match.group(1)

    # Fallback: directory name.
    return project_root.name
