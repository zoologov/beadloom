"""C4 architecture model mapping from the Beadloom graph.

Reads nodes and edges from SQLite and maps them to C4 model elements:
- ``C4Node`` with level (System / Container / Component)
- ``C4Relationship`` from ``uses`` and ``depends_on`` edges

Level assignment priority:
1. Explicit ``c4_level`` in node's ``extra`` JSON
2. ``part_of`` depth heuristic: root=System, depth 1=Container, depth 2+=Component
3. (Future) tag-based inference
"""

# beadloom:feature=c4-diagrams

from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


# Edge kinds that map to C4 Rel() relationships
_RELATIONSHIP_EDGE_KINDS = frozenset({"uses", "depends_on"})

# Pattern for characters that are invalid in Mermaid/PlantUML identifiers
_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_]")

# Tags that set is_external / is_database flags
_EXTERNAL_TAGS = frozenset({"external"})
_DATABASE_TAGS = frozenset({"database", "storage"})


@dataclass(frozen=True)
class C4Node:
    """A node in the C4 architecture model."""

    ref_id: str
    label: str
    c4_level: str  # "System" | "Container" | "Component"
    description: str
    boundary: str | None  # ref_id of the part_of parent (None for roots)
    is_external: bool
    is_database: bool


@dataclass(frozen=True)
class C4Relationship:
    """A relationship between two C4 nodes."""

    src: str
    dst: str
    label: str  # edge kind: "uses" | "depends_on"


def _compute_depths(
    parent_of: dict[str, str],
    all_ref_ids: set[str],
) -> dict[str, int]:
    """Compute depth of each node via BFS from roots.

    A root is any node that has no ``part_of`` parent.
    Returns a mapping of ref_id -> depth (0 for roots).
    """
    # Children lookup: parent -> list of children (skip self-referencing edges)
    children: dict[str, list[str]] = {}
    for child, par in parent_of.items():
        if child != par:
            children.setdefault(par, []).append(child)

    # Roots are nodes not present as children in part_of (excluding self-refs)
    non_self_children = {child for child, par in parent_of.items() if child != par}
    roots = all_ref_ids - non_self_children

    depths: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque()

    for root in roots:
        depths[root] = 0
        queue.append((root, 0))

    while queue:
        node, depth = queue.popleft()
        for child in children.get(node, []):
            if child not in depths:
                depths[child] = depth + 1
                queue.append((child, depth + 1))

    # Any node not reached (e.g. orphans) gets depth 0 (root-level)
    for ref_id in all_ref_ids:
        if ref_id not in depths:
            depths[ref_id] = 0

    return depths


def _depth_to_c4_level(depth: int) -> str:
    """Map depth to C4 level using the heuristic.

    - depth 0: System
    - depth 1: Container
    - depth 2+: Component
    """
    if depth == 0:
        return "System"
    if depth == 1:
        return "Container"
    return "Component"


def _load_nodes(
    conn: sqlite3.Connection,
) -> tuple[set[str], dict[str, dict[str, object]]]:
    """Load all nodes from the database and parse their data.

    Returns:
        A tuple of (all_ref_ids, node_data) where node_data maps
        ref_id to a dict with keys: kind, summary, source, extra.
    """
    node_rows = conn.execute(
        "SELECT ref_id, kind, summary, source, extra FROM nodes ORDER BY ref_id"
    ).fetchall()

    all_ref_ids: set[str] = set()
    node_data: dict[str, dict[str, object]] = {}

    for row in node_rows:
        ref_id: str = row["ref_id"]
        all_ref_ids.add(ref_id)
        extra_raw = row["extra"]
        extra: dict[str, object] = json.loads(str(extra_raw)) if extra_raw else {}
        node_data[ref_id] = {
            "kind": row["kind"],
            "summary": row["summary"] or "",
            "source": row["source"],
            "extra": extra,
        }

    return all_ref_ids, node_data


