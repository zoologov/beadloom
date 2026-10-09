"""A node matcher may select by the beginning of a tag (BDL-080 S2b, RFC D3).

A Feature-Sliced frontend tags each slice with its layer (``fsd-widgets``,
``fsd-features``, ...), so a size signal over every layer needed one rule per tag.
``tag_prefix:`` lets one rule select every node carrying a tag that begins with
it. What is pinned here: which nodes a prefix selects, how the matcher reads in a
finding, that the evaluators know to load tags for it, and the loader's refusals,
whose wording is the only thing an adopter reads when the key is wrong.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import CardinalityRule, NodeMatcher

if TYPE_CHECKING:
    from pathlib import Path


def _rules_file(tmp_path: Path, matcher: str) -> Path:
    path = tmp_path / "rules.yml"
    path.write_text(
        "version: 1\nrules:\n"
        "  - name: ui-cohesion\n"
        '    description: "a slice owns few symbols"\n'
        "    check:\n"
        f"      for: {matcher}\n"
        "      max_symbols: 60\n",
        encoding="utf-8",
    )
    return path


_REFUSED_PREFIX = "Rule 'ui-cohesion' check.for: 'tag_prefix' must be a non-empty string"


def _exactly(message: str) -> str:
    return f"^{re.escape(message)}$"


class TestWhatAPrefixSelects:
    """A node is selected when ANY of its tags begins with the prefix."""

    def test_a_node_whose_tag_begins_with_the_prefix_is_selected(self) -> None:
        matcher = NodeMatcher(tag_prefix="ui-")

        assert matcher.matches("board", "component", tags={"ui-widgets"})

    def test_a_node_with_one_matching_tag_among_others_is_selected(self) -> None:
        matcher = NodeMatcher(tag_prefix="ui-")

        assert matcher.matches("board", "component", tags={"legacy", "ui-features"})

    def test_a_node_whose_tags_only_contain_the_prefix_elsewhere_is_not(self) -> None:
        matcher = NodeMatcher(tag_prefix="ui-")

        assert not matcher.matches("ledger", "component", tags={"tier-core", "core-ui-"})

    def test_a_node_with_no_tags_is_not_selected(self) -> None:
        matcher = NodeMatcher(tag_prefix="ui-")

        assert not matcher.matches("ledger", "component", tags=set())

    def test_the_kind_still_has_to_match(self) -> None:
        matcher = NodeMatcher(kind="component", tag_prefix="ui-")

        assert not matcher.matches("board", "feature", tags={"ui-widgets"})

    def test_a_tag_and_a_prefix_together_both_have_to_hold(self) -> None:
        matcher = NodeMatcher(tag="ui-widgets", tag_prefix="ui-")

        assert matcher.matches("board", "component", tags={"ui-widgets"})
        assert not matcher.matches("search", "component", tags={"ui-features"})

    def test_a_caller_that_passes_no_tags_skips_the_prefix_like_the_tag(self) -> None:
        # The contract `tag` already has, kept for the prefix: a caller that never
        # loaded tags is not broken by a rule it cannot judge.
        assert NodeMatcher(tag_prefix="ui-").matches("board", "component", tags=None)


class TestWhoLoadsTags:
    """An evaluator loads a node's tags only for a matcher that reads them."""

    @pytest.mark.parametrize(
        ("matcher", "reads"),
        [
            (NodeMatcher(tag="ui-widgets"), True),
            (NodeMatcher(tag_prefix="ui-"), True),
            (NodeMatcher(kind="component", ref_id="board"), False),
            (NodeMatcher(), False),
        ],
    )
    def test_reads_tags_is_true_for_a_tag_or_a_prefix(
        self, matcher: NodeMatcher, reads: bool
    ) -> None:
        assert matcher.reads_tags is reads


class TestHowItReadsInAFinding:
    def test_describe_names_the_prefix_after_the_kind(self) -> None:
        matcher = NodeMatcher(kind="component", tag_prefix="fsd-")

        assert matcher.describe() == "kind=component, tag_prefix=fsd-"


class TestTheLoaderReadsIt:
    def test_a_for_block_with_a_prefix_becomes_a_prefix_matcher(self, tmp_path: Path) -> None:
        (rule,) = load_rules(_rules_file(tmp_path, "{ kind: component, tag_prefix: fsd- }"))

        assert isinstance(rule, CardinalityRule)
        assert rule.for_matcher == NodeMatcher(kind="component", tag_prefix="fsd-")

    def test_a_prefix_alone_is_a_matcher(self, tmp_path: Path) -> None:
        (rule,) = load_rules(_rules_file(tmp_path, "{ tag_prefix: fsd- }"))

        assert isinstance(rule, CardinalityRule)
        assert rule.for_matcher == NodeMatcher(tag_prefix="fsd-")

    def test_an_empty_prefix_is_refused_because_it_would_select_every_tagged_node(
        self, tmp_path: Path
    ) -> None:
        path = _rules_file(tmp_path, "{ kind: component, tag_prefix: '' }")

        with pytest.raises(
            ValueError,
            match=_exactly(_REFUSED_PREFIX),
        ):
            load_rules(path)

    def test_a_prefix_that_is_not_a_string_is_refused(self, tmp_path: Path) -> None:
        path = _rules_file(tmp_path, "{ kind: component, tag_prefix: [fsd-] }")

        with pytest.raises(
            ValueError,
            match=_exactly(_REFUSED_PREFIX),
        ):
            load_rules(path)

    def test_a_matcher_with_no_field_names_the_prefix_among_the_fields(
        self, tmp_path: Path
    ) -> None:
        path = _rules_file(tmp_path, "{ exclude: [board] }")

        with pytest.raises(
            ValueError,
            match=_exactly(
                "Rule 'ui-cohesion' check.for: node matcher must have at least one of "
                "'ref_id', 'kind', 'tag', or 'tag_prefix'"
            ),
        ):
            load_rules(path)
