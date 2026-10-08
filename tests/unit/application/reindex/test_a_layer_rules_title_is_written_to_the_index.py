"""A layer rule's ``title`` reaches the ``rules`` table, and only when declared.

BDL-080 S1e (``beadloom-af99.2``). The architecture view reads its layer rules
from the index, not from ``rules.yml``, so a title the serializer dropped would
be one the rules file declares and the portal never shows. Written only when
declared, so the index of a project that declares none is what it was.
"""

from __future__ import annotations

from beadloom.application.reindex.rules_loader import _serialize_rule
from beadloom.graph.rules.types import LayerDef, LayerRule

_LAYERS = (LayerDef(name="pages", tag="ui-pages"), LayerDef(name="shared", tag="ui-shared"))


def _rule(title: str | None) -> LayerRule:
    return LayerRule(
        name="ui-slices",
        description="",
        layers=_LAYERS,
        enforce="top-down",
        edge_kind="depends_on",
        title=title,
    )


def test_a_declared_title_is_written() -> None:
    rule_type, rule_def = _serialize_rule(_rule("Storefront FSD"))
    assert rule_type == "layers"
    assert rule_def["title"] == "Storefront FSD"


def test_no_title_writes_no_key() -> None:
    _, rule_def = _serialize_rule(_rule(None))
    assert "title" not in rule_def
