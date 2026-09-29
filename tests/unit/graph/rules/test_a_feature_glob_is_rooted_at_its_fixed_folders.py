"""The suite root of a ``scenario_binding`` rule is its glob's segments before the first wildcard.

Every placement the rule judges is read relative to that root, and the move hint names it,
so a root that loses its separators would misplace every file in a nested suite.
"""

from __future__ import annotations

import pytest

from beadloom.graph.rules.scenario_binding import suite_root


@pytest.mark.parametrize(
    ("glob", "root"),
    [
        pytest.param("tests/acceptance/**/*.feature", "tests/acceptance", id="two folders"),
        pytest.param("specs/*.feature", "specs", id="one folder"),
        pytest.param("**/*.feature", "", id="a wildcard first"),
        pytest.param("specs/v[12]/*.feature", "specs", id="a character class"),
    ],
)
def test_the_root_is_every_segment_before_the_first_wildcard(glob: str, root: str) -> None:
    found = suite_root(glob)

    assert found == root
