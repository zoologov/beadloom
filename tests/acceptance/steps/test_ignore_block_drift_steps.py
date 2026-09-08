"""Step implementations for `features/ignore_block_drift.feature` (BDL-068 S6).

Thin by design: every step writes a real ``.gitignore`` into a real project and
runs the real check, and the expected patterns come from the generator's own
:data:`~beadloom.onboarding.ignore_block.GENERATED_WORKING_SET` rather than from
a copy. A scenario that names a pattern literally is naming the STALE line an
adopter's file carries, never the line the generator emits.

The module is named ``test_*`` so default pytest collection picks the scenarios
up -- the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

import beadloom
from beadloom.onboarding import ignore_block
from beadloom.onboarding.ignore_block import (
    GENERATED_WORKING_SET,
    IgnoreEntry,
    ignore_block_findings,
    undeclared_patterns,
)
from beadloom.services.cli import main

scenarios("../features/ignore_block_drift.feature")

#: The project the package under test ships from: src/beadloom/__init__.py's
#: grandparent. Derived from the PACKAGE and not from this file, because the
#: suite is copied out of the tree by `tests/test_bead14_s4_binding.py` while
#: PYTHONPATH still names the source under test -- a scenario that located the
#: project by counting parents of its own path answered about the copy.
_SHIPPED_FROM = Path(beadloom.__file__).resolve().parents[2]


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    (tmp_path / ".beadloom").mkdir()
    return {"root": tmp_path}


def _write_ignore(world: dict[str, Any], text: str) -> None:
    (world["root"] / ".gitignore").write_text(text, encoding="utf-8")


def _make_git(world: dict[str, Any]) -> None:
    (world["root"] / ".git").mkdir()


@given("a git project whose .gitignore declares every generated pattern")
def _declares_everything(world: dict[str, Any]) -> None:
    _make_git(world)
    _write_ignore(world, "\n".join(entry.pattern for entry in GENERATED_WORKING_SET) + "\n")


@given("a git project whose .gitignore declares every generated pattern under its own heading")
def _declares_everything_hand_written(world: dict[str, Any]) -> None:
    """This repository's own shape: the patterns, under prose nobody generated."""
    _make_git(world)
    lines = ["# Beadloom (auto-generated SQLite databases + WAL files)"]
    lines.extend(entry.pattern for entry in GENERATED_WORKING_SET)
    _write_ignore(world, "\n".join(lines) + "\n")


@given("a git project whose .gitignore declares nothing")
def _declares_nothing(world: dict[str, Any]) -> None:
    _make_git(world)
    _write_ignore(world, "# nothing here\n")


@given(parsers.parse('a git project whose .gitignore declares "{pattern}"'))
def _declares_one_stale_pattern(world: dict[str, Any], pattern: str) -> None:
    """Every current pattern except the one *pattern* is the stale ancestor of."""
    _make_git(world)
    kept = [
        entry.pattern
        for entry in GENERATED_WORKING_SET
        if not ignore_block.supersedes(entry.pattern, pattern)
    ]
    _write_ignore(world, "\n".join([*kept, pattern]) + "\n")


@given("a project with no git working tree and a .gitignore that declares nothing")
def _no_git_tree(world: dict[str, Any]) -> None:
    _write_ignore(world, "# nothing here\n")
    assert not (world["root"] / ".git").exists()


@given("the generator emits one pattern the file does not declare")
def _generator_grows(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """A later release adding a pattern, which is how the class reaches an adopter."""
    added = IgnoreEntry(
        pattern=".beadloom/example-record*.jsonl",
        why="A pattern a later release added, which no adopter's file can already carry.",
    )
    monkeypatch.setattr(ignore_block, "GENERATED_WORKING_SET", (*GENERATED_WORKING_SET, added))
    world["added"] = added


@given("the .gitignore of the project this flow ships from")
def _this_repositorys_ignore_file(world: dict[str, Any]) -> None:
    path = _SHIPPED_FROM / ".gitignore"
    # Asserted rather than skipped: a room without the file is a checkout this
    # scenario cannot be taken in, and the claim is the same in every room.
    assert path.is_file(), f"no .gitignore beside the package under test at {_SHIPPED_FROM}"
    world["text"] = path.read_text(encoding="utf-8")


@when("the ignore block is checked")
def _check(world: dict[str, Any]) -> None:
    world["findings"] = ignore_block_findings(world["root"])


@when("its declared patterns are checked against the generator")
def _check_text(world: dict[str, Any]) -> None:
    world["findings"] = undeclared_patterns(world["text"])


@when("the agent-config check runs")
def _config_check(world: dict[str, Any]) -> None:
    world["outcome"] = CliRunner().invoke(main, ["config-check", "--project", str(world["root"])])


def _drifts(world: dict[str, Any]) -> list[Any]:
    """The ignore-block findings the agent-config check reported, by file."""
    from beadloom.infrastructure.db import connection
    from beadloom.onboarding import check_config_drift

    with connection(world["root"] / ".beadloom" / "beadloom.db") as conn:
        drifts = check_config_drift(world["root"], conn)
    return [d for d in drifts if d.file == str(ignore_block.IGNORE_RELPATH)]


@then(parsers.parse('that pattern is reported against "{relpath}"'))
def _reported_against(world: dict[str, Any], relpath: str) -> None:
    pattern = world["added"].pattern
    assert pattern in world["outcome"].output, world["outcome"].output
    assert [d for d in _drifts(world) if pattern in d.reason]
    assert str(ignore_block.IGNORE_RELPATH) == relpath


@then(parsers.parse('the finding for "{pattern}" names "{stale}" as the line it supersedes'))
def _names_superseded(world: dict[str, Any], pattern: str, stale: str) -> None:
    matches = [f for f in world["findings"] if f.pattern == pattern]
    assert len(matches) == 1, [f.pattern for f in world["findings"]]
    assert matches[0].supersedes == (stale,)
    world["finding"] = matches[0]


@then("its remediation says to replace that line rather than to add one")
def _remediation_replaces(world: dict[str, Any]) -> None:
    remediation = world["finding"].remediation
    assert "replace" in remediation
    assert world["finding"].supersedes[0] in remediation


@then("no ignore-block finding is reported")
def _no_findings(world: dict[str, Any]) -> None:
    assert world["findings"] == [], [f.pattern for f in world["findings"]]


@then("one finding is reported for each pattern the generator emits")
def _one_per_pattern(world: dict[str, Any]) -> None:
    assert [f.pattern for f in world["findings"]] == [
        entry.pattern for entry in GENERATED_WORKING_SET
    ]


@then(parsers.parse('every ignore-block finding carries severity "{severity}"'))
def _severity(world: dict[str, Any], severity: str) -> None:
    drifts = _drifts(world)
    assert drifts, "no ignore-block drift was reported at all"
    assert {d.severity for d in drifts} == {severity}


@then("no ignore-block finding offers --fix as its remedy")
def _not_fixable(world: dict[str, Any]) -> None:
    drifts = _drifts(world)
    assert drifts, "no ignore-block drift was reported at all"
    assert not any(d.fixable for d in drifts)
    assert not any("--fix" in (d.remediation or "") for d in drifts)
