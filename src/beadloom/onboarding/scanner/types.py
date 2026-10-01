"""Typed structures for project-scan results (replaces loose dicts)."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TypedDict


class ScanResult(TypedDict):
    """Result of :func:`scan_project` — discovered project structure.

    Same runtime shape as the prior ``dict[str, Any]``; the TypedDict only
    sharpens static typing for callers reading these keys.
    """

    manifests: list[str]
    source_dirs: list[str]
    file_count: int
    languages: list[str]


class _ClusterPlacement(TypedDict, total=False):
    """Where a cluster and its children sit, when that is not their names below ``source_dir``.

    The JVM package clusters (BDL-076 B6, :mod:`.jvm_layout`) set both: a package
    is named by its last segment and sits several folders below its source root,
    and a module's children sit under ``src/<set>/<language>/`` inside it.
    """

    directory: str
    child_directories: dict[str, str]


class ClusterEntry(_ClusterPlacement):
    """A two-level directory cluster (one top-level source subdirectory).

    Produced by :func:`_cluster_with_children`: ``files`` are all code files
    in the cluster (including those nested under ``children``), ``children``
    maps each child directory name to its own code-file list, and
    ``source_dir`` is the owning top-level source directory. Read a cluster's
    folder with :func:`cluster_directory` and a child's with
    :func:`child_directory`, never by joining the names.
    """

    files: list[str]
    children: dict[str, list[str]]
    source_dir: str


def cluster_directory(name: str, entry: ClusterEntry) -> str:
    """The project-relative folder of the cluster *name*."""
    return entry.get("directory", f"{entry['source_dir']}/{name}".strip("/"))


def child_directory(name: str, entry: ClusterEntry, child: str) -> str:
    """The project-relative folder of the child *child* of the cluster *name*."""
    placed = entry.get("child_directories", {})
    return placed.get(child, f"{cluster_directory(name, entry)}/{child}")
