"""``beadloom config-check`` and the Gate refuse an ``activity:`` block they cannot use.

BDL-078 ``beadloom-btkd.1``. ``activity: {exclude: [...]}`` names the project's
generated files, which do not count as change. A key the block does not read is
a typo whose cost is invisible — every generated line counted as work — so the
check that owns configuration names it and blocks, as it does for ``site:``: no
project declared an ``activity:`` block before this release, so no green project
turns red on upgrade.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.gate import _step_config_check
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _project(tmp_path: Path, block: str) -> Path:
    root = tmp_path / "acme-orders"
    (root / ".beadloom").mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n- src\n" + block, encoding="utf-8"
    )
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return root


def test_config_check_names_the_unknown_key_and_blocks(tmp_path: Path) -> None:
    root = _project(tmp_path, "activity:\n  exlude:\n    - '*.pb.go'\n")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 1, result.output
    assert "activity.exlude" in result.output
    assert "`exclude:`" in result.output


def test_config_check_passes_a_block_it_can_use(tmp_path: Path) -> None:
    root = _project(tmp_path, "activity:\n  exclude:\n    - '*.pb.go'\n")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "activity." not in result.output


def test_the_gate_blocks_on_the_same_refusal(tmp_path: Path) -> None:
    root = _project(tmp_path, "activity:\n  exclude: '*.pb.go'\n")
    step = _step_config_check(root)
    assert step.passed is False
    assert any("activity.exclude" in str(finding.get("why")) for finding in step.findings)
    assert "`activity:`" in step.summary


def test_the_gate_is_green_without_an_activity_block(tmp_path: Path) -> None:
    root = _project(tmp_path, "")
    step = _step_config_check(root)
    assert not any("activity" in str(finding.get("why")) for finding in step.findings)
