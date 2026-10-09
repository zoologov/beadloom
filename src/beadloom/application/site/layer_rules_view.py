# beadloom:domain=application
# beadloom:feature=site-generation
"""Every layer rule the project declares, as the architecture view draws it.

BDL-080 S1b (``beadloom-kgh6``), RFC D2. The view drew ONE stratification — the
first ``layers`` rule by name — so a repository with a backend and a frontend
drew its frontend grey while ``beadloom lint`` judged it. Measured on this
repository on 2026-10-08: two layer rules, the twenty site slices carried the
second one's tags, and the data file named the first one only.

This module reads every rule from the index and answers three questions for the
data file, each from the rule engine's own arithmetic in
:mod:`beadloom.graph.rules.layers`:

- **which rule places a node** — the rule whose tag the node carries itself,
  else the rule its nearest tagged ``part_of`` ancestor carries; at one distance
  the first rule by name. A rule declared with ``scope:`` places nothing outside
  its subtree.
- **which container a rule stratifies** — the declared ``scope:``, else the
  lowest container holding every node the rule places a layer on, else ``""``.
- **which edges are found against** — the union of every rule's verdict, read
  off the rule engine rather than decided here.

The original keys — ``layers``, ``layer_order``, a node's ``layer`` and
``layer_rank`` — are not answered here and keep describing the first rule by
name, so a reader of schema 2 sees what it saw.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.graph.rule_engine import (
    LayerDef,
    LayerExemption,
    LayerRule,
    flagged_layer_edges,
    layer_membership,
    layer_of,
    part_of_ancestors,
    part_of_generations,
    within_scope,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Collection, Iterable, Mapping

logger = logging.getLogger(__name__)

#: The edge kind the view renders a layering verdict on: dependency arrows.
FLAGGED_EDGE_KIND = "depends_on"

#: The distance of a node's OWN tag, against ``1`` for its parent's generation.
_OWN_TAG = 0


def declared_layer_rules(conn: sqlite3.Connection) -> tuple[LayerRule, ...]:
    """Every layer rule the index holds, ordered by name.

    Read from the ``rules`` table — the same indexed graph every other read of
    the view goes through — rather than from ``rules.yml``. The JSON is the one
    ``application.reindex.rules_loader._serialize_rule`` writes; that is a
    coupling between a writer and a reader of one shape, stated here because it
    is the kind of pair that drifts silently.

    The rule's ``severity`` is not in the index and is not reconstructed: it
    decides how loudly a finding is reported, and the view asks only WHICH edges
    are found against. The ``exempt`` entries and the ``scope`` are, because they
    decide exactly that. An index written before a release carried them holds
    neither, so a project that excuses crossings or scopes a rule and renders its
    site without reindexing sees the wider verdict until it does. The ``title``
    is read for the portal to show the rule by; an index without it shows the name.

    A row that is not readable JSON, or declares no layer, is left out and logged:
    one unreadable rule does not take the others' strata with it.
    """
    rows = conn.execute(
        "SELECT name, description, rule_json FROM rules WHERE rule_type = 'layers' ORDER BY name"
    ).fetchall()
    return tuple(rule for row in rows if (rule := _rule_from_row(row)) is not None)


def _rule_from_row(row: sqlite3.Row) -> LayerRule | None:
    name = str(row["name"])
    try:
        definition = json.loads(str(row["rule_json"]))
    except json.JSONDecodeError:
        logger.warning("architecture view: the indexed layer rule %r is not readable JSON", name)
        return None
    if not isinstance(definition, dict):
        return None
    layers = _declared_layers(definition)
    if not layers:
        return None
    scope = definition.get("scope")
    title = definition.get("title")
    return LayerRule(
        name=name,
        description=str(row["description"] or ""),
        layers=layers,
        enforce=str(definition.get("enforce", "top-down")),
        allow_skip=bool(definition.get("allow_skip", True)),
        edge_kind=str(definition.get("edge_kind", "uses")),
        exempt=_declared_exemptions(definition),
        scope=scope if isinstance(scope, str) and scope else None,
        title=title if isinstance(title, str) and title else None,
    )


def _declared_layers(definition: dict[str, object]) -> tuple[LayerDef, ...]:
    """The rule's layers, top to bottom, from its indexed JSON."""
    declared = definition.get("layers")
    if not isinstance(declared, list):
        return ()
    return tuple(
        LayerDef(name=str(layer.get("name", "")), tag=str(layer["tag"]))
        for layer in declared
        if isinstance(layer, dict) and layer.get("tag")
    )


def _declared_exemptions(definition: dict[str, object]) -> tuple[LayerExemption, ...]:
    """The same-layer crossings the rule excuses, from its indexed JSON.

    The entries were validated when the rules file was loaded — each names both
    ends, a reason and an exit condition, or the load failed — so this reads
    them rather than re-checking them. An entry missing an end is dropped
    instead of being reconstructed with an empty glob, which would match
    nothing and read as an entry that excuses nothing.
    """
    declared = definition.get("exempt")
    if not isinstance(declared, list):
        return ()
    return tuple(
        LayerExemption(
            from_glob=str(entry["from"]),
            to_glob=str(entry["to"]),
            reason=str(entry.get("reason", "")),
            until=str(entry.get("until", "")),
        )
        for entry in declared
        if isinstance(entry, dict) and entry.get("from") and entry.get("to")
    )


