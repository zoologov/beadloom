"""``sync-check --since`` refuses below the git root instead of passing (BDL-083 S2e, #325).

``beadloom-7pd6``. Below the git root ``--since`` reads ``git show <ref>:<path>`` with a path
git holds at another place, both sides come back empty, and every pair read ``ok``: a green
verdict over an empty comparison. The refusal exits 1 and names the git root. ``sync-check``
without ``--since`` translates its paths through ``git rev-parse --show-prefix`` and is not
refused; that is measured here too, so the refusal stays where the ruling put it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.shipped_monorepo import shipped_monorepo_below_its_git_root

if TYPE_CHECKING:
    from pathlib import Path


def _nested_indexed(tmp_path: Path) -> Path:
    root = shipped_monorepo_below_its_git_root(tmp_path)
    result = CliRunner().invoke(main, ["reindex", "--project", str(root)])
    assert result.exit_code == 0, result.output
    return root


def test_since_refuses_with_the_git_root_named(tmp_path: Path) -> None:
    root = _nested_indexed(tmp_path)

    result = CliRunner().invoke(main, ["sync-check", "--since", "HEAD", "--project", str(root)])

    assert result.exit_code == 1, result.output
    output = " ".join(result.output.split())
    assert "the git root is above the project root" in output
    assert str(root.parent.resolve()) in output
    assert "--since" in output


def test_since_refuses_in_json_mode_too(tmp_path: Path) -> None:
    root = _nested_indexed(tmp_path)

    result = CliRunner().invoke(
        main, ["sync-check", "--since", "HEAD", "--json", "--project", str(root)]
    )

    assert result.exit_code == 1, result.output


def test_without_since_the_nested_project_is_still_checked(tmp_path: Path) -> None:
    root = _nested_indexed(tmp_path)

    result = CliRunner().invoke(main, ["sync-check", "--project", str(root)])

    assert result.exit_code == 0, result.output
    assert "git root" not in result.output
