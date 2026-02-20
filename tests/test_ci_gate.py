"""Tests for --fail-if CI gate on docs audit command."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click
import pytest

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _project_with_stale(tmp_path: Path) -> Path:
    """Create a project with stale version mention for CLI testing."""
    proj = tmp_path / "proj"
    proj.mkdir()
    beadloom_dir = proj / ".beadloom"
    beadloom_dir.mkdir()
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "3.0.0"\n',
        encoding="utf-8",
    )
    (proj / "README.md").write_text(
        "# Demo\n\nDemo v2.0.0 is the current release.\n",
        encoding="utf-8",
    )

    from beadloom.infrastructure.db import create_schema, open_db

    db_path = beadloom_dir / "beadloom.db"
    conn = open_db(db_path)
    create_schema(conn)
    conn.close()

    return proj


@pytest.fixture()
def _project_no_stale(tmp_path: Path) -> Path:
    """Create a project with no stale mentions."""
    proj = tmp_path / "proj"
    proj.mkdir()
    beadloom_dir = proj / ".beadloom"
    beadloom_dir.mkdir()
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "3.0.0"\n',
        encoding="utf-8",
    )
    (proj / "README.md").write_text(
        "# Demo\n\nDemo v3.0.0 is the current release.\n",
        encoding="utf-8",
    )

    from beadloom.infrastructure.db import create_schema, open_db

    db_path = beadloom_dir / "beadloom.db"
    conn = open_db(db_path)
    create_schema(conn)
    conn.close()

    return proj


# ---------------------------------------------------------------------------
# parse_fail_condition unit tests
# ---------------------------------------------------------------------------


class TestParseFailCondition:
    """Tests for parse_fail_condition() expression parser."""

    def test_parse_fail_condition_stale_gt_zero(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        metric, op, threshold = parse_fail_condition("stale>0")
        assert metric == "stale"
        assert op == ">"
        assert threshold == 0

    def test_parse_fail_condition_stale_gt_five(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        metric, op, threshold = parse_fail_condition("stale>5")
        assert metric == "stale"
        assert op == ">"
        assert threshold == 5

    def test_parse_fail_condition_stale_gte(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        metric, op, threshold = parse_fail_condition("stale>=1")
        assert metric == "stale"
        assert op == ">="
        assert threshold == 1

    def test_parse_fail_condition_with_spaces(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        metric, op, threshold = parse_fail_condition("  stale > 0  ")
        assert metric == "stale"
        assert op == ">"
        assert threshold == 0

    def test_parse_fail_condition_invalid(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        with pytest.raises(click.BadParameter, match="Invalid --fail-if expression"):
            parse_fail_condition("xyz")

    def test_parse_fail_condition_unsupported_metric(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        with pytest.raises(click.BadParameter, match="Unsupported metric"):
            parse_fail_condition("fresh>0")

    def test_parse_fail_condition_negative_threshold(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        with pytest.raises(click.BadParameter, match="Invalid --fail-if expression"):
            parse_fail_condition("stale>-1")

    def test_parse_fail_condition_non_numeric_threshold(self) -> None:
        from beadloom.doc_sync.audit import parse_fail_condition

        with pytest.raises(click.BadParameter, match="Invalid --fail-if expression"):
            parse_fail_condition("stale>abc")


# ---------------------------------------------------------------------------
# CLI --fail-if integration tests
# ---------------------------------------------------------------------------


class TestCliFailIf:
    """Tests for ``beadloom docs audit --fail-if`` CLI integration."""

    def test_cli_fail_if_triggers(self, _project_with_stale: Path) -> None:
        """Exit code 1 when stale count exceeds threshold."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "audit", "--fail-if", "stale>0", "--project", str(_project_with_stale)],
        )
        msg = f"exit {result.exit_code}: {result.output}"
        assert result.exit_code == 1, msg

    def test_cli_fail_if_passes(self, _project_no_stale: Path) -> None:
        """Exit code 0 when no stale items."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "audit", "--fail-if", "stale>0", "--project", str(_project_no_stale)],
        )
        msg = f"exit {result.exit_code}: {result.output}"
        assert result.exit_code == 0, msg

    def test_cli_fail_if_threshold(self, _project_with_stale: Path) -> None:
        """Under threshold: stale=1 but threshold is stale>5 -> exit 0."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "audit", "--fail-if", "stale>5", "--project", str(_project_with_stale)],
        )
        msg = f"exit {result.exit_code}: {result.output}"
        assert result.exit_code == 0, msg

    def test_cli_fail_if_gte_triggers(self, _project_with_stale: Path) -> None:
        """stale>=1 should trigger with 1 stale item."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "audit", "--fail-if", "stale>=1", "--project", str(_project_with_stale)],
        )
        msg = f"exit {result.exit_code}: {result.output}"
        assert result.exit_code == 1, msg

    def test_cli_fail_if_message(self, _project_with_stale: Path) -> None:
        """Verify CI gate message appears in output."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "audit", "--fail-if", "stale>0", "--project", str(_project_with_stale)],
        )
        assert "CI gate triggered" in result.output
        assert "stale" in result.output.lower()

    def test_cli_fail_if_invalid_expression(self, _project_no_stale: Path) -> None:
        """Invalid expression should produce error."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "audit", "--fail-if", "xyz", "--project", str(_project_no_stale)],
        )
        assert result.exit_code != 0

    def test_cli_fail_if_with_json(self, _project_with_stale: Path) -> None:
        """--fail-if works with --json output."""
        import json as json_mod

        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "docs", "audit", "--json",
                "--fail-if", "stale>0",
                "--project", str(_project_with_stale),
            ],
        )
        assert result.exit_code == 1
        # Output may contain CI gate message after JSON; extract JSON block
        output = result.output.strip()
        # Find the JSON object boundaries
        json_start = output.index("{")
        brace_depth = 0
        json_end = json_start
        for i in range(json_start, len(output)):
            if output[i] == "{":
                brace_depth += 1
            elif output[i] == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    json_end = i + 1
                    break
        data = json_mod.loads(output[json_start:json_end])
        assert "ci_gate" in data
        assert data["ci_gate"]["triggered"] is True

    def test_cli_no_fail_if_no_exit(self, _project_with_stale: Path) -> None:
        """Without --fail-if, stale items don't cause non-zero exit."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "audit", "--project", str(_project_with_stale)],
        )
        msg = f"exit {result.exit_code}: {result.output}"
        assert result.exit_code == 0, msg
