"""Step implementations for BDL-069 S3 — the report over the version surface.

Thin by design. Every step drives the real ``beadloom version-surface`` over a
real project on disk: a real manifest, a real document inside the audit's own
surface, and a real file the audit excludes. The defect being pinned is a report
that names a population without naming what judges it, and a double would report
whatever the double was told to.

The fixture declares ``7.3.1`` rather than this project's own version, for the
reason ``beadloom-w4cd`` measured: a fixture equal to the real literal put fifty
rows of its own data into the first run of the sweep it feeds.

The module is named ``test_*`` so default pytest collection picks the scenarios
up -- the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/version_surface.feature")

_VERSION = "7.3.1"

_MANIFEST = f"""\
[project]
name = "widget"
version = "{_VERSION}"

[tool.pytest.ini_options]
testpaths = ["tests"]
"""

#: Inside the documentation audit's own surface, so the audit is its checker.
_GUIDE = f"""\
# Widget

Some prose that states nothing.

The current release is {_VERSION}.
"""

#: The audit excludes a changelog by default, so nothing judges this line -- the
#: gap the release of 2026-09-10 met one place at a time.
_CHANGELOG = f"""\
# Changelog

## [{_VERSION}] - 2026-01-01
"""


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _line_of(root: Path, relative: str, needle: str) -> int:
    """The 1-based line of *needle*, read from the file rather than counted here."""
    lines = (root / relative).read_text(encoding="utf-8").splitlines()
    return next(number for number, line in enumerate(lines, 1) if needle in line)


@given("a project stating its version where an instrument reads and where none does")
def _project(state: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "widget"
    project.mkdir()
    _write(project, "pyproject.toml", _MANIFEST)
    _write(project, "docs/getting-started.md", _GUIDE)
    _write(project, "CHANGELOG.md", _CHANGELOG)
    state["project"] = project


@when("the version surface is reported")
def _report(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["version-surface", "--project", str(state["project"])])
    state["exit_code"] = result.exit_code
    state["output"] = result.output


def _section(output: str, heading: str) -> str:
    """The block under *heading*, so a row is asserted where it was printed."""
    blocks = output.split("\n\n")
    return next((block for block in blocks if heading in block), "")


@then("every place is named with the file and the line that states it")
def _every_place(state: dict[str, Any]) -> None:
    output: str = state["output"]
    project: Path = state["project"]
    assert state["exit_code"] == 0, output
    for relative, needle in (
        ("pyproject.toml", "version ="),
        ("docs/getting-started.md", "current release"),
        ("CHANGELOG.md", "## ["),
    ):
        line = _line_of(project, relative, needle)
        assert relative in output, output
        assert f"{line}" in output, f"{relative}:{line} missing\n{output}"


@then("the place an instrument holds names that instrument")
def _names_the_instrument(state: dict[str, Any]) -> None:
    checked = _section(state["output"], "Checked (")
    assert "docs/getting-started.md" in checked, state["output"]
    assert "docs-audit" in checked, state["output"]
    assert "pyproject.toml" in checked, state["output"]
    assert "packaging-manifest" in checked, state["output"]


@then("the place no instrument holds is reported as checked by nothing, with the reason")
def _names_the_gap(state: dict[str, Any]) -> None:
    gap = _section(state["output"], "Checked by nothing")
    assert "CHANGELOG.md" in gap, state["output"]
    assert "excluded" in gap, state["output"]
    assert "docs/getting-started.md" not in gap, state["output"]


@then("the report states the population it read and what it did not read")
def _states_population(state: dict[str, Any]) -> None:
    output: str = state["output"]
    population = _section(output, "Population")
    assert "file(s) read" in population, output
    assert "Not read" in population, output
    assert "Directories skipped" in population, output
