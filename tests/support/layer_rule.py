"""The layer rule, as the tests declare it, recompute its split and compare it with the view."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.site.architecture_view import build_architecture_view_data
from beadloom.graph.rules.layer_edges import flagged_layer_edges
from beadloom.graph.rules.layer_reach import (
    live_edges_of_kind,
    part_of_parents,
    reach_of,
)
from beadloom.graph.rules.layers import (
    layer_of,
    own_layer_of,
    part_of_generations,
    same_layer_crossings,
)
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import (
    LayerDef,
    LayerRule,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence
    from pathlib import Path


def rule_of(project: Path) -> LayerRule:
    """The layer rule the project declares, as the linter loads it."""
    return next(
        rule
        for rule in load_rules(project / ".beadloom" / "_graph" / "rules.yml")
        if isinstance(rule, LayerRule)
    )


@dataclass(frozen=True)
class Split:
    """One recomputation of a layer rule's edge set, by what the rule does with it.

    Every field is derived in :func:`split_of` from one index and one rule. The
    class exists so a test names the half it is asserting about instead of
    indexing a tuple, and so a failure message can print all of them at once —
    the question a red here raises is always "then what ARE the numbers".
    """

    total: int
    evaluated: int
    same_layer: tuple[tuple[str, str], ...]
    internal: tuple[tuple[str, str], ...]
    crossings: tuple[tuple[str, str], ...]

    @property
    def skipped(self) -> int:
        """Edges with an end in no declared layer, which the rule does not judge."""
        return self.total - self.evaluated


def split_of(conn: sqlite3.Connection, rule: LayerRule) -> Split:
    """Recompute *rule*'s split over the indexed graph, from the shipped predicates.

    It calls :func:`~beadloom.graph.rules.layers.same_layer_crossings` rather
    than restating the predicate, because a test that reimplements the rule
    asserts agreement between two of its own bodies.
    """
    edges = live_edges_of_kind(conn, rule.edge_kind)
    parents = part_of_parents(conn)
    tags = node_tags(conn).as_mapping()
    same_layer = tuple(
        (src, dst)
        for src, dst in edges
        if (layer := layer_of(src, rule.layers, parents, tags)) is not None
        and layer == layer_of(dst, rule.layers, parents, tags)
    )
    crossings = tuple(same_layer_crossings(edges, rule.layers, parents, tags))
    return Split(
        total=len(edges),
        evaluated=reach_of(rule, edges, parents, tags).population.evaluated,
        same_layer=same_layer,
        internal=tuple(edge for edge in same_layer if edge not in set(crossings)),
        crossings=crossings,
    )


def nearest_tagged_container(
    ref_id: str,
    layers: Sequence[LayerDef],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> str | None:
    """The RETIRED predicate's half: the nearest container that carries a layer.

    Transcribed here, in the test that shows it is not the shipped one, because
    the alternative is a paragraph claiming the two differ. Reflexive in the
    same way the shipped predicate is — a node carrying its own tag is its own
    nearest tagged container — and that reflexivity is exactly where the two
    part company.
    """
    if own_layer_of(ref_id, layers, tags) is not None:
        return ref_id
    for generation in part_of_generations(ref_id, parents):
        declared = sorted(
            ancestor for ancestor in generation if own_layer_of(ancestor, layers, tags) is not None
        )
        if declared:
            return declared[0]
    return None


def read_only_index(project: Path) -> closing[sqlite3.Connection]:
    """A read-only handle on *project*'s index that closes itself.

    Read-only on purpose: every handle this module opens on the live index is
    one that cannot move the lineage the session fixture established.
    """
    db_path = project / ".beadloom" / "beadloom.db"
    return closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True))


def retired_crossings(project: Path, split: Split) -> set[tuple[str, str]]:
    """The same-layer edges the RETIRED predicate would have called crossings."""
    rule = rule_of(project)
    with read_only_index(project) as conn:
        parents = part_of_parents(conn)
        tags = node_tags(conn).as_mapping()
    return {
        (src, dst)
        for src, dst in split.same_layer
        if nearest_tagged_container(src, rule.layers, parents, tags)
        != nearest_tagged_container(dst, rule.layers, parents, tags)
    }


def row_connection(project: Path) -> closing[sqlite3.Connection]:
    """A row-keyed handle on the project's index that closes itself."""
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    return closing(conn)


def view_verdicts(project: Path) -> dict[tuple[str, str], object]:
    """Each `depends_on` edge of the rendered view, with its `violation` value.

    A missing flag comes back as ``None`` rather than being dropped, because
    "the view said nothing about this edge" is one of the three answers and a
    test that could not see it would read an omission as a pass.
    """
    with row_connection(project) as conn:
        data = build_architecture_view_data(conn, pages={})
    edges = [e for e in data["edges"] if isinstance(e, dict) and e.get("kind") == "depends_on"]
    return {(str(e["src"]), str(e["dst"])): e.get("violation") for e in edges}


def view_flags(project: Path) -> set[tuple[str, str]]:
    return {edge for edge, verdict in view_verdicts(project).items() if verdict is True}


def rule_flags(project: Path) -> set[tuple[str, str]]:
    with row_connection(project) as conn:
        return set(flagged_layer_edges(conn, rule_of(project)))


#: This repository's own declaration, read from `.beadloom/_graph/rules.yml`.
DDD_LAYERS = (
    LayerDef(name="services", tag="layer-service"),
    LayerDef(name="application", tag="layer-application"),
    LayerDef(name="domains", tag="layer-domain"),
    LayerDef(name="infrastructure", tag="layer-infra"),
)


def ddd_layer_rule(
    *,
    severity: str = "error",
    edge_kind: str = "depends_on",
    allow_skip: bool = True,
) -> LayerRule:
    return LayerRule(
        name="architecture-layers",
        description="Services → application → domains → infrastructure — not reverse",
        layers=DDD_LAYERS,
        enforce="top-down",
        allow_skip=allow_skip,
        edge_kind=edge_kind,
        severity=severity,
    )
