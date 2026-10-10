"""``lint --strict`` judges an FSD project's layers when the command before it was ``init``.

BDL-080 S3T, the PRD's goal 4: "*Done when* ``init`` on the fixture needs no hand edit for
``lint --strict`` to judge its layers". The adopter harness declares a portal's identity
and reindexes between ``init`` and ``lint``; here nothing runs between them, so the rules,
tags and edges ``lint`` reads are the ones ``init`` wrote and nobody else.

The findings each fixture earns are read from its code
(:data:`tests.support.fsd_adopter_fixtures.PLANTED`), not from the product.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import FIXTURES_BY_STACK, FSD_LAYERS
from tests.support.fsd_adopter_fixtures import PLANTED, PlantedFinding
from tests.support.initialised_fixture import InitialisedFixture, initialise_fixture

if TYPE_CHECKING:
    from collections.abc import Callable

pytest.importorskip("tree_sitter_typescript")

#: The two FSD fixtures, whose layers ``init`` writes.
_FSD_STACKS = [stack for stack, fixture in FIXTURES_BY_STACK.items() if fixture.layers_by_init]


@dataclass(frozen=True)
class Linted:
    """A fixture straight after ``init``, and ``lint --strict``'s answer on it."""

    initialised: InitialisedFixture
    exit_code: int
    report: dict[str, Any]

    def findings(self) -> list[dict[str, Any]]:
        """Every finding but the layer rule's statement of the edges it judged."""
        return [v for v in self.report["violations"] if v["rule_type"] != "layer_population"]


@pytest.fixture(scope="module")
def linted(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], Linted]:
    """The fixture of *stack* given ``init`` and then ``lint --strict``, once per module."""
    done: dict[str, Linted] = {}

    def linted_of(stack: str) -> Linted:
        if stack not in done:
            initialised = initialise_fixture(stack, tmp_path_factory.mktemp(f"init-{stack}"))
            result = CliRunner().invoke(
                main,
                ["lint", "--strict", "--format", "json", "--project", str(initialised.root)],
            )
            done[stack] = Linted(initialised, result.exit_code, json.loads(result.stdout))
        return done[stack]

    return linted_of


@pytest.mark.parametrize("stack", _FSD_STACKS)
def test_lint_after_init_exits_with_the_code_the_fixtures_code_earns(
    linted: Callable[[str], Linted], stack: str
) -> None:
    run = linted(stack)

    assert run.exit_code == FIXTURES_BY_STACK[stack].init_exit, run.initialised.init_output


@pytest.mark.parametrize("stack", _FSD_STACKS)
def test_lint_after_init_judges_edges_under_the_six_layers_init_wrote(
    linted: Callable[[str], Linted], stack: str
) -> None:
    run = linted(stack)
    rules_file = run.initialised.root / ".beadloom" / "_graph" / "rules.yml"
    layer_rules = [
        rule
        for rule in yaml.safe_load(rules_file.read_text(encoding="utf-8"))["rules"]
        if "layers" in rule
    ]

    population = [
        v["message"]
        for v in run.report["violations"]
        if v["rule_type"] == "layer_population" and v["rule_name"] == layer_rules[0]["name"]
    ]

    assert [tuple(layer["name"] for layer in rule["layers"]) for rule in layer_rules] == [
        FSD_LAYERS
    ]
    assert len(population) == 1, run.report["violations"]
    judged = int(population[0].split("evaluated ", 1)[1].split(" of ", 1)[0])
    assert judged > 0, population


@pytest.mark.parametrize("stack", _FSD_STACKS)
def test_lint_after_init_reports_exactly_the_findings_the_fixtures_code_plants(
    linted: Callable[[str], Linted], stack: str
) -> None:
    run = linted(stack)
    sources = run.initialised.sources()

    found = {
        PlantedFinding(
            v["rule_name"],
            v["severity"],
            sources.get(v["from_ref_id"] or "", ""),
            sources.get(v["to_ref_id"] or "", ""),
            v["file_path"] or "",
        )
        for v in run.findings()
    }

    assert found == PLANTED[stack]
