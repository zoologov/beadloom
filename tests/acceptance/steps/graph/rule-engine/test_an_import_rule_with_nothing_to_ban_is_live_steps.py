"""Steps for `graph/rule-engine/an_import_rule_with_nothing_to_ban_is_live.feature`.

BDL-083 S1b (``beadloom-q8x6``), RFC D2, BDL-UX #328. Against a copy of the monorepo
fixture, the real reindex and the real linter: the fixture's own
``domain-no-io-imports-digest-os`` rule is the one the adopter's measurement was taken on, and
a step that changes a glob or adds an import edits the copy, never the fixture.

The copy is taken from the checkout the package under test ships from, as the composed-hooks
scenarios take theirs: ``tests.support.monorepo_fixture`` finds this repository's root when it
is imported, and a copied suite has none.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.graph.linter import lint
from beadloom.graph.rules.types import (
    INFO_SEVERITY,
    LIVENESS_RULE_TYPE,
    NOTHING_TO_BAN_RULE_TYPE,
)
from tests.support.package_under_test import SHIPPED_FROM

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules.types import Violation

scenarios("../../../graph/rule-engine/an_import_rule_with_nothing_to_ban_is_live.feature")

#: The fixture's rule, as the adopter wrote it; the steps rewrite only its `to:` glob.
_FIXTURE_TO = 'to: "os/**"'

#: A test boundary over the backend's unit tests, appended by the scenario that needs it.
_TEST_RULE = """
  - name: backend-unit-tests-no-os
    description: "A backend unit test does no I/O"
    test_import_boundary:
      from: "backend/tests/unit/**"
      to: "{to}"
"""

#: The suffix a fixture file named like one of this repository's tests is stored under —
#: ``tests.support.adopter_portals.STORED_SUFFIX``, spelled again because that module finds
#: this repository's root when it is imported, and a copied suite has none.
_STORED_SUFFIX = ".fixture"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / "metrics-desk"
    shutil.copytree(SHIPPED_FROM / "tests" / "fixtures" / "monorepo", root)
    for stored in sorted(root.rglob(f"*{_STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(_STORED_SUFFIX)))
    return {"root": root}


def _rules_file(world: dict[str, Any]) -> Path:
    path: Path = world["root"] / ".beadloom" / "_graph" / "rules.yml"
    return path


@given(parsers.parse('the monorepo fixture, whose digest domain bans every import of "{glob}"'))
def _digest_bans(world: dict[str, Any], glob: str) -> None:
    rules = _rules_file(world)
    text = rules.read_text(encoding="utf-8")
    assert _FIXTURE_TO in text, "the fixture's rule is the measurement; it must be present"
    rules.write_text(text.replace(_FIXTURE_TO, f'to: "{glob}"'), encoding="utf-8")


@given(
    parsers.parse('the monorepo fixture, whose backend unit tests ban every import of "{glob}"')
)
def _unit_tests_ban(world: dict[str, Any], glob: str) -> None:
    rules = _rules_file(world)
    rules.write_text(
        rules.read_text(encoding="utf-8") + _TEST_RULE.format(to=glob), encoding="utf-8"
    )


@given(parsers.parse('the digest domain imports "{module}"'))
def _digest_imports(world: dict[str, Any], module: str) -> None:
    sections = world["root"] / "backend" / "src" / "digest" / "sections.py"
    text = sections.read_text(encoding="utf-8")
    anchor = "from dataclasses import dataclass\n"
    sections.write_text(text.replace(anchor, f"{anchor}import {module}\n"), encoding="utf-8")


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    reindex(world["root"])
    world["result"] = lint(world["root"])


def _findings(world: dict[str, Any], rule: str, rule_type: str) -> list[Violation]:
    return [
        v
        for v in world["result"].violations
        if v.rule_name == rule and v.rule_type == rule_type
    ]


@then(parsers.parse('"{rule}" is stated live with nothing to ban, at info'))
def _live(world: dict[str, Any], rule: str) -> None:
    (statement,) = _findings(world, rule, NOTHING_TO_BAN_RULE_TYPE)
    assert statement.severity == INFO_SEVERITY
    assert "the rule is live" in statement.message
    assert "0 imports of" in statement.message


@then(parsers.parse('"{rule}" is not stated live with nothing to ban'))
def _not_live(world: dict[str, Any], rule: str) -> None:
    assert _findings(world, rule, NOTHING_TO_BAN_RULE_TYPE) == []


@then(parsers.parse('no finding says "{rule}" cannot fire'))
def _no_dead(world: dict[str, Any], rule: str) -> None:
    assert _findings(world, rule, LIVENESS_RULE_TYPE) == []


@then(parsers.parse('"{rule}" reports the import in "{path}"'))
def _reports(world: dict[str, Any], rule: str, path: str) -> None:
    (crossing,) = _findings(world, rule, "forbid_import")
    assert crossing.file_path == path


@then(parsers.parse('"{rule}" cannot fire, at warn, because its glob begins with "{segment}"'))
def _dead(world: dict[str, Any], rule: str, segment: str) -> None:
    (dead,) = _findings(world, rule, LIVENESS_RULE_TYPE)
    assert dead.severity == "warn"
    assert "cannot fire" in dead.message
    assert f"begins with '{segment}'" in dead.message
    assert _findings(world, rule, NOTHING_TO_BAN_RULE_TYPE) == []


@then("the strict lint passes")
def _passes(world: dict[str, Any]) -> None:
    assert not world["result"].has_errors


@then("the strict lint fails")
def _fails(world: dict[str, Any]) -> None:
    assert world["result"].has_errors