def _load_edges(
    conn: sqlite3.Connection,
) -> tuple[dict[str, str], list[C4Relationship]]:
    """Load edges and separate part_of hierarchy from relationships.

    Returns:
        A tuple of (parent_of, relationships) where parent_of maps
        child -> parent via part_of edges.
    """
    edge_rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind FROM edges ORDER BY src_ref_id, dst_ref_id"
    ).fetchall()

    parent_of: dict[str, str] = {}
    relationships: list[C4Relationship] = []

    for erow in edge_rows:
        src: str = erow["src_ref_id"]
        dst: str = erow["dst_ref_id"]
        edge_kind: str = erow["kind"]

        if edge_kind == "part_of":
            if src == dst:
                continue  # skip self-referencing part_of
            parent_of[src] = dst
        elif edge_kind in _RELATIONSHIP_EDGE_KINDS:
            relationships.append(C4Relationship(src=src, dst=dst, label=edge_kind))

    return parent_of, relationships


def _build_c4_node(
    ref_id: str,
    data: dict[str, object],
    depth: int,
    parent_of: dict[str, str],
) -> C4Node:
    """Build a single C4Node from parsed node data and computed depth."""
    raw_extra = data["extra"]
    node_extra = raw_extra if isinstance(raw_extra, dict) else {}

    summary = str(data["summary"])
    raw_tags = node_extra.get("tags", [])
    tags: set[str] = set(raw_tags) if isinstance(raw_tags, list) else set()

    # C4 level: explicit > depth heuristic
    explicit_level = node_extra.get("c4_level")
    if isinstance(explicit_level, str) and explicit_level:
        c4_level = explicit_level
    else:
        c4_level = _depth_to_c4_level(depth)

    # Label: title-case from ref_id (hyphen -> space)
    label = ref_id.replace("-", " ").title()

    return C4Node(
        ref_id=ref_id,
        label=label,
        c4_level=c4_level,
        description=summary,
        boundary=parent_of.get(ref_id),
        is_external=bool(tags & _EXTERNAL_TAGS),
        is_database=bool(tags & _DATABASE_TAGS),
    )


def map_to_c4(
    conn: sqlite3.Connection,
) -> tuple[list[C4Node], list[C4Relationship]]:
    """Map architecture graph to C4 model elements.

    Reads all nodes and edges from the database and produces:
    1. A list of ``C4Node`` with assigned C4 levels
    2. A list of ``C4Relationship`` from ``uses``/``depends_on`` edges

    Level assignment priority:
    - Explicit ``c4_level`` in node's ``extra`` JSON overrides everything
    - Otherwise, ``part_of`` depth heuristic applies

    Returns:
        A tuple of (c4_nodes, c4_relationships).
    """
    all_ref_ids, node_data = _load_nodes(conn)
    if not all_ref_ids:
        return [], []

    parent_of, relationships = _load_edges(conn)
    depths = _compute_depths(parent_of, all_ref_ids)

    c4_nodes = [
        _build_c4_node(ref_id, node_data[ref_id], depths[ref_id], parent_of)
        for ref_id in sorted(all_ref_ids)
    ]

    return c4_nodes, relationships


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _c4_element_name(node: C4Node) -> str:
    """Return the C4 element name for a node based on its level and flags.

    Used by both Mermaid and PlantUML renderers to produce consistent
    element names (e.g. ``System``, ``Container_Ext``, ``ContainerDb``).
    """
    level = node.c4_level

    if node.is_external:
        return f"{level}_Ext"
    if node.is_database and level in ("Container", "Component"):
        return f"{level}Db"
    return level


# ---------------------------------------------------------------------------
# Mermaid C4 renderer
# ---------------------------------------------------------------------------


def _mermaid_node_line(node: C4Node, indent: str) -> str:
    """Return a single Mermaid C4 node line."""
    elem = _c4_element_name(node)
    sid = _sanitize_id(node.ref_id)
    desc = node.description

    if node.c4_level == "System":
        return f'{indent}{elem}({sid}, "{node.label}", "{desc}")'
    # Container / Component: include technology slot
    return f'{indent}{elem}({sid}, "{node.label}", "", "{desc}")'


