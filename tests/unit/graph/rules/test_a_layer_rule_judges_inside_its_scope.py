"""A ``layers`` rule may name the container it judges inside, and is held to it.

BDL-080 S1b (``beadloom-kgh6``), RFC D2. ``scope: <ref_id>`` on a layer rule is
read by the loader, refused when it names nothing, and narrows what the rule is
handed to the subtree under that node: the node itself and everything
transitively ``part_of`` it. The narrowing is one pure function, so the
evaluator, the reach count, liveness and the architecture view cannot narrow
differently.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import layers as layers_module
from beadloom.graph.rules.evaluators import evaluate_layer_rules
from beadloom.graph.rules.layer_reach import reach_of, scoped_reach
from beadloom.graph.rules.layers import subtree_of, within_scope
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import LayerDef, LayerRule
from tests.support.in_memory_graph import add_edge, add_node, open_graph

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from pathlib import Path


def _layer_rule_file(tmp_path: Path, scope_line: str) -> Path:
    path = tmp_path / "rules.yml"
    path.write_text(
        "version: 3\nrules:\n"
        "  - name: ui-slices\n"
        "    layers:\n"
        "      - name: pages\n        tag: ui-pages\n"
        "      - name: shared\n        tag: ui-shared\n"
        "    enforce: top-down\n"
        "    edge_kind: depends_on\n" + scope_line,
        encoding="utf-8",
    )
    return path


class TestTheLoaderReadsTheScope:
    def test_a_declared_scope_is_carried_on_the_rule(self, tmp_path: Path) -> None:
        (rule,) = load_rules(_layer_rule_file(tmp_path, "    scope: shop-portal\n"))
        assert isinstance(rule, LayerRule)
        assert rule.scope == "shop-portal"

    def test_a_rule_without_a_scope_has_none(self, tmp_path: Path) -> None:
        (rule,) = load_rules(_layer_rule_file(tmp_path, ""))
        assert isinstance(rule, LayerRule)
        assert rule.scope is None

    @pytest.mark.parametrize("value", ["''", "'  '", "[a, b]", "7"])
    def test_a_scope_that_is_not_a_ref_id_is_refused(self, tmp_path: Path, value: str) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Rule 'ui-slices': 'scope' must name one node by its ref_id, "
                "the container the rule judges inside"
            ),
        ):
            load_rules(_layer_rule_file(tmp_path, f"    scope: {value}\n"))


#: ``portal`` holds two slices and one of them holds a segment; ``api`` is the
#: portal's sibling under ``shop``.
PARENTS = {
    "portal": {"shop"},
    "api": {"shop"},
    "pages": {"portal"},
    "shared": {"portal"},
    "shared-ui": {"shared"},
}


class TestTheSubtreeUnderAScope:
    def test_the_scope_and_every_descendant_are_in_it(self) -> None:
        assert subtree_of("portal", PARENTS) == {"portal", "pages", "shared", "shared-ui"}

    def test_a_sibling_and_an_ancestor_are_not(self) -> None:
        members = subtree_of("portal", PARENTS)
        assert "api" not in members
        assert "shop" not in members

    def test_a_scope_naming_no_node_holds_only_its_name(self) -> None:
        assert subtree_of("nowhere", PARENTS) == {"nowhere"}

    def test_a_containment_cycle_terminates(self) -> None:
        assert subtree_of("a", {"a": {"b"}, "b": {"a"}}) == {"a", "b"}


#: Two edges inside the portal, two with an end outside it.
EDGES = (("pages", "shared"), ("api", "pages"), ("shared-ui", "pages"), ("api", "shop"))

#: ``api`` carries a slice tag outside the portal; ``shop`` holds the portal.
TAGS = {"pages": {"ui-pages"}, "shared": {"ui-shared"}, "api": {"ui-pages"}, "shop": {"x"}}


class TestWithinScope:
    def test_no_scope_hands_everything_on(self) -> None:
        edges, tags = within_scope(None, EDGES, PARENTS, TAGS)
        assert edges == list(EDGES)
        assert tags == TAGS

    def test_an_edge_with_an_end_outside_the_subtree_is_dropped(self) -> None:
        edges, _ = within_scope("portal", EDGES, PARENTS, TAGS)
        assert edges == [("pages", "shared"), ("shared-ui", "pages")]

    def test_a_tag_outside_the_subtree_is_dropped(self) -> None:
        """So no node outside is in a layer, and nothing inside inherits from above."""
        _, tags = within_scope("portal", EDGES, PARENTS, TAGS)
        assert tags == {"pages": {"ui-pages"}, "shared": {"ui-shared"}}


class TestTheEvaluatorNarrowsOnce:
    """BDL-080 S1f (``beadloom-af99.3``), review ``beadloom-m7xq`` finding 5.

    The evaluator narrows a scoped rule's population and counts its reach over
    that narrowed population; the count does not narrow it a second time. Read
    as the number of subtree walks a lint run makes per scoped rule.
    """

    def test_a_scoped_rules_subtree_is_walked_once_per_evaluation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        conn = open_graph()
        try:
            for ref_id, tags in (
                ("shop", ()),
                ("portal", ()),
                ("pages", ("ui-pages",)),
                ("shared", ("ui-shared",)),
            ):
                add_node(conn, ref_id, "component", *tags)
            for child, parent in (("portal", "shop"), ("pages", "portal"), ("shared", "portal")):
                add_edge(conn, child, parent, "part_of")
            add_edge(conn, "shared", "pages", "depends_on")
            conn.commit()
            walked: list[str] = []
            walk = layers_module.subtree_of

            def counted(scope: str, parents: Mapping[str, Collection[str]]) -> frozenset[str]:
                walked.append(scope)
                return walk(scope, parents)

            monkeypatch.setattr(layers_module, "subtree_of", counted)
            found = evaluate_layer_rules(conn, [_scoped_rule("portal")])
        finally:
            conn.close()
        assert walked == ["portal"]
        # The narrowed population is still judged: the upward import is found.
        assert [(v.from_ref_id, v.to_ref_id) for v in found if v.from_ref_id] == [
            ("shared", "pages")
        ]

    def test_the_reach_of_a_narrowed_population_is_the_reach_of_the_whole(self) -> None:
        """Counting what the evaluator narrowed equals counting the whole graph."""
        rule = _scoped_rule("portal")
        edges, tags = within_scope(rule.scope, EDGES, PARENTS, TAGS)
        assert scoped_reach(rule, edges, PARENTS, tags) == reach_of(rule, EDGES, PARENTS, TAGS)


def _scoped_rule(scope: str) -> LayerRule:
    return LayerRule(
        name="ui-slices",
        description="the portal's slices import downward",
        layers=(LayerDef(name="pages", tag="ui-pages"), LayerDef(name="shared", tag="ui-shared")),
        enforce="top-down",
        edge_kind="depends_on",
        scope=scope,
    )
