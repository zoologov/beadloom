"""``beadloom config-check`` and the Gate refuse an ``imports:`` block they cannot use.

BDL-080 S3a (``beadloom-cwzc``). ``imports: {aliases: {...}}`` names the aliases a
project's bundler applies, which the import resolver reads. A folder that is not in the
project, or a key the block does not read, would leave every import under the alias
unresolved without a word, so the check that owns configuration names it and blocks, as
it does for ``site:`` and ``activity:``: no project declared an ``imports:`` block before
this release, so no green project turns red on upgrade.
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
    root = tmp_path / "harbourline"
    (root / ".beadloom").mkdir(parents=True)
    (root / "src" / "shared").mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n- src\n" + block, encoding="utf-8"
    )
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return root


def test_config_check_names_the_unusable_alias_and_blocks(tmp_path: Path) -> None:
    root = _project(tmp_path, "imports:\n  aliases:\n    '@shared': src/shraed\n")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 1, result.output
    assert "The `imports:` block" in result.output
    assert "imports.aliases.@shared" in result.output
    assert "src/shraed" in result.output


def test_config_check_passes_a_block_it_can_use(tmp_path: Path) -> None:
    root = _project(tmp_path, "imports:\n  aliases:\n    '@shared': src/shared\n")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "imports." not in result.output


def test_the_gate_blocks_on_the_same_refusal(tmp_path: Path) -> None:
    root = _project(tmp_path, "imports:\n  alias:\n    '@shared': src/shared\n")
    step = _step_config_check(root)
    assert step.passed is False
    assert any("imports.alias" in str(finding.get("why")) for finding in step.findings)
    assert "`imports:`" in step.summary


def test_the_gate_is_green_without_an_imports_block(tmp_path: Path) -> None:
    root = _project(tmp_path, "")
    step = _step_config_check(root)
    assert not any("imports" in str(finding.get("why")) for finding in step.findings)
