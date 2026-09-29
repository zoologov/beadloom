"""`prime`'s health line states what the layer rule judged, once per rule.

Split out of ``tests/test_every_surface_past_lint_states_the_population.py``
by node (BDL-074 E1); the behaviour is BDL-070 A4's (`beadloom-q6jh`). A4 is
additive at every surface: nothing here changes a count, and whether an advisory
statement counts as a violation is decided once, on `LintResult`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.scanner.prime import prime_context
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


class TestPrimeStatesThePopulation:
    """The context an agent is primed with states what its health line covers."""

    def test_the_health_line_carries_the_phrase(self, partly_layered_project: Path) -> None:
        text = prime_context(partly_layered_project)
        assert isinstance(text, str)
        health = next(line for line in text.splitlines() if line.startswith("Health:"))
        assert THE_PHRASE in health

    def test_the_json_form_carries_it(self, partly_layered_project: Path) -> None:
        payload = prime_context(partly_layered_project, fmt="json")
        assert isinstance(payload, dict)
        assert payload["health"]["layer_populations"] == [THE_PHRASE]

    def test_a_project_with_no_layer_rule_gets_no_clause(self, unlayered_project: Path) -> None:
        text = prime_context(unlayered_project)
        assert isinstance(text, str)
        assert "judged" not in text

    def test_the_clause_is_per_rule_not_per_finding(self, partly_layered_project: Path) -> None:
        """The budget survives because the clause does not grow with the graph.

        ``prime``'s list is capped at ten findings; the population is one line
        per DECLARED layer rule, so a repository with a thousand findings adds
        the same one clause a repository with none does.
        """
        text = prime_context(partly_layered_project)
        assert isinstance(text, str)
        assert text.count("judged") == 1
        assert len(text.encode("utf-8")) < 8000
