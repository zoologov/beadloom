"""Infer depends_on edges between clusters via a quick import scan."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.go_modules import GoModules
from beadloom.onboarding.scanner.constants import _sanitize_ref_id

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.scanner.types import ClusterEntry

# Maximum number of import-based edges to avoid overwhelming the graph.
_MAX_IMPORT_EDGES = 50

_GO_EXTENSION = ".go"


def _cluster_by_directory(
    clusters: dict[str, ClusterEntry], cluster_refs: dict[str, str]
) -> dict[str, str]:
    """Each cluster's project-relative directory, mapped to the ref_id it was written under."""
    return {
        f"{info['source_dir']}/{name}".strip("/"): cluster_refs[name]
        for name, info in clusters.items()
    }


def _go_import_cluster(
    import_path: str, importer: str, modules: GoModules, by_directory: dict[str, str]
) -> str | None:
    """The cluster holding the package a Go import names, read through its module path.

    BDL-076 B5: the module path ``go.mod`` declares is stripped first (see
    :mod:`beadloom.graph.go_modules`), so ``cmd/<module-name>/`` — the standard
    layout — no longer takes every import whose module path ends in its name.
    The standard library and modules the project does not hold name no cluster.
    """
    directory = modules.package_directory(import_path, importer)
    if directory is None:
        return None
    holders = [d for d in by_directory if directory == d or directory.startswith(f"{d}/")]
    return by_directory[max(holders, key=len)] if holders else None


def _segment_cluster(import_path: str, src_ref_id: str, by_name: dict[str, str]) -> str | None:
    """The first cluster, other than the importer's, that a segment of *import_path* names."""
    for part in import_path.replace(".", "/").split("/"):
        dst_ref_id = by_name.get(_sanitize_ref_id(part))
        if dst_ref_id is not None and dst_ref_id != src_ref_id:
            return dst_ref_id
    return None


def _quick_import_scan(
    project_root: Path,
    clusters: dict[str, ClusterEntry],
    cluster_refs: dict[str, str],
) -> list[dict[str, str]]:
    """Quick import scan to infer depends_on edges between clusters.

    For each cluster, scans a sample of code files, extracts imports
    using import_resolver.extract_imports(), and maps them to other
    clusters to create depends_on edges.

    *cluster_refs* is the ref_id each cluster was WRITTEN under, keyed by cluster
    name. It is passed in rather than recomputed because a cluster is not always
    written under its own sanitized name since BDL-069: on the classic
    `src/<project>/` layout the root service takes the project name first and the
    package is written as `<project>-<kind>`. A recomputed name would then name
    no node, and the edge this function builds from it would be dropped by the
    loader exactly as quietly as the duplicate node it replaced (BDL-UX #214).

    Returns list of edge dicts: {src, dst, kind: "depends_on"}.
    """
    try:
        from beadloom.graph.import_resolver import extract_imports
    except ImportError:
        # tree-sitter or grammar packages not installed.
        return []

    # An import names a directory; the edge must name the node that directory
    # was written as. Where two cluster names sanitize to one string the first
    # wins, which is the same answer the membership test this map replaced gave.
    ref_by_sanitized_name: dict[str, str] = {}
    for name in clusters:
        ref_by_sanitized_name.setdefault(_sanitize_ref_id(name), cluster_refs[name])

    by_directory = _cluster_by_directory(clusters, cluster_refs)
    go_modules = GoModules(project_root)

    seen_edges: set[tuple[str, str]] = set()
    edges: list[dict[str, str]] = []

    for name, info in clusters.items():
        src_ref_id = cluster_refs[name]
        # Sample up to 10 code files per cluster.
        sample_files = info["files"][:10]

        for rel_path in sample_files:
            abs_path = project_root / rel_path
            if not abs_path.is_file():
                continue

            try:
                imports = extract_imports(abs_path)
            except Exception:  # noqa: S112
                # Unreadable file or tree-sitter error; skip.
                continue

            for imp in imports:
                # A Go import is read through its module path; any other import
                # by the first of its segments that names a cluster.
                if abs_path.suffix == _GO_EXTENSION:
                    dst_ref_id = _go_import_cluster(
                        imp.import_path, rel_path, go_modules, by_directory
                    )
                else:
                    dst_ref_id = _segment_cluster(
                        imp.import_path, src_ref_id, ref_by_sanitized_name
                    )
                if dst_ref_id is None or dst_ref_id == src_ref_id:
                    continue
                edge_key = (src_ref_id, dst_ref_id)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                edges.append({"src": src_ref_id, "dst": dst_ref_id, "kind": "depends_on"})
                if len(edges) >= _MAX_IMPORT_EDGES:
                    return edges

    return edges
