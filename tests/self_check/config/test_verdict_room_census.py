"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/unit/application/rooms/test_verdict_room_census.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.application.rooms import take_census
from tests.support.repository_root import REPO_ROOT


class TestTheCensusOverARealDeclaration:
    def test_this_repository_is_not_in_any_of_its_own_ci_legs_unless_it_is(
        self,
    ) -> None:
        """The claim BDL-067 made nine times, computed instead of assumed.

        Stated over the arithmetic rather than under a platform branch. The
        earlier form asserted the interesting half only when `platform.system()`
        was not Linux — and Linux is the one platform this repository's legs run
        on, so the assertion stepped out of the room it is about. Every leg is
        accounted for as entered or not in either room, and an entered leg
        carries no reason, which is the half a developer machine cannot reach.
        """
        census = take_census(REPO_ROOT)
        assert census.comparisons != ()
        assert len(census.entered) + len(census.not_entered) == len(census.comparisons)
        assert census.not_entered, "no run is inside every leg this project declares"
        for comparison in census.entered:
            assert comparison.why == "", comparison.room.label
