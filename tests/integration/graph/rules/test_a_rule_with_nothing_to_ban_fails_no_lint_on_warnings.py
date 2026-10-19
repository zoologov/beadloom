"""`lint --fail-on-warn` passes a project whose banned module nothing imports.

One of the finding-set moves the RFC of BDL-083 names under its Public API (D2, BDL-UX
#328). On 9.0.0 a `forbid_import` rule whose `to:` glob matched none of the imports the
index held was a `rule_liveness` warning, "cannot fire", and `--fail-on-warn` exited 1 on
it. Measured on 2026-10-18 on the monorepo fixture, whose digest domain bans every import
of `os/**` and imports none: 9.0.0 (`0f1cb9a3`) exited 1 with "Rule
'domain-no-io-imports-digest-os' cannot fire"; the branch exited 0 with the rule stated
live at info. The other warnings of that run are the layer rules' population statements,
which are advisory and exit 0 under `--fail-on-warn` on both versions.

This file holds the move end to end, through the command a pipeline runs: the unit tests
beside it hold the result object, and the scenario holds `--strict`, whose exit code did
not move. The test is written against the command only, so it runs on 9.0.0 too, and is
red there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.monorepo_fixture import monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

#: The fixture's rule, as the adopter wrote it.
_RULE = "domain-no-io-imports-digest-os"


def _lint_failing_on_warnings(root: Path) -> tuple[int, str]:
    result = CliRunner().invoke(
        main, ["lint", "--project", str(root), "--strict", "--fail-on-warn", "--format", "rich"]
    )
    return result.exit_code, result.output


def test_a_banned_module_nothing_imports_exits_zero_under_fail_on_warn(tmp_path: Path) -> None:
    root = monorepo_checkout(tmp_path)

    exit_code, output = _lint_failing_on_warnings(root)

    assert exit_code == 0, output


def test_the_rule_with_nothing_to_ban_is_not_said_to_be_unable_to_fire(tmp_path: Path) -> None:
    root = monorepo_checkout(tmp_path)

    _, output = _lint_failing_on_warnings(root)

    assert f"Rule '{_RULE}' cannot fire" not in output, output
