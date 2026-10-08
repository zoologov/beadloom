"""A node declared `kind: site` bounds the context of what is part of it.

BDL-080 S1a (`beadloom-je0i`), RFC D1. `impact` states a change's bounded
context as the nearest `part_of` ancestor that is a domain or a service. A
portal declared `kind: site` was neither, so a slice of the portal was placed in
the product's root service, as if the portal were not a context of its own. The
graph loader reads `site` as `service`; this case holds the boundary to it,
through the real loader rather than a row seeded with the canonical kind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.impact.boundary import GraphBoundary
from beadloom.graph.loader import load_graph
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

_GRAPH = """\
nodes:
  - ref_id: atlas
    kind: service
    summary: The atlas product.
  - ref_id: atlas-portal
    kind: site
    summary: The atlas portal.
  - ref_id: portal-search
    kind: component
    summary: The portal's search slice.
edges:
  - src: atlas-portal
    dst: atlas
    kind: part_of
  - src: portal-search
    dst: atlas-portal
    kind: part_of
"""


def test_a_slice_of_a_site_node_sits_in_the_site_not_in_the_root(tmp_path: Path) -> None:
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "atlas.yml").write_text(_GRAPH, encoding="utf-8")
    conn = open_db(tmp_path / "graph.db")
    create_schema(conn)
    load_graph(graph_dir, conn)

    boundary = GraphBoundary(conn)

    assert boundary.context_of("portal-search") == "atlas-portal"
