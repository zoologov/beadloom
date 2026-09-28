"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_verdict_room_population.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.application.rooms import (
    take_census,
)
from tests.support.repository_root import REPO_ROOT


class TestThisRepositorysOwnRoomsStayDerived:
    """The property a hand-written list would satisfy and then lose."""

    def test_the_declared_legs_come_from_files_that_exist(self) -> None:
        # Arrange

        repo = REPO_ROOT

        # Act
        census = take_census(repo)

        # Assert
        sources = {c.room.source.split(":", 1)[0] for c in census.comparisons}
        assert sources
        for source in sources:
            assert (repo / source).is_file(), source

    def test_every_leg_this_run_did_not_enter_says_which_axis_decided_it(
        self,
    ) -> None:
        """A leg dismissed without a reason is a leg nobody can act on.

        Over the whole declared population rather than over one synthetic leg,
        so a leg whose axis this report cannot describe is caught here and not
        only in the arrangement that anticipated it.
        """
        # Arrange

        repo = REPO_ROOT

        # Act
        census = take_census(repo)

        # Assert
        assert census.not_entered
        for comparison in census.not_entered:
            assert comparison.why.strip(), comparison.room.label
            assert ":" in comparison.why, comparison.room.label
