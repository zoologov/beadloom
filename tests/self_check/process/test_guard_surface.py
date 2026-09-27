"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_guard_surface.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from beadloom.application.guards.surface import (
    build_surface,
)
from beadloom.services.cli import main

_REPO_ROOT = Path(__file__).resolve().parents[3]


class TestThisRepositoryRunsWhatItShips:
    """The live dogfood assertion — the same class as the live-matcher check."""

    def test_the_binding_sees_every_write_path_this_repository_grants(self) -> None:
        surface = build_surface(_REPO_ROOT)
        assert surface.unresolved == (), surface.to_dict()
        assert surface.unseen == (), surface.to_dict()
        assert surface.unclassified == (), surface.to_dict()
        assert surface.covered == (3, 3), surface.to_dict()

    def test_the_report_names_the_surface_before_the_guard_rows(self) -> None:
        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--project", str(_REPO_ROOT)]
        )
        assert result.exit_code == 0, result.output
        first = result.output.splitlines()[0]
        assert first.startswith("surface (claude): 3 of 3 write path(s) bound"), first

    def test_the_json_report_answers_both_questions(self) -> None:
        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--json", "--project", str(_REPO_ROOT)]
        )
        payload = json.loads(result.stdout)
        assert payload["surface"]["covered"] == [3, 3]
        assert payload["guards"]
