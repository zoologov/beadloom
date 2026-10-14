"""The five ``fsd`` overlays say feature-sliced.design 2.1 (BDL-082 S2b, RFC D6).

The measurement is ``axes.md`` gap 7 of BDL-082: a table of the overlays' claims against
the reference pages ``/docs/reference/{layers,slices-segments,public-api}`` and the 2.1
migration guide. Three claims the specification contradicts (no cross-import at all
between slices of one layer, a size signal that asks to split a page, a slice's top holding
nothing but its segments), five it states and the overlays left out (``@x``, slice groups,
pages-first, custom segments by purpose, the public API of ``shared`` and ``app``), the
three barrel pitfalls, and ``insignificant-slice`` read as a rule to weigh rather than as
the rule the migration guide calls one of "the most helpful".

Each case pins what a role reads after ``compose_role``, the text an adopter's agent is
given, and the contradicted sentences are pinned absent so they cannot come back.
"""

from __future__ import annotations

import pytest

from beadloom.onboarding.role_composer import compose_role

_ROLES = ("dev", "explore", "review", "test", "tech-writer")


def _fsd(role: str) -> str:
    return compose_role(role, architecture="fsd", stack=["vuejs"])


class TestTheClaimsTheSpecificationContradictsAreGone:
    def test_no_role_forbids_every_cross_import_between_slices_of_one_layer(self) -> None:
        texts = {role: _fsd(role) for role in _ROLES}

        assert "No cross-imports between slices of the SAME layer" not in texts["dev"]
        assert (
            "no cross-slice import within the same layer (must go through" not in (texts["review"])
        )
        assert "(that import is illegal anyway)" not in texts["test"]

    def test_the_dev_role_no_longer_asks_to_split_a_page_by_its_size(self) -> None:
        text = _fsd("dev")

        assert "60 for every other layer" not in text
        assert "A slice past it is split by responsibility" not in text

    def test_a_slices_top_is_not_limited_to_its_segments_and_index(self) -> None:
        text = _fsd("dev")

        assert "holds its segments and its `index` and nothing else" not in text

    def test_processes_is_deprecated_without_a_version_the_pages_do_not_state(self) -> None:
        text = _fsd("dev")

        assert "deprecated since FSD 2.1" not in text
        assert "`processes` is deprecated" in text

    def test_insignificant_slice_is_no_longer_weighed_rather_than_obeyed(self) -> None:
        assert "weighed, not obeyed" not in _fsd("dev")


class TestTheCrossImportApi:
    @pytest.mark.parametrize("role", ["dev", "review", "test", "explore", "tech-writer"])
    def test_every_role_names_the_x_notation(self, role: str) -> None:
        assert "@x" in _fsd(role)

    def test_the_dev_role_states_it_on_the_entities_layer_only_and_for_one_importer(
        self,
    ) -> None:
        text = _fsd("dev")

        assert "`entities/A/@x/B`" in text
        assert "on the entities layer only" in text
        assert "imported by entity B alone" in text

    def test_the_review_role_grades_an_x_outside_entities_and_a_third_importer(self) -> None:
        text = _fsd("review")

        assert "outside `entities`" in text
        assert "a third slice" in text


class TestSliceGroups:
    @pytest.mark.parametrize("role", ["dev", "review", "explore"])
    def test_a_group_is_a_folder_of_slices_that_shares_no_code(self, role: str) -> None:
        text = _fsd(role)

        assert "slice group" in text
        assert "<layer>-<group>-<slice>" in text

    def test_the_dev_role_quotes_the_isolation_the_specification_asks_for(self) -> None:
        text = _fsd("dev")

        assert "there should be no code sharing in that folder" in text
        assert "the group has no node" in text


class TestPagesFirst:
    @pytest.mark.parametrize("role", ["dev", "review"])
    def test_pages_carry_no_size_signal(self, role: str) -> None:
        text = _fsd(role)

        assert "pages-first" in text
        assert "no `check` rule for `pages`" in text

    def test_the_dev_role_starts_in_the_page_and_extracts_on_real_reuse(self) -> None:
        text = _fsd("dev")

        assert "Start in `pages`" in text
        assert "a second page" in text
        assert "duplication" in text
        assert "not everything needs to be a feature" in text


class TestCustomSegmentsByPurpose:
    @pytest.mark.parametrize("role", ["dev", "review"])
    def test_a_segment_is_named_by_its_purpose_and_the_bad_names_are_listed(
        self, role: str
    ) -> None:
        text = _fsd(role)

        assert "describes the purpose of the content, not its essence" in text
        assert "`components`, `hooks`, `types`" in text
        assert "`discouraged:`" in text

    def test_the_dev_role_names_a_purposeful_custom_segment(self) -> None:
        assert "`analytics`" in _fsd("dev")


class TestTheBarrelPitfalls:
    @pytest.mark.parametrize("role", ["dev", "review"])
    def test_the_three_pitfalls_are_stated(self, role: str) -> None:
        text = _fsd(role)

        assert "export *" in text
        assert "no `index` on a segment of a sliced layer" in text
        assert "`shared/ui/button/index`" in text

    def test_the_dev_role_says_which_tool_reports_each(self) -> None:
        text = _fsd("dev")

        assert "`no-wildcard-exports`" in text
        assert "off in `recommended`" in text


class TestThePublicApiOfTheUnslicedLayers:
    @pytest.mark.parametrize("role", ["dev", "review", "tech-writer"])
    def test_a_segment_of_shared_and_app_is_entered_through_its_index(self, role: str) -> None:
        assert "a segment of `shared` or `app` is entered through its own `index`" in _fsd(role)

    @pytest.mark.parametrize("role", ["dev", "review"])
    def test_steigers_public_api_reports_a_segment_too(self, role: str) -> None:
        assert "a slice or a segment with no public API" in _fsd(role)


class TestInsignificantSlice:
    @pytest.mark.parametrize("role", ["dev", "review"])
    def test_it_stays_on_and_a_switch_off_is_a_reasoned_exception(self, role: str) -> None:
        text = _fsd(role)

        assert "`insignificant-slice` stays on" in text
        assert "reasoned exception" in text

    def test_the_dev_role_names_the_portals_switch_off_as_an_example_not_a_default(
        self,
    ) -> None:
        text = _fsd("dev")

        assert "Beadloom's own portal switches it off" in text
        assert "an example of a reasoned exception, not a default" in text
