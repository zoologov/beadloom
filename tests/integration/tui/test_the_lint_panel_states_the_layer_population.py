"""The TUI lint panel states the layer rule's population, which it reads from a finding.

The panel never sees a `LintResult`: `tui/data_providers.py` calls `evaluate_all`
directly, which is why BDL-070 A2 emitted the population as a FINDING.

Split out of ``tests/test_every_surface_past_lint_states_the_population.py``
by node (BDL-074 E1); the behaviour is BDL-070 A4's (`beadloom-q6jh`). A4 is
additive at every surface: nothing here changes a count, and whether an advisory
statement counts as a violation is decided once, on `LintResult`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.layer_reach import LAYER_POPULATION_RULE_TYPE
from beadloom.infrastructure.db import connection
from beadloom.tui.data_providers import LintDataProvider
from beadloom.tui.widgets.lint_panel import LintPanelWidget
from tests.support.layer_population_projects import write_partly_layered_project

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@contextmanager
def _provider(project_root: Path) -> Iterator[LintDataProvider]:
    """The TUI's lint provider over the fixture's index."""
    with connection(project_root / ".beadloom" / "beadloom.db") as conn:
        yield LintDataProvider(conn=conn, project_root=project_root)


@pytest.fixture()
def partly_layered_project(tmp_path: Path) -> Path:
    """A project whose layer rule reaches half the edges it is handed."""
    return write_partly_layered_project(tmp_path)


class TestTheTuiPanelStatesThePopulation:
    """The panel never sees a `LintResult`; it takes the population from the finding."""

    def test_the_provider_carries_the_rule_type_and_the_message(
        self, partly_layered_project: Path
    ) -> None:
        """Both were dropped: the numbers live in the message and nowhere else."""
        with _provider(partly_layered_project) as provider:
            rows = provider.get_violations()

        population = [r for r in rows if r["rule_type"] == LAYER_POPULATION_RULE_TYPE]
        assert len(population) == 1
        assert "1 of 2" in (population[0]["message"] or "")

    def test_the_panel_renders_the_numbers(self, partly_layered_project: Path) -> None:
        with _provider(partly_layered_project) as provider:
            rows = provider.get_violations()
        panel = LintPanelWidget(violations=rows)

        rendered = panel.render().plain
        assert "1 of 2" in rendered

    def test_the_population_leads_the_list(self, partly_layered_project: Path) -> None:
        """The reach of a check is what the findings under it are true of."""
        with _provider(partly_layered_project) as provider:
            rows = provider.get_violations()
        panel = LintPanelWidget(violations=rows)

        body = panel.render().plain.splitlines()[1:]
        assert "1 of 2" in body[0]

    def test_the_count_is_unchanged(self, partly_layered_project: Path) -> None:
        """A4 states; it does not re-count. The open item is recorded on A7."""
        with _provider(partly_layered_project) as provider:
            assert provider.get_violation_count() == len(provider.get_violations())

    def test_a_panel_with_no_population_renders_as_before(self) -> None:
        panel = LintPanelWidget(
            violations=[
                {
                    "rule_name": "billing-no-auth",
                    "severity": "error",
                    "from_ref_id": "billing",
                    "to_ref_id": "auth",
                    "description": "Billing must not import auth",
                    "rule_type": "deny",
                    "message": "billing depends on auth",
                }
            ]
        )
        rendered = panel.render().plain
        assert "billing-no-auth" in rendered
        assert "judged" not in rendered
