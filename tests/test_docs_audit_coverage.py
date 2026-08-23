"""What the docs audit did NOT check (BDL-061.45 / BDL-UX #173).

``13 mention(s) fresh`` was measured on this repo to be thirteen restatements of
ONE of the NINE facts the same output declares.  A green ``docs-audit`` meant
"one fact of nine was checked" and read as a clean bill of health.  This file
pins the fix: the audit reports its own coverage — every declared fact, how many
mentions were judged for it, and the reason when none could be.

Three statuses, and the third is the one that keeps the report honest:

``verified``      at least one mention was compared against the fact.
``not_covered``   no document states the fact — nothing to check, said out loud.
``unreadable``    the extractor cannot read a claim of this value at all
                  (counts of 0/1 and single digits are deliberately unread), so
                  the fact is structurally unverifiable, not merely unmentioned.

Every class also asserts the opposite direction, so a status can never be an
artefact of a fixture that produced no mentions at all.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.doc_sync.audit import Fact, IgnoreRule, compare_facts
from beadloom.doc_sync.scanner import DocScanner, Mention
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mention(fact_name: str, value: str | int, tmp_path: Path) -> Mention:
    return Mention(
        fact_name=fact_name,
        value=value,
        file=tmp_path / "README.md",
        line=3,
        context=f"{fact_name} is {value}",
    )


def _project(tmp_path: Path, readme: str = "") -> Path:
    """A minimal indexed project: empty graph DB, one README.

    An empty database yields count facts of 0, which the extractor is
    deliberately unable to read — so the same fixture exercises ``unreadable``
    and (via the MCP/CLI surface facts, which are large) ``verified``.
    """
    from beadloom.infrastructure.db import create_schema, open_db

    proj = tmp_path / "proj"
    (proj / ".beadloom").mkdir(parents=True)
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "3.0.0"\n', encoding="utf-8"
    )
    (proj / "README.md").write_text(f"# Demo\n\n{readme}\n", encoding="utf-8")
    conn = open_db(proj / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return proj


def _audit_json(project: Path, *extra: str) -> tuple[int, dict[str, object]]:
    """Run ``docs audit --json`` and return ``(exit code, payload)``.

    Output is read as JSON and verdicts as exit codes — never as a line count,
    whose shape changes when the stream is piped (BDL-UX #148).
    """
    invocation = CliRunner().invoke(
        main, ["docs", "audit", "--json", "--project", str(project), *extra]
    )
    payload = json.loads(invocation.stdout)
    assert isinstance(payload, dict)
    return invocation.exit_code, payload


def _scan_line(scanner: DocScanner, tmp_path: Path, line: str) -> list[tuple[str, object]]:
    doc = tmp_path / "guide.md"
    doc.write_text(f"# Guide\n\n{line}\n", encoding="utf-8")
    return [(m.fact_name, m.value) for m in scanner.scan_file(doc)]


@pytest.fixture()
def scanner() -> DocScanner:
    return DocScanner()


# ===========================================================================
# Per-fact coverage
# ===========================================================================


class TestPerFactCoverage:
    """A fact nobody states was not checked, and must not read as checked."""

    def test_a_stated_fact_is_verified_and_counts_its_mentions(
        self, tmp_path: Path
    ) -> None:
        """Non-vacuity guard: coverage does report the fact that WAS checked."""
        facts = {"mcp_tool_count": Fact("mcp_tool_count", 18, "MCP tool catalog")}
        mentions = [
            _mention("mcp_tool_count", 18, tmp_path),
            _mention("mcp_tool_count", 18, tmp_path),
        ]

        coverage = compare_facts(facts, mentions).coverage["mcp_tool_count"]

        assert coverage.status == "verified"
        assert coverage.mentions == 2

    def test_a_fact_no_document_states_is_reported_not_covered(
        self, tmp_path: Path
    ) -> None:
        facts = {
            "mcp_tool_count": Fact("mcp_tool_count", 18, "MCP tool catalog"),
            "cli_command_count": Fact("cli_command_count", 39, "CLI"),
        }
        result = compare_facts(facts, [_mention("mcp_tool_count", 18, tmp_path)])

        assert result.coverage["cli_command_count"].status == "not_covered"
        assert result.coverage["cli_command_count"].mentions == 0
        assert result.unverified_facts == ["cli_command_count"], (
            "a fact with zero mentions must be NAMED, not merely absent from the "
            "fresh list — naming is what makes 'N fresh' readable as coverage"
        )

    def test_a_stale_mention_still_counts_as_coverage(self, tmp_path: Path) -> None:
        """Coverage is 'was it checked', not 'was it right' — the two must differ."""
        facts = {"cli_command_count": Fact("cli_command_count", 39, "CLI")}
        result = compare_facts(facts, [_mention("cli_command_count", 12, tmp_path)])

        assert [f.status for f in result.findings] == ["stale"]
        assert result.coverage["cli_command_count"].status == "verified"
        assert result.unverified_facts == []

    def test_a_fact_whose_value_cannot_be_read_is_unreadable_not_uncovered(
        self,
    ) -> None:
        """``language_count`` is 1 here: no true claim about it can ever be read.

        ``not_covered`` says the docs are silent; ``unreadable`` says the audit
        is blind.  Printing the same word for both is the defect.
        """
        facts = {"language_count": Fact("language_count", 1, "code symbols")}
        coverage = compare_facts(facts, []).coverage["language_count"]

        assert coverage.status == "unreadable"
        assert coverage.reason, "an unreadable fact must say WHY it cannot be read"

    def test_a_readable_fact_nobody_states_is_not_called_unreadable(self) -> None:
        """Bite guard for the status above — 39 is perfectly readable."""
        facts = {"cli_command_count": Fact("cli_command_count", 39, "CLI")}

        assert compare_facts(facts, []).coverage["cli_command_count"].status == (
            "not_covered"
        )

    def test_a_suppressed_mention_does_not_count_as_coverage(
        self, tmp_path: Path
    ) -> None:
        """An ``ignore`` entry silences a mention; silence is not verification."""
        facts = {"mcp_tool_count": Fact("mcp_tool_count", 18, "MCP tool catalog")}
        mentions = [_mention("mcp_tool_count", 14, tmp_path)]
        rules = [IgnoreRule(path="README.md", fact="mcp_tool_count", value="14")]

        result = compare_facts(facts, mentions, ignore=rules)

        assert result.findings == []
        assert result.coverage["mcp_tool_count"].status == "not_covered", (
            "a suppression that hides the only mention of a fact leaves the fact "
            "unchecked; counting it as covered would read as coverage it does not have"
        )


# ===========================================================================
# The CLI reports the coverage
# ===========================================================================


class TestDocsAuditCliReportsCoverage:
    def test_json_payload_carries_per_fact_coverage(self, tmp_path: Path) -> None:
        exit_code, payload = _audit_json(
            _project(tmp_path, "The MCP server exposes 18 tools.")
        )

        assert exit_code == 0
        coverage = payload["coverage"]
        assert isinstance(coverage, dict)
        assert coverage["mcp_tool_count"]["status"] == "verified"
        assert coverage["mcp_tool_count"]["mentions"] == 1
        assert coverage["cli_command_count"]["status"] == "not_covered"

    def test_json_summary_counts_the_facts_that_verified_nothing(
        self, tmp_path: Path
    ) -> None:
        _, payload = _audit_json(_project(tmp_path, "The MCP server exposes 18 tools."))

        summary = payload["summary"]
        assert isinstance(summary, dict)
        declared = summary["declared_fact_count"]
        verified = summary["verified_fact_count"]
        assert verified == 1, "only the MCP tool count is stated by this fixture"
        assert declared > verified, "the fixture must leave facts unstated"
        assert summary["unverified_count"] == declared - verified

    def test_rich_output_names_a_fact_it_verified_nothing_for(
        self, tmp_path: Path
    ) -> None:
        project = _project(tmp_path, "The MCP server exposes 18 tools.")
        invocation = CliRunner().invoke(
            main, ["docs", "audit", "--project", str(project)]
        )

        assert invocation.exit_code == 0
        assert "cli_command_count" in invocation.output, (
            "the human report must NAME the facts it checked nothing for"
        )

    def test_fail_if_unverified_exits_non_zero_when_a_fact_is_unchecked(
        self, tmp_path: Path
    ) -> None:
        project = _project(tmp_path, "The MCP server exposes 18 tools.")
        invocation = CliRunner().invoke(
            main,
            ["docs", "audit", "--project", str(project), "--fail-if", "unverified>0"],
        )

        assert invocation.exit_code == 1

    def test_fail_if_unverified_tolerates_a_threshold_it_does_not_reach(
        self, tmp_path: Path
    ) -> None:
        """Bite guard: the metric must be a real comparison, not a constant fail."""
        project = _project(tmp_path, "The MCP server exposes 18 tools.")
        invocation = CliRunner().invoke(
            main,
            ["docs", "audit", "--project", str(project), "--fail-if", "unverified>99"],
        )

        assert invocation.exit_code == 0


# ===========================================================================
# The scan surface — which files were never read, and why
# ===========================================================================


class TestTheScanSurfaceIsReported:
    @staticmethod
    def _project_with_hidden_docs(tmp_path: Path) -> Path:
        project = _project(tmp_path, "The MCP server exposes 18 tools.")
        spec = project / "docs" / "domains" / "d" / "features" / "f" / "SPEC.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("# Spec\n\nThe server exposes 99 tools.\n", encoding="utf-8")
        (project / "CONTRIBUTING.md").write_text(
            "# Contributing\n\nThe server exposes 99 tools.\n", encoding="utf-8"
        )
        return project

    def test_an_excluded_spec_is_named_with_its_reason(self, tmp_path: Path) -> None:
        project = self._project_with_hidden_docs(tmp_path)

        surface = DocScanner().resolve_surface(project)

        excluded = {e.path.name: e.reason for e in surface.excluded}
        assert "SPEC.md" in excluded
        assert excluded["SPEC.md"], "an excluded file must carry the reason it was excluded"

    def test_a_file_whose_counts_are_suppressed_is_named(self, tmp_path: Path) -> None:
        project = self._project_with_hidden_docs(tmp_path)

        surface = DocScanner().resolve_surface(project)

        assert "CONTRIBUTING.md" in [p.name for p in surface.count_suppressed]
        assert "CONTRIBUTING.md" in [p.name for p in surface.scanned], (
            "the file IS scanned for versions — only its counts are suppressed"
        )

    def test_a_plain_doc_is_reported_as_scanned(self, tmp_path: Path) -> None:
        """Non-vacuity guard: the surface is not simply 'everything is hidden'."""
        project = self._project_with_hidden_docs(tmp_path)

        surface = DocScanner().resolve_surface(project)

        assert "README.md" in [p.name for p in surface.scanned]
        assert "README.md" not in [e.path.name for e in surface.excluded]

    def test_json_payload_carries_the_scan_surface(self, tmp_path: Path) -> None:
        _, payload = _audit_json(self._project_with_hidden_docs(tmp_path))

        surface = payload["scan_surface"]
        assert isinstance(surface, dict)
        assert surface["files_excluded"] >= 1
        assert surface["files_count_suppressed"] >= 1
        assert surface["files_scanned"] >= 1
        assert any(
            "SPEC.md" in entry["path"] for entry in surface["excluded"]
        ), "the payload must name the files, not only count them"


# ===========================================================================
# The gate line says what it covered
# ===========================================================================


class TestTheGateLineSaysWhatItCovered:
    def test_the_docs_audit_step_states_its_fact_coverage(self, tmp_path: Path) -> None:
        from beadloom.application.gate import run_ci_gate
        from beadloom.onboarding import generate_agents_md

        (tmp_path / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
        generate_agents_md(tmp_path)

        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        step = next(s for s in result.steps if s.name == "docs-audit")

        assert step.passed is True
        assert "fact(s)" in step.summary, (
            "the one line everybody reads must say how much of the declared surface "
            f"it covered — got {step.summary!r}"
        )


# ===========================================================================
# A modifier binds inside its own clause (BDL-UX #173, class 3)
# ===========================================================================


class TestAModifierBindsWithinItsClause:
    def test_a_modifier_in_another_clause_does_not_blind_a_genuine_count(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        line = "The graph holds 316 edges, one per import."
        assert _scan_line(scanner, tmp_path, line) == [("edge_count", 316)]

    def test_a_modifier_in_the_same_clause_still_suppresses(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Bite guard: clause scoping must not disarm Layer 1 where it belongs."""
        assert _scan_line(scanner, tmp_path, "The graph holds up to 316 edges.") == []
        assert _scan_line(scanner, tmp_path, "The crawler visits 316 nodes per run.") == []

    def test_a_keyword_in_another_clause_does_not_bind_the_number(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """The same scoping, applied to the noun: a breakdown is not a total.

        ``exposes 18 tools: 14 over the graph`` used to yield BOTH 18 and 14 as
        ``mcp_tool_count`` — the 14 needed an ``ignore`` entry to stay quiet.
        """
        line = "The server exposes 18 tools: 14 over the graph plus four process ones."
        assert _scan_line(scanner, tmp_path, line) == [("mcp_tool_count", 18)]


# ===========================================================================
# Small counts stay unread — deliberately, and reported (class 2)
# ===========================================================================


class TestSmallCountsAreUnreadAndSaidSo:
    def test_a_single_digit_count_claim_is_not_extracted(
        self, scanner: DocScanner, tmp_path: Path
    ) -> None:
        """Measured decision, not an oversight — see the audit SPEC's blind spots.

        Extracting single digits was measured on this repo: 14 new mentions, of
        which 13 are ordinals, table cells and category breakdowns.  The floor
        stays; what changes is that the audit now SAYS which facts it costs.
        """
        assert _scan_line(scanner, tmp_path, "Beadloom indexes 7 languages.") == []

    def test_the_cost_of_the_floor_is_reported_per_fact(self) -> None:
        facts = {
            "language_count": Fact("language_count", 1, "code symbols"),
            "cli_command_count": Fact("cli_command_count", 39, "CLI"),
        }
        coverage = compare_facts(facts, []).coverage

        assert coverage["language_count"].status == "unreadable"
        assert coverage["cli_command_count"].status == "not_covered"
