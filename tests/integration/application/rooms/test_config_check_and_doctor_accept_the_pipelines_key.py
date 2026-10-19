"""``config-check`` and ``doctor`` accept ``rooms.pipelines`` (BDL-083 S2F1, RFC D6).

``beadloom-ba9w.22``. The key is read by the room census and the gate's coverage report and by
nothing that judges configuration, so declaring it must leave both checks' verdicts exactly as
they were: the same exit code and no line naming the key, in the CLI and in the Gate's steps.
Measured on a project that declares the key against the same project without it, so a check
that started reading ``rooms:`` would show as a difference rather than hide in an output that
happens to be green.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.gate import _step_config_check, _step_doctor
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

_KEY = "rooms:\n  pipelines: [github]\n"


def _project(root: Path, block: str) -> Path:
    (root / ".beadloom").mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n- src\n" + block, encoding="utf-8"
    )
    (root / ".gitlab-ci.yml").write_text(
        "t:\n  image: python:3.12\n  script: [pytest]\n", encoding="utf-8"
    )
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    commit_project(root)
    return root


@pytest.mark.parametrize("command", ["config-check", "doctor"])
def test_the_cli_verdict_is_the_one_given_without_the_key(tmp_path: Path, command: str) -> None:
    without = _project(tmp_path / "without", "")
    declared = _project(tmp_path / "declared", _KEY)

    plain = CliRunner().invoke(main, [command, "--project", str(without)])
    keyed = CliRunner().invoke(main, [command, "--project", str(declared)])

    assert keyed.exit_code == plain.exit_code, keyed.output
    assert "rooms" not in keyed.output.lower(), keyed.output
    assert "pipelines" not in keyed.output, keyed.output


def test_the_gate_steps_pass_as_they_do_without_the_key(tmp_path: Path) -> None:
    without = _project(tmp_path / "without", "")
    declared = _project(tmp_path / "declared", _KEY)

    for step in (_step_config_check, _step_doctor):
        plain, keyed = step(without), step(declared)
        assert keyed.passed == plain.passed, keyed.findings
        assert not [f for f in keyed.findings if "pipelines" in str(f)], keyed.findings
