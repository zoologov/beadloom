"""One phrase states a layer rule's population, and every surface prints that phrase.

`population_phrase` is the single wording; the Gate line, the GitHub notice,
`prime`'s health line and the debt report all call it. Five surfaces phrasing one
fact five ways is the defect BDL-070 is about, in miniature, so it is asserted
rather than reviewed.

Split out of ``tests/test_every_surface_past_lint_states_the_population.py``
by node (BDL-074 E1); the behaviour is BDL-070 A4's (`beadloom-q6jh`). A4 is
additive at every surface: nothing here changes a count, and whether an advisory
statement counts as a violation is decided once, on `LintResult`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.linter import format_github, lint
from beadloom.graph.rules.layer_reach import (
    layer_rule_reaches,
    population_phrase,
    stated_populations,
)
from beadloom.infrastructure.db import connection
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


class TestOnePhrasingServesEverySurface:
    """The wording lives once, so five surfaces cannot drift into five wordings."""

    def test_the_phrase_names_the_rule_the_fraction_and_the_edge_kind(
        self, partly_layered_project: Path
    ) -> None:
        with connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            from beadloom.graph.rules import LayerRule, load_rules

            rules = load_rules(partly_layered_project / ".beadloom" / "_graph" / "rules.yml")
            reaches = layer_rule_reaches(conn, [r for r in rules if isinstance(r, LayerRule)])

        assert [population_phrase(reach) for reach in reaches] == [THE_PHRASE]

    def test_a_rule_handed_no_edge_of_its_kind_is_not_stated(
        self, unlayered_project: Path
    ) -> None:
        """No denominator, nothing to say — and liveness already says the rest."""
        assert stated_populations(lint(unlayered_project).layer_populations) == []

    def test_the_github_notice_carries_the_shared_phrase(
        self, partly_layered_project: Path
    ) -> None:
        """A3's rendering is now the shared phrase rather than its own copy."""
        assert f"::notice::{THE_PHRASE}" in format_github(lint(partly_layered_project))
