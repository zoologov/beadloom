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
    DEFAULT_DISCOURAGED_SEGMENTS,
    CardinalityRule,
    LayerRule,
    SlicePublicApiRule,
    SliceShapeRule,
)
from beadloom.onboarding.scanner import rules_gen
from beadloom.onboarding.scanner.rules_gen import (
    FSD_COHESION_LIMITS,
    STEIGER_RECOMMENDED,
    fsd_rules_text,
    generate_fsd_rules,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

SLICE_TAGS = ("fsd-pages", "fsd-widgets", "fsd-features", "fsd-entities")
#: The public API is judged on every layer: the segments of `shared` and `app` are entered
#: through their index as well (BDL-082 RFC D5; S1T measured PRD goal 5 holding for the rule
#: only until init wrote these two tags).
PUBLIC_API_TAGS = (*SLICE_TAGS, "fsd-shared", "fsd-app")

#: `fsd.configs.recommended` of `@feature-sliced/steiger-plugin` 0.8.0, in the plugin's order,
#: measured by importing the installed package (Node v22.9.0, `npm ci` of the scaffold's lock).
STEIGER_0_8_0_RECOMMENDED = (
    "ambiguous-slice-names",
    "excessive-slicing",
    "forbidden-imports",
    "inconsistent-naming",
    "insignificant-slice",
    "no-layer-public-api",
    "no-public-api-sidestep",
    "no-reserved-folder-names",
    "no-segmentless-slices",
    "no-segments-on-sliced-layers",
    "no-ui-in-app",
    "public-api",
    "repetitive-naming",
    "segments-by-purpose",
    "shared-lib-grouping",
    "typo-in-layer-name",
    "no-processes",
)


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


def test_the_public_api_rule_judges_every_layer_and_the_shape_rule_the_sliced_four(
    tmp_path: Path,
) -> None:
    _, path = _written(tmp_path)
    rules = load_rules(path)

    (public_api,) = [rule for rule in rules if isinstance(rule, SlicePublicApiRule)]
    (shape,) = [rule for rule in rules if isinstance(rule, SliceShapeRule)]

    assert public_api.tags == PUBLIC_API_TAGS
    assert public_api.severity == "error"
    assert shape.tags == SLICE_TAGS
    assert shape.segments == ("ui", "model", "lib", "api", "config")
    assert shape.severity == "warn"


def test_the_shape_rule_is_written_with_both_lists(tmp_path: Path) -> None:
    # BDL-082 RFC D4: the known-good set and the deny-list, both in the file an adopter
    # edits, rather than the deny-list left to a default the file does not show.
    _, path = _written(tmp_path)

    (shape,) = [rule for rule in load_rules(path) if isinstance(rule, SliceShapeRule)]
    text = path.read_text(encoding="utf-8")

    assert shape.discouraged == DEFAULT_DISCOURAGED_SEGMENTS
    assert len(shape.discouraged) == 69
    assert "discouraged:" in text


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

    assert count == len(load_rules(path)) == 8


def test_no_cohesion_check_is_written_for_the_pages_layer(tmp_path: Path) -> None:
    # BDL-082 RFC D3, pages-first: "There's no limit to how much code you can place in a
    # page slice as long as your team still finds it easy to navigate" (/docs/reference/
    # layers). Before, `fsd-cohesion-pages` fired on a 90-symbol page at 60.
    _, path = _written(tmp_path)

    names = {rule.name for rule in load_rules(path)}

    assert "fsd-cohesion-pages" not in names
    assert {
        "fsd-cohesion-app",
        "fsd-cohesion-widgets",
        "fsd-cohesion-features",
        "fsd-cohesion-entities",
        "fsd-cohesion-shared",
    } <= names


def test_the_count_follows_the_text_not_a_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # BDL-080 S3f (beadloom-af99.14), the S3 review's nit 6: the count was `3 + len(...)`,
    # so a rule taken out of the text left the number init prints unchanged.
    monkeypatch.setattr(rules_gen, "_FSD_SHAPE_RULE", "")

    count, path = _written(tmp_path)

    assert count == len(load_rules(path)) == 2 + len(FSD_COHESION_LIMITS)


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


def test_an_import_past_a_slices_index_is_named_by_steigers_sidestep_check(
    tmp_path: Path,
) -> None:
    """BDL-080 S2d: the public-API rule cites ``no-public-api-sidestep``, the Steiger
    check that reports an import past another slice's index; ``public-api`` is the one
    that reports a slice with no index at all."""
    _, path = _written(tmp_path)
    text = " ".join(
        line.strip().removeprefix("#").strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("#")
    )

    assert "(Steiger: no-public-api-sidestep;" in text
    assert "(Steiger: public-api)" not in text


def _comments(path: Path) -> str:
    return " ".join(
        line.strip().removeprefix("#").strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("#")
    )


def test_the_written_rules_state_the_specifications_reasons(tmp_path: Path) -> None:
    _, path = _written(tmp_path)
    text = _comments(path)

    for phrase in (
        # RFC D3: pages-first, in the specification's words.
        "There's no limit to how much code you can place in a page slice",
        # RFC D4: custom segments by purpose.
        "describes the purpose of the content, not its essence",
        # RFC D2: a group shares no code.
        "there should be no code sharing in that folder",
        # RFC D1: the one sanctioned cross-import.
        "@x",
        # RFC D5: the unsliced layers' segments have a public API.
        "per-component index",
    ):
        assert phrase in text, phrase


def test_the_header_lists_steigers_recommended_rules_one_line_each(tmp_path: Path) -> None:
    # BDL-082 RFC D6: the header named 5 of the 17 as "its `recommended` set".
    text = fsd_rules_text("orchard-web")
    lines = [line for line in text.splitlines() if line.startswith("#   fsd/")]

    assert tuple(rule for rule, _line in STEIGER_RECOMMENDED) == STEIGER_0_8_0_RECOMMENDED
    assert [line.split()[1] for line in lines] == [
        f"fsd/{rule}" for rule in STEIGER_0_8_0_RECOMMENDED
    ]
    assert all(len(line) <= 95 for line in text.splitlines() if line.lstrip().startswith("#"))
