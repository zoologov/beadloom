"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_rooms_command.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from click.testing import CliRunner

from beadloom.services.cli import main


class TestTheCommandOverThisRepository:
    def test_it_lists_the_interpreters_this_project_supports(self) -> None:
        from pathlib import Path as _Path

        root = _Path(__file__).resolve().parents[3]
        outcome = CliRunner().invoke(
            main, ["rooms", "--project", str(root), "--dimension", "python"]
        )
        assert outcome.exit_code == 0
        assert outcome.stdout.split() == ["3.10", "3.11", "3.12", "3.13"]
