# beadloom:domain=graph
# beadloom:feature=rule-engine
"""What layer a node is in — one answer, derived from the declaration.

Three bodies answered this question and they disagreed.
:func:`~beadloom.graph.rules.evaluators.evaluate_layer_rules` read a node's OWN
tags and skipped every edge whose ends carried none, so on this repository at
``aa4bfad4`` it judged 16 of 362 live ``depends_on`` edges while 354 of them have
a layer at both ends by ``part_of`` ancestry.
``application.architecture_view._layer_rank`` climbed ``part_of`` but hardcoded
the four tags and their ranks, so it cannot serve a project whose layers are
declared differently — and Beadloom ships to those projects.
``liveness._layer_reasons`` did neither.

This module is the answer the three become callers of. It knows nothing except
what it is handed:

``layers``
    the rule's own ``layers`` list, top-to-bottom. **No layer tag is written
    down here.** A layer is whatever the declaration names one, which is why a
    project whose layers are ``tier-ui`` / ``tier-core`` gets the same answers.
``parents``
    each node's DIRECT ``part_of`` containers.
``tags``
    each node's own tags.

Everything is pure — no connection, no filesystem — so the rule's hardest
property is testable without a graph, and the caller decides how the three
inputs are read.

**A layer is returned as its INDEX in the declared order** (``0`` is topmost),
because the index IS what the rule compares to decide direction; the name and
the tag are one subscript away for a caller that renders rather than decides.

Two answers could be read off an ambiguous graph, and both are settled by the
DECLARATION rather than by a dictionary's iteration order:

- a node carrying two declared layer tags is in the topmost of them. The
  evaluator this replaces iterated the node's tag ``set`` and took the first
  match, so its answer depended on hash order.
- two tagged ancestors at the SAME distance resolve to the topmost of the two.
  There is no uniformly conservative choice — a topmost source makes a downward
  edge legal while a topmost target makes it a finding — so the tie is settled
  for determinism, and stated here so a reader knows the ambiguous node was
  answered rather than left to chance. Measured on this repository's graph on
  2026-09-12: no node has more than one ``part_of`` parent, so the tie is
  unreachable here and exists for the graphs this ships to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Mapping, Sequence

    from beadloom.graph.rules.types import LayerDef


#: A layered rule needs two populated layers before "above" and "below" mean
#: anything: with one, there is no direction for an edge to violate. Declared
#: here rather than in :mod:`.liveness`, because :mod:`.layer_declaration` stays
#: silent under exactly the condition liveness reports — and a threshold written
#: twice is a pair of reports that can drift into saying the same thing twice or
#: neither of them saying it.
MIN_POPULATED_LAYERS = 2


def part_of_generations(
    ref_id: str, parents: Mapping[str, Collection[str]]
) -> list[tuple[str, ...]]:
    """The node's ``part_of`` ancestors, nearest generation first.

    **This is the one ``part_of`` ancestry walk in the rule engine's reach**;
    :func:`beadloom.graph.import_resolver._part_of_ancestors` builds the parent
    map and calls :func:`part_of_ancestors` rather than climbing it a second
    time.

    Each ancestor appears once, in the nearest generation that reaches it, and
    each generation is sorted, so an answer derived from it does not move with
    the iteration order of a ``set``. A cycle terminates: a node already seen is
    not expanded again, and a node that is ``part_of`` itself — the convention
    this project's root service follows — is its own ancestor of no generation.
    """
    seen = {ref_id}
    frontier = [ref_id]
    generations: list[tuple[str, ...]] = []
    while frontier:
        nxt: set[str] = set()
        for node in frontier:
            nxt.update(parent for parent in parents.get(node, ()) if parent not in seen)
        if not nxt:
            break
        seen |= nxt
        generations.append(tuple(sorted(nxt)))
        frontier = sorted(nxt)
    return generations


def part_of_ancestors(ref_id: str, parents: Mapping[str, Collection[str]]) -> frozenset[str]:
    """Every node *ref_id* is transitively ``part_of``, as a set."""
    return frozenset(
        ancestor for generation in part_of_generations(ref_id, parents) for ancestor in generation
    )


def own_layer_of(
    ref_id: str,
    layers: Sequence[LayerDef],
    tags: Mapping[str, Collection[str]],
) -> int | None:
    """Index of the layer the node's OWN tags declare, or ``None``.

    Iterates the DECLARATION, not the node's tags, so a node carrying two
    declared tags lands in the topmost of them for every caller and every run.
    """
    node_tags = tags.get(ref_id) or ()
    for index, layer in enumerate(layers):
        if layer.tag in node_tags:
            return index
    return None


def layer_of(
    ref_id: str,
    layers: Sequence[LayerDef],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> int | None:
    """Index of the layer the node is in: its own, else its nearest ancestor's.

    A node that declares a layer KEEPS it and does not climb: a node tagged as a
    domain inside a container tagged as a service is a domain, not a service.
    Otherwise the nearest ``part_of`` generation holding a declared layer
    decides, and ``None`` when no generation does: an untagged node with no
    tagged container has no layer, which is a different fact from being in the
    bottom one.
    """
    own = own_layer_of(ref_id, layers, tags)
    if own is not None:
        return own
    for generation in part_of_generations(ref_id, parents):
        declared = [
            index
            for index in (own_layer_of(ancestor, layers, tags) for ancestor in generation)
            if index is not None
        ]
        if declared:
            return min(declared)
    return None


def tagged_containers(
    ref_id: str,
    layers: Sequence[LayerDef],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> frozenset[str]:
    """Every node that gives *ref_id* a layer: itself when it declares one, plus ancestors.

    Reflexive on purpose. A node that declares a layer is the container of its
    own layer membership, and without that a part would "cross" with the very
    container it is inside — ``ledger-api -> ledger`` is an edge into the thing
    it is part of, which is the most internal edge a graph has.
    """
    found = {
        ancestor
        for generation in part_of_generations(ref_id, parents)
        for ancestor in generation
        if own_layer_of(ancestor, layers, tags) is not None
    }
    if own_layer_of(ref_id, layers, tags) is not None:
        found.add(ref_id)
    return frozenset(found)


def shares_tagged_ancestor(
    src_ref_id: str,
    dst_ref_id: str,
    layers: Sequence[LayerDef],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> bool:
    """True when one container the declaration gives a layer holds BOTH ends.

    This is the predicate BDL-070 RFC Q1 decided, on a measurement: of this
    repository's 132 same-layer ``depends_on`` edges, 116 run between two parts
    of one domain and 16 between peers. The two predicates that existed before
    it split that population 0/132 and 132/0 — one passed every same-layer edge
    and the other flagged every one — so neither could tell an internal edge
    from a peer crossing.

    A container that carries no declared layer tag shares nothing here, which is
    what makes the predicate say anything at all: this project's root service
    holds every domain and every service and is untagged, so peers under it
    cross. Tagging that root would make every same-layer edge legal by
    construction.
    """
    return bool(
        tagged_containers(src_ref_id, layers, parents, tags)
        & tagged_containers(dst_ref_id, layers, parents, tags)
    )


def same_layer_crossings(
    edges: Iterable[tuple[str, str]],
    layers: Sequence[LayerDef],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> list[tuple[str, str]]:
    """The edges of *edges* that run inside one layer between ends sharing no container.

    An edge whose ends are in DIFFERENT layers is not here: direction is the
    rest of the layer rule's business, and an edge with an unlayered end is not
    judged at all. Order is the caller's, so a report over the result reads in
    the order the edge set was handed over rather than in a set's.
    """
    crossings: list[tuple[str, str]] = []
    for src_ref_id, dst_ref_id in edges:
        src_layer = layer_of(src_ref_id, layers, parents, tags)
        dst_layer = layer_of(dst_ref_id, layers, parents, tags)
        if src_layer is None or dst_layer is None or src_layer != dst_layer:
            continue
        if not shares_tagged_ancestor(src_ref_id, dst_ref_id, layers, parents, tags):
            crossings.append((src_ref_id, dst_ref_id))
    return crossings


@dataclass(frozen=True)
class LayerPopulation:
    """How much of an edge set a layer rule actually judged.

    ``evaluated`` is the edges with a layer at BOTH ends; ``skipped_untagged``
    is the rest, which the rule passes over in silence. The green line names no
    population today, so 16 of 362 is reported in the words that would report
    362 of 362 — this pair is what makes the two readable apart.
    """

    evaluated: int
    skipped_untagged: int

    @property
    def total(self) -> int:
        """The edge set the rule was handed, judged or not."""
        return self.evaluated + self.skipped_untagged


def layer_population(
    edges: Iterable[tuple[str, str]],
    layer_at: Callable[[str], int | None],
) -> LayerPopulation:
    """Count *edges* by whether *layer_at* resolves a layer at both ends.

    The resolver is a parameter because the same edge set has two populations
    worth stating — what own-tags reach and what ancestry reaches — and the
    difference between them is this epic's whole subject. Reporting is the
    caller's; this returns the numbers.
    """
    evaluated = 0
    skipped = 0
    for src_ref_id, dst_ref_id in edges:
        if layer_at(src_ref_id) is None or layer_at(dst_ref_id) is None:
            skipped += 1
        else:
            evaluated += 1
    return LayerPopulation(evaluated=evaluated, skipped_untagged=skipped)
