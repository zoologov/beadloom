"""What layer a node is in, answered by one function that reads the declaration.

BDL-070 A1 (`beadloom-e64o`). Three bodies computed layer membership and they
disagreed: `evaluators.evaluate_layer_rules` read a node's own tags and skipped
every edge whose ends carried none — 16 of 362 `depends_on` edges evaluated on
this repository at `aa4bfad4` — while `architecture_view._layer_rank` climbed
`part_of` and `liveness._layer_reasons` did neither. This module holds the one
answer the three become callers of.

The two properties the disagreement turned on are asserted here rather than
described: a node with its own tag keeps it and does not climb, and a node
without one takes the NEAREST tagged ancestor's. The rest is about what the
function refuses to know — it reads the rule's declared `layers` list, so a
project whose layers are called `tier-*` gets the same answers, and a tag the
declaration does not name is not a layer however much it looks like one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.import_resolver import _part_of_ancestors
from beadloom.graph.rules.layers import (
    LayerPopulation,
    layer_of,
    layer_population,
    own_layer_of,
    part_of_ancestors,
    part_of_generations,
)
from beadloom.graph.rules.types import LayerDef

if TYPE_CHECKING:
    import sqlite3

#: This repository's own declaration, read from `.beadloom/_graph/rules.yml`.
DDD_LAYERS = (
    LayerDef(name="services", tag="layer-service"),
    LayerDef(name="application", tag="layer-application"),
    LayerDef(name="domains", tag="layer-domain"),
    LayerDef(name="infrastructure", tag="layer-infra"),
)

#: A declaration that is NOT this repository's, so every answer below is a
#: property of the function rather than of the tags it happened to be written
#: against.
TIER_LAYERS = (
    LayerDef(name="ui", tag="tier-ui"),
    LayerDef(name="core", tag="tier-core"),
)


class TestOwnLayer:
    """`own_layer_of` — the tag the node itself carries, and nothing else."""

    def test_a_declared_tag_is_the_nodes_layer_by_its_declared_index(self) -> None:
        tags = {"graph": {"layer-domain"}}
        assert own_layer_of("graph", DDD_LAYERS, tags) == 2

    def test_an_undeclared_tag_is_not_a_layer(self) -> None:
        tags = {"graph": {"layer-domain", "external"}}
        assert own_layer_of("graph", TIER_LAYERS, tags) is None

    def test_a_node_the_tag_map_does_not_hold_has_no_layer(self) -> None:
        assert own_layer_of("absent", DDD_LAYERS, {}) is None

    def test_two_declared_tags_resolve_to_the_topmost_declared_one(self) -> None:
        """The declaration decides, not the iteration order of a `set`."""
        tags = {"odd": {"layer-infra", "layer-service"}}
        assert own_layer_of("odd", DDD_LAYERS, tags) == 0


class TestInheritedLayer:
    """`layer_of` — the node's own layer, else the nearest tagged ancestor's."""

    def test_a_node_with_its_own_tag_keeps_it_and_does_not_climb(self) -> None:
        parents = {"repository": {"beadloom"}}
        tags = {"repository": {"layer-infra"}, "beadloom": {"layer-service"}}
        assert layer_of("repository", DDD_LAYERS, parents, tags) == 3

    def test_an_untagged_node_takes_its_parents_layer(self) -> None:
        parents = {"rule-engine": {"graph"}}
        tags = {"graph": {"layer-domain"}}
        assert layer_of("rule-engine", DDD_LAYERS, parents, tags) == 2

    def test_the_nearest_tagged_ancestor_wins_over_a_further_one(self) -> None:
        parents = {"leaf": {"middle"}, "middle": {"root"}}
        tags = {"middle": {"layer-domain"}, "root": {"layer-service"}}
        assert layer_of("leaf", DDD_LAYERS, parents, tags) == 2

    def test_an_untagged_generation_is_climbed_through(self) -> None:
        parents = {"leaf": {"middle"}, "middle": {"root"}}
        tags = {"root": {"layer-service"}}
        assert layer_of("leaf", DDD_LAYERS, parents, tags) == 0

    def test_a_node_with_no_tagged_ancestor_has_no_layer(self) -> None:
        parents = {"leaf": {"middle"}}
        tags = {"other": {"layer-domain"}}
        assert layer_of("leaf", DDD_LAYERS, parents, tags) is None

    def test_a_graph_with_no_part_of_at_all_answers_from_own_tags_only(self) -> None:
        tags = {"a": {"tier-ui"}, "b": {"tier-core"}}
        assert layer_of("a", TIER_LAYERS, {}, tags) == 0
        assert layer_of("b", TIER_LAYERS, {}, tags) == 1
        assert layer_of("c", TIER_LAYERS, {}, tags) is None

    def test_two_ancestors_at_one_distance_resolve_to_the_topmost_declared(self) -> None:
        """A tie is decided by the declaration, not by the parent set's order."""
        parents = {"leaf": {"api", "store"}}
        tags = {"api": {"layer-service"}, "store": {"layer-infra"}}
        assert layer_of("leaf", DDD_LAYERS, parents, tags) == 0

    def test_a_nearer_ancestor_beats_a_topmost_one_further_up(self) -> None:
        parents = {"leaf": {"store"}, "store": {"api"}}
        tags = {"api": {"layer-service"}, "store": {"layer-infra"}}
        assert layer_of("leaf", DDD_LAYERS, parents, tags) == 3


