"""The two FSD slice rules reach the ``rules`` table whole (BDL-080 S3c).

A reader of the index must not see a narrower rule than the one that runs, so a
``slice_shape`` rule's segments are stored even when the rule took the default ones.
"""

from __future__ import annotations

from beadloom.application.reindex.rules_loader import _serialize_rule
from beadloom.graph.rules.types import SlicePublicApiRule, SliceShapeRule


def test_the_public_api_rule_is_stored_with_its_tags() -> None:
    rule = SlicePublicApiRule(name="fsd-public-api", description="", tags=("fsd-features",))

    assert _serialize_rule(rule) == ("slice_public_api", {"tags": ["fsd-features"]})


def test_the_shape_rule_is_stored_with_its_default_segments() -> None:
    rule = SliceShapeRule(name="fsd-slice-shape", description="", tags=("fsd-pages",))

    assert _serialize_rule(rule) == (
        "slice_shape",
        {"tags": ["fsd-pages"], "segments": ["ui", "model", "lib", "api", "config"]},
    )
