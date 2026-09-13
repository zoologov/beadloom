"""One declaration of what layer a node is in, and a check that it names something.

BDL-070 A6 (`beadloom-punn`). Two things were true of the layer declaration when
this bead opened, and each was invisible for its own reason.

`validate_rules` had no `LayerRule` in its `isinstance` chain, so a rule could
declare a layer whose tag no node carries and nothing said so. The rule keeps
running, keeps reporting green, and the direction check it performs is one step
shorter than the declaration reads.

And `.beadloom/_graph/rules.yml` carried a second declaration of the same fact —
a top-level `tags:` catalog naming 10 nodes where the graph tags 12 — that no
production code read. Q5 was answered in this bead's comments before any code
changed: the catalog is REMOVED, because rules.yml declares constraints ON the
graph while a node's tags are a property OF the graph, and a second unread
declaration of one fact is the drift this epic exists to remove.

What this module holds:

- the pure predicate — which declared layers no node is in — answers from the
  declaration and the tag map alone;
- both surfaces that ask it, `validate_rules` and the evaluator, get the same
  answer from the same function;
- the evaluator's finding is `warn`, never the rule's declared severity, for the
  reason the population statement is: a statement about a declaration is not a
  boundary breach, and `architecture-layers` ships at `error`;
- on THIS repository nothing is added, because all four declared tags are
  carried — the neutrality Release A claims, measured here rather than argued;
- `rules.yml` is owned by exactly one node, measured over every node in the
  graph.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.application.impact.boundary import open_boundary
from beadloom.application.impact.unread_ownership import unread_ownership
from beadloom.graph.rules.evaluators import evaluate_layer_rules
from beadloom.graph.rules.layer_declaration import (
    LAYER_DECLARATION_RULE_TYPE,
    declaration_statement,
    layers_no_node_is_in,
)
from beadloom.graph.rules.loader import load_rules, validate_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LayerDef, LayerRule
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent

#: This repository's own declaration, read from `.beadloom/_graph/rules.yml`.
DDD_LAYERS = (
    LayerDef(name="services", tag="layer-service"),
    LayerDef(name="application", tag="layer-application"),
    LayerDef(name="domains", tag="layer-domain"),
    LayerDef(name="infrastructure", tag="layer-infra"),
)

#: The file this bead gives an owner, relative to the project root.
THE_RULES_FILE = ".beadloom/_graph/rules.yml"


def _rule(layers: tuple[LayerDef, ...], *, severity: str = "error") -> LayerRule:
    return LayerRule(
        name="architecture-layers",
        description="Services -> application -> domains -> infrastructure",
        layers=layers,
        enforce="top-down",
        allow_skip=True,
        edge_kind="depends_on",
        severity=severity,
    )


def _build_graph(
    db_path: Path,
    *,
    nodes: list[tuple[str, list[str]]],
    edges: list[tuple[str, str, str]],
) -> sqlite3.Connection:
    conn = open_db(db_path)
    create_schema(conn)
    for ref_id, tags in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            (ref_id, "feature", ref_id, json.dumps({"tags": tags})),
        )
    for src, dst, kind in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )
    conn.commit()
    return conn


@pytest.fixture()
def one_empty_layer(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Three of four declared layers populated: the case nothing reported.

    Two populated layers is what liveness needs before it calls the rule live,
    so this graph is one the rule runs on — and the empty fourth layer is a hole
    in a declaration that reads complete.
    """
    conn = _build_graph(
        tmp_path / "one-empty.db",
        nodes=[
            ("svc", ["layer-service"]),
            ("app", ["layer-application"]),
            ("dom", ["layer-domain"]),
        ],
        edges=[("svc", "app", "depends_on"), ("app", "dom", "depends_on")],
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def every_layer_populated(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """A graph in which every declared layer holds at least one node."""
    conn = _build_graph(
        tmp_path / "populated.db",
        nodes=[
            ("svc", ["layer-service"]),
            ("app", ["layer-application"]),
            ("dom", ["layer-domain"]),
            ("infra", ["layer-infra"]),
        ],
        edges=[("svc", "app", "depends_on")],
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def nothing_tagged(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """A graph carrying none of the declared tags — liveness already names them."""
    conn = _build_graph(
        tmp_path / "nothing.db",
        nodes=[("a", []), ("b", [])],
        edges=[("a", "b", "depends_on")],
    )
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------


class TestLayersNoNodeIsIn:
    """Which declared layers the graph holds no node for."""

    def test_names_the_empty_layer(self) -> None:
        empty = layers_no_node_is_in(
            DDD_LAYERS,
            {"svc": {"layer-service"}, "dom": {"layer-domain"}},
        )
        assert empty == ("layer-application", "layer-infra")

    def test_answers_in_declaration_order_not_alphabetical(self) -> None:
        """The declaration decides the order, so two runs state one list."""
        layers = (
            LayerDef(name="z-top", tag="zzz"),
            LayerDef(name="a-bottom", tag="aaa"),
        )
        assert layers_no_node_is_in(layers, {}) == ("zzz", "aaa")

    def test_silent_when_every_layer_is_populated(self) -> None:
        assert (
            layers_no_node_is_in(
                DDD_LAYERS,
                {
                    "s": {"layer-service"},
                    "a": {"layer-application"},
                    "d": {"layer-domain"},
                    "i": {"layer-infra"},
                },
            )
            == ()
        )

    def test_a_node_carrying_several_tags_populates_each(self) -> None:
        """Membership is asked of the tag, not of the node's single layer."""
        assert (
            layers_no_node_is_in(
                DDD_LAYERS,
                {"everything": {"layer-service", "layer-application"}},
            )
            == ("layer-domain", "layer-infra")
        )


# ---------------------------------------------------------------------------
# validate_rules — the public API that had no LayerRule case
# ---------------------------------------------------------------------------


class TestValidateRulesSeesLayerRules:
    """`validate_rules` names a layer tag the nodes table does not carry."""

    def test_reports_the_unpopulated_tag(self, one_empty_layer: sqlite3.Connection) -> None:
        warnings = validate_rules([_rule(DDD_LAYERS)], one_empty_layer)
        assert len(warnings) == 1
        assert "layer-infra" in warnings[0]
        assert "architecture-layers" in warnings[0]

    def test_silent_when_every_declared_tag_is_carried(
        self, every_layer_populated: sqlite3.Connection
    ) -> None:
        assert validate_rules([_rule(DDD_LAYERS)], every_layer_populated) == []

    def test_names_every_empty_layer_in_one_warning_per_rule(
        self, nothing_tagged: sqlite3.Connection
    ) -> None:
        """One warning for the rule, not one per tag: the rule is the subject."""
        warnings = validate_rules([_rule(DDD_LAYERS)], nothing_tagged)
        assert len(warnings) == 1
        for layer in DDD_LAYERS:
            assert layer.tag in warnings[0]


# ---------------------------------------------------------------------------
# The finding the readers past `validate_rules` receive
# ---------------------------------------------------------------------------


class TestTheFinding:
    """What the evaluator emits, and at what severity."""

    def test_the_evaluator_emits_it(self, one_empty_layer: sqlite3.Connection) -> None:
        findings = evaluate_layer_rules(one_empty_layer, [_rule(DDD_LAYERS)])
        declaration = [f for f in findings if f.rule_type == LAYER_DECLARATION_RULE_TYPE]
        assert len(declaration) == 1
        assert "layer-infra" in declaration[0].message

    def test_it_is_warn_never_the_rules_declared_severity(
        self, one_empty_layer: sqlite3.Connection
    ) -> None:
        """`architecture-layers` ships at `error` in every project that copied it.

        A statement about a declaration is not a boundary breach, and emitting it
        at the declared severity would turn a green Gate red on upgrade for a
        graph nobody changed.
        """
        findings = evaluate_layer_rules(one_empty_layer, [_rule(DDD_LAYERS, severity="error")])
        declaration = [f for f in findings if f.rule_type == LAYER_DECLARATION_RULE_TYPE]
        assert [f.severity for f in declaration] == ["warn"]

    def test_it_carries_a_remediation(self, one_empty_layer: sqlite3.Connection) -> None:
        findings = evaluate_layer_rules(one_empty_layer, [_rule(DDD_LAYERS)])
        declaration = [f for f in findings if f.rule_type == LAYER_DECLARATION_RULE_TYPE]
        assert declaration[0].remediation

    def test_silent_when_fewer_than_two_layers_are_populated(
        self, nothing_tagged: sqlite3.Connection
    ) -> None:
        """Liveness already names the empty layers then; twice is once too many."""
        findings = evaluate_layer_rules(nothing_tagged, [_rule(DDD_LAYERS)])
        assert [f for f in findings if f.rule_type == LAYER_DECLARATION_RULE_TYPE] == []

    def test_silent_when_every_layer_is_populated(
        self, every_layer_populated: sqlite3.Connection
    ) -> None:
        findings = evaluate_layer_rules(every_layer_populated, [_rule(DDD_LAYERS)])
        assert [f for f in findings if f.rule_type == LAYER_DECLARATION_RULE_TYPE] == []

    def test_both_surfaces_answer_from_one_function(
        self, one_empty_layer: sqlite3.Connection
    ) -> None:
        """The warning and the finding name the same tags, by construction.

        Two implementations of "which layer is empty" would be free to disagree,
        which is the defect this epic is about one level up.
        """
        rule = _rule(DDD_LAYERS)
        tags = node_tags(one_empty_layer).as_mapping()
        empty = layers_no_node_is_in(rule.layers, tags)
        statement = declaration_statement(rule, tags)
        warnings = validate_rules([rule], one_empty_layer)
        for tag in empty:
            assert tag in statement[0].message
            assert tag in warnings[0]


# ---------------------------------------------------------------------------
# This repository: the declaration it ships, and the file's owner
# ---------------------------------------------------------------------------


class TestThisRepository:
    """What the removal and the new check do to this project's own graph."""

    def test_the_rules_file_carries_no_tags_catalog(self) -> None:
        """Q5, as data: one declaration of a node's layer, and it is the node."""
        data = yaml.safe_load((REPO_ROOT / THE_RULES_FILE).read_text(encoding="utf-8"))
        assert "tags" not in data

    def test_the_loader_no_longer_parses_a_tags_catalog(self) -> None:
        """`load_rules_with_tags` is withdrawn with the block it parsed.

        Keeping a parser for a block nothing applies ships the trap rather than
        closing it.
        """
        from beadloom.graph.rules import loader

        assert not hasattr(loader, "load_rules_with_tags")

    def test_every_declared_layer_is_populated_here(
        self, live_repo_reindexed: Path
    ) -> None:
        """The neutrality claim for this repository, measured rather than argued."""
        db_path = live_repo_reindexed / ".beadloom" / "beadloom.db"
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            declared = [
                rule
                for rule in load_rules(live_repo_reindexed / ".beadloom" / "_graph" / "rules.yml")
                if isinstance(rule, LayerRule)
            ]
            tags = node_tags(conn).as_mapping()
            for rule in declared:
                assert layers_no_node_is_in(rule.layers, tags) == ()
        finally:
            conn.close()

    def test_exactly_one_node_owns_the_rules_file(self, live_repo_reindexed: Path) -> None:
        """Measured over every node in the graph, not over one impact answer.

        `impact` derives the nodes it names from Python call sites, and this
        file is YAML, so no code sweep can reach its owner. The claim the bead
        makes — one owner, not none and not two — is therefore held against the
        whole node population, which is the stronger measurement.
        """
        boundary = open_boundary(live_repo_reindexed)
        db_path = live_repo_reindexed / ".beadloom" / "beadloom.db"
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            every_node = [str(row[0]) for row in conn.execute("SELECT ref_id FROM nodes")]
        finally:
            conn.close()
        owners = [
            owned.node
            for owned in unread_ownership(boundary, every_node, live_repo_reindexed)
            if THE_RULES_FILE in owned.files
        ]
        assert len(owners) == 1

    def test_the_owner_owns_the_rules_file_and_nothing_else(
        self, live_repo_reindexed: Path
    ) -> None:
        """So the `Owns unread` cell reads `1 — .beadloom/_graph/rules.yml`.

        A node whose source were the whole `_graph/` directory would own a
        hundred files and the cell would lead with whichever sorted first.
        """
        boundary = open_boundary(live_repo_reindexed)
        owned = unread_ownership(boundary, ["architecture-rules"], live_repo_reindexed)
        assert [entry.files for entry in owned] == [(THE_RULES_FILE,)]
