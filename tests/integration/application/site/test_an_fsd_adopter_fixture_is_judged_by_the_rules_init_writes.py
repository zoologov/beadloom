"""``init`` on each FSD adopter fixture writes rules that judge its layers, with no hand edit.

BDL-080 S3d (``beadloom-chdx``), the PRD's goal 4: "*Done when* ``init`` on the fixture
needs no hand edit for ``lint --strict`` to judge its layers". The two fixtures are a
Vue 3 + TypeScript storefront and an Expo + React Native app, both in the Feature-Sliced
layout (the PRD's answer 2). Each is adopted as :func:`~tests.support.adopter_portals.adopt`
adopts every claimed stack: copied, committed, ``init --yes``, the portal's identity and
nothing else declared, ``reindex``, ``docs site``. Then ``lint --strict`` runs on it.

What the cases hold, each read from the fixture's code in
:mod:`tests.support.fsd_adopter_fixtures` and not from the product:

- ``init`` exits with the code its fixture's code earns (1 on the Vue fixture, whose code
  breaks the error rules twice on purpose; 0 on the React Native one) and writes the six
  layers itself, and the layer rule judges edges;
- ``lint`` reports exactly the planted findings;
- every import form of the RFC's list resolves to the folder its reader names, and every
  import into the project resolves at all;
- the Expo module's TypeScript is joined to its Swift and its Kotlin side.

Not slow: no ``npm``, no browser. The portals themselves are built by the slow tests.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import FIXTURES_BY_STACK, FSD_LAYERS, adopt
from tests.support.fsd_adopter_fixtures import (
    EXPO_BRIDGES,
    EXPO_ROUTER_FILES,
    EXPO_ROUTER_ROUTES,
    FORMS,
    IMPORT_FORMS,
    PLANTED,
    PROJECT_PREFIXES,
    PlantedFinding,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from tests.support.adopter_portals import BuiltPortal

pytest.importorskip("tree_sitter_typescript")

#: The two FSD fixtures, in the order they are claimed.
_FSD_STACKS = [stack for stack, fixture in FIXTURES_BY_STACK.items() if fixture.layers_by_init]

#: The gap this bead measured and did not close: a product change, for the coordinator.
_ROUTES_GAP = (
    "beadloom-chdx gap: init writes no node for Expo Router's app/ beside an FSD src/ - "
    "it clusters app/trail/ as a node named after the route and leaves app/_layout.tsx "
    "and app/index.tsx with no owner, so two of the three route imports draw no edge"
)


@dataclass
class Adopted:
    """A fixture adopted, with its index and ``lint --strict``'s answer on it."""

    portal: BuiltPortal
    lint_exit: int
    lint: dict[str, Any]

    @property
    def root(self) -> Path:
        return self.portal.root

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        with sqlite3.connect(self.root / ".beadloom" / "beadloom.db") as conn:
            return list(conn.execute(sql))

    def sources(self) -> dict[str, str]:
        """Each node's source folder, without its trailing slash, by ref_id."""
        return {
            ref: (src or "").rstrip("/")
            for ref, src in self.query("SELECT ref_id, source FROM nodes")
        }


@pytest.fixture(scope="module")
def adopted(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], Adopted]:
    """The FSD fixture of *stack*, adopted and linted once per module."""
    done: dict[str, Adopted] = {}

    def adopted_of(stack: str) -> Adopted:
        if stack not in done:
            portal = adopt(FIXTURES_BY_STACK[stack], tmp_path_factory.mktemp(f"fsd-{stack}"))
            assert portal.failed_step() is None, portal.failed_step()
            result = CliRunner().invoke(
                main, ["lint", "--strict", "--format", "json", "--project", str(portal.root)]
            )
            done[stack] = Adopted(portal, result.exit_code, json.loads(result.stdout))
        return done[stack]

    return adopted_of


def test_the_two_fsd_fixtures_are_claimed_stacks() -> None:
    assert _FSD_STACKS == ["vue-fsd", "rn-fsd"]
    assert set(IMPORT_FORMS) == set(PLANTED) == set(_FSD_STACKS)


@pytest.mark.parametrize("stack", _FSD_STACKS)
def test_init_exits_with_the_code_the_fixtures_code_earns(
    adopted: Callable[[str], Adopted], stack: str
) -> None:
    fixture = adopted(stack)
    init = fixture.portal.steps["init"]

    assert init.returncode == fixture.portal.fixture.init_exit, init.output
    names_the_code = "your code does not pass the rules this command wrote" in init.output
    assert names_the_code is (init.returncode == 1)


