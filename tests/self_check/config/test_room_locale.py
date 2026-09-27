"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_room_locale.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from tests.test_room_locale import (
    _declared_locales,
)


class TestTheNamesThisProjectPublishes:
    """The reproduction #249 is about, taken against this repository's own legs.

    A developer reproducing a locale leg copies the name out of `ci.yml`. These
    rows start a child under each of those names and ask the census what room
    that child is in. They are room-independent by construction: they assert the
    census AGREES with the child's own codec, never that a given name degrades —
    which it does on Darwin and does not on the leg that builds the locale.
    """

    def test_the_workflow_declares_locale_legs(self) -> None:
        """The population is found rather than listed, and it is not empty."""
        assert _declared_locales(), "ci.yml declares no locale leg to reproduce"
