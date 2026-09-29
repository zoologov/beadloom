"""The MCP lint tool's JSON carries the layer rule's population beside its counts.

Split out of ``tests/test_every_surface_past_lint_states_the_population.py``
by node (BDL-074 E1); the behaviour is BDL-070 A4's (`beadloom-q6jh`). A4 is
additive at every surface: nothing here changes a count, and whether an advisory
statement counts as a violation is decided once, on `LintResult`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.services.mcp_server import handle_lint
from tests.support.layer_population_projects import (
    write_partly_layered_project,
    write_unlayered_project,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The summary keys `handle_lint` carried before this bead, named one by one.
#: "Additive only" is a promise to a consumer that reads a key by name, and a
#: length check keeps passing while a rename breaks it.
_MCP_SUMMARY_KEYS_BEFORE_A4 = frozenset({"errors", "warnings", "rules_evaluated"})


@pytest.fixture()
def partly_layered_project(tmp_path: Path) -> Path:
    """A project whose layer rule reaches half the edges it is handed."""
    return write_partly_layered_project(tmp_path)


@pytest.fixture()
def unlayered_project(tmp_path: Path) -> Path:
    """A project that declares no layer rule."""
    return write_unlayered_project(tmp_path)


class TestTheMcpLintToolStatesThePopulation:
    """An agent reading the tool's JSON gets the denominator with the counts."""

    def test_the_summary_carries_one_entry_per_layer_rule(
        self, partly_layered_project: Path
    ) -> None:
        summary = handle_lint(partly_layered_project)["summary"]

        assert [entry["rule"] for entry in summary["layer_populations"]] == ["architecture-layers"]
        entry = summary["layer_populations"][0]
        assert (entry["evaluated"], entry["total"]) == (1, 2)
        assert entry["edge_kind"] == "depends_on"

    def test_the_keys_that_were_there_are_still_there(self, partly_layered_project: Path) -> None:
        summary = handle_lint(partly_layered_project)["summary"]
        assert set(summary) >= _MCP_SUMMARY_KEYS_BEFORE_A4

    def test_a_severity_filter_does_not_filter_the_population(
        self, partly_layered_project: Path
    ) -> None:
        """The population is not a finding, so a finding filter cannot hide it."""
        summary = handle_lint(partly_layered_project, severity="error")["summary"]
        assert len(summary["layer_populations"]) == 1

    def test_a_project_with_no_layer_rule_carries_an_empty_list(
        self, unlayered_project: Path
    ) -> None:
        assert handle_lint(unlayered_project)["summary"]["layer_populations"] == []
