"""Documentation skeleton generator from knowledge graph."""

# beadloom:domain=onboarding

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def _load_graph_from_yaml(
    project_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load all graph nodes and edges from ``.beadloom/_graph/*.yml``."""
    import yaml

    graph_dir = project_root / ".beadloom" / "_graph"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for yml in sorted(graph_dir.glob("*.yml")):
        if yml.name == "rules.yml":
            continue
        data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        if data:
            nodes.extend(data.get("nodes", []))
            edges.extend(data.get("edges", []))
    return nodes, edges


def _generate_mermaid(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> str:
    """Generate a Mermaid ``graph LR`` block from *edges*.

    Only ``part_of`` and ``depends_on`` edge kinds are included.
    ``depends_on`` renders as ``-->``, ``part_of`` as ``.->`` (dotted).
    """
    lines: list[str] = []
    for edge in edges:
        kind = edge.get("kind", "")
        src = edge.get("src", "")
        dst = edge.get("dst", "")
        if kind == "depends_on":
            lines.append(f"  {src} --> {dst}")
        elif kind == "part_of":
            lines.append(f"  {src} -.-> {dst}")
    return "\n".join(lines)


def _write_if_missing(path: Path, content: str) -> bool:
    """Write *content* to *path* only if the file does not yet exist.

    Returns ``True`` when a new file was created, ``False`` when skipped.
    """
    if path.exists():
        logger.debug("Skipping existing file: %s", path)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("Created: %s", path)
    return True


def _find_root_node(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the root service node.

    Root = service node that has no ``part_of`` edge as *src*
    (i.e. it is not a child of any other node).
    """
    part_of_srcs = {e["src"] for e in edges if e.get("kind") == "part_of"}
    for node in nodes:
        if node.get("kind") == "service" and node["ref_id"] not in part_of_srcs:
            return node
    return None


def _edges_for(
    ref_id: str,
    edges: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Return (depends_on, used_by) lists for a given *ref_id*.

    Excludes ``part_of`` edges — those are structural, not dependency.
    """
    depends_on: list[str] = []
    used_by: list[str] = []
    for edge in edges:
        if edge.get("kind") == "part_of":
            continue
        if edge.get("src") == ref_id:
            depends_on.append(edge.get("dst", ""))
        if edge.get("dst") == ref_id:
            used_by.append(edge.get("src", ""))
    return depends_on, used_by


def _children_of(
    ref_id: str,
    edges: list[dict[str, Any]],
) -> list[str]:
    """Return ref_ids of nodes that are ``part_of`` *ref_id*."""
    return [
        edge["src"]
        for edge in edges
        if edge.get("kind") == "part_of" and edge.get("dst") == ref_id
    ]


def _parent_of(
    ref_id: str,
    edges: list[dict[str, Any]],
) -> str | None:
    """Return the parent ref_id (via ``part_of`` edge) for *ref_id*."""
    for edge in edges:
        if edge.get("kind") == "part_of" and edge.get("src") == ref_id:
            return edge.get("dst", "")
    return None


# ------------------------------------------------------------------
# Path resolution
# ------------------------------------------------------------------


def _doc_path_for_node(
    node: dict[str, Any],
    edges: list[dict[str, Any]],
    project_root: Path,
) -> Path | None:
    """Determine the correct doc path for a node.

    Priority: ``docs:`` field from graph node > convention-based fallback.
    Returns ``None`` when no path can be determined.
    """
    from pathlib import Path as _Path

    # Explicit docs field — use the first entry.
    docs_field: list[str] = node.get("docs", [])
    if docs_field:
        return _Path(project_root) / docs_field[0]

    kind = node.get("kind", "")
    ref_id: str = node["ref_id"]
    docs_dir = _Path(project_root) / "docs"

    if kind == "domain":
        return docs_dir / "domains" / ref_id / "README.md"
    if kind == "service":
        return docs_dir / "services" / f"{ref_id}.md"
    if kind == "feature":
        parent = _parent_of(ref_id, edges)
        if parent:
            return docs_dir / "domains" / parent / "features" / ref_id / "SPEC.md"
        return docs_dir / "features" / ref_id / "SPEC.md"
    return None


# ------------------------------------------------------------------
# Symbols (best-effort from SQLite)
# ------------------------------------------------------------------


def _load_symbols_by_source(project_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Load code symbols from SQLite grouped by file path.

    Returns empty dict when no database exists or the table is missing.
    """
    from pathlib import Path as _Path

    db_path = _Path(project_root) / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        return {}

    import sqlite3

    symbols_by_source: dict[str, list[dict[str, Any]]] = {}
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT symbol_name, kind, file_path, line_start, line_end FROM code_symbols"
        ).fetchall()
        for row in rows:
            fp: str = row["file_path"]
            symbols_by_source.setdefault(fp, []).append(dict(row))
        conn.close()
    except sqlite3.OperationalError:
        pass
    return symbols_by_source


def _symbols_for_node(
    node: dict[str, Any],
    symbols_by_source: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Return code symbols whose file path starts with *node*'s source."""
    source = node.get("source", "").rstrip("/")
    if not source:
        return []
    result: list[dict[str, Any]] = []
    for fp, syms in symbols_by_source.items():
        if fp.startswith(source):
            result.extend(syms)
    return result


def _render_symbols_section(symbols: list[dict[str, Any]]) -> str:
    """Render a ``## Public API`` markdown table from *symbols*.

    Filters out private symbols (leading ``_``) and deduplicates.
    Returns empty string when no public symbols are found.
    """
    if not symbols:
        return ""
    public: list[dict[str, Any]] = []
    seen: set[str] = set()
    for s in symbols:
        name = s.get("symbol_name", "")
        if name.startswith("_") or name in seen:
            continue
        seen.add(name)
        public.append(s)
    if not public:
        return ""
    lines = [
        "## Public API\n",
        "| Symbol | Kind |",
        "|--------|------|",
    ]
    for s in sorted(public, key=lambda x: x.get("symbol_name", "")):
        lines.append(f"| `{s['symbol_name']}` | {s.get('kind', '')} |")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------
# Render functions
# ------------------------------------------------------------------


def _render_architecture(
    project_name: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> str:
    """Render ``docs/architecture.md`` content."""
    domains = [n for n in nodes if n.get("kind") == "domain"]
    services = [n for n in nodes if n.get("kind") == "service" and n.get("source", "").strip()]

    domain_rows = "\n".join(
        f"| {d['ref_id']} | {d.get('summary', '')} | `{d.get('source', '')}` |" for d in domains
    )
    service_rows = "\n".join(
        f"| {s['ref_id']} | {s.get('summary', '')} | `{s.get('source', '')}` |" for s in services
    )

    mermaid = _generate_mermaid(nodes, edges)

    return (
        f"# {project_name} — Architecture\n"
        "\n"
        "> Auto-generated by `beadloom docs generate`. Edit to add context.\n"
        "\n"
        "## Domains\n"
        "\n"
        "| Domain | Summary | Source |\n"
        "|--------|---------|--------|\n"
        f"{domain_rows}\n"
        "\n"
        "## Services\n"
        "\n"
        "| Service | Summary | Source |\n"
        "|---------|---------|--------|\n"
        f"{service_rows}\n"
        "\n"
        "## Dependency Map\n"
        "\n"
        "```mermaid\n"
        "graph LR\n"
        f"{mermaid}\n"
        "```\n"
        "\n"
        "<!-- enrich with: beadloom docs polish -->\n"
    )


# ------------------------------------------------------------------
# Domain README
# ------------------------------------------------------------------


def _render_domain_readme(
    node: dict[str, Any],
    edges: list[dict[str, Any]],
    symbols: list[dict[str, Any]] | None = None,
) -> str:
    """Render domain README content."""
    ref_id: str = node["ref_id"]
    summary: str = node.get("summary", "")
    source: str = node.get("source", "")

    depends_on, used_by = _edges_for(ref_id, edges)
    children = _children_of(ref_id, edges)

    dep_list = ", ".join(depends_on) if depends_on else "(none)"
    used_list = ", ".join(used_by) if used_by else "(none)"
    feat_list = "\n".join(f"- {c}" for c in children) if children else "(none)"

    symbols_section = _render_symbols_section(symbols or [])

    parts = [
        f"# {ref_id}\n",
        f"> {summary}\n",
        f"## Source\n\n`{source}`\n",
    ]
    if symbols_section:
        parts.append(symbols_section)
    parts.extend(
        [
            f"## Dependencies\n\n- Depends on: {dep_list}\n- Used by: {used_list}\n",
            f"## Features\n\n{feat_list}\n",
            "<!-- enrich with: beadloom docs polish -->\n",
        ]
    )
    return "\n".join(parts)


# ------------------------------------------------------------------
# Service page
# ------------------------------------------------------------------


def _render_service(
    node: dict[str, Any],
    edges: list[dict[str, Any]],
    symbols: list[dict[str, Any]] | None = None,
) -> str:
    """Render service page content."""
    ref_id: str = node["ref_id"]
    summary: str = node.get("summary", "")
    source: str = node.get("source", "")

    depends_on, used_by = _edges_for(ref_id, edges)
    dep_list = ", ".join(depends_on) if depends_on else "(none)"
    used_list = ", ".join(used_by) if used_by else "(none)"

    symbols_section = _render_symbols_section(symbols or [])

    parts = [
        f"# {ref_id}\n",
        f"> {summary}\n",
        f"## Source\n\n`{source}`\n",
    ]
    if symbols_section:
        parts.append(symbols_section)
    parts.extend(
        [
            f"## Dependencies\n\n- Depends on: {dep_list}\n- Used by: {used_list}\n",
            "<!-- enrich with: beadloom docs polish -->\n",
        ]
    )
    return "\n".join(parts)


# ------------------------------------------------------------------
# Feature SPEC
# ------------------------------------------------------------------


def _render_feature_spec(
    node: dict[str, Any],
    edges: list[dict[str, Any]],
    symbols: list[dict[str, Any]] | None = None,
) -> str:
    """Render feature SPEC content."""
    ref_id: str = node["ref_id"]
    summary: str = node.get("summary", "")
    source: str = node.get("source", "")
    parent = _parent_of(ref_id, edges) or "(unknown)"

    depends_on, used_by = _edges_for(ref_id, edges)
    dep_list = ", ".join(depends_on) if depends_on else "(none)"
    used_list = ", ".join(used_by) if used_by else "(none)"

    symbols_section = _render_symbols_section(symbols or [])

    parts = [
        f"# {ref_id}\n",
        f"> {summary}\n",
        f"## Source\n\n`{source}`\n",
    ]
    if symbols_section:
        parts.append(symbols_section)
    parts.extend(
        [
            f"## Dependencies\n\n- Depends on: {dep_list}\n- Used by: {used_list}\n",
            f"## Parent\n\n{parent}\n",
            "<!-- enrich with: beadloom docs polish -->\n",
        ]
    )
    return "\n".join(parts)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def generate_polish_data(
    project_root: Path,
    ref_id: str | None = None,
) -> dict[str, Any]:
    """Generate structured data for AI agent to enrich documentation.

    Returns a dict with:
    - nodes: list of node data with symbols, deps, dependents
    - architecture: project overview
    - instructions: str prompt for the AI agent

    If *ref_id* is given, returns data for that single node.
    """
    nodes, edges = _load_graph_from_yaml(project_root)

    # Detect project name from root node.
    root_node = _find_root_node(nodes, edges)
    project_name: str = root_node["ref_id"] if root_node else project_root.name

    # Load code symbols from SQLite DB (if available).
    symbols_by_source = _load_symbols_by_source(project_root)

    # Build node data list.
    target_nodes = nodes
    if ref_id is not None:
        target_nodes = [n for n in nodes if n["ref_id"] == ref_id]

    node_data_list: list[dict[str, Any]] = []
    for node in target_nodes:
        depends_on, used_by = _edges_for(node["ref_id"], edges)
        children = _children_of(node["ref_id"], edges)

        # Read existing doc content via resolved path.
        doc_path = _doc_path_for_node(node, edges, project_root)
        existing_doc: str | None = None
        if doc_path is not None and doc_path.exists():
            existing_doc = doc_path.read_text(encoding="utf-8")

        node_data: dict[str, Any] = {
            "ref_id": node["ref_id"],
            "kind": node.get("kind", ""),
            "summary": node.get("summary", ""),
            "source": node.get("source", ""),
            "symbols": _symbols_for_node(node, symbols_by_source),
            "depends_on": depends_on,
            "used_by": used_by,
            "features": children,
            "existing_docs": existing_doc,
        }
        node_data_list.append(node_data)

    # Build Mermaid diagram.
    mermaid_str = _generate_mermaid(nodes, edges)

    # Build instructions prompt.
    instructions = (
        "You are enriching documentation for the software project "
        f"'{project_name}'. For each node below, write a concise but "
        "informative description based on its public API symbols, "
        "dependencies, and source paths. Replace placeholder text and "
        "expand skeleton docs with real architectural context. "
        "Use the update_node MCP tool to save improved summaries."
    )

    return {
        "nodes": node_data_list,
        "architecture": {
            "project_name": project_name,
            "mermaid": mermaid_str,
        },
        "instructions": instructions,
    }


def generate_skeletons(
    project_root: Path,
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Generate doc skeletons from graph nodes and edges.

    Uses ``docs:`` paths from graph nodes when available, falls back to
    convention-based paths.  Features use ``docs/domains/{parent}/features/``
    layout.  Never overwrites existing files.

    Returns ``{"files_created": N, "files_skipped": M}``.
    """
    if nodes is None or edges is None:
        nodes, edges = _load_graph_from_yaml(project_root)

    # Detect project name and root node.
    root_node = _find_root_node(nodes, edges)
    project_name: str = root_node["ref_id"] if root_node else project_root.name
    root_ref_id: str | None = root_node["ref_id"] if root_node else None

    # Best-effort symbol loading.
    symbols_by_source = _load_symbols_by_source(project_root)

    docs_dir = project_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0

    # 1. architecture.md
    arch_content = _render_architecture(project_name, nodes, edges)
    if _write_if_missing(docs_dir / "architecture.md", arch_content):
        created += 1
    else:
        skipped += 1

    # 2. Node docs (domains, services, features)
    for node in nodes:
        kind = node.get("kind", "")
        ref_id = node["ref_id"]

        # Skip root service — covered by architecture.md.
        if ref_id == root_ref_id:
            continue

        if kind not in ("domain", "service", "feature"):
            continue

        doc_path = _doc_path_for_node(node, edges, project_root)
        if doc_path is None:
            continue

        node_symbols = _symbols_for_node(node, symbols_by_source)

        if kind == "domain":
            content = _render_domain_readme(node, edges, node_symbols)
        elif kind == "service":
            content = _render_service(node, edges, node_symbols)
        else:
            content = _render_feature_spec(node, edges, node_symbols)

        if _write_if_missing(doc_path, content):
            created += 1
        else:
            skipped += 1

    logger.info("Doc skeletons: %d created, %d skipped", created, skipped)
    return {"files_created": created, "files_skipped": skipped}
