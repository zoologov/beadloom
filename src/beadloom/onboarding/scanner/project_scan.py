"""Project structure discovery: dirs, manifests, clusters, project name."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

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
    from pathlib import Path


def scan_project(project_root: Path) -> dict[str, Any]:
    """Scan project structure and return summary.

    Returns dict with manifests, source_dirs, file_count, languages.

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
        if item.name.startswith("."):
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


def _cluster_with_children(
    project_root: Path,
    source_dirs: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Two-level directory scan for preset-aware bootstrap.

    Parameters
    ----------
    project_root:
        Root of the project.
    source_dirs:
        Discovered source directories.  When *None*, falls back to
        ``_SOURCE_DIRS`` for backwards compatibility.

    Returns dict of dir_name -> {files, children, source_dir} where
    children is a dict of child_name -> {files}.
    """
    result: dict[str, dict[str, Any]] = {}
    dirs_to_scan = source_dirs if source_dirs is not None else list(_SOURCE_DIRS)

    for src_dir_name in dirs_to_scan:
        src_dir = project_root / src_dir_name
        if not src_dir.is_dir():
            continue

        for sub in sorted(src_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("_"):
                continue
            if sub.name in _RECURSIVE_SKIP or sub.name in _CLUSTER_SKIP:
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
