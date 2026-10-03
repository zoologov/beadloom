"""The scaffold ``docs site`` writes names none of this repository's graph nodes.

BDL-076 ``beadloom-ujzb.18``, found by T2 (``beadloom-19l6``). The scaffold's
source carries ``beadloom:component=<ref>`` lines, one per theme file, so that
this repository's graph binds the theme to its slice nodes. Before this bead
they shipped into every adopter's ``site/``, where they named nodes the adopter
does not have: invisible in the built portal, and read by the adopter's own
indexer the moment the adopter scans ``site/`` or ``.``.

The source keeps them, because this repository's graph needs them; the writer
leaves them out. Read here over the real package, and over the node ids the
real graph binds to it, so a slice added later is covered without editing a list.

``beadloom-ujzb.20`` (R2 finding F8) widened the check from the scaffold's own
nodes to every node of this repository's graph: three shipped specs preferred
``rule-engine`` as their subject, a node outside the scaffold, so the narrower
check passed them. A spec now chooses its subject from the graph's shape, and a
written file cites neither this repository's epics nor its beads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.scaffold import read_marker, shipped_files, write_scaffold
from tests.support.package_under_test import PACKAGE_ROOT
from tests.support.scaffold_node_ids import (
    coined,
    literal_id_comparisons,
    node_ids_named,
    repository_node_ids,
    scaffold_node_ids,
    tracker_ids,
    tracker_references,
)

if TYPE_CHECKING:
    from pathlib import Path

_VERSION = "7.0.0"


@pytest.fixture(scope="module")
def ids() -> frozenset[str]:
    found = scaffold_node_ids()
    assert found, "the graph binds no node to the scaffold, so this check would check nothing"
    return found


def _portal(tmp_path: Path) -> Path:
    project = tmp_path / "shop"
    (project / ".beadloom").mkdir(parents=True)
    write_scaffold(project / "site", project_root=project, version=_VERSION)
    return project / "site"


def test_the_source_still_names_every_node_the_graph_binds_to_it(ids: frozenset[str]) -> None:
    """This repository's own tree stays annotated: the check below has something to bite."""
    source = PACKAGE_ROOT / "site_scaffold"
    annotated = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(source.rglob("*"))
        if path.is_file() and "node_modules" not in path.parts
    )
    named = {ref for ref in ids if f"beadloom:component={ref}\n" in annotated}
    assert sorted(ids - named) == []


def test_no_written_file_carries_an_annotation(tmp_path: Path) -> None:
    site = _portal(tmp_path)
    annotated = []
    for rel in shipped_files():
        marker = read_marker((site / rel).read_text(encoding="utf-8"))
        assert marker is not None, rel
        if "beadloom:" in marker.body:
            annotated.append(rel)
    assert annotated == []


def test_no_written_file_names_a_node_of_this_repository(
    tmp_path: Path, ids: frozenset[str]
) -> None:
    site = _portal(tmp_path)
    named = {
        rel: refs
        for rel in shipped_files()
        if (refs := node_ids_named((site / rel).read_text(encoding="utf-8"), ids))
    }
    assert named == {}


def test_no_written_file_names_a_coined_node_id_of_this_repository(tmp_path: Path) -> None:
    ids = coined(repository_node_ids())
    assert len(ids) > len(scaffold_node_ids()), "the check would cover only the scaffold's own"
    site = _portal(tmp_path)
    named = {
        rel: refs
        for rel in shipped_files()
        if (refs := node_ids_named((site / rel).read_text(encoding="utf-8"), ids))
    }
    assert named == {}


def test_no_written_file_chooses_a_node_by_a_literal_id(tmp_path: Path) -> None:
    site = _portal(tmp_path)
    chosen = {
        rel: lines
        for rel in shipped_files()
        if (lines := literal_id_comparisons((site / rel).read_text(encoding="utf-8")))
    }
    assert chosen == {}


def test_no_written_file_cites_this_repositorys_planning_or_tracker(
    tmp_path: Path, self_check_snapshot: Path
) -> None:
    beads = tracker_ids(self_check_snapshot)
    assert beads, "the tracker export holds no bead, so the check would check none"
    site = _portal(tmp_path)
    cited = {
        rel: refs
        for rel in shipped_files()
        if (refs := tracker_references((site / rel).read_text(encoding="utf-8"), beads))
    }
    assert cited == {}


def test_no_written_file_speaks_of_this_repository(tmp_path: Path) -> None:
    """A portal is the adopter's: "this repository" in a written file would mean ours."""
    site = _portal(tmp_path)
    speaking = sorted(
        rel
        for rel in shipped_files()
        if "this repository" in (site / rel).read_text(encoding="utf-8").lower()
    )
    assert speaking == []


def test_a_second_run_over_the_real_scaffold_changes_nothing(tmp_path: Path) -> None:
    site = _portal(tmp_path)
    again = write_scaffold(site, project_root=site.parent, version=_VERSION)
    assert sorted(again.unchanged) == sorted(shipped_files())
    assert (again.written, again.updated, again.kept, again.retired) == ((), (), (), ())
