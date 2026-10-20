"""``config-check`` and ``ci`` in a ``git worktree`` of the composed monorepo fixture (#334).

The first outside adopter's ``beadloom ci`` was red in a worktree of a clean HEAD and green
in the main checkout of the same files, because the composed ``.claude/CLAUDE.md`` carried
the checkout's directory name in its heading and the comparison recomposed it from the
directory it ran in. Measured on the monorepo fixture, which names itself in no root
manifest: on 9.0.0 ``config-check`` and ``ci`` exit 0 in the checkout and 1 in a worktree;
this release exits 0 in both.

The fixture is composed with ``setup-agentic-flow`` and judged by the two command lines, so
the file collects against 9.0.0 and fails there on the exit code it asserts. The clean-room
half of the same move is held by ``test_the_verdict_names_what_it_compared.py`` beside this
file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.committed_project import git
from tests.support.shipped_monorepo import shipped_monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


def _places(tmp_path: Path) -> dict[str, Path]:
    """The fixture composed and committed in its checkout, and a worktree of that HEAD."""
    checkout = shipped_monorepo_checkout(tmp_path)
    composed = CliRunner().invoke(main, ["setup-agentic-flow", "--project", str(checkout)])
    assert composed.exit_code == 0, composed.output
    git(checkout, "add", "-A")
    git(checkout, *_IDENTITY, "commit", "-q", "-m", "the flow composed")
    worktree = tmp_path / "desk-worktree"
    git(checkout, "worktree", "add", "-q", "--detach", str(worktree), "HEAD")
    return {"checkout": checkout, "worktree": worktree}


@pytest.mark.parametrize("place", ["checkout", "worktree"])
@pytest.mark.parametrize("command", ["config-check", "ci"])
def test_the_command_exits_0_in_the_checkout_and_in_a_worktree_of_it(
    tmp_path: Path, command: str, place: str
) -> None:
    root = _places(tmp_path)[place]

    result = CliRunner().invoke(main, [command, "--project", str(root)])

    assert result.exit_code == 0, result.output
