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


class ClusterEntry(TypedDict):
    """A two-level directory cluster (one top-level source subdirectory).

    Produced by :func:`_cluster_with_children`: ``files`` are all code files
    in the cluster (including those nested under ``children``), ``children``
    maps each child directory name to its own code-file list, and
    ``source_dir`` is the owning top-level source directory.
    """

    files: list[str]
    children: dict[str, list[str]]
    source_dir: str
