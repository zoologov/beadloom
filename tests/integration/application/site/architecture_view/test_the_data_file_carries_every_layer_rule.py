"""The architecture data file carries every layer rule, and its original keys keep their meaning.

BDL-080 S1b (``beadloom-kgh6``), RFC D2. Schema 2 stays: ``layers``,
``layer_order``, a node's ``layer`` and ``layer_rank`` describe the FIRST layer
rule by name, as they did. Added beside them:

- ``layer_rules``: every ``layers`` rule, ``{name, title, scope, edge_kind,
  layers: [{name, rank, tag, token}]}``, ordered by name. ``title`` is the
  rule's declared ``title:``, else ``""`` (BDL-080 S1e). ``scope`` is the rule's
  declared ``scope:``, else derived — the lowest container holding every node
  the rule stratifies — else ``""``. ``token`` is the layer's name.
- per node ``layer_rule`` and ``layer_rule_rank``: the rule that places the node
  and its rank there. A node is placed by the rule whose tag it carries itself,
  else by the rule its nearest tagged ``part_of`` ancestor carries; at one
  distance the first rule by name wins.
- a ``depends_on`` edge's ``violation`` is the union of every rule's verdict.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from beadloom.application.site.architecture_view import build_architecture_view_data
from tests.support.in_memory_graph import add_edge, add_node, open_graph

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence

#: The keys this bead adds; every other key is the one schema 2 already had.
NEW_TOP_LEVEL_KEYS = ("layer_rules",)
NEW_NODE_KEYS = ("layer_rule", "layer_rule_rank")


def _declare(
    conn: sqlite3.Connection,
    name: str,
    tags: Sequence[str],
    *,
    scope: str | None = None,
    edge_kind: str = "depends_on",
    title: str | None = None,
) -> None:
    """A layer rule written where a reindexed project carries it, layer name = tag's tail."""
    rule: dict[str, object] = {
        "layers": [{"name": tag.split("-", 1)[1], "tag": tag} for tag in tags],
        "enforce": "top-down",
        "allow_skip": True,
        "edge_kind": edge_kind,
    }
    if scope is not None:
        rule["scope"] = scope
    if title is not None:
        rule["title"] = title
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
        "VALUES (?, ?, 'layers', ?, 1)",
        (name, f"{name}, declared", json.dumps(rule)),
    )


BACKEND = ("tier-web", "tier-core")
FRONTEND = ("ui-pages", "ui-widgets", "ui-shared")


def _portal_graph(conn: sqlite3.Connection) -> None:
    """``shop`` holds a backend and a portal; the portal's slices carry their own tags."""
    add_node(conn, "shop", "service")
    add_node(conn, "api", "domain", "tier-web")
    add_node(conn, "core", "domain", "tier-core")
    add_node(conn, "portal", "service", "tier-web")
    add_node(conn, "pages", "component", "ui-pages")
    add_node(conn, "widgets", "component", "ui-widgets")
    add_node(conn, "widgets-ui", "component")
    add_node(conn, "shared", "component", "ui-shared")
    add_node(conn, "loose", "component")
    for child, parent in (
        ("api", "shop"),
        ("core", "shop"),
        ("portal", "shop"),
        ("pages", "portal"),
        ("widgets", "portal"),
        ("widgets-ui", "widgets"),
        ("shared", "portal"),
    ):
        add_edge(conn, child, parent, "part_of")
    for src, dst in (
        ("api", "core"),
        ("core", "api"),
        ("pages", "widgets"),
        ("shared", "widgets"),
        ("widgets-ui", "shared"),
    ):
        add_edge(conn, src, dst, "depends_on")


def _built(*rules: tuple[str, Sequence[str], str | None]) -> dict[str, Any]:
    conn = open_graph()
    try:
        _portal_graph(conn)
        for name, tags, scope in rules:
            _declare(conn, name, tags, scope=scope)
        conn.commit()
        return build_architecture_view_data(conn, pages={})
    finally:
        conn.close()


def _nodes(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(node["id"]): node for node in data["nodes"]}


def _without_new_keys(data: dict[str, Any]) -> dict[str, Any]:
    stripped = {key: value for key, value in data.items() if key not in NEW_TOP_LEVEL_KEYS}
    stripped["nodes"] = [
        {key: value for key, value in node.items() if key not in NEW_NODE_KEYS}
        for node in data["nodes"]
    ]
    return stripped


class TestTheRulesAreListed:
    def test_every_rule_is_listed_by_name_with_its_layers_and_their_names_as_tokens(
        self,
    ) -> None:
        data = _built(("ui-slices", FRONTEND, None), ("architecture", BACKEND, None))
        assert data["layer_rules"] == [
            {
                "name": "architecture",
                "title": "",
                "scope": "shop",
                "edge_kind": "depends_on",
                "layers": [
                    {"name": "web", "rank": 0, "tag": "tier-web", "token": "web"},
                    {"name": "core", "rank": 1, "tag": "tier-core", "token": "core"},
                ],
            },
            {
                "name": "ui-slices",
                "title": "",
                "scope": "portal",
                "edge_kind": "depends_on",
                "layers": [
                    {"name": "pages", "rank": 0, "tag": "ui-pages", "token": "pages"},
                    {"name": "widgets", "rank": 1, "tag": "ui-widgets", "token": "widgets"},
                    {"name": "shared", "rank": 2, "tag": "ui-shared", "token": "shared"},
                ],
            },
        ]

    def test_a_declared_scope_is_named_instead_of_the_derived_one(self) -> None:
        data = _built(("architecture", BACKEND, "portal"))
        assert [rule["scope"] for rule in data["layer_rules"]] == ["portal"]

    def test_a_rule_that_stratifies_nothing_names_no_scope(self) -> None:
        data = _built(("nobody", ("x-top", "x-bottom"), None))
        assert [rule["scope"] for rule in data["layer_rules"]] == [""]

    def test_a_rule_stratifying_one_node_names_the_node_that_holds_it(self) -> None:
        """The scope HOLDS the population, so a single tagged node is not its own scope."""
        data = _built(("solo", ("ui-pages", "x-bottom"), None))
        assert [rule["scope"] for rule in data["layer_rules"]] == ["portal"]

    def test_a_project_with_no_layer_rule_lists_none(self) -> None:
        data = _built()
        assert data["layer_rules"] == []
        for node in data["nodes"]:
            assert (node["layer_rule"], node["layer_rule_rank"]) == ("", None)


