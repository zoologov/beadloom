"""Documentation skeleton generator from architecture graph."""

# beadloom:domain=onboarding

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)

_BEADLOOM_README_TEMPLATE = """\
# {project_name} — AI Agent Native Architecture Graph

This project uses **Beadloom** for architecture-as-code — a local architecture
graph that keeps documentation in sync with code, enforces architectural
boundaries, and provides structured context to AI agents.

## What is Beadloom?

Beadloom is a Context Oracle + Doc Sync Engine designed for AI-assisted
development. It maintains a queryable architecture graph over your codebase,
so agents spend less time searching and more time building.

## Quick Start

### Essential Commands

    # Project overview
    beadloom status

    # Architecture graph (Mermaid)
    beadloom graph

    # Context bundle for a domain/feature
    beadloom ctx <ref-id>

    # Check doc-code freshness
    beadloom sync-check

    # Architecture boundary lint
    beadloom lint

    # Full-text search
    beadloom search "<query>"

    # Rebuild index after changes
    beadloom reindex

### For AI Agents (MCP)

Beadloom exposes tools via Model Context Protocol (MCP):

    beadloom mcp-serve             # start MCP server (stdio)
    beadloom setup-mcp             # configure your editor

MCP tools: `get_context`, `get_graph`, `list_nodes`, `sync_check`,
`search`, `update_node`, `mark_synced`, `generate_docs`.

## Directory Contents

    .beadloom/
    \u251c\u2500\u2500 _graph/
    \u2502   \u251c\u2500\u2500 services.yml    # Architecture graph (nodes + edges)
    \u2502   \u2514\u2500\u2500 rules.yml       # Architecture lint rules
    \u251c\u2500\u2500 config.yml          # Project configuration
    \u251c\u2500\u2500 beadloom.db         # SQLite index (gitignored)
    \u2514\u2500\u2500 README.md           # This file

## Why Beadloom?

- **Agent Native** \u2014 structured context for LLMs, not another LLM wrapper
- **Doc Sync** \u2014 detects when docs go stale after code changes
- **AaC Lint** \u2014 enforces architectural boundaries via deny/require rules
- **Local-first** \u2014 SQLite + YAML, no cloud services, no API keys
"""


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


def _generate_beadloom_readme(project_root: Path, project_name: str) -> Path:
    """Generate ``.beadloom/README.md`` with quick-start instructions."""
    readme_path = project_root / ".beadloom" / "README.md"
    content = _BEADLOOM_README_TEMPLATE.format(project_name=project_name)
    if _write_if_missing(readme_path, content):
        logger.info("Created: %s", readme_path)
    return readme_path


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
            return str(edge.get("dst", ""))
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
# YAML patching — write docs: field back to graph files
# ------------------------------------------------------------------


