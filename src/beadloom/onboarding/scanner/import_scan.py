"""Infer depends_on edges between clusters via a quick import scan."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from beadloom.onboarding.scanner.constants import _sanitize_ref_id

if TYPE_CHECKING:
    from pathlib import Path

# Maximum number of import-based edges to avoid overwhelming the graph.
_MAX_IMPORT_EDGES = 50


def _quick_import_scan(
    project_root: Path,
    clusters: dict[str, dict[str, Any]],
    seen_ref_ids: set[str],
) -> list[dict[str, str]]:
    """Quick import scan to infer depends_on edges between clusters.

    For each cluster, scans a sample of code files, extracts imports
    using import_resolver.extract_imports(), and maps them to other
    clusters to create depends_on edges.

    Returns list of edge dicts: {src, dst, kind: "depends_on"}.
    """
    try:
        from beadloom.graph.import_resolver import extract_imports
    except ImportError:
        # tree-sitter or grammar packages not installed.
        return []

    # Build a mapping: relative file path -> cluster ref_id.
    file_to_cluster: dict[str, str] = {}
    for name, info in clusters.items():
        ref_id = _sanitize_ref_id(name)
        for fpath in info["files"]:
            file_to_cluster[fpath] = ref_id

    # Build set of known cluster ref_ids for fast lookup.
    cluster_ref_ids: set[str] = {_sanitize_ref_id(n) for n in clusters}

    seen_edges: set[tuple[str, str]] = set()
    edges: list[dict[str, str]] = []

    for name, info in clusters.items():
        src_ref_id = _sanitize_ref_id(name)
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
                # and check if any segment matches a cluster ref_id.
                parts = imp.import_path.replace(".", "/").split("/")
                for part in parts:
                    sanitized_part = _sanitize_ref_id(part)
                    if (
                        sanitized_part in cluster_ref_ids
                        and sanitized_part in seen_ref_ids
                        and sanitized_part != src_ref_id
                    ):
                        edge_key = (src_ref_id, sanitized_part)
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            edges.append(
                                {
                                    "src": src_ref_id,
                                    "dst": sanitized_part,
                                    "kind": "depends_on",
                                }
                            )
                            if len(edges) >= _MAX_IMPORT_EDGES:
                                return edges
                        break  # One match per import is enough.

    return edges