def _mermaid_grandchildren(
    child: C4Node,
    boundary_children: dict[str, list[C4Node]],
) -> list[str]:
    """Render nested Container_Boundary for a child's grandchildren."""
    grandchildren = boundary_children.get(child.ref_id, [])
    if not grandchildren:
        return []

    csid = _sanitize_id(child.ref_id)
    lines = [f'        Container_Boundary({csid}_boundary, "{child.label}") {{']
    for gc in grandchildren:
        lines.append(_mermaid_node_line(gc, "            "))
    lines.append("        }")
    return lines


def _mermaid_top_level_node(
    node: C4Node,
    boundary_children: dict[str, list[C4Node]],
) -> list[str]:
    """Render a top-level node, wrapping children in a System_Boundary if needed."""
    children = boundary_children.get(node.ref_id, [])
    if not children:
        return [_mermaid_node_line(node, "    ")]

    sid = _sanitize_id(node.ref_id)
    lines = [f'    System_Boundary({sid}_boundary, "{node.label}") {{']
    for child in children:
        lines.append(_mermaid_node_line(child, "        "))
        lines.extend(_mermaid_grandchildren(child, boundary_children))
    lines.append("    }")
    return lines


def _mermaid_orphan_boundaries(
    boundary_children: dict[str, list[C4Node]],
    rendered_ids: set[str],
    node_by_id: dict[str, C4Node],
) -> list[str]:
    """Render boundary groups for parents that are not top-level nodes."""
    lines: list[str] = []
    # Sort orphan boundaries alphabetically for deterministic output
    sorted_parent_ids = sorted(
        pid for pid in boundary_children if pid not in rendered_ids
    )
    for parent_id in sorted_parent_ids:
        children = boundary_children[parent_id]
        parent = node_by_id.get(parent_id)
        parent_label = parent.label if parent else parent_id
        sid = _sanitize_id(parent_id)
        lines.append(f'    System_Boundary({sid}_boundary, "{parent_label}") {{')
        for child in children:
            lines.append(_mermaid_node_line(child, "        "))
        lines.append("    }")
    return lines


def render_c4_mermaid(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
) -> str:
    """Render C4 model elements as Mermaid C4 syntax.

    Produces a ``C4Container`` diagram with:
    - ``System()``, ``Container()``, ``Component()`` elements
    - ``System_Ext()``, ``Container_Ext()``, ``ContainerDb()``, ``ComponentDb()`` variants
    - ``System_Boundary()`` for grouping children by their ``part_of`` parent
    - ``Rel()`` for relationships

    Args:
        nodes: C4 nodes from ``map_to_c4()``.
        relationships: C4 relationships from ``map_to_c4()``.

    Returns:
        A string containing Mermaid C4 diagram source.
    """
    lines: list[str] = ["C4Container"]
    boundary_children: dict[str, list[C4Node]] = {}
    top_level: list[C4Node] = []

    for node in nodes:
        if node.boundary is not None:
            boundary_children.setdefault(node.boundary, []).append(node)
        else:
            top_level.append(node)

    node_by_id: dict[str, C4Node] = {n.ref_id: n for n in nodes}

    for node in top_level:
        lines.extend(_mermaid_top_level_node(node, boundary_children))

    rendered_ids = {n.ref_id for n in top_level}
    lines.extend(_mermaid_orphan_boundaries(boundary_children, rendered_ids, node_by_id))

    for rel in relationships:
        src_id = _sanitize_id(rel.src)
        dst_id = _sanitize_id(rel.dst)
        lines.append(f'    Rel({src_id}, {dst_id}, "{rel.label}")')

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# C4 level filtering
# ---------------------------------------------------------------------------

# Valid C4 view levels for the --level CLI option
C4_LEVELS = frozenset({"context", "container", "component"})


