"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/integration/application/rooms/test_verdict_room_derivation.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import pytest

from beadloom.application.rooms import derive_declared_rooms
from tests.support.repository_root import REPO_ROOT


class TestThisRepositorysOwnDeclaration:
    """The derivation over the tree it ships in, so a leg change is felt here."""

    @pytest.fixture()
    def declared(self) -> object:
        return derive_declared_rooms(REPO_ROOT)

    def test_every_supported_interpreter_has_a_leg(self, declared: object) -> None:
        rooms = declared.rooms  # type: ignore[attr-defined]
        legs = {r.dimensions.get("python") for r in rooms}
        for version in declared.supported:  # type: ignore[attr-defined]
            assert version in legs, f"{version} is supported and no CI leg enters it"

    def test_every_hosted_leg_is_the_one_platform_this_project_declares(
        self, declared: object
    ) -> None:
        """The platform dimension was priced and declined, so this is one value.

        The assertion is not that Ubuntu is right. It is that the report reads
        the declaration: if a second platform is ever added, this fails and the
        room reporting is re-read rather than assumed. The self-hosted publisher
        is excluded by its label naming no platform, not by being named here.
        """
        from beadloom.application.rooms import RUNNER_PLATFORMS

        hosted = {
            r.dimensions["os"]
            for r in declared.rooms  # type: ignore[attr-defined]
            if r.dimensions["os"].split("-", 1)[0] in RUNNER_PLATFORMS
        }
        assert hosted == {"ubuntu-latest"}, hosted
