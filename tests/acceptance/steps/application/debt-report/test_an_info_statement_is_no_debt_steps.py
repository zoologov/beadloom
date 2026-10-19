"""Steps for `application/debt-report/an_info_statement_is_no_debt.feature`.

BDL-083 S1 fix 2 (``beadloom-ilrn``), S1R Major 2. Against a copy of the monorepo fixture,
the real reindex and the real debt collector. The collector reads its rules from
``rules.yml`` or ``.beadloom/rules.yml`` only, and the fixture declares them in
``.beadloom/_graph/rules.yml`` (BDL-UX #291), so the step writes the fixture's one import
rule where the collector looks.

The copy is taken from the checkout the package under test ships from, as the rule-engine
scenarios take theirs, because a copied suite has no repository root to find.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.debt_report import collect_debt_data
from beadloom.application.reindex import reindex
from beadloom.graph.rule_engine import INFO_SEVERITY, evaluate_all, load_rules
from beadloom.infrastructure.db import open_db
from tests.support.package_under_test import SHIPPED_FROM

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/debt-report/an_info_statement_is_no_debt.feature")

#: The fixture's own `forbid_import` rule, alone, with its `to:` glob left to the scenario.
_RULES = """\
version: 3
rules:
  - name: domain-no-io-imports-digest-os
    description: "The digest domain does no I/O: it imports nothing of os"
    forbid_import:
      from: "backend/src/digest/**"
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


def _rules_path(world: dict[str, Any]) -> Path:
    path: Path = world["root"] / ".beadloom" / "rules.yml"
    return path


@given(parsers.parse('the monorepo fixture, whose digest domain bans every import of "{glob}"'))
def _digest_bans(world: dict[str, Any], glob: str) -> None:
    _rules_path(world).write_text(_RULES.format(to=glob), encoding="utf-8")


@given(parsers.parse('the digest domain imports "{module}"'))
def _digest_imports(world: dict[str, Any], module: str) -> None:
    sections = world["root"] / "backend" / "src" / "digest" / "sections.py"
    text = sections.read_text(encoding="utf-8")
    anchor = "from dataclasses import dataclass\n"
    assert anchor in text, "the import is placed after the fixture's own first import"
    sections.write_text(text.replace(anchor, f"{anchor}import {module}\n"), encoding="utf-8")


@when("the debt report is collected")
def _collect(world: dict[str, Any]) -> None:
    root = world["root"]
    reindex(root)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        world["findings"] = evaluate_all(conn, load_rules(_rules_path(world)), project_root=root)
        world["debt"] = collect_debt_data(conn, root)
    finally:
        conn.close()


@then(parsers.parse('the rule engine stated "{rule}" at info'))
def _stated_at_info(world: dict[str, Any], rule: str) -> None:
    assert [(f.rule_name, f.severity) for f in world["findings"]] == [(rule, INFO_SEVERITY)]


@then(
    parsers.re(
        r"the debt report counts (?P<errors>\d+) rule errors? "
        r"and (?P<warnings>\d+) rule warnings?"
    )
)
def _counts(world: dict[str, Any], errors: str, warnings: str) -> None:
    debt = world["debt"]
    assert (debt.error_count, debt.warning_count) == (int(errors), int(warnings))
