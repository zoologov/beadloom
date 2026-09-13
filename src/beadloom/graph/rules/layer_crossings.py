# beadloom:domain=graph
# beadloom:feature=rule-engine
"""What a layer rule says about a dependency that stays inside one layer.

BDL-070 B3 (`beadloom-ku26`). Two predicates existed for this and they split the
same population 0/130 and 130/0: ``evaluators.py`` passed every same-layer edge
(``# Same layer -- always OK``) and ``architecture_view.py`` flagged every one
(``dst_rank <= src_rank``). Neither could tell a dependency between two parts of
one domain from a dependency between two peer domains — 116 of this
repository's 130 same-layer edges are the first and 14 are the second, measured
2026-09-13.

RFC Q1, decided by the owner: an edge inside one layer is legal when both ends
share a container the declaration gives a layer, and a finding when they do not.
:func:`~beadloom.graph.rules.layers.same_layer_crossings` applies that
predicate; this module decides what the rule SAYS about what it finds, and hands
the excusing to :mod:`.layer_exemptions`.

The split is deliberate and is the same one :mod:`.exemptions` draws for the
import boundary rules: one module decides what crosses, one decides what an
exemption does about it, and one — this one — turns the pair into findings. A
project with a crossing it has decided about writes an ``exempt:`` entry with a
reason and an exit condition; a project with a crossing nobody has decided about
reads about it on the next run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.layer_exemptions import (
    excused_crossings,
    stale_layer_exemption_findings,
)
from beadloom.graph.rules.layers import layer_membership, same_layer_crossings
from beadloom.graph.rules.types import LAYER_EDGE_RULE_TYPE, Violation

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from beadloom.graph.rules.types import LayerRule

#: What to do about a crossing the rules file has not decided about. It offers
#: all three honest moves rather than only the one that makes the run green:
#: the edge can go, the two ends can come to share a container, or the project
#: can say why it stays. A remediation that names only the exemption is advice
#: to silence the check.
SAME_LAYER_REMEDIATION = (
    "Remove the dependency, move both ends inside one container the declaration "
    "gives a layer, or add an `exempt:` entry to this rule naming the pair, why "
    "it stands and what would retire it. A dependency between peers inside one "
    "layer is the coupling a layered architecture is drawn to prevent, so it is "
    "a decision to record rather than a detail to pass over."
)


def _where(
    ref_id: str,
    rule: LayerRule,
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> str:
    """*ref_id* with the container that gives it its layer, when one does.

    A reader meeting a crossing for the first time asks why two components they
    never tagged are in one layer at all, and the answer is the container's
    name.
    """
    membership = layer_membership(ref_id, rule.layers, parents, tags)
    if membership is None or not membership.inherited:
        return f"'{ref_id}'"
    return f"'{ref_id}' (inside '{membership.declared_by}')"


def _crossing_finding(
    rule: LayerRule,
    src_ref_id: str,
    dst_ref_id: str,
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> Violation:
    """One un-excused crossing, at the severity the rule declares."""
    membership = layer_membership(src_ref_id, rule.layers, parents, tags)
    layer_name = "?" if membership is None else rule.layers[membership.index].name
    return Violation(
        rule_name=rule.name,
        rule_description=rule.description,
        rule_type=LAYER_EDGE_RULE_TYPE,
        severity=rule.severity,
        file_path=None,
        line_number=None,
        from_ref_id=src_ref_id,
        to_ref_id=dst_ref_id,
        message=(
            f"Same-layer crossing: {_where(src_ref_id, rule, parents, tags)} depends on "
            f"{_where(dst_ref_id, rule, parents, tags)}. Both are in layer "
            f"'{layer_name}' and no container that declares a layer holds both, so this "
            f"is a dependency between peers rather than inside one of them "
            f"(rule '{rule.name}')."
        ),
        remediation=SAME_LAYER_REMEDIATION,
    )


def same_layer_statements(
    rule: LayerRule,
    edges: Sequence[tuple[str, str]],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> list[Violation]:
    """Every crossing no entry excuses, and every entry that stopped earning its place.

    Both come from one pass, because they are two readings of one split: what
    the rule reports and what its exemptions are still doing. Deriving them
    separately is how an excused count and a reported count come to disagree.

    The crossings are reported in the order the edge set was handed over, so a
    run's output does not move with a ``set``'s iteration order, and the
    exemption findings follow in declaration order.
    """
    crossings = same_layer_crossings(edges, rule.layers, parents, tags)
    reported, excused = excused_crossings(rule, crossings)
    findings = [
        _crossing_finding(rule, src_ref_id, dst_ref_id, parents, tags)
        for src_ref_id, dst_ref_id in reported
    ]
    findings.extend(stale_layer_exemption_findings(rule, excused))
    return findings
