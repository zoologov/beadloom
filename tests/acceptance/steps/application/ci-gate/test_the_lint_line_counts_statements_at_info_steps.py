"""Step implementations for `application/ci-gate/the_lint_line_counts_statements_at_info.feature`.

BDL-083 S1 fix 1 (``beadloom-4m0w``, S1R Minor 5). The real ``beadloom ci`` runs
in-process over a copy of the monorepo fixture, whose digest domain bans every import of
``os`` and imports none, so the linter states that rule live at info. The count the line
must carry is read from the linter's own result over the same copy rather than spelled
here alone, so the scenario holds the Gate line to the command it summarises.

The copy is taken from the checkout the package under test ships from, as the S1b
scenarios take theirs, and the tracker adapter is doubled to report no claimed bead.
"""

from __future__ import annotations

import re
import shutil
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.graph.linter import lint
from beadloom.graph.rules.types import INFO_SEVERITY
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main
from tests.support.package_under_test import SHIPPED_FROM

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/ci-gate/the_lint_line_counts_statements_at_info.feature")

#: The fixture's own rule over the digest domain: it bans `os`, and the domain imports none.
_FIXTURE_TO = 'to: "os/**"'

#: The suffix a fixture file named like one of this repository's tests is stored under.
_STORED_SUFFIX = ".fixture"

#: The rich report's lint line, ``[STATUS] lint: summary``.
_LINT_LINE = re.compile(r"^\s*\[(?P<status>[A-Z]+)\] lint: (?P<summary>.*)$", re.MULTILINE)


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    from beadloom.services import guard_probes

    monkeypatch.setattr(guard_probes.BdWorkTracker, "claimed_beads", lambda _self: ())
    return {"root": tmp_path / "project", "result": None}


@given(parsers.parse('the monorepo fixture, whose digest domain has nothing of "{module}" to ban'))
def _the_fixture(world: dict[str, Any], module: str) -> None:
    root = world["root"]
    shutil.copytree(SHIPPED_FROM / "tests" / "fixtures" / "monorepo", root)
    for stored in sorted(root.rglob(f"*{_STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(_STORED_SUFFIX)))
    rules = (root / ".beadloom" / "_graph" / "rules.yml").read_text(encoding="utf-8")
    assert f'to: "{module}/**"' == _FIXTURE_TO, "the scenario names the fixture's own rule"
    assert _FIXTURE_TO in rules, "the fixture's rule is the measurement; it must be present"
    reindex(root)


@given("a project on which every gate step passes")
def _a_clean_project(world: dict[str, Any]) -> None:
    root = world["root"]
    (root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(root)
    reindex(root)


@when("the gate runs on that project")
def _run_rich(world: dict[str, Any]) -> None:
    world["result"] = CliRunner().invoke(
        main, ["ci", "--project", str(world["root"]), "--format", "rich"]
    )


def _lint_line(world: dict[str, Any]) -> re.Match[str]:
    match = _LINT_LINE.search(world["result"].stdout)
    assert match is not None, world["result"].output
    return match


@then(parsers.parse("the lint line counts {count:d} statement(s) at info"))
def _counts_info(world: dict[str, Any], count: int) -> None:
    found = sum(1 for v in lint(world["root"]).violations if v.severity == INFO_SEVERITY)
    assert found == count, "the fixture's measurement moved; the scenario names it"
    assert f"{count} statement(s) at info" in _lint_line(world)["summary"]


@then("the lint step passes")
def _lint_passes(world: dict[str, Any]) -> None:
    assert _lint_line(world)["status"] == "PASS"


@then("the lint line names no statement at info")
def _no_info(world: dict[str, Any]) -> None:
    assert "at info" not in _lint_line(world)["summary"]
