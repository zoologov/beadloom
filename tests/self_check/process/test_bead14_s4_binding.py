"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_bead14_s4_binding.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.scenarios import DEFAULT_FEATURE_GLOB, load_suite
from tests.support.nested_pytest import (
    run_pytest,
)
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: This repository, so the shipped configuration is read rather than restated.


def _shipped_scenario_count() -> int:
    """How many scenarios the shipped suite declares, READ from the suite.

    Counted rather than written down (`beadloom-b0xl`): the number was 7 when
    `.13` shipped and every later slice that adds a scenario would otherwise
    redden two tests that have nothing to do with it. The count comes from the
    project's own parser, which `.13` cross-checked against gherkin-official, so
    a parser that started disagreeing with the runner still shows up here.
    """
    suite = load_suite(REPO_ROOT, DEFAULT_FEATURE_GLOB)
    return len(suite.scenarios)


class TestTheScenariosExecute:
    """A `.feature` file nothing runs is prose, and the rule would be checking text."""

    def test_the_shipped_acceptance_suite_runs_every_scenario_and_skips_none(
        self, tmp_path: Path
    ) -> None:
        """Every declared scenario RAN.

        Collected-and-skipped would give the same reassuring green with nothing
        executed, so the outcome of every row is read individually and a skip is a
        failure of this test. The expected number is the number the suite declares.
        """
        code, outcomes = run_pytest(
            ["tests/acceptance"], cwd=REPO_ROOT, report=tmp_path / "report.xml"
        )

        assert code == 0, outcomes
        assert [name for name, outcome in outcomes if outcome == "skipped"] == []
        passed = [name for name, outcome in outcomes if outcome == "passed"]
        assert len(passed) == _shipped_scenario_count(), outcomes
