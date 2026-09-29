"""Self-checks of the session snapshot this suite's self-checks read (BDL-074 A2, F3).

Moved out of ``tests/test_self_check_snapshot.py``; the product tests of the
snapshot helper, and the test of the rule that marks a snapshot reader, stay
there. These two ask for the real session snapshot -- this repository's working
tree, copied and indexed -- so they are self-checks of the suite's own
discipline, and carry the ``self_check`` marker by their folder (see
``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path


class TestTheSessionSnapshot:
    """The fixture every self-check reads instead of the live index."""

    def test_it_is_not_this_repository(self, self_check_snapshot: Path) -> None:
        assert self_check_snapshot.resolve() != REPO_ROOT.resolve()
        assert not self_check_snapshot.resolve().is_relative_to(REPO_ROOT.resolve())

    def test_it_carries_an_index_of_its_own(self, self_check_snapshot: Path) -> None:
        assert (self_check_snapshot / ".beadloom" / "beadloom.db").is_file()
        assert (self_check_snapshot / ".beadloom" / "_graph" / "rules.yml").is_file()
