# beadloom:domain=graph
# beadloom:feature=rule-engine
"""The set of edges a layer rule finds against, for an instrument that renders.

BDL-070 B4 (`beadloom-w34m`). The rule engine reports its verdict as findings
with messages and remediations, which is what a person reads. An instrument that
DRAWS the graph needs the same verdict as a set of edges, and until this module
existed the one that draws it answered the question itself: ``architecture_view``
flagged every ``depends_on`` edge at ``dst_rank <= src_rank``, which is every
edge pointing up and every edge staying inside one layer. Measured on this
repository on 2026-09-13 over a warm full rebuild of the index, the view flagged
130 edges and the rule found against none of them.

**This is not a fourth predicate — it is a projection of the rule's own
verdict.** The findings are produced by
:func:`~beadloom.graph.rules.evaluators.evaluate_layer_rules` and the edges are
read off them. A caller therefore gets the direction check, the skip check, the
same-layer predicate RFC Q1 decided and the ``exempt:`` entries a project wrote,
without any of the four being stated twice. The alternative — a shared predicate
called by both — was rejected for this seam: it keeps two call sites that agree
only as long as somebody keeps them agreeing, which is the failure this bead
closes.

The cost is one extra evaluation of the rule for a caller that also lints. It is
a pass over the edge set in memory, and it buys a disagreement that cannot
reappear between releases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.evaluators import evaluate_layer_rules
from beadloom.graph.rules.types import LAYER_EDGE_RULE_TYPE

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules.types import LayerRule


def flagged_layer_edges(
    conn: sqlite3.Connection, rule: LayerRule
) -> frozenset[tuple[str, str]]:
    """Every ``(src, dst)`` *rule* finds against in the indexed graph.

    Empty when the rule finds against nothing, which is a different fact from
    the rule judging nothing: what it reached is
    :func:`~beadloom.graph.rules.layer_reach.layer_rule_reach`'s answer, and a
    caller that renders a verdict per edge needs both — an edge the rule never
    judged must not be drawn as healthy.

    The pairs are the ``ref_id`` ends of the rule's edge findings only. A
    finding about the rule itself — the population it judged, a declared layer
    no node carries, an exemption excusing nothing — names no edge and is not
    here.
    """
    return frozenset(
        (violation.from_ref_id, violation.to_ref_id)
        for violation in evaluate_layer_rules(conn, [rule])
        if violation.rule_type == LAYER_EDGE_RULE_TYPE
        and violation.from_ref_id is not None
        and violation.to_ref_id is not None
    )
