"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_each_decision_fails_in_its_stated_direction.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from tests.support.repository_root import REPO_ROOT


class TestTheHonestyNoteAndTheCodeAgree:
    """`.79`'s note listed the line-start protection under ENFORCED. It was not.

    The reviewer's own words: had it read that first, it would have accepted the
    claim as the specification instead of probing it. So the sentence is fixed
    with the code, in every place that carries it.
    """

    def test_the_spec_states_the_colon_and_the_opening_line(self) -> None:

        spec = (
            REPO_ROOT
            / "docs"
            / "domains"
            / "application"
            / "features"
            / "review-brief"
            / "SPEC.md"
        ).read_text(encoding="utf-8")
        recognised = spec.split("### How a verdict is recognised", 1)[1]
        recognised = recognised.split("###", 1)[0]
        assert "colon" in recognised
        assert "first" in recognised