@pytest.mark.parametrize("stack", _FSD_STACKS)
def test_init_writes_the_six_layers_and_the_rule_judges_edges_with_no_hand_edit(
    adopted: Callable[[str], Adopted], stack: str
) -> None:
    fixture = adopted(stack)
    rules = yaml.safe_load(
        (fixture.root / ".beadloom" / "_graph" / "rules.yml").read_text(encoding="utf-8")
    )["rules"]
    layer_rules = [rule for rule in rules if "layers" in rule]
    population = [
        v["message"]
        for v in fixture.lint["violations"]
        if v["rule_type"] == "layer_population" and v["rule_name"] == layer_rules[0]["name"]
    ]

    assert len(layer_rules) == 1
    assert tuple(layer["name"] for layer in layer_rules[0]["layers"]) == FSD_LAYERS
    assert len(population) == 1
    judged = int(population[0].split("evaluated ", 1)[1].split(" of ", 1)[0])
    assert judged > 0, population


@pytest.mark.parametrize("stack", _FSD_STACKS)
def test_lint_reports_exactly_the_findings_the_fixtures_code_plants(
    adopted: Callable[[str], Adopted], stack: str
) -> None:
    fixture = adopted(stack)
    sources = fixture.sources()

    found = {
        PlantedFinding(
            v["rule_name"],
            v["severity"],
            sources.get(v["from_ref_id"] or "", ""),
            sources.get(v["to_ref_id"] or "", ""),
            v["file_path"] or "",
        )
        for v in fixture.lint["violations"]
        if v["rule_type"] != "layer_population"
    }

    assert found == PLANTED[stack]
    assert fixture.lint_exit == fixture.portal.fixture.init_exit


@pytest.mark.parametrize("stack", _FSD_STACKS)
def test_every_import_form_resolves_to_the_folder_its_reader_names(
    adopted: Callable[[str], Adopted], stack: str
) -> None:
    fixture = adopted(stack)
    sources = fixture.sources()
    resolved = {
        (path, specifier): sources.get(ref or "")
        for path, specifier, ref in fixture.query(
            "SELECT file_path, import_path, resolved_ref_id FROM code_imports"
        )
    }

    wrong = [
        (form.form, form.importer, form.specifier, resolved.get((form.importer, form.specifier)))
        for form in IMPORT_FORMS[stack]
        if resolved.get((form.importer, form.specifier)) != form.target
    ]

    assert wrong == []


@pytest.mark.parametrize("stack", _FSD_STACKS)
def test_every_import_into_the_project_resolves(
    adopted: Callable[[str], Adopted], stack: str
) -> None:
    fixture = adopted(stack)
    rows = fixture.query("SELECT file_path, import_path, resolved_ref_id FROM code_imports")
    into_the_project = [row for row in rows if row[1].startswith(PROJECT_PREFIXES[stack])]

    unresolved = [(path, specifier) for path, specifier, ref in into_the_project if ref is None]

    assert into_the_project
    assert unresolved == []


def test_every_form_of_the_rfcs_list_is_carried_by_a_fixture() -> None:
    carried = {form.form for forms in IMPORT_FORMS.values() for form in forms}

    assert carried == set(FORMS)


def test_the_expo_module_joins_its_typescript_to_its_swift_and_kotlin_sides(
    adopted: Callable[[str], Adopted],
) -> None:
    fixture = adopted("rn-fsd")
    sources = fixture.sources()

    bridges = {
        (sources[src], sources[dst])
        for src, dst, extra in fixture.query("SELECT src_ref_id, dst_ref_id, extra FROM edges")
        if json.loads(extra or "{}").get("derived") == "expo-module"
    }

    assert bridges == EXPO_BRIDGES["rn-fsd"]


@pytest.mark.xfail(reason=_ROUTES_GAP, strict=True)
def test_expo_routers_routes_are_one_node_that_owns_every_route_file(
    adopted: Callable[[str], Adopted],
) -> None:
    fixture = adopted("rn-fsd")
    sources = set(fixture.sources().values())

    assert EXPO_ROUTER_ROUTES in sources
    assert [s for s in sources if s.startswith(f"{EXPO_ROUTER_ROUTES}/")] == []
    assert all((fixture.root / path).is_file() for path in EXPO_ROUTER_FILES)