def filter_c4_nodes(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
    *,
    level: str = "container",
    scope: str | None = None,
) -> tuple[list[C4Node], list[C4Relationship]]:
    """Filter C4 nodes and relationships by diagram level.

    Args:
        nodes: All C4 nodes from ``map_to_c4()``.
        relationships: All C4 relationships from ``map_to_c4()``.
        level: One of ``"context"``, ``"container"`` (default), ``"component"``.
        scope: Required when ``level="component"``. The ``ref_id`` of the
            container whose internals to show.

    Returns:
        A filtered tuple of (c4_nodes, c4_relationships) containing only the
        nodes and relationships relevant to the requested level.

    Raises:
        ValueError: If ``level="component"`` and ``scope`` is not provided,
            or if ``scope`` ref_id is not found among the nodes.
    """
    if level == "component" and not scope:
        msg = "--level=component requires --scope=<ref-id>"
        raise ValueError(msg)

    if level == "context":
        return _filter_context(nodes, relationships)
    if level == "container":
        return _filter_container(nodes, relationships)
    # level == "component"
    assert scope is not None  # guaranteed by the check above
    return _filter_component(nodes, relationships, scope)


def _filter_context(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
) -> tuple[list[C4Node], list[C4Relationship]]:
    """Context level: keep only System-level nodes and external nodes."""
    kept = [n for n in nodes if n.c4_level == "System" or n.is_external]
    kept_ids = {n.ref_id for n in kept}
    kept_rels = [r for r in relationships if r.src in kept_ids and r.dst in kept_ids]
    return kept, kept_rels


def _filter_container(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
) -> tuple[list[C4Node], list[C4Relationship]]:
    """Container level: keep System and Container nodes."""
    kept = [n for n in nodes if n.c4_level in ("System", "Container")]
    kept_ids = {n.ref_id for n in kept}
    kept_rels = [r for r in relationships if r.src in kept_ids and r.dst in kept_ids]
    return kept, kept_rels


def _filter_component(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
    scope: str,
) -> tuple[list[C4Node], list[C4Relationship]]:
    """Component level: keep children of the scoped container."""
    # Verify scope exists
    all_ids = {n.ref_id for n in nodes}
    if scope not in all_ids:
        msg = f"--scope ref_id '{scope}' not found in graph"
        raise ValueError(msg)

    # Keep nodes whose boundary == scope (direct children of the container)
    kept = [n for n in nodes if n.boundary == scope]
    kept_ids = {n.ref_id for n in kept}
    kept_rels = [r for r in relationships if r.src in kept_ids and r.dst in kept_ids]
    return kept, kept_rels


# ---------------------------------------------------------------------------
# PlantUML C4 renderer
# ---------------------------------------------------------------------------

_C4_PLANTUML_BASE_URL = (
    "https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master"
)

_C4_PLANTUML_INCLUDES: dict[str, str] = {
    "context": f"{_C4_PLANTUML_BASE_URL}/C4_Context.puml",
    "container": f"{_C4_PLANTUML_BASE_URL}/C4_Container.puml",
    "component": f"{_C4_PLANTUML_BASE_URL}/C4_Component.puml",
}


def _sanitize_id(ref_id: str) -> str:
    """Sanitize a ref_id into a valid Mermaid/PlantUML identifier.

    Replaces hyphens and other non-alphanumeric characters with underscores.
    """
    return _SANITIZE_RE.sub("_", ref_id)


