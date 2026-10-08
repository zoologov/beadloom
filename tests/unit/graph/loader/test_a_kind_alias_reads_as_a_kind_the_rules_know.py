"""A node kind the graph accepts as an alias reads as a kind the rules know.

BDL-080 S1a (`beadloom-je0i`), RFC D1. `kind: site` stays accepted in a graph
file — removing a kind from the graph schema would be a major change — and is
read as `service`. The table lives with the graph loader, the one place it is
applied, and what it maps to has to be one of `VALID_NODE_KINDS`: an alias that
resolved to a kind no rule can match would repeat the defect it exists to close.
"""

from __future__ import annotations

from beadloom.graph.loader import KIND_ALIASES, canonical_kind
from beadloom.graph.rules.types import VALID_NODE_KINDS


def test_site_is_an_alias_of_service() -> None:
    assert KIND_ALIASES["site"] == "service"


def test_every_alias_resolves_to_a_kind_the_rules_know() -> None:
    assert set(KIND_ALIASES.values()) <= VALID_NODE_KINDS


def test_no_alias_shadows_a_kind_the_rules_know() -> None:
    assert not set(KIND_ALIASES) & VALID_NODE_KINDS


def test_the_canonical_kind_of_an_alias_is_the_kind_it_names() -> None:
    assert canonical_kind("site") == "service"


def test_a_kind_that_is_no_alias_is_its_own_canonical_kind() -> None:
    assert [canonical_kind(kind) for kind in ("domain", "service", "", "gizmo")] == [
        "domain",
        "service",
        "",
        "gizmo",
    ]
