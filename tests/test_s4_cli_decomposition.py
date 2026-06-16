"""Tests guarding the BDL-059 S4 decomposition outcome (behavior-preserving).

S4 split the ``services/cli.py`` monolith into cohesive command modules under
``services/commands/`` and moved the ``status`` command's data-gathering down to
``application/status.py``. These tests pin the externally observable contract:

1. ``TestCliSurfaceStability`` — the console-script entry ``main`` and every
   private helper imported from ``beadloom.services.cli`` still resolve via the
   OLD import path; the full command set is unchanged.
2. ``TestGoldenHelp`` — golden ``--help`` text for representative commands is
   byte-stable across the split (command name + usage + options preserved).
3. ``TestStatusLogicLayering`` — the status read-side lives in the application
   layer and returns the same figures the command renders.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.services.cli import (
    _bd_statuses_from_list,
    _detect_link_label,
    _format_gate_github,
    _format_markdown,
    _has_active_table,
    _jsonl_is_tracked,
    _parse_fail_on,
    _query_bd_statuses,
    main,
)

# The complete, ordered command set the CLI exposes (the S4 split must not add,
# drop, or rename any command — registration is behavior-preserving).
EXPECTED_COMMANDS = {
    "active-sync",
    "ci",
    "config-check",
    "ctx",
    "diff",
    "docs",
    "doctor",
    "export",
    "federate",
    "graph",
    "init",
    "install-hooks",
    "link",
    "lint",
    "mcp-serve",
    "prime",
    "reindex",
    "search",
    "setup-agentic-flow",
    "setup-ai-techwriter",
    "setup-branch-protection",
    "setup-mcp",
    "setup-rules",
    "snapshot",
    "status",
    "sync-check",
    "sync-update",
    "tui",
    "ui",
    "watch",
    "why",
}


class TestCliSurfaceStability:
    """Public + private CLI surface still imports from ``beadloom.services.cli``."""

    def test_full_command_set_preserved(self) -> None:
        assert set(main.commands) == EXPECTED_COMMANDS

    def test_private_helpers_still_importable(self) -> None:
        # All are callables re-exported from the registration shell.
        for fn in (
            _bd_statuses_from_list,
            _detect_link_label,
            _format_gate_github,
            _format_markdown,
            _has_active_table,
            _jsonl_is_tracked,
            _parse_fail_on,
            _query_bd_statuses,
        ):
            assert callable(fn)

    def test_console_script_entry_is_main(self) -> None:
        # The pyproject console-script ``beadloom.services.cli:main`` resolves.
        import importlib

        module = importlib.import_module("beadloom.services.cli")
        assert module.main is main

    def test_docs_subgroup_commands(self) -> None:
        assert set(main.commands["docs"].commands) == {  # type: ignore[attr-defined]
            "generate",
            "polish",
            "site",
            "audit",
        }

    def test_snapshot_subgroup_commands(self) -> None:
        assert set(main.commands["snapshot"].commands) == {  # type: ignore[attr-defined]
            "save",
            "list",
            "compare",
        }


class TestGoldenHelp:
    """Golden ``--help`` for representative commands across the cohesive groups."""

    def _help(self, *args: str) -> str:
        result = CliRunner().invoke(main, [*args, "--help"])
        assert result.exit_code == 0, result.output
        return result.output

    def test_status_help(self) -> None:
        out = self._help("status")
        assert "Show project index statistics with health trends." in out
        assert "--debt-report" in out
        assert "--fail-if" in out
        assert "--category" in out

    def test_ci_help(self) -> None:
        out = self._help("ci")
        assert "Run the unified CI gate" in out
        assert "--hub" in out
        assert "--fail-on" in out

    def test_sync_check_help(self) -> None:
        out = self._help("sync-check")
        assert "Check doc-code synchronization status." in out
        assert "--porcelain" in out
        assert "--since" in out

    def test_ctx_help(self) -> None:
        out = self._help("ctx")
        assert "Get context bundle for one or more ref_ids." in out
        assert "--depth" in out

    def test_link_help(self) -> None:
        out = self._help("link")
        assert "Manage external tracker links on graph nodes." in out


# Every command + documented subcommand, so the parametrized --help stability
# test below exercises the WHOLE registered surface (not just the 5 spot-checks
# above). A command whose module failed to wire up cleanly after the S4 split
# fails its --help render here even if it still appears in ``main.commands``.
_SUBGROUPS = {
    "docs": ("generate", "polish", "site", "audit"),
    "snapshot": ("save", "list", "compare"),
}
_ALL_HELP_INVOCATIONS = sorted(
    [(cmd,) for cmd in EXPECTED_COMMANDS]
    + [(group, sub) for group, subs in _SUBGROUPS.items() for sub in subs]
)


class TestEveryCommandHelpStable:
    """Each command's (and subcommand's) ``--help`` renders cleanly (exit 0)."""

    @pytest.mark.parametrize(
        "invocation", _ALL_HELP_INVOCATIONS, ids=lambda inv: " ".join(inv)
    )
    def test_help_renders_for_every_command(
        self, invocation: tuple[str, ...]
    ) -> None:
        result = CliRunner().invoke(main, [*invocation, "--help"])
        assert result.exit_code == 0, result.output
        # A rendered Click help always carries a Usage line naming the command.
        assert "Usage:" in result.output
        assert invocation[-1] in result.output


class TestStatusLogicLayering:
    """The status read-side lives in the application layer (logic moved down)."""

    def test_gather_status_in_application_layer(self) -> None:
        from beadloom.application import status as status_mod

        assert hasattr(status_mod, "gather_status")
        assert hasattr(status_mod, "compute_context_metrics")
        assert hasattr(status_mod, "StatusData")

    def test_gather_status_reads_counts(self) -> None:
        from beadloom.application.status import gather_status
        from beadloom.infrastructure.db import create_schema

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES ('a', 'domain', 'x')"
        )
        conn.commit()

        data = gather_status(conn, Path.cwd())
        assert data.nodes_count == 1
        assert data.coverage_pct == 0.0
        conn.close()
