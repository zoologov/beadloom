"""What a slice rule judges: slices, containers, segments and groups, read off the graph.

BDL-082 S1 (RFC D2, D5). :func:`beadloom.graph.rules.slice_units.read_units` decides which
carrier of a rule is a slice, which a container (the ``shared`` or ``app`` layer node) and
which a segment of one, and which folder is a group. These cases hold the decisions the rule
files reach only through a whole rule: a ``part_of`` between carriers that share no tag of
the rule, a node-owned folder between a layer and its slices, and the stem of a platform file.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.graph.rules.slice_units import read_units, stem
from tests.support.in_memory_graph import add_edge, open_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

TAGS = ("fsd-pages", "fsd-features", "fsd-shared")


def _graph(root: Path, nodes: dict[str, tuple[str, str]]) -> sqlite3.Connection:
    """*nodes* map a ref id to ``(source, tag)``; each source is a folder on disk."""
    conn = open_graph()
    for ref_id, (source, tag) in nodes.items():
        (root / source).mkdir(parents=True, exist_ok=True)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
            (ref_id, "component", ref_id, source, json.dumps({"tags": [tag]})),
        )
    return conn


def test_the_stem_of_a_platform_file_is_its_name_before_the_first_dot() -> None:
    assert stem("index.ios.tsx") == "index"


def test_a_part_of_between_carriers_sharing_a_tag_makes_a_container(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {"shared": ("src/shared/", "fsd-shared"), "shared-ui": ("src/shared/ui/", "fsd-shared")},
    )
    add_edge(conn, "shared-ui", "shared", "part_of")

    units = read_units(conn, TAGS, tmp_path)

    assert dict(units.container_of) == {"shared-ui": "shared"}


def test_a_part_of_between_carriers_sharing_no_tag_makes_no_container(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {
            "pages-home": ("src/pages/home/", "fsd-pages"),
            "features-search": ("src/features/search/", "fsd-features"),
        },
    )
    add_edge(conn, "features-search", "pages-home", "part_of")

    units = read_units(conn, TAGS, tmp_path)

    assert (dict(units.container_of), units.slices()) == ({}, ["features-search", "pages-home"])


def test_a_folder_a_node_owns_between_the_layer_and_a_slice_is_no_group(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {
            "features-auth": ("src/features/auth/", "fsd-pages"),
            "features-auth-login": ("src/features/auth/login/", "fsd-features"),
        },
    )

    units = read_units(conn, ("fsd-features",), tmp_path)

    assert units.groups() == {}


def test_an_unowned_folder_between_the_layer_and_a_slice_is_a_group(tmp_path: Path) -> None:
    conn = _graph(tmp_path, {"features-auth-login": ("src/features/auth/login/", "fsd-features")})

    units = read_units(conn, ("fsd-features",), tmp_path)

    assert units.groups() == {"src/features/auth": ["features-auth-login"]}
