"""``doctor`` names a git root above the project root as an error (BDL-083 S2e, #325).

``beadloom-7pd6``. The check is one of :func:`run_checks`'s rows, so the CLI and the Gate's
``doctor`` step read the same answer; the CLI exits 1 when any row is an error, which is the
rule the Gate's step already applied. Real repositories, the real ``git``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.doctor import Severity, run_checks
from beadloom.application.gate import _step_doctor
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

#: The name of the check's row in the doctor report.
_CHECK = "git_root"


def _indexed_project(root: Path) -> Path:
    (root / ".beadloom").mkdir(parents=True)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return root


@pytest.fixture
def nested(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    project = _indexed_project(repository / "app")
    commit_project(repository)
    return project


@pytest.fixture
def at_root(tmp_path: Path) -> Path:
    project = _indexed_project(tmp_path / "repository")
    commit_project(project)
    return project


def _rows(project: Path) -> list[Severity]:
    conn = open_db(project / ".beadloom" / "beadloom.db")
    try:
        checks = run_checks(conn, project_root=project)
    finally:
        conn.close()
    return [c.severity for c in checks if c.name == _CHECK]


def test_a_nested_project_root_is_an_error_row(nested: Path) -> None:
    assert _rows(nested) == [Severity.ERROR]


def test_a_project_root_at_the_git_root_is_an_ok_row(at_root: Path) -> None:
    assert _rows(at_root) == [Severity.OK]


def test_a_project_root_in_no_repository_is_an_ok_row(tmp_path: Path) -> None:
    assert _rows(_indexed_project(tmp_path / "plain")) == [Severity.OK]


def test_the_cli_exits_1_and_prints_the_error_row(nested: Path) -> None:
    result = CliRunner().invoke(main, ["doctor", "--project", str(nested)])

    assert result.exit_code == 1, result.output
    line = next(row for row in result.output.splitlines() if "git root" in row)
    assert line.lstrip().startswith("[ERR]"), result.output
    assert str(nested.parent.resolve()) in result.output


def test_the_cli_exits_0_at_the_git_root(at_root: Path) -> None:
    result = CliRunner().invoke(main, ["doctor", "--project", str(at_root)])

    assert result.exit_code == 0, result.output
    assert "[ok] No git root above the project root." in result.output


def test_the_gate_doctor_step_fails_on_a_nested_project_root(nested: Path) -> None:
    step = _step_doctor(nested)

    assert not step.passed
    assert any("git root" in str(finding) for finding in step.findings), step.findings