@dataclass(frozen=True)
class RulePlacement:
    """The rule that places a node, and the node's rank in that rule's layers."""

    rule: str
    rank: int


@dataclass(frozen=True)
class LayerRulesView:
    """Every declared layer rule, each with the tag map its scope hands it.

    ``scoped_tags`` holds, per rule in ``rules`` order, the tags of the nodes
    inside the rule's scope only — :func:`~beadloom.graph.rules.layers.within_scope`'s
    answer, the narrowing the linter applies — so the view cannot place a node
    in a rule the linter does not judge it by. Build it with :func:`layer_rules_view`.
    """

    rules: tuple[LayerRule, ...]
    parents: Mapping[str, Collection[str]]
    scoped_tags: tuple[Mapping[str, Collection[str]], ...]

    def declared(self, ref_ids: Iterable[str]) -> list[dict[str, object]]:
        """Every rule as the data file carries it, ordered by name.

        *ref_ids* is the graph's node set, from which a rule without a declared
        ``scope`` derives the container it stratifies. ``title`` is the rule's
        declared title, ``""`` when it declares none and is shown by its name.
        """
        nodes = tuple(ref_ids)
        return [
            {
                "name": rule.name,
                "title": rule.title or "",
                "scope": rule.scope or self._derived_scope(index, nodes),
                "edge_kind": rule.edge_kind,
                "layers": [
                    {"name": layer.name, "rank": rank, "tag": layer.tag, "token": layer.name}
                    for rank, layer in enumerate(rule.layers)
                ],
            }
            for index, rule in enumerate(self.rules)
        ]

    def _derived_scope(self, index: int, ref_ids: tuple[str, ...]) -> str:
        """The lowest container holding every node rule *index* places a layer on.

        A container HOLDS its parts and is not its own: a rule that places one
        node names the node's container. ``""`` when the rule places no node, or
        when no single container holds them all — the whole graph, said as the
        absence of a box rather than as a box nobody declared.
        """
        rule = self.rules[index]
        stratified = [
            ref_id
            for ref_id in ref_ids
            if layer_of(ref_id, rule.layers, self.parents, self.scoped_tags[index]) is not None
        ]
        if not stratified:
            return ""
        common = frozenset.intersection(
            *(part_of_ancestors(ref_id, self.parents) for ref_id in stratified)
        )
        lowest = sorted(
            candidate
            for candidate in common
            if not any(
                candidate in part_of_ancestors(other, self.parents)
                for other in common
                if other != candidate
            )
        )
        return lowest[0] if lowest else ""

    def placement(self, ref_id: str) -> RulePlacement | None:
        """The rule that places *ref_id* and its rank there; ``None`` when no rule does.

        The nearest declaration wins: the node's own tag is distance 0 and an
        ancestor's is its ``part_of`` generation. Two rules at one distance are
        settled by name, because ``rules`` is ordered by name — never by the
        order rows came back in.
        """
        generations = part_of_generations(ref_id, self.parents)
        found: list[tuple[int, int, int]] = []
        for index, rule in enumerate(self.rules):
            membership = layer_membership(
                ref_id, rule.layers, self.parents, self.scoped_tags[index]
            )
            if membership is None:
                continue
            distance = _OWN_TAG
            if membership.inherited:
                distance = 1 + next(
                    depth
                    for depth, generation in enumerate(generations)
                    if membership.declared_by in generation
                )
            found.append((distance, index, membership.index))
        if not found:
            return None
        _, index, rank = min(found)
        return RulePlacement(rule=self.rules[index].name, rank=rank)

    def judges(self, src: str, dst: str) -> bool:
        """True when a dependency-arrow rule places a layer at BOTH ends of the edge.

        Such an edge was judged, so it carries a verdict; an edge no rule judged
        must not be drawn as healthy.
        """
        return any(
            rule.edge_kind == FLAGGED_EDGE_KIND
            and layer_of(src, rule.layers, self.parents, self.scoped_tags[index]) is not None
            and layer_of(dst, rule.layers, self.parents, self.scoped_tags[index]) is not None
            for index, rule in enumerate(self.rules)
        )

    def flagged(self, conn: sqlite3.Connection) -> frozenset[tuple[str, str]]:
        """The edges ANY rule over dependency arrows finds against — the rules' verdict.

        Asked of the rule engine, never decided here (BDL-070 B4): the view once
        drew an edge red whenever ``dst_rank <= src_rank`` and, measured on this
        repository on 2026-09-13, drew 130 edges red that ``beadloom lint`` found
        nothing against.

        A rule declared over another edge kind is reported by ``beadloom lint``
        and drawn by nothing here: the view renders the flag on dependency
        arrows only. That is a gap in what the picture shows rather than a
        disagreement about what is true.
        """
        found: set[tuple[str, str]] = set()
        for rule in self.rules:
            if rule.edge_kind == FLAGGED_EDGE_KIND:
                found |= flagged_layer_edges(conn, rule)
        return frozenset(found)


def layer_rules_view(
    rules: tuple[LayerRule, ...],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> LayerRulesView:
    """The view over *rules*, each rule handed the tags inside its scope."""
    return LayerRulesView(
        rules=rules,
        parents=parents,
        scoped_tags=tuple(within_scope(rule.scope, (), parents, tags)[1] for rule in rules),
    )
