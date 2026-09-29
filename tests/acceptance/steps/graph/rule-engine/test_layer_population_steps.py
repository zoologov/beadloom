"""Steps for `graph/rule-engine/layer_population.feature` (BDL-070 A7; BDL-074 E1).

Against a real project directory, the real reindex and the real linter: the
scenarios arrange a graph on disk and run the shipped code over it, through
:class:`~tests.support.rule_engine_driver.LayeredProject`. Nothing is mocked,
because a scenario that passes against a double proves the double.

Every step but one is the shared vocabulary
(:mod:`tests.support.rule_engine_vocabulary`); the one defined here
is the only sentence no other feature says.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_bdd import scenarios, then

from tests.support.rule_engine_driver import LayeredProject
from tests.support.rule_engine_vocabulary import (
    use_findings_vocabulary,
    use_layered_project_vocabulary,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/layer_population.feature")
use_findings_vocabulary()
use_layered_project_vocabulary()


@pytest.fixture()
def layered_project(tmp_path: Path) -> LayeredProject:
    return LayeredProject(tmp_path / "ledger")


@pytest.fixture()
def outcome(layered_project: LayeredProject) -> LayeredProject:
    return layered_project


@then("the statement is a warning even though the rule is declared an error")
def _a_warning_under_an_error_rule(layered_project: LayeredProject) -> None:
    [statement] = layered_project.run.population_statements()
    assert layered_project.layer_rule().severity == "error"
    assert statement.severity == "warn"
