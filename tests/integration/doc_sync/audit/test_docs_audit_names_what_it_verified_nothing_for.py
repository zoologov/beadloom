"""``docs audit`` names the declared facts its green line verified nothing for.

* ``docs audit`` declares 9 facts and its green line ``13 mention(s) fresh``
  covers exactly one of them (``mcp_tool_count``); the other 8 verified nothing
  and the payload has no channel that says so.

Tests that assert a gap carry ``xfail(strict=True)``: the gap is recorded as an
executable statement, and the day it is fixed the marker fails the suite rather
than letting the finding be quietly forgotten. Each class also carries at least
one PASSING test using the same fixture, so an xfail can never be an artefact of
a broken helper (TESTS MUST BITE).

Split out of ``tests/test_s2_false_green_residue.py`` by node (BDL-074 E1). Every gap
below was measured on a clean-room copy of this repository at 004487a before it
was written down.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.doc_sync.audit import run_audit
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.two_component_project import ALPHA_DOC, indexed_project


def _audit(project: Path) -> tuple[set[str], set[str]]:
    """Return ``(declared facts, facts with at least one verified mention)``."""
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        result = run_audit(project, conn)
    finally:
        conn.close()
    return set(result.facts), {f.mention.fact_name for f in result.findings}


def _declare_own_mcp_tool_count(project: Path, value: int = 18) -> None:
    """Give the fixture project its OWN MCP tool count.

    Until BDL-062 `.3` the audit handed every project the running Beadloom's
    catalog length, so this fixture got a large, scanner-readable fact for free
    — a fact about Beadloom, in an adopter's report. The count is now declared
    the way an adopter with their own MCP server declares it, which is the same
    escape hatch the audit's decline reason names.
    """
    config = project / ".beadloom" / "config.yml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + "docs_audit:\n"
        + "  extra_facts:\n"
        + "    mcp_tool_count:\n"
        + f"      value: {value}\n"
        + '      source: "the fixture project\'s own MCP server"\n',
        encoding="utf-8",
    )


def _state_a_fact(project: Path, fact_name: str, sentence: str) -> None:
    """Write a doc that states *fact_name* truthfully, at its current value.

    Counts below ten are ignored by the scanner (``scanner.py``: a ``*_count``
    mention under 10 is too noisy to trust), so the sentence must name a fact
    whose value clears that floor — hence ``mcp_tool_count`` rather than this
    two-node fixture's own ``node_count``.
    """
    declared, _ = _audit(project)
    del declared
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        value = run_audit(project, conn).facts[fact_name].value
    finally:
        conn.close()
    (project / "docs" / "components" / "alpha.md").write_text(
        ALPHA_DOC + "\n" + sentence.format(value) + "\n", encoding="utf-8"
    )


class TestDocsAuditNamesWhatItVerifiedNothingFor:
    """``13 mention(s) fresh`` was 13 restatements of one of nine declared facts."""

    def test_a_fact_the_docs_do_state_is_verified(self, tmp_path: Path) -> None:
        """The audit does check something — this class's non-vacuity guard."""
        # Arrange — state one declared fact truthfully, reading its value from the
        # audit itself so the test does not hard-code a number that will move
        project = indexed_project(tmp_path)
        _declare_own_mcp_tool_count(project)
        _state_a_fact(project, "mcp_tool_count", "This project exposes {} MCP tools.")

        # Act
        declared, verified = _audit(project)

        # Assert
        assert declared, "the audit must declare some facts at all"
        assert verified == {"mcp_tool_count"}, (
            f"a stated fact must be verified — declared {sorted(declared)}"
        )

    def test_the_audit_names_the_facts_it_verified_nothing_for(self, tmp_path: Path) -> None:
        # Arrange
        project = indexed_project(tmp_path)
        _declare_own_mcp_tool_count(project)
        _state_a_fact(project, "mcp_tool_count", "This project exposes {} MCP tools.")
        declared, verified = _audit(project)
        unverified = declared - verified
        assert unverified, "the fixture must leave some fact unmentioned"

        # Act
        runner = CliRunner()
        invocation = runner.invoke(main, ["docs", "audit", "--json", "--project", str(project)])
        payload = json.loads(invocation.stdout)

        # Assert
        assert payload["summary"].get("unverified_count") == len(unverified), (
            "a fact nobody states was not verified; the summary that says 'N fresh' must "
            f"also say how many of its {len(declared)} facts checked nothing — "
            f"unverified today: {sorted(unverified)}"
        )
