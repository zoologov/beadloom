"""A box's card names the debt inside it beside its own (BDL-080 S4a, `beadloom-5pxv`).

The card said `Debt 0` for a box from the box's own score while its activity
rolled up from its parts, two populations on one card and neither named
(BDL-UX #306). A box now carries, under its debt, what is inside: how many of
its ``part_of`` descendants carry debt, the sum of their own scores, and how
many of them carry each reason. A leaf is unchanged.
"""

from __future__ import annotations

from beadloom.application.debt_report import NodeDebt
from beadloom.application.site.architecture_card import DebtInside, debt_inside


def _debt(ref_id: str, score: float, *reasons: str) -> NodeDebt:
    return NodeDebt(ref_id=ref_id, score=score, reasons=list(reasons))


#: shop holds orders and storefront; orders holds pricing and tax.
_PARENT = {"orders": "shop", "storefront": "shop", "pricing": "orders", "tax": "orders"}


def test_a_box_sums_every_descendant_and_counts_them_by_reason() -> None:
    debt = {
        "shop": _debt("shop", 2.0, "undocumented"),
        "orders": _debt("orders", 1.0, "stale_doc"),
        "pricing": _debt("pricing", 3.0, "undocumented", "stale_doc"),
        "tax": _debt("tax", 0.5, "dormant"),
    }

    inside = debt_inside(debt, _PARENT)

    assert inside["shop"] == DebtInside(
        nodes=3, score=4.5, by_reason={"dormant": 1, "stale_doc": 2, "undocumented": 1}
    )
    assert inside["orders"] == DebtInside(
        nodes=2, score=3.5, by_reason={"dormant": 1, "stale_doc": 1, "undocumented": 1}
    )


def test_a_reason_a_node_carries_twice_counts_that_node_once() -> None:
    debt = {"pricing": _debt("pricing", 2.0, "violation:warning:tiers", "violation:warning:tiers")}

    assert debt_inside(debt, _PARENT)["orders"].by_reason == {"violation:warning:tiers": 1}


def test_a_box_with_nothing_owed_inside_says_zero_and_a_leaf_has_no_entry() -> None:
    inside = debt_inside({"shop": _debt("shop", 2.0, "undocumented")}, _PARENT)

    assert inside["orders"] == DebtInside(nodes=0, score=0.0, by_reason={})
    assert inside["shop"] == DebtInside(nodes=0, score=0.0, by_reason={})
    assert "pricing" not in inside
    assert "storefront" not in inside


def test_a_part_of_cycle_does_not_loop() -> None:
    inside = debt_inside({"a": _debt("a", 1.0, "dormant")}, {"a": "b", "b": "a"})

    assert inside["b"].nodes == 1
    assert inside["a"].nodes == 0


def test_the_data_file_shape() -> None:
    assert DebtInside(nodes=1, score=0.5, by_reason={"dormant": 1}).as_dict() == {
        "nodes": 1,
        "score": 0.5,
        "by_reason": {"dormant": 1},
    }


def test_a_root_part_of_itself_is_a_box_only_by_what_it_holds() -> None:
    """The root service is `part_of` itself in this repository's graph."""
    debt = {"root": _debt("root", 1.0, "dormant"), "leaf": _debt("leaf", 1.0, "dormant")}

    inside = debt_inside(debt, {"root": "root", "leaf": "leaf", "part": "root"})

    assert inside == {"root": DebtInside(nodes=0, score=0.0, by_reason={})}


def test_a_part_of_cycle_above_an_indebted_leaf_counts_the_leaf_once_in_each_box_of_it() -> None:
    inside = debt_inside(
        {"leaf": _debt("leaf", 1.0, "dormant")}, {"leaf": "a", "a": "b", "b": "a"}
    )

    assert (inside["a"].nodes, inside["b"].nodes) == (1, 1)
