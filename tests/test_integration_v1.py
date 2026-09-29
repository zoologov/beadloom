# beadloom:domain=linter
"""Integration tests for v1.0 release — self-lint, version, graph completeness."""

from __future__ import annotations

from click.testing import CliRunner

from beadloom import __version__
from beadloom.services.cli import main

# ---------------------------------------------------------------------------
# Project root detection
# ---------------------------------------------------------------------------


class TestVersion:
    """Verify the version is 7.0.0, and that the CLI reports the same one.

    The literal is deliberate and has to be edited every release: it is what
    turns an ACCIDENTAL version change into a red test rather than a silent
    ship. What it does not do is find the version's other homes — this project
    states it in nine places, and four of them fail nowhere a developer looks
    until a release is underway (BDL-UX #281).
    """

    def test_version_string(self) -> None:
        assert __version__ == "7.0.0"

    def test_cli_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "7.0.0" in result.output


