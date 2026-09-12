"""What a same-layer crossing is, and what excusing one costs the person who does.

BDL-070 B2 (``beadloom-xmfs``). RFC Q1 decided the predicate: an edge inside one
layer is legal when both ends share a tagged ancestor and a finding when they do
not. This module holds the predicate itself and the declaration that excuses a
crossing it catches — ``exempt:`` on a layer rule, which requires a reason and an
exit condition and is therefore never a bare allow.

The graphs here declare ``tier-web`` / ``tier-core`` / ``tier-store``, a
vocabulary that appears nowhere under ``src/``, so a test that passes here passed
because the code read the declaration rather than this repository's four
``layer-*`` tags.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.layer_exemptions import (
    layer_exemption_index_for,
    stale_layer_exemption_findings,
)
from beadloom.graph.rules.layers import same_layer_crossings, shares_tagged_ancestor
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import LayerDef, LayerExemption, LayerRule

if TYPE_CHECKING:
    from pathlib import Path

TIERS = (LayerDef(name="web", tag="tier-web"), LayerDef(name="core", tag="tier-core"))

#: ``ledger`` and ``postings`` are two containers in the same tier; each holds
#: one part. ``shared`` is tagged itself and inside neither.
PARENTS = {
    "ledger-api": {"ledger"},
    "ledger-store": {"ledger"},
    "postings-api": {"postings"},
    "ledger": {"root"},
    "postings": {"root"},
    "shared": {"root"},
}
TAGS = {
    "ledger": {"tier-core"},
    "postings": {"tier-core"},
    "shared": {"tier-core"},
    "root": set[str](),
}


def _rule(*exempt: LayerExemption) -> LayerRule:
    return LayerRule(
        name="tier-order",
        description="web -> core, and never the other way",
        layers=TIERS,
        enforce="top-down",
        edge_kind="depends_on",
        exempt=exempt,
    )


class TestTheSharedAncestorPredicate:
    """RFC Q1, as a function: what containment says about two ends in one layer."""

    def test_two_parts_of_one_container_share_it(self) -> None:
        assert shares_tagged_ancestor("ledger-api", "ledger-store", TIERS, PARENTS, TAGS)

    def test_two_parts_of_different_containers_share_nothing_tagged(self) -> None:
        assert not shares_tagged_ancestor("ledger-api", "postings-api", TIERS, PARENTS, TAGS)

    def test_a_part_and_its_own_container_share_the_container(self) -> None:
        """The predicate is reflexive, or a node would cross with its own container."""
        assert shares_tagged_ancestor("ledger-api", "ledger", TIERS, PARENTS, TAGS)

    def test_an_untagged_common_ancestor_is_not_a_shared_one(self) -> None:
        """``root`` holds both containers and declares no layer, so it shares nothing.

        This is the whole reason peer containers cross: an untagged root would
        otherwise make every same-layer edge legal and the predicate vacuous.
        """
        assert not shares_tagged_ancestor("ledger", "postings", TIERS, PARENTS, TAGS)

    def test_two_tagged_siblings_under_one_tagged_container_share_it(self) -> None:
        assert shares_tagged_ancestor("ledger-api", "ledger-store", TIERS, PARENTS, TAGS)


class TestWhichEdgesCross:
    """The predicate applied to an edge set: only same-layer edges are candidates."""

    def test_a_cross_layer_edge_is_not_a_same_layer_crossing(self) -> None:
        """Direction is the rest of the rule's business, not this function's."""
        parents = {**PARENTS, "portal": {"root"}}
        tags = {**TAGS, "portal": {"tier-web"}}
        crossings = same_layer_crossings([("portal", "ledger")], TIERS, parents, tags)
        assert crossings == []

    def test_an_edge_with_an_unlayered_end_is_not_a_crossing(self) -> None:
        crossings = same_layer_crossings([("root", "ledger")], TIERS, PARENTS, TAGS)
        assert crossings == []

    def test_peer_containers_cross_and_parts_of_one_container_do_not(self) -> None:
        crossings = same_layer_crossings(
            [("ledger-api", "ledger-store"), ("ledger-api", "postings-api")],
            TIERS,
            PARENTS,
            TAGS,
        )
        assert crossings == [("ledger-api", "postings-api")]


class TestAnExemptionNamesTwoEnds:
    """Matching is by ref_id, on both ends, because an edge has two of them."""

    def test_an_exemption_matches_the_pair_it_names(self) -> None:
        rule = _rule(
            LayerExemption(
                from_glob="ledger-api", to_glob="postings-api", reason="r", until="2030-01-01"
            )
        )
        assert layer_exemption_index_for(rule, "ledger-api", "postings-api") == 0

    def test_an_exemption_does_not_match_the_reverse_edge(self) -> None:
        """Excusing one direction excuses one direction."""
        rule = _rule(
            LayerExemption(
                from_glob="ledger-api", to_glob="postings-api", reason="r", until="2030-01-01"
            )
        )
        assert layer_exemption_index_for(rule, "postings-api", "ledger-api") is None

    def test_a_glob_matches_a_family_of_ends(self) -> None:
        rule = _rule(
            LayerExemption(
                from_glob="ledger-*", to_glob="postings-api", reason="r", until="2030-01-01"
            )
        )
        assert layer_exemption_index_for(rule, "ledger-store", "postings-api") == 0

    def test_the_first_matching_exemption_is_the_one_that_answers(self) -> None:
        rule = _rule(
            LayerExemption(from_glob="ledger-*", to_glob="*", reason="wide", until="2030-01-01"),
            LayerExemption(
                from_glob="ledger-api", to_glob="postings-api", reason="narrow", until="2030-01-01"
            ),
        )
        assert layer_exemption_index_for(rule, "ledger-api", "postings-api") == 0


class TestAnExemptionThatHasStoppedEarningItsPlace:
    """Every entry is visible: it excuses something, or it is reported."""

    def test_an_exemption_that_excuses_nothing_is_reported_dead(self) -> None:
        rule = _rule(
            LayerExemption(
                from_glob="ledger-api", to_glob="postings-api", reason="r", until="2030-01-01"
            )
        )
        findings = stale_layer_exemption_findings(rule, {}, today=date(2026, 1, 1))
        assert len(findings) == 1
        assert "excuses nothing" in findings[0].message
        assert findings[0].severity == "warn"

    def test_an_exemption_still_excusing_a_crossing_is_not_reported(self) -> None:
        rule = _rule(
            LayerExemption(
                from_glob="ledger-api", to_glob="postings-api", reason="r", until="2030-01-01"
            )
        )
        assert stale_layer_exemption_findings(rule, {0: 1}, today=date(2026, 1, 1)) == []

    def test_an_exemption_past_its_deadline_is_reported_with_what_it_still_excuses(
        self,
    ) -> None:
        rule = _rule(
            LayerExemption(
                from_glob="ledger-api", to_glob="postings-api", reason="r", until="2026-01-01"
            )
        )
        findings = stale_layer_exemption_findings(rule, {0: 2}, today=date(2026, 1, 2))
        assert len(findings) == 1
        assert "expired on 2026-01-01" in findings[0].message
        assert "2 same-layer crossings" in findings[0].message

    def test_an_exemption_naming_an_event_never_expires_on_its_own(self) -> None:
        """An event is not a date, and no clock can observe whether it happened."""
        rule = _rule(
            LayerExemption(
                from_glob="ledger-api",
                to_glob="postings-api",
                reason="r",
                until="the tree-sitter facilities move below both domains",
            )
        )
        assert stale_layer_exemption_findings(rule, {0: 1}, today=date(2099, 1, 1)) == []


def _rules_yaml(exempt_block: str) -> str:
    return (
        "version: 3\n\nrules:\n"
        "  - name: tier-order\n"
        '    description: "web -> core, and never the other way"\n'
        "    layers:\n"
        "      - name: web\n        tag: tier-web\n"
        "      - name: core\n        tag: tier-core\n"
        "    enforce: top-down\n"
        "    edge_kind: depends_on\n" + exempt_block
    )


def _load(tmp_path: Path, exempt_block: str) -> LayerRule:
    path = tmp_path / "rules.yml"
    path.write_text(_rules_yaml(exempt_block), encoding="utf-8")
    rule = load_rules(path)[0]
    assert isinstance(rule, LayerRule)
    return rule


class TestWhatTheDeclarationRequires:
    """A bare allow is not an outcome, which the loader enforces rather than asks."""

    def test_a_rule_with_no_exempt_block_carries_none(self, tmp_path: Path) -> None:
        assert _load(tmp_path, "").exempt == ()

    def test_a_well_formed_entry_is_parsed(self, tmp_path: Path) -> None:
        rule = _load(
            tmp_path,
            "    exempt:\n"
            "      - from: ledger-api\n"
            "        to: postings-api\n"
            '        reason: "the two read one ledger"\n'
            '        until: "2030-01-01"\n',
        )
        assert rule.exempt == (
            LayerExemption(
                from_glob="ledger-api",
                to_glob="postings-api",
                reason="the two read one ledger",
                until="2030-01-01",
            ),
        )

    @pytest.mark.parametrize(
        ("entry", "expected"),
        [
            (
                "      - to: postings-api\n        reason: r\n        until: u\n",
                "must name both ends",
            ),
            (
                "      - from: ledger-api\n        reason: r\n        until: u\n",
                "must name both ends",
            ),
            (
                "      - from: ledger-api\n        to: postings-api\n        until: u\n",
                "non-empty 'reason'",
            ),
            (
                "      - from: ledger-api\n        to: postings-api\n        reason: r\n",
                "non-empty 'until'",
            ),
            (
                '      - from: "*"\n        to: "*"\n        reason: r\n        until: u\n',
                "would exempt the rule",
            ),
        ],
    )
    def test_an_entry_that_excuses_without_saying_what_or_why_is_refused(
        self, tmp_path: Path, entry: str, expected: str
    ) -> None:
        with pytest.raises(ValueError, match=expected):
            _load(tmp_path, "    exempt:\n" + entry)

    def test_an_exempt_block_that_is_not_a_list_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="exempt must be a list"):
            _load(tmp_path, "    exempt: ledger-api\n")