def _node_macro(node: C4Node) -> str:
    """Return the PlantUML C4 macro call for a single node."""
    sid = _sanitize_id(node.ref_id)
    label = node.label
    desc = node.description

    if node.c4_level == "System":
        if node.is_external:
            return f'System_Ext({sid}, "{label}", "{desc}")'
        return f'System({sid}, "{label}", "{desc}")'

    if node.c4_level == "Container":
        if node.is_external:
            return f'Container_Ext({sid}, "{label}", "", "{desc}")'
        if node.is_database:
            return f'ContainerDb({sid}, "{label}", "", "{desc}")'
        return f'Container({sid}, "{label}", "", "{desc}")'

    # Component level
    if node.is_external:
        return f'Component_Ext({sid}, "{label}", "", "{desc}")'
    if node.is_database:
        return f'ComponentDb({sid}, "{label}", "", "{desc}")'
    return f'Component({sid}, "{label}", "", "{desc}")'


def _plantuml_top_level_node(
    node: C4Node,
    boundary_children: dict[str, list[C4Node]],
) -> list[str]:
    """Render a top-level node as a boundary or standalone macro."""
    children = boundary_children.get(node.ref_id, [])
    if not children:
        return [_node_macro(node)]

    sid = _sanitize_id(node.ref_id)
    lines = [f'System_Boundary({sid}_boundary, "{node.label}") {{']
    for child in children:
        lines.append(f"    {_node_macro(child)}")
    lines.append("}")
    lines.append("")
    return lines


def _plantuml_orphan_boundaries(
    boundary_children: dict[str, list[C4Node]],
    rendered_ids: set[str],
    node_by_id: dict[str, C4Node],
) -> list[str]:
    """Render boundary groups for parents that are not top-level nodes."""
    lines: list[str] = []
    # Sort orphan boundaries alphabetically for deterministic output
    sorted_parent_ids = sorted(
        pid for pid in boundary_children if pid not in rendered_ids
    )
    for parent_id in sorted_parent_ids:
        children = boundary_children[parent_id]
        parent = node_by_id.get(parent_id)
        parent_label = parent.label if parent else parent_id
        sid = _sanitize_id(parent_id)
        lines.append(f'System_Boundary({sid}_boundary, "{parent_label}") {{')
        for child in children:
            lines.append(f"    {_node_macro(child)}")
        lines.append("}")
        lines.append("")
    return lines


def render_c4_plantuml(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
    *,
    level: str = "container",
) -> str:
    """Render C4 model elements as C4-PlantUML syntax.

    Produces a complete ``@startuml``/``@enduml`` block with:
    - ``!include`` for the C4-PlantUML stdlib (selected by level)
    - ``System_Boundary()`` grouping for nodes sharing a boundary
    - Standard macros: ``System()``, ``Container()``, ``Component()``, ``Rel()``
    - ``_Ext`` / ``Db`` variants for external/database nodes

    Args:
        nodes: C4 nodes from ``map_to_c4()``.
        relationships: C4 relationships from ``map_to_c4()``.
        level: C4 diagram level — ``"context"``, ``"container"`` (default),
            or ``"component"``. Controls which ``!include`` is emitted.

    Returns:
        A string containing valid C4-PlantUML diagram source.
    """
    include_url = _C4_PLANTUML_INCLUDES.get(level, _C4_PLANTUML_INCLUDES["container"])
    lines: list[str] = ["@startuml", f"!include {include_url}", ""]
    boundary_children: dict[str, list[C4Node]] = {}
    top_level_nodes: list[C4Node] = []

    for node in nodes:
        if node.boundary is not None:
            boundary_children.setdefault(node.boundary, []).append(node)
        else:
            top_level_nodes.append(node)

    node_by_id: dict[str, C4Node] = {n.ref_id: n for n in nodes}

    for node in top_level_nodes:
        lines.extend(_plantuml_top_level_node(node, boundary_children))

    rendered_ids = {n.ref_id for n in top_level_nodes}
    lines.extend(_plantuml_orphan_boundaries(boundary_children, rendered_ids, node_by_id))

    if relationships:
        lines.append("")
        for rel in relationships:
            src = _sanitize_id(rel.src)
            dst = _sanitize_id(rel.dst)
            lines.append(f'Rel({src}, {dst}, "{rel.label}")')

    lines.append("")
    lines.append("@enduml")

    return "\n".join(lines)
