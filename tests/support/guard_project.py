"""A guarded project, a tracker that claims nothing, and the CLI over both.

The project's flow blocks on an unclaimed bead, so a guard that runs and finds
nothing claimed has something to refuse.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

BLOCKING_FLOW = "guards:\n  bead-claimed:\n    strictness: { default: block }\n"


class NoBeads:
    """A tracker that answers, and answers "nothing is claimed"."""

    @staticmethod
    def claimed_beads() -> tuple[()]:
        return ()


def guarded_project(tmp_path: Path, flow: str = BLOCKING_FLOW) -> Path:
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".beadloom" / "flow.yml").write_text(flow, encoding="utf-8")
    return tmp_path


def invoke_cli(args: list[str], *, stdin: str = ""):
    return CliRunner().invoke(main, args, input=stdin)
