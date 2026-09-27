"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_cli_json_streams.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestTheWarningNeverReachesTheMachineStream:
    """The JSON document and the human warning travel on different streams."""

    def test_this_repository_lints_to_a_parsable_document_on_stdout(
        self, self_check_snapshot: Path
    ) -> None:
        """The live-repo self-lint, which is where the fragility was measured."""
        result = CliRunner().invoke(
            main,
            ["lint", "--format", "json", "--project", str(self_check_snapshot), "--no-reindex"],
        )

        payload = json.loads(result.stdout)

        assert "violations" in payload
        assert "summary" in payload
