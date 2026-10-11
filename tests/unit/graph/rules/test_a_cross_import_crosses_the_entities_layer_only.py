"""The layer rule reads ``via: "@x"`` off an edge: legal on entities, a finding elsewhere.

BDL-082 S1a (``beadloom-r15q``), RFC D1. feature-sliced.design, *Public API for
cross-imports*: "entity A can declare a separate public API just for entity B", with the
note "only use this notation on the Entities layer, where eliminating cross-imports is often
unreasonable". The reindex records on a derived ``depends_on`` edge whether every import
behind it lands on the target's ``@x/<importer>``; the layer rule reads that fact off the
edge and never ``code_imports``, so it stays a graph rule.

The layer that may use ``@x`` is the one the rule's ``layers:`` list NAMES ``entities``; the
tags here are not FSD's, so a test that passes read the name rather than a tag.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.graph.rules.cross_imports import (
    CrossImportFact,
    read_cross_import_facts,
)
from beadloom.graph.rules.evaluators import evaluate_layer_rules
from beadloom.graph.rules.layer_crossings import same_layer_statements
from beadloom.graph.rules.layers import same_layer_crossings
from beadloom.graph.rules.types import LayerDef, LayerRule
from tests.support.in_memory_graph import add_node, open_graph

if TYPE_CHECKING:
    import sqlite3

LAYERS = (
    LayerDef(name="features", tag="t-features"),
    LayerDef(name="entities", tag="t-entities"),
)
PARENTS: dict[str, set[str]] = {}
TAGS = {
    "entities-artist": {"t-entities"},
    "entities-song": {"t-entities"},
    "features-b": {"t-features"},
    "features-a": {"t-features"},
}
ARTIST_SONG = ("entities-artist", "entities-song")
B_A = ("features-b", "features-a")

RULE = LayerRule(
    name="fsd-layers",
    description="",
    layers=LAYERS,
    enforce="top-down",
    edge_kind="depends_on",
)


class TestTheCrossingPredicate:
    def test_an_edge_every_import_of_which_is_via_x_on_entities_is_not_a_crossing(self) -> None:
        crossings = same_layer_crossings([ARTIST_SONG], LAYERS, PARENTS, TAGS, via_x={ARTIST_SONG})

        assert crossings == []

    def test_the_same_fact_on_another_layer_is_still_a_crossing(self) -> None:
        crossings = same_layer_crossings([B_A], LAYERS, PARENTS, TAGS, via_x={B_A})

        assert crossings == [B_A]

    def test_an_entities_edge_without_the_fact_is_a_crossing(self) -> None:
        assert same_layer_crossings([ARTIST_SONG], LAYERS, PARENTS, TAGS) == [ARTIST_SONG]

    def test_the_layer_is_known_by_its_declared_name_not_its_tag(self) -> None:
        renamed = (LayerDef(name="features", tag="t-features"), LayerDef("models", "t-entities"))

        crossings = same_layer_crossings(
            [ARTIST_SONG], renamed, PARENTS, TAGS, via_x={ARTIST_SONG}
        )

        assert crossings == [ARTIST_SONG]


class TestWhatTheRuleSays:
    def test_x_outside_entities_is_reported_with_the_specifications_wording(self) -> None:
        facts = {B_A: CrossImportFact(every=True, not_via=None)}

        [finding] = same_layer_statements(RULE, [B_A], PARENTS, TAGS, facts=facts)

        assert finding.from_ref_id == "features-b"
        assert finding.to_ref_id == "features-a"
        assert "`@x` is for the Entities layer only" in finding.message
        assert "only use this notation on the Entities layer" in finding.message
        assert "layer 'features'" in finding.message
        assert finding.remediation is not None
        assert "`entities`" in finding.remediation

    def test_a_mixed_edge_names_the_import_that_does_not_go_through_x(self) -> None:
        facts = {
            ARTIST_SONG: CrossImportFact(every=False, not_via="src/entities/artist/model/rel.ts:2")
        }

        [finding] = same_layer_statements(RULE, [ARTIST_SONG], PARENTS, TAGS, facts=facts)

        assert finding.file_path == "src/entities/artist/model/rel.ts"
        assert finding.line_number == 2
        assert "src/entities/artist/model/rel.ts:2" in finding.message
        assert "not every import" in finding.message

    def test_a_plain_crossing_reads_as_it_did_before(self) -> None:
        [finding] = same_layer_statements(RULE, [ARTIST_SONG], PARENTS, TAGS)

        assert finding.message.startswith("Same-layer crossing: 'entities-artist' depends on")
        assert finding.file_path is None
        assert "@x" not in finding.message


def _graph(*edges: tuple[str, str, dict[str, str]]) -> sqlite3.Connection:
    conn = open_graph()
    for ref_id, tags in TAGS.items():
        add_node(conn, ref_id, "component", *tags)
    for src, dst, extra in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) "
            "VALUES (?, ?, 'depends_on', ?)",
            (src, dst, json.dumps(extra)),
        )
    return conn


def _crossings(conn: sqlite3.Connection) -> list[tuple[str | None, str | None, str]]:
    return [
        (v.from_ref_id, v.to_ref_id, v.message)
        for v in evaluate_layer_rules(conn, [RULE])
        if v.from_ref_id is not None
    ]


class TestTheRuleReadsTheEdge:
    def test_the_fact_is_read_off_the_edge_row(self) -> None:
        conn = _graph(
            (*ARTIST_SONG, {"derived": "imports", "via": "@x"}),
            (
                *B_A,
                {"derived": "imports", "partly_via": "@x", "not_via": "src/features/b/b.ts:3"},
            ),
            ("features-a", "entities-song", {"derived": "imports"}),
        )

        facts = read_cross_import_facts(conn, "depends_on")

        assert facts == {
            ARTIST_SONG: CrossImportFact(every=True, not_via=None),
            B_A: CrossImportFact(every=False, not_via="src/features/b/b.ts:3"),
        }

    def test_an_entities_edge_via_x_is_clean_and_reads_no_code_imports(self) -> None:
        conn = _graph((*ARTIST_SONG, {"derived": "imports", "via": "@x"}))
        conn.execute("DROP TABLE code_imports")

        assert _crossings(conn) == []

    def test_a_features_edge_via_x_is_one_finding_in_the_specifications_words(self) -> None:
        conn = _graph((*B_A, {"derived": "imports", "via": "@x"}))

        [(src, dst, message)] = _crossings(conn)

        assert (src, dst) == B_A
        assert "`@x` is for the Entities layer only" in message

    def test_an_edge_declared_without_the_fact_is_a_crossing(self) -> None:
        conn = _graph((*ARTIST_SONG, {}))

        assert [(s, d) for s, d, _ in _crossings(conn)] == [ARTIST_SONG]
