"""Infer depends_on edges between clusters via a quick import scan."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.constants import _sanitize_ref_id

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.scanner.types import ClusterEntry

# Maximum number of import-based edges to avoid overwhelming the graph.
_MAX_IMPORT_EDGES = 50


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
                # Try to resolve the import path to a cluster.
                # Strategy: convert dotted import path to path segments
                # and check if any segment matches a cluster's directory name.
                parts = imp.import_path.replace(".", "/").split("/")
                for part in parts:
                    dst_ref_id = ref_by_sanitized_name.get(_sanitize_ref_id(part))
                    if dst_ref_id is not None and dst_ref_id != src_ref_id:
                        edge_key = (src_ref_id, dst_ref_id)
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            edges.append(
                                {
                                    "src": src_ref_id,
                                    "dst": dst_ref_id,
                                    "kind": "depends_on",
                                }
                            )
                            if len(edges) >= _MAX_IMPORT_EDGES:
                                return edges
                        break  # One match per import is enough.

    return edges
