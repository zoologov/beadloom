"""``beadloom config-check`` and the Gate refuse a ``site:`` block the portal cannot use.

BDL-076 B1 (``beadloom-dfwt``). The ``site:`` block of ``.beadloom/config.yml``
names the portal's title, description, base path and repository link. A key the
block does not read is a typo whose cost shows up only on the deployed portal —
``bsae: /orders/`` deploys under ``/`` — so the check that owns configuration
names it before ``docs site`` ever runs, and blocks: no project declared a
``site:`` block before this release, so no green project turns red on upgrade.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.gate import _step_config_check
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _project(tmp_path: Path, site_block: str) -> Path:
    root = tmp_path / "acme-orders"
    (root / ".beadloom").mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n- src\n" + site_block, encoding="utf-8"
    )
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return root


def test_config_check_names_the_unknown_key_and_blocks(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  title: Acme Orders\n  bsae: /orders/\n")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 1, result.output
    assert "site.bsae" in result.output
    assert "`base:`" in result.output


def test_config_check_passes_a_block_it_can_use(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "site:\n  title: Acme Orders\n  base: /orders/\n"
        "  repo_url: https://gitlab.com/acme/orders\n  powered_by: false\n  repo_icon: gitlab\n",
    )
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "site." not in result.output


def test_config_check_names_a_portal_without_a_repository_link(tmp_path: Path) -> None:
    """BDL-080 S4d: no `repo_url`, no header link, and config-check says so without blocking."""
    root = _project(tmp_path, "site:\n  title: Acme Orders\n  repo_icon: gitlab\n")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "site.repo_url" in result.output
    assert "no repository link" in result.output
    assert "nothing draws it" in result.output


def test_config_check_names_nothing_for_a_project_without_a_site_block(tmp_path: Path) -> None:
    root = _project(tmp_path, "")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "site.repo_url" not in result.output


def test_the_gate_blocks_on_the_same_refusal(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  base: orders\n")
    step = _step_config_check(root)
    assert step.passed is False
    assert any("site.base" in str(finding.get("why")) for finding in step.findings)


def test_the_gate_is_green_without_a_site_block(tmp_path: Path) -> None:
    root = _project(tmp_path, "")
    step = _step_config_check(root)
    assert not any("site" in str(finding.get("why")) for finding in step.findings)


# BDL-076 B4 (`beadloom-ujzb.8`): `site.forges` names the forge of a self-hosted
# host. A kind the generator does not know would leave the portal without the
# links the project asked for, so it is refused by host, by all three readers.


def test_config_check_names_an_unknown_forge_kind_by_its_host(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  forges:\n    git.acme.example: gitlab-ce\n")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 1, result.output
    assert "site.forges[git.acme.example]" in result.output
    assert "`gitlab`" in result.output


def test_the_gate_blocks_on_a_malformed_forge_template(tmp_path: Path) -> None:
    root = _project(
        tmp_path, "site:\n  forges:\n    code.acme.example:\n      source: '{url}/{branch}'\n"
    )
    step = _step_config_check(root)
    assert step.passed is False
    assert any(
        "site.forges[code.acme.example]" in str(finding.get("why")) for finding in step.findings
    )


def test_config_check_passes_a_declared_forge(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  forges:\n    git.acme.example: gitlab\n")
    result = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert result.exit_code == 0, result.output