class TestTheRulesCarryTheirTitles:
    """BDL-080 S1e (``beadloom-af99.2``): the name the portal shows a rule by."""

    def test_a_declared_title_is_carried_beside_the_rules_name(self) -> None:
        conn = open_graph()
        try:
            _portal_graph(conn)
            _declare(conn, "architecture", BACKEND, title="Backend order")
            _declare(conn, "ui-slices", FRONTEND)
            conn.commit()
            data = build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        titled = [(rule["name"], rule["title"]) for rule in data["layer_rules"]]
        assert titled == [("architecture", "Backend order"), ("ui-slices", "")]

    def test_a_title_places_no_node_differently(self) -> None:
        """The title is a name for a reader; what the rule places and finds is its own."""
        conn = open_graph()
        try:
            _portal_graph(conn)
            _declare(conn, "architecture", BACKEND, title="Backend order")
            _declare(conn, "ui-slices", FRONTEND, title="Storefront FSD")
            conn.commit()
            titled = build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        plain = _built(("architecture", BACKEND, None), ("ui-slices", FRONTEND, None))
        assert titled["nodes"] == plain["nodes"]
        assert titled["edges"] == plain["edges"]


class TestEachNodeIsPlacedByOneRule:
    def test_an_own_tag_places_the_node_over_an_inherited_layer(self) -> None:
        nodes = _nodes(_built(("architecture", BACKEND, None), ("ui-slices", FRONTEND, None)))
        assert (nodes["widgets"]["layer_rule"], nodes["widgets"]["layer_rule_rank"]) == (
            "ui-slices",
            1,
        )
        assert (nodes["portal"]["layer_rule"], nodes["portal"]["layer_rule_rank"]) == (
            "architecture",
            0,
        )

    def test_the_nearest_tagged_ancestor_decides_for_an_untagged_node(self) -> None:
        """`widgets-ui` is one hop from `widgets` (ui) and two from `portal` (tier)."""
        nodes = _nodes(_built(("architecture", BACKEND, None), ("ui-slices", FRONTEND, None)))
        assert (nodes["widgets-ui"]["layer_rule"], nodes["widgets-ui"]["layer_rule_rank"]) == (
            "ui-slices",
            1,
        )

    def test_a_node_no_rule_reaches_is_placed_by_none(self) -> None:
        nodes = _nodes(_built(("architecture", BACKEND, None), ("ui-slices", FRONTEND, None)))
        assert (nodes["loose"]["layer_rule"], nodes["loose"]["layer_rule_rank"]) == ("", None)

    def test_at_one_distance_the_first_rule_by_name_places_the_node(self) -> None:
        """Two rules declaring the same tag: a tie, settled by name, never by order of rows."""
        nodes = _nodes(_built(("zeta", BACKEND, None), ("alpha", BACKEND, None)))
        assert nodes["api"]["layer_rule"] == "alpha"

    def test_a_node_outside_a_rules_scope_is_not_placed_by_it(self) -> None:
        """`api` carries `tier-web`; a tier rule scoped to the portal does not reach it."""
        nodes = _nodes(_built(("scoped", BACKEND, "portal")))
        assert (nodes["api"]["layer_rule"], nodes["api"]["layer_rule_rank"]) == ("", None)
        assert (nodes["portal"]["layer_rule"], nodes["portal"]["layer_rule_rank"]) == (
            "scoped",
            0,
        )


class TestTheOriginalKeysKeepTheirMeaning:
    def test_a_second_rule_changes_no_original_key(self) -> None:
        """The data file with both rules, minus the new keys, is the data file with the first."""
        both = _built(("architecture", BACKEND, None), ("ui-slices", FRONTEND, None))
        first = _built(("architecture", BACKEND, None))
        assert _without_new_keys(both) == _without_new_keys(first) | {
            "edges": _without_new_keys(both)["edges"]
        }
        changed = [
            (e["src"], e["dst"])
            for e, f in zip(both["edges"], first["edges"], strict=True)
            if e != f
        ]
        # The one edge whose drawing moves is the one only the second rule finds against.
        assert changed == [("shared", "widgets")]

    def test_the_new_keys_are_the_only_keys_added(self) -> None:
        both = _built(("architecture", BACKEND, None), ("ui-slices", FRONTEND, None))
        first = _built(("architecture", BACKEND, None))
        assert set(both) == set(first)
        assert set(_without_new_keys(both)) == set(first) - set(NEW_TOP_LEVEL_KEYS)


class TestTheVerdictIsTheUnionOverRules:
    def test_an_edge_either_rule_finds_against_is_drawn_as_a_violation(self) -> None:
        data = _built(("architecture", BACKEND, None), ("ui-slices", FRONTEND, None))
        drawn = {
            (e["src"], e["dst"]): e.get("violation")
            for e in data["edges"]
            if e["kind"] == "depends_on"
        }
        assert drawn[("core", "api")] is True  # the backend's finding
        assert drawn[("shared", "widgets")] is True  # the frontend's finding
        assert drawn[("pages", "widgets")] is False
        assert drawn[("api", "core")] is False