class TestTermination:
    """A `part_of` cycle terminates; it is a graph the loader does not forbid."""

    def test_a_two_node_cycle_terminates(self) -> None:
        parents = {"a": {"b"}, "b": {"a"}}
        assert layer_of("a", DDD_LAYERS, parents, {}) is None

    def test_a_cycle_still_reports_a_layer_declared_inside_it(self) -> None:
        parents = {"a": {"b"}, "b": {"a"}}
        tags = {"b": {"layer-domain"}}
        assert layer_of("a", DDD_LAYERS, parents, tags) == 2

    def test_a_node_that_is_part_of_itself_terminates(self) -> None:
        """The root service is `part_of` itself by this project's convention."""
        parents = {"beadloom": {"beadloom"}}
        tags = {"beadloom": {"layer-service"}}
        assert layer_of("beadloom", DDD_LAYERS, parents, tags) == 0
        assert part_of_ancestors("beadloom", parents) == frozenset()

    def test_a_longer_cycle_terminates(self) -> None:
        parents = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
        assert part_of_ancestors("a", parents) == frozenset({"b", "c"})


class TestGenerations:
    """`part_of_generations` — the one walk, nearest generation first."""

    def test_generations_are_ordered_by_distance(self) -> None:
        parents = {"leaf": {"middle"}, "middle": {"root"}}
        assert part_of_generations("leaf", parents) == [("middle",), ("root",)]

    def test_a_generation_is_sorted_so_the_answer_does_not_move(self) -> None:
        parents = {"leaf": {"store", "api"}}
        assert part_of_generations("leaf", parents) == [("api", "store")]

    def test_an_ancestor_reached_twice_is_reported_at_its_nearest_distance(self) -> None:
        parents = {"leaf": {"api", "store"}, "api": {"root"}, "store": {"root"}}
        assert part_of_generations("leaf", parents) == [("api", "store"), ("root",)]

    def test_a_node_with_no_parent_has_no_generations(self) -> None:
        assert part_of_generations("lonely", {}) == []

    def test_ancestors_are_the_generations_flattened(self) -> None:
        parents = {"leaf": {"middle"}, "middle": {"root"}}
        assert part_of_ancestors("leaf", parents) == frozenset({"middle", "root"})


