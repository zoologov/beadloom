"""A crossing of the site's layers, planted in a copy of this graph, is found and drawn red.

BDL-080 PRD goal 2, *done when*: "``lint``'s FSD findings are red on the canvas".
This repository's graph has no finding of ``site-fsd-layers`` today, so the claim
that the data file draws one red can only be measured on a finding introduced on
purpose. The case copies this repository's graph files into a project of its own,
adds one ``depends_on`` edge from a slice of the rule's lowest layer to a slice of
its highest, and reads the verdict twice: from ``lint``, and from the architecture
data file the viewer draws. The two must name the same edge. The browser half,
the edge drawn red on the canvas, is ``layer-boxes.spec.js``.

Only the graph files are copied: the edges the code scan derives are not needed to
judge a declared edge, and the copy reindexes in well under a second. The slices
are chosen from ``rules.yml`` and the graph files, not named here, so a slice
renamed or retagged is followed. It carries the ``self_check`` marker by its folder.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.application.reindex import reindex
from beadloom.application.site.architecture_view import build_architecture_view_data
from beadloom.graph.linter import lint
from beadloom.onboarding.graph_files import each_graph_file
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: The rule that stratifies the portal's slices, and the portal it is scoped to.
FSD_RULE = "site-fsd-layers"
SITE = "vitepress-site"

_GRAPH = REPO_ROOT / ".beadloom" / "_graph"


def _fsd_tags() -> list[str]:
    """The FSD rule's layer tags, top to bottom, as `rules.yml` declares them."""
    rules = yaml.safe_load((_GRAPH / "rules.yml").read_text(encoding="utf-8"))["rules"]
    (rule,) = [r for r in rules if r["name"] == FSD_RULE]
    return [str(layer["tag"]) for layer in rule["layers"]]


def _a_slice_of_the_site_tagged(tag: str) -> str:
    """The first slice, by ref_id, that is part of the site and carries *tag*."""
    tagged: set[str] = set()
    parts: set[str] = set()
    for _path, data in each_graph_file(_GRAPH):
        for node in data.get("nodes") or []:
            if tag in (node.get("tags") or []):
                tagged.add(str(node["ref_id"]))
        for edge in data.get("edges") or []:
            if edge.get("kind") == "part_of" and edge.get("dst") == SITE:
                parts.add(str(edge["src"]))
    return min(tagged & parts)


def _a_copy_of_this_graph(root: Path, planted: list[tuple[str, str]]) -> Path:
    """This repository's graph files in a project of their own, with *planted* edges added."""
    (root / ".beadloom").mkdir(parents=True)
    shutil.copytree(_GRAPH, root / ".beadloom" / "_graph")
    if planted:
        edges = [{"src": src, "dst": dst, "kind": "depends_on"} for src, dst in planted]
        (root / ".beadloom" / "_graph" / "planted.yml").write_text(
            yaml.safe_dump({"edges": edges}), encoding="utf-8"
        )
    reindex(root)
    return root


def _drawn_red(root: Path) -> set[tuple[str, str]]:
    conn = sqlite3.connect(root / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        data: dict[str, Any] = build_architecture_view_data(conn, pages={})
    finally:
        conn.close()
    return {(str(e["src"]), str(e["dst"])) for e in data["edges"] if e.get("violation") is True}


def _found_by(root: Path, rule: str) -> set[tuple[str, str]]:
    return {
        (str(v.from_ref_id), str(v.to_ref_id))
        for v in lint(root).violations
        if v.rule_name == rule and v.from_ref_id is not None
    }


def test_an_upward_import_between_the_sites_layers_is_found_and_drawn_red(
    tmp_path: Path,
) -> None:
    tags = _fsd_tags()
    lowest, highest = _a_slice_of_the_site_tagged(tags[-1]), _a_slice_of_the_site_tagged(tags[0])
    root = _a_copy_of_this_graph(tmp_path / "planted", [(lowest, highest)])

    found = _found_by(root, FSD_RULE)
    drawn = _drawn_red(root)

    assert found == {(lowest, highest)}
    assert drawn == found


def test_the_copy_without_the_planted_edge_has_no_finding_and_nothing_red(
    tmp_path: Path,
) -> None:
    """The control: the red above is the planted edge's, not something the copy holds."""
    root = _a_copy_of_this_graph(tmp_path / "unplanted", [])

    found = _found_by(root, FSD_RULE)
    drawn = _drawn_red(root)

    assert (found, drawn) == (set(), set())
