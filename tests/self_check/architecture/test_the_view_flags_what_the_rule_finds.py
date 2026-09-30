"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/integration/application/test_the_view_flags_what_the_rule_finds.py``;
the product tests of the same code stay in that file, which BDL-076 K1 moved to
``tests/integration/application/site/``.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.layer_rule import (
    rule_flags,
    view_flags,
    view_verdicts,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture()
def live(self_check_snapshot: Path) -> Iterator[Path]:
    yield self_check_snapshot


class TestOnThisRepository:
    """The done-when, taken on the graph the bead names."""

    def test_the_two_instruments_flag_the_same_edge_set(self, live: Path) -> None:
        assert view_flags(live) == rule_flags(live)

    def test_the_agreement_is_not_vacuous(self, live: Path) -> None:
        """Both sets are empty here, and that has to be a measurement.

        This repository's crossings were removed or excused by name in B2, so
        the agreement above would also hold if the view had stopped flagging
        anything at all. What makes it a measurement is the population: the view
        renders a verdict on the edges the rule judges, and that is most of
        them.
        """
        verdicts = view_verdicts(live)
        decided = [edge for edge, verdict in verdicts.items() if verdict is not None]
        assert len(verdicts) > 300
        assert len(decided) > len(verdicts) * 9 // 10
        assert view_flags(live) == set()
