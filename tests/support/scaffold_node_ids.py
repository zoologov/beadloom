"""The node ids this repository's graph binds to the portal scaffold, read from the graph.

BDL-076 ``beadloom-ujzb.18``. The scaffold's source files carry
``beadloom:component=<ref>`` lines so that this repository's graph binds the
theme to its slice nodes, and those refs are exactly the nodes whose declared
``source:`` lies inside the scaffold package. Reading them from the graph rather
than listing them keeps a check over a written portal true when a slice is
added, renamed or retired.

Read through :data:`tests.support.package_under_test.SHIPPED_FROM`, so an
acceptance step copied away from the checkout still reads this project's graph.
"""

from __future__ import annotations

import re

from beadloom.graph.loader import parse_graph_file
from tests.support.package_under_test import SHIPPED_FROM

#: This repository's graph directory.
GRAPH_DIR = SHIPPED_FROM / ".beadloom" / "_graph"

#: The scaffold package, as a node's ``source:`` names it.
SCAFFOLD_SOURCE = "src/beadloom/site_scaffold/"


def scaffold_node_ids() -> frozenset[str]:
    """Every node of this repository's graph whose source lies inside the scaffold."""
    ids: set[str] = set()
    for path in sorted(GRAPH_DIR.glob("*.yml")):
        for node in parse_graph_file(path).nodes:
            source = node.get("source")
            if isinstance(source, str) and source.startswith(SCAFFOLD_SOURCE):
                ids.add(str(node["ref_id"]))
    return frozenset(ids)


def node_ids_named(text: str, ids: frozenset[str]) -> list[str]:
    """The ids in *ids* that *text* names as a whole token, hyphens included."""
    return sorted(ref for ref in ids if re.search(rf"(?<![\w-]){re.escape(ref)}(?![\w-])", text))
