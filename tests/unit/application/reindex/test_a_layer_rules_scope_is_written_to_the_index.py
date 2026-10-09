"""A layer rule's ``scope`` reaches the ``rules`` table, and only when declared.

BDL-080 S1b (``beadloom-kgh6``). The architecture view reads its layer rules from
the index, not from ``rules.yml``, so a scope the serializer dropped would be a
scope the linter honours and the portal ignores. Written only when declared, so
the index of a project that declares none is byte-for-byte what it was.
"""

from __future__ import annotations

from beadloom.application.reindex.rules_loader import _serialize_rule
from beadloom.graph.rules.types import LayerDef, LayerRule

_LAYERS = (LayerDef(name="pages", tag="ui-pages"), LayerDef(name="shared", tag="ui-shared"))


def _rule(scope: str | None) -> LayerRule:
    return LayerRule(
        name="ui-slices",
        description="",
        layers=_LAYERS,
        enforce="top-down",
        edge_kind="depends_on",
        scope=scope,
    )


def test_a_declared_scope_is_written() -> None:
    rule_type, rule_def = _serialize_rule(_rule("shop-portal"))
    assert rule_type == "layers"
    assert rule_def["scope"] == "shop-portal"


def test_no_scope_writes_no_key() -> None:
    _, rule_def = _serialize_rule(_rule(None))
    assert "scope" not in rule_def
