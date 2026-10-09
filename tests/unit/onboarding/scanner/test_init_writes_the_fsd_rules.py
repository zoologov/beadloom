"""The rules ``init`` writes for a Feature-Sliced frontend (BDL-080 S3c, RFC D3 + D4).

Four kinds of rule, each with the owner's wording beside it in ``rules.yml``: the layer
order (scoped to the frontend service, titled for the portal), the public API of a slice,
a slice's shape, and the cohesion signal per layer. The file is read back by the loader
the linter uses, so a rule the writer gets wrong fails here as it would fail ``lint``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import (
    CardinalityRule,
    LayerRule,
    SlicePublicApiRule,
    SliceShapeRule,
)
from beadloom.onboarding.scanner.rules_gen import (
    FSD_COHESION_LIMITS,
    generate_fsd_rules,
)

if TYPE_CHECKING:
    from pathlib import Path

SLICE_TAGS = ("fsd-pages", "fsd-widgets", "fsd-features", "fsd-entities")


def _written(tmp_path: Path) -> tuple[int, Path]:
    path = tmp_path / "rules.yml"
    return generate_fsd_rules("orchard-web", path), path


def test_the_layer_rule_is_scoped_to_the_frontend_and_titled(tmp_path: Path) -> None:
    _, path = _written(tmp_path)

    (layers,) = [rule for rule in load_rules(path) if isinstance(rule, LayerRule)]

    assert layers.name == "fsd-layers"
    assert layers.title == "FSD architecture"
    assert layers.scope == "orchard-web"
    assert layers.edge_kind == "depends_on"
    assert layers.severity == "error"
    assert [(layer.name, layer.tag) for layer in layers.layers] == [
        ("app", "fsd-app"),
        ("pages", "fsd-pages"),
        ("widgets", "fsd-widgets"),
        ("features", "fsd-features"),
        ("entities", "fsd-entities"),
        ("shared", "fsd-shared"),
    ]


def test_the_slice_rules_judge_the_four_sliced_layers(tmp_path: Path) -> None:
    _, path = _written(tmp_path)
    rules = load_rules(path)

    (public_api,) = [rule for rule in rules if isinstance(rule, SlicePublicApiRule)]
    (shape,) = [rule for rule in rules if isinstance(rule, SliceShapeRule)]

    assert public_api.tags == SLICE_TAGS
    assert public_api.severity == "error"
    assert shape.tags == SLICE_TAGS
    assert shape.segments == ("ui", "model", "lib", "api", "config")
    assert shape.severity == "warn"


def test_the_cohesion_signal_is_one_check_per_layer_at_its_stated_limit(
    tmp_path: Path,
) -> None:
    _, path = _written(tmp_path)

    checks = {
        rule.for_matcher.tag: (rule.max_symbols, rule.severity, rule.for_matcher.kind)
        for rule in load_rules(path)
        if isinstance(rule, CardinalityRule)
    }

    assert FSD_COHESION_LIMITS == {
        "app": 60,
        "pages": 60,
        "widgets": 80,
        "features": 60,
        "entities": 60,
        "shared": 60,
    }
    assert checks == {
        f"fsd-{layer}": (limit, "warn", "component")
        for layer, limit in FSD_COHESION_LIMITS.items()
    }


def test_the_count_is_the_number_of_rules_written(tmp_path: Path) -> None:
    count, path = _written(tmp_path)

    assert count == len(load_rules(path)) == 9


def test_each_rule_carries_the_owners_wording(tmp_path: Path) -> None:
    _, path = _written(tmp_path)
    # The comments, read as prose: a sentence wraps over several comment lines.
    text = " ".join(
        line.strip().removeprefix("#").strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("#")
    )

    for phrase in (
        "FSD's layers belong to one application root",
        "Cross imports inside one layer are forbidden by the rule, as FSD prescribes",
        "a slice is one business entity or feature, with the standard segments",
        "a public API in index",
        "reaches past another slice's index",
        "a signal, not a target",
        "Steiger",
        "forbidden-imports",
        "public-api",
    ):
        assert phrase in text, phrase
