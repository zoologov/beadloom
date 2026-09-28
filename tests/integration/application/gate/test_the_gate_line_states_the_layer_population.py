"""`beadloom ci`'s lint step states the population the layer rule judged.

Split out of ``tests/test_every_surface_past_lint_states_the_population.py``
by node (BDL-074 E1); the behaviour is BDL-070 A4's (`beadloom-q6jh`). A4 is
additive at every surface: nothing here changes a count, and whether an advisory
statement counts as a violation is decided once, on `LintResult`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.gate import lint_step
from tests.support.layer_population_projects import (
    THE_PHRASE,
    write_partly_layered_project,
    write_unlayered_project,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def partly_layered_project(tmp_path: Path) -> Path:
    """A project whose layer rule reaches half the edges it is handed."""
    return write_partly_layered_project(tmp_path)


@pytest.fixture()
def unlayered_project(tmp_path: Path) -> Path:
    """A project that declares no layer rule."""
    return write_unlayered_project(tmp_path)


class TestTheGateLineStatesThePopulation:
    """`beadloom ci`'s lint step is the line a push is judged by."""

    def test_the_summary_carries_the_phrase(self, partly_layered_project: Path) -> None:
        assert THE_PHRASE in lint_step(partly_layered_project).summary

    def test_a_project_with_no_layer_rule_gets_no_clause(self, unlayered_project: Path) -> None:
        assert "judged" not in lint_step(unlayered_project).summary

    def test_the_verdict_is_unchanged(self, partly_layered_project: Path) -> None:
        """The clause qualifies the line; it decides nothing on it."""
        step = lint_step(partly_layered_project)
        assert step.passed is True
