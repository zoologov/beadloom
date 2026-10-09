"""A ``layers`` rule may carry a title, the name the portal shows it by.

BDL-080 S1e (``beadloom-af99.2``). A rule's ``name`` is its identifier: lint
reports it, an exemption and the URL of the portal's Layer filter name it, so it
is written for a machine (``architecture-layers``). The portal's legend, filter
and card show a reader the rule, and the owner asked for "DDD architecture"
there. ``title:`` is that name; the rule keeps its ``name``. A title that is not
a non-empty string is refused at load, because an empty one would read as "no
title" and the portal would fall back to the name in silence.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import LayerRule

if TYPE_CHECKING:
    from pathlib import Path


def _layer_rule_file(tmp_path: Path, title_line: str) -> Path:
    path = tmp_path / "rules.yml"
    path.write_text(
        "version: 3\nrules:\n"
        "  - name: ui-slices\n" + title_line + "    layers:\n"
        "      - name: pages\n        tag: ui-pages\n"
        "      - name: shared\n        tag: ui-shared\n"
        "    enforce: top-down\n"
        "    edge_kind: depends_on\n",
        encoding="utf-8",
    )
    return path


def test_a_declared_title_is_carried_on_the_rule(tmp_path: Path) -> None:
    (rule,) = load_rules(_layer_rule_file(tmp_path, '    title: "  Storefront FSD "\n'))
    assert isinstance(rule, LayerRule)
    assert rule.title == "Storefront FSD"
    assert rule.name == "ui-slices"


def test_a_rule_without_a_title_has_none(tmp_path: Path) -> None:
    (rule,) = load_rules(_layer_rule_file(tmp_path, ""))
    assert isinstance(rule, LayerRule)
    assert rule.title is None


@pytest.mark.parametrize("value", ["''", "'  '", "[a, b]", "7", "null"])
def test_a_title_that_is_not_a_non_empty_string_is_refused(tmp_path: Path, value: str) -> None:
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Rule 'ui-slices': 'title' must be a non-empty string, "
            "the name the portal shows the rule by"
        ),
    ):
        load_rules(_layer_rule_file(tmp_path, f"    title: {value}\n"))
