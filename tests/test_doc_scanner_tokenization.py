"""Tokenization boundary tests for the doc-fact scanner (BDL-061.44 / BDL-UX #169).

A number that is *part of a larger token* — a bead reference (``BDL-061.33``), a
version (``v2.2.0``), a language version (``Python 3.10``), an issue reference
(``PR #33``) — is an identifier, not a claim about the project.  The scanner must
tokenize before matching rather than scan for digits near a keyword.

Both directions are asserted for every rule: the identifier must NOT be read as
the fact, AND a genuine drift on the same line must still be caught.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.audit import Fact, compare_facts
from beadloom.doc_sync.scanner import DocScanner

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def scanner() -> DocScanner:
    return DocScanner()


def _scan_line(scanner: DocScanner, tmp_path: Path, line: str) -> list[tuple[str, object]]:
    """Scan a single prose line and return ``(fact_name, value)`` pairs."""
    doc = tmp_path / "guide.md"
    doc.write_text(f"# Guide\n\n{line}\n", encoding="utf-8")
    return [(m.fact_name, m.value) for m in scanner.scan_file(doc)]


# ===========================================================================
# A number inside a larger token is not a fact
# ===========================================================================


class TestNumberInsideIdentifier:
    def test_bead_reference_tail_is_not_a_tool_count(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """``(BDL-061.33)`` must not be read as ``mcp_tool_count = 33``."""
        line = (
            "Reached through `--hook`, the same class exits `2` (BDL-061.33), "
            "which the MCP tool adapter relies on."
        )
        assert _scan_line(scanner, tmp_path, line) == []

    def test_genuine_drift_on_a_line_that_also_carries_a_bead_reference(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """The identifier is ignored; a real claim on the same line is still read."""
        line = "Since BDL-061.33 the MCP server ships 33 tools."
        assert _scan_line(scanner, tmp_path, line) == [("mcp_tool_count", 33)]

    def test_dotted_version_is_not_a_language_count(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """``Python 3.10`` names a language version, not a count of languages."""
        line = "Beadloom targets Python 3.10 and newer for every supported language."
        assert _scan_line(scanner, tmp_path, line) == []

    def test_semantic_version_yields_only_a_version_mention(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        line = "Release v2.2.0 of the CLI is on PyPI."
        assert _scan_line(scanner, tmp_path, line) == [("version", "v2.2.0")]

    def test_issue_reference_is_not_a_count(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        line = "See PR #33 for the MCP tool rework."
        assert _scan_line(scanner, tmp_path, line) == []

    def test_slash_separated_ratio_is_not_a_count(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        line = "The MCP tool suite passes 33/40 of the contract checks."
        assert _scan_line(scanner, tmp_path, line) == []


# ===========================================================================
# Grouped numbers: the whole number is the claim, not its tail
# ===========================================================================


class TestThousandsSeparator:
    def test_grouped_number_is_read_whole(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """``1,067`` is one thousand and sixty-seven — never ``067``."""
        line = "The graph holds 1,067 nodes."
        assert _scan_line(scanner, tmp_path, line) == [("node_count", 1067)]

    def test_grouped_number_matching_truth_is_fresh(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        line = "The suite has 6,390 tests."
        doc = tmp_path / "guide.md"
        doc.write_text(f"# Guide\n\n{line}\n", encoding="utf-8")
        facts = {"test_count": Fact("test_count", 6390, "graph DB")}
        result = compare_facts(facts, scanner.scan_file(doc))
        assert [f.status for f in result.findings] == ["fresh"]

    def test_grouped_number_drift_is_not_reported_as_verified(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """A wrong grouped claim must be stale, never silently 'fresh'."""
        line = "The graph holds 1,067 nodes."
        doc = tmp_path / "guide.md"
        doc.write_text(f"# Guide\n\n{line}\n", encoding="utf-8")
        facts = {"node_count": Fact("node_count", 67, "graph DB")}
        result = compare_facts(facts, scanner.scan_file(doc))
        assert [f.status for f in result.findings] == ["stale"]


# ===========================================================================
# Plain claims keep working (the fix must not blind the audit)
# ===========================================================================


class TestPlainClaimsStillRead:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("Beadloom exposes 33 MCP tools.", ("mcp_tool_count", 33)),
            ("The MCP server ships **33** tools.", ("mcp_tool_count", 33)),
            ("| MCP tools | 33 |", ("mcp_tool_count", 33)),
            ("The CLI has 55 commands.", ("cli_command_count", 55)),
            ("55 CLI commands are available.", ("cli_command_count", 55)),
            ("The graph holds 316 edges in total.", ("edge_count", 316)),
            ('A doc claiming "39 commands" is checked too.', ("cli_command_count", 39)),
        ],
    )
    def test_plain_claim_is_extracted(
        self,
        scanner: DocScanner,
        tmp_path: Path,
        line: str,
        expected: tuple[str, int],
    ) -> None:
        assert expected in _scan_line(scanner, tmp_path, line)


# ===========================================================================
# Measured blind spots (BDL-061.44 sweep) -- RESOLVED by BDL-061.45
#
# A false POSITIVE announces itself by failing the Gate; a false NEGATIVE is
# silent.  Two silent ones were pinned here as strict xfails.  Both are now
# settled, in opposite ways, and both live in tests/test_docs_audit_coverage.py:
#
#   * A modifier word suppressing a count it does not modify ("316 edges, one
#     per import") was a real defect and is FIXED -- windows are scoped to the
#     number's own clause.
#   * Counts below ten are NOT extracted, and that stays: re-measuring the
#     alternative on this repo produced 14 extra mentions, 13 of them ordinals,
#     table cells and category breakdowns.  What changed is that the audit now
#     REPORTS the fact it therefore cannot check, instead of reading green
#     about it.
# ===========================================================================