def _patch_docs_field(graph_dir: Path, docs_map: dict[str, str]) -> None:
    """Write ``docs:`` entries into graph YAML files for newly created docs.

    For each ``.yml`` file in *graph_dir*, if a node's ``ref_id`` appears in
    *docs_map* **and** the node does not already have a ``docs:`` field, a
    ``docs: [<relative_path>]`` entry is added.

    Parameters
    ----------
    graph_dir:
        Path to ``.beadloom/_graph/`` directory.
    docs_map:
        Mapping of ``{ref_id: relative_doc_path}`` for files that were
        **newly created** (not skipped).
    """
    import yaml

    if not docs_map:
        return

    for yml in sorted(graph_dir.glob("*.yml")):
        if yml.name == "rules.yml":
            continue

        data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        if not data or "nodes" not in data:
            continue

        modified = False
        for node in data["nodes"]:
            ref_id = node.get("ref_id", "")
            if ref_id in docs_map and "docs" not in node:
                node["docs"] = [docs_map[ref_id]]
                modified = True

        if modified:
            yml.write_text(
                yaml.dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            logger.info("Patched docs: field in %s", yml)


# ------------------------------------------------------------------
# SQLite edge enrichment
# ------------------------------------------------------------------


def _enrich_edges_from_sqlite(
    project_root: Path,
    node_data_list: list[dict[str, Any]],
) -> None:
    """Enrich *node_data_list* with ``depends_on`` / ``used_by`` from SQLite.

    At bootstrap time only ``part_of`` edges exist in the YAML graph files.
    Real ``depends_on`` edges are created by the import resolver during
    ``reindex``.  This function reads those edges from SQLite and merges
    them into the node data dictionaries (without duplicates).

    Modifies *node_data_list* in place.  Silently skips when the database
    does not exist or the edges table is missing.
    """
    from pathlib import Path as _Path

    db_path = _Path(project_root) / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        return

    import sqlite3

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            for node_data in node_data_list:
                ref_id: str = node_data["ref_id"]

                # Forward: this node depends on …
                rows = conn.execute(
                    "SELECT dst_ref_id FROM edges WHERE src_ref_id = ? AND kind = 'depends_on'",
                    (ref_id,),
                ).fetchall()
                if rows:
                    existing = set(node_data.get("depends_on") or [])
                    for (dst,) in rows:
                        if dst not in existing:
                            node_data.setdefault("depends_on", []).append(dst)
                            existing.add(dst)

                # Reverse: … depends on this node
                rows = conn.execute(
                    "SELECT src_ref_id FROM edges WHERE dst_ref_id = ? AND kind = 'depends_on'",
                    (ref_id,),
                ).fetchall()
                if rows:
                    existing = set(node_data.get("used_by") or [])
                    for (src,) in rows:
                        if src not in existing:
                            node_data.setdefault("used_by", []).append(src)
                            existing.add(src)
        finally:
            conn.close()
    except sqlite3.OperationalError:
        # Table may not exist yet — graceful degradation.
        pass


# ------------------------------------------------------------------
# Symbol change detection (BEAD-10)
# ------------------------------------------------------------------


def _detect_symbol_changes(
    project_root: Path,
    ref_id: str,
) -> dict[str, Any] | None:
    """Detect symbol drift for *ref_id* by comparing stored vs current symbols hash.

    Opens the SQLite database, queries the ``sync_state`` and ``code_symbols``
    tables, and returns a dict describing the drift (or ``None`` when there is
    no database, no sync_state entry, or no drift detected).

    Returns
    -------
    dict or None
        ``None`` when drift cannot be determined or no drift exists.
        Otherwise a dict with keys:
        - ``has_drift``: ``True``
        - ``current_symbols``: list of ``{"name": str, "kind": str}``
        - ``message``: human-readable summary
    """
    import sqlite3
    from pathlib import Path as _Path

    db_path = _Path(project_root) / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            return _detect_symbol_changes_with_conn(conn, ref_id)
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return None


def _detect_symbol_changes_with_conn(
    conn: sqlite3.Connection,
    ref_id: str,
) -> dict[str, Any] | None:
    """Core logic for symbol change detection (requires an open connection).

    Compares the ``symbols_hash`` stored in ``sync_state`` against the
    current hash computed from ``code_symbols``.  When they differ the
    current symbol list is returned so the AI agent can see what the
    API looks like now.
    """
    import hashlib
    import sqlite3 as _sqlite3

    # 1. Load stored symbols hash from sync_state.
    try:
        sync_rows = conn.execute(
            "SELECT symbols_hash FROM sync_state WHERE ref_id = ?",
            (ref_id,),
        ).fetchall()
    except _sqlite3.OperationalError:
        # Table may not exist.
        return None

    if not sync_rows:
        return None

    # Collect all stored hashes for this ref_id (may have multiple code paths).
    stored_hashes = [row["symbols_hash"] for row in sync_rows if row["symbols_hash"]]
    if not stored_hashes:
        # No symbols_hash recorded yet — cannot determine drift.
        return None

    # 2. Compute current symbols hash (same algorithm as engine._compute_symbols_hash).
    try:
        current_rows = conn.execute(
            "SELECT symbol_name, kind FROM code_symbols "
            "WHERE annotations LIKE ? ORDER BY file_path, symbol_name",
            (f'%"{ref_id}"%',),
        ).fetchall()
    except _sqlite3.OperationalError:
        return None

    if not current_rows:
        # No current symbols — if there were stored hashes, symbols were removed.
        current_hash = ""
    else:
        data = "|".join(f"{r['symbol_name']}:{r['kind']}" for r in current_rows)
        current_hash = hashlib.sha256(data.encode()).hexdigest()

    # 3. Compare: if ANY stored hash differs from current, there is drift.
    has_drift = any(h != current_hash for h in stored_hashes)
    if not has_drift:
        return None

    # 4. Build the current symbols list for the AI agent.
    current_symbols = (
        [{"name": r["symbol_name"], "kind": r["kind"]} for r in current_rows]
        if current_rows
        else []
    )

    n_symbols = len(current_symbols)
    message = f"symbols changed since last doc sync ({n_symbols} current symbols)"

    return {
        "has_drift": True,
        "current_symbols": current_symbols,
        "message": message,
    }


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
        doc_status: str = "missing"
        if doc_path is not None and doc_path.exists():
            existing_doc = doc_path.read_text(encoding="utf-8")
            doc_status = "exists"

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
            "doc_path": str(doc_path) if doc_path is not None else None,
            "doc_status": doc_status,
        }

        # Symbol change detection (BEAD-10).
        symbol_changes = _detect_symbol_changes(project_root, node["ref_id"])
        if symbol_changes:
            node_data["symbol_changes"] = symbol_changes

        node_data_list.append(node_data)

    # Enrich with real dependency edges from SQLite (post-reindex).
    _enrich_edges_from_sqlite(project_root, node_data_list)

    # Build Mermaid diagram.
    mermaid_str = _generate_mermaid(nodes, edges)

    # Build instructions prompt.
    instructions = (
        "You are enriching documentation for the software project "
        f"'{project_name}'. For each node below, write a concise but "
        "informative description based on its public API symbols, "
        "dependencies, and source paths. Replace placeholder text and "
        "expand skeleton docs with real architectural context. "
        "Pay special attention to nodes marked with symbol drift — their "
        "docs are likely stale and need updating to reflect API changes. "
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


def format_polish_text(data: dict[str, Any]) -> str:
    """Format ``generate_polish_data()`` output as human-readable text.

    Renders all nodes with their metadata (source, summary, dependencies,
    symbols, doc status) followed by the AI instructions prompt.
    """
    lines: list[str] = []

    arch = data.get("architecture", {})
    project_name: str = arch.get("project_name", "project")
    nodes_list: list[dict[str, Any]] = data.get("nodes", [])

    lines.append(f"# {project_name}")
    lines.append(f"Nodes needing enrichment: {len(nodes_list)}")
    lines.append("")

    for node in nodes_list:
        ref_id: str = node.get("ref_id", "?")
        kind: str = node.get("kind", "?")
        source: str = node.get("source", "")
        summary: str = node.get("summary", "")
        depends_on: list[str] = node.get("depends_on", [])
        used_by: list[str] = node.get("used_by", [])
        symbols: list[dict[str, Any]] = node.get("symbols", [])
        doc_path: str | None = node.get("doc_path")
        doc_status: str = node.get("doc_status", "missing")

        lines.append(f"## {ref_id} ({kind})")
        lines.append(f"   Source: {source}")
        lines.append(f"   Summary: {summary}")
        dep_str = ", ".join(depends_on) if depends_on else "(none)"
        used_str = ", ".join(used_by) if used_by else "(none)"
        lines.append(f"   Depends on: {dep_str}")
        lines.append(f"   Used by: {used_str}")

        if symbols:
            # Show public symbols only (skip _private).
            pub = [
                s.get("symbol_name", "")
                for s in symbols
                if not s.get("symbol_name", "").startswith("_")
            ]
            if pub:
                lines.append(f"   Symbols: {', '.join(sorted(pub))}")
            else:
                lines.append("   Symbols: (none public)")
        else:
            lines.append("   Symbols: (none)")

        # Symbol changes (BEAD-10).
        changes = node.get("symbol_changes")
        if changes and changes.get("has_drift"):
            lines.append(f"   \u26a0 Symbol drift: {changes.get('message', 'symbols changed')}")

        doc_display = doc_path if doc_path else "(none)"
        lines.append(f"   Doc: {doc_display} ({doc_status})")
        lines.append("")

    lines.append("---")
    lines.append(data.get("instructions", ""))

    return "\n".join(lines)


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
    # Track ref_id -> relative doc path for newly created files.
    docs_map: dict[str, str] = {}

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
            # Record relative path from project root for the docs: field.
            try:
                rel_path = doc_path.relative_to(project_root)
            except ValueError:
                rel_path = doc_path
            docs_map[ref_id] = str(rel_path)
        else:
            skipped += 1

    # 3. Generate .beadloom/README.md with quick-start instructions.
    _generate_beadloom_readme(project_root, project_name)

    # 4. Patch docs: field into graph YAML for newly created files.
    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir() and docs_map:
        _patch_docs_field(graph_dir, docs_map)

    logger.info("Doc skeletons: %d created, %d skipped", created, skipped)
    return {"files_created": created, "files_skipped": skipped}