class TestPopulation:
    """The counter every reader of this rule reports its reach from."""

    def test_an_edge_layered_at_both_ends_is_evaluated(self) -> None:
        tags = {"a": {"layer-service"}, "b": {"layer-domain"}}

        def resolve(ref_id: str) -> int | None:
            return own_layer_of(ref_id, DDD_LAYERS, tags)

        assert layer_population([("a", "b")], resolve) == LayerPopulation(
            evaluated=1, skipped_untagged=0
        )

    def test_an_edge_with_one_untagged_end_is_skipped(self) -> None:
        tags = {"a": {"layer-service"}}

        def resolve(ref_id: str) -> int | None:
            return own_layer_of(ref_id, DDD_LAYERS, tags)

        assert layer_population([("a", "b"), ("b", "a")], resolve) == LayerPopulation(
            evaluated=0, skipped_untagged=2
        )

    def test_the_population_totals_the_edge_set_it_was_given(self) -> None:
        tags = {"a": {"layer-service"}, "b": {"layer-domain"}}

        def resolve(ref_id: str) -> int | None:
            return own_layer_of(ref_id, DDD_LAYERS, tags)

        population = layer_population([("a", "b"), ("a", "c"), ("c", "d")], resolve)
        assert (population.evaluated, population.skipped_untagged) == (1, 2)
        assert population.total == 3

    def test_a_declaration_no_node_carries_reports_a_zero_numerator(self) -> None:
        """The `mutation-run-zero-mutants` shape: the denominator still stands."""

        def resolve(ref_id: str) -> int | None:
            return own_layer_of(ref_id, TIER_LAYERS, {})

        population = layer_population([("a", "b"), ("b", "c")], resolve)
        assert (population.evaluated, population.total) == (0, 2)

    def test_an_empty_edge_set_reports_zero_of_zero(self) -> None:
        population = layer_population([], lambda _ref_id: None)
        assert (population.evaluated, population.skipped_untagged, population.total) == (0, 0, 0)

    def test_the_counter_reads_whatever_resolver_it_is_handed(self) -> None:
        """Own-tag and inherited answers differ, and the counter reports each."""
        parents = {"rule-engine": {"graph"}, "repository": {"infrastructure"}}
        tags = {"graph": {"layer-domain"}, "infrastructure": {"layer-infra"}}
        edges = [("rule-engine", "repository")]

        own = layer_population(edges, lambda ref: own_layer_of(ref, DDD_LAYERS, tags))
        inherited = layer_population(edges, lambda ref: layer_of(ref, DDD_LAYERS, parents, tags))

        assert (own.evaluated, own.skipped_untagged) == (0, 1)
        assert (inherited.evaluated, inherited.skipped_untagged) == (1, 0)


class TestTheResolverKeepsItsAnswers:
    """`import_resolver._part_of_ancestors` delegates and answers what it did.

    It decides which derived import edges are dropped as parent-to-child
    containment, so a change in its answers changes the edge set every rule in
    the engine reads. The expected sets below are written out rather than
    computed, so this compares the code against the shapes rather than against
    itself.
    """

    @staticmethod
    def _resolved(conn: sqlite3.Connection, edges: list[tuple[str, str]]) -> dict[str, set[str]]:
        for src, dst in edges:
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, 'feature', '')"
                " ON CONFLICT DO NOTHING",
                (src,),
            )
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, 'feature', '')"
                " ON CONFLICT DO NOTHING",
                (dst,),
            )
            conn.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, 'part_of')",
                (src, dst),
            )
        return _part_of_ancestors(conn)

    def test_a_chain_gives_every_node_its_whole_ancestry(
        self, schema_db: sqlite3.Connection
    ) -> None:
        resolved = self._resolved(schema_db, [("leaf", "middle"), ("middle", "root")])
        assert resolved == {"leaf": {"middle", "root"}, "middle": {"root"}}

    def test_a_diamond_reports_the_shared_ancestor_once(
        self, schema_db: sqlite3.Connection
    ) -> None:
        resolved = self._resolved(
            schema_db, [("leaf", "api"), ("leaf", "store"), ("api", "root"), ("store", "root")]
        )
        assert resolved == {
            "leaf": {"api", "store", "root"},
            "api": {"root"},
            "store": {"root"},
        }

    def test_a_cycle_terminates_and_excludes_the_node_itself(
        self, schema_db: sqlite3.Connection
    ) -> None:
        resolved = self._resolved(schema_db, [("a", "b"), ("b", "c"), ("c", "a")])
        assert resolved == {"a": {"b", "c"}, "b": {"c", "a"}, "c": {"a", "b"}}

    def test_a_node_that_is_part_of_itself_is_not_its_own_ancestor(
        self, schema_db: sqlite3.Connection
    ) -> None:
        resolved = self._resolved(schema_db, [("beadloom", "beadloom"), ("graph", "beadloom")])
        assert resolved == {"graph": {"beadloom"}}
