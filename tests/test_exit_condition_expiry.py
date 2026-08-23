# beadloom:domain=graph
"""An exit condition that has passed, and a crossing nobody counted (BDL-061.49).

``rules.yml`` promised, in prose, that "an exemption that stops suppressing
anything is itself reported, which is how the exit condition announces itself
instead of waiting to be remembered". Only half of that was true. A **dead**
exemption was reported; an **expired** one was not, because ``until`` was
required to be a non-empty string and nothing more — no date parsing existed
anywhere in ``graph/`` or ``application/guards/``.

Measured by review ``.7`` (MAJOR 2) before this file was written: an exemption
``to: "*" / from: "*" / until: "1999-01-01"`` added to ``tui-no-direct-infra``,
with a real ``tui -> infrastructure`` import injected, produced
``0 violations, 12 rules evaluated`` at exit 0 and said **nothing** about a
suppression. A wildcard exemption a quarter of a century expired swallowed an
error-severity crossing in silence.

Two halves are pinned here, and they are separate claims:

* **the count** — what an exemption suppressed is reported on every run, so a
  clean line can never mean "nothing crossed" when it means "what crossed was
  excused" (A GREEN COUNT IS NOT A CHECKED COUNT);
* **the deadline** — an ``until`` that leads with an ISO date is parsed, and one
  whose date has passed while it is still suppressing something is a finding.

Both surfaces that require an exit condition are covered in one file on purpose:
``forbid_import.exempt[].until`` in ``rules.yml`` and
``guards.<name>.exclusions[].until`` in ``flow.yml`` share ONE grammar, and a
test file per surface is how the two would drift into promising different
things.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.guards.config import GuardExclusion
from beadloom.application.reindex import reindex
from beadloom.graph.linter import format_json, format_rich
from beadloom.graph.linter import lint as run_lint
from beadloom.graph.rule_engine import (
    ImportBoundaryRule,
    ImportExemption,
    evaluate_import_boundary_rules,
    exit_condition_deadline,
    load_rules,
    suppressed_crossings,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules import Violation

LIVENESS_KIND = "rule_liveness"

#: Far enough in the past that no clock skew makes it live, and the exact date
#: the reviewer used in the probe this bead exists to answer.
LONG_PAST = "1999-01-01"
#: Far enough ahead that the suite does not rot on a birthday.
FAR_FUTURE = "2099-01-01"


# ---------------------------------------------------------------------------
# Fixtures — an index shaped like a real one
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """An empty index with the full schema."""
    db = open_db(tmp_path / "test.db")
    create_schema(db)
    yield db  # type: ignore[misc]
    db.close()


def _add_import(conn: sqlite3.Connection, file_path: str, line: int, import_path: str) -> None:
    conn.execute(
        "INSERT INTO code_imports (file_path, line_number, import_path, file_hash) "
        "VALUES (?, ?, ?, ?)",
        (file_path, line, import_path, "h"),
    )


@pytest.fixture()
def indexed(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Two crossings of one boundary, plus one import that crosses nothing."""
    _add_import(conn, "src/pkg/onboarding/scan.py", 11, "pkg.infrastructure.atomic_io")
    _add_import(conn, "src/pkg/onboarding/prime.py", 12, "pkg.infrastructure.db")
    _add_import(conn, "src/pkg/tui/app.py", 10, "pkg.application.graph_reads")
    return conn


def _rule(*exemptions: ImportExemption) -> ImportBoundaryRule:
    """The boundary this repository actually baselined, with the given exemptions."""
    return ImportBoundaryRule(
        name="onboarding-no-direct-infra",
        description="Onboarding must not import infrastructure directly",
        from_glob="src/pkg/onboarding/**",
        to_glob="pkg/infrastructure/**",
        exempt=exemptions,
    )


def _exemption(until: str, *, to_glob: str = "pkg/infrastructure/**") -> ImportExemption:
    return ImportExemption(
        to_glob=to_glob,
        from_glob="*",
        reason="baselined by BDL-061.43",
        until=until,
    )


def _findings(violations: list[Violation]) -> list[Violation]:
    return [v for v in violations if v.rule_type == LIVENESS_KIND]


# ---------------------------------------------------------------------------
# The grammar
# ---------------------------------------------------------------------------


class TestTheExitConditionGrammar:
    """``until`` is a date OR an event, and which one it is must not depend on Python.

    ``date.fromisoformat`` widened in 3.11 (``20260101`` and week dates parse
    there and raise on 3.10), so leaning on it alone would make the same
    ``flow.yml`` enforceable on one supported interpreter and prose on another.
    The grammar is therefore pinned to one spelling: a leading ``YYYY-MM-DD``.
    """

    def test_a_bare_iso_date_is_a_deadline(self) -> None:
        assert exit_condition_deadline("2026-01-01") == date(2026, 1, 1)

    def test_a_date_may_lead_the_sentence_that_explains_it(self) -> None:
        """The useful real form: a deadline AND the condition it stands for."""
        assert exit_condition_deadline(
            "2026-09-01 — when the repository read seam lands"
        ) == date(2026, 9, 1)

    def test_an_event_is_not_a_deadline(self) -> None:
        """This repository's own exemptions retire on an event; that stays legal."""
        assert exit_condition_deadline("the rule is re-scoped — BDL-UX #150 follow-up") is None

    @pytest.mark.parametrize(
        "spelling",
        ["2026-1-1", "20260101", "01/02/2026", "2026-W01-1", "next Tuesday", ""],
    )
    def test_only_one_spelling_counts_as_a_date(self, spelling: str) -> None:
        """Anything else is an event: silently reading a half-date would be worse."""
        assert exit_condition_deadline(spelling) is None

    def test_surrounding_whitespace_is_not_a_different_grammar(self) -> None:
        assert exit_condition_deadline("  2026-01-01  ") == date(2026, 1, 1)

    def test_a_date_in_the_middle_of_prose_is_not_read_as_a_deadline(self) -> None:
        """A deadline is the first thing an exit condition says, or it is not one."""
        assert exit_condition_deadline("some time after 2026-01-01") is None


# ---------------------------------------------------------------------------
# An expired exemption is a finding
# ---------------------------------------------------------------------------


class TestAnExpiredExemptionIsReported:
    """The half the prose promised and the code never did."""

    def test_a_passed_deadline_is_reported_while_it_still_suppresses(
        self, indexed: sqlite3.Connection
    ) -> None:
        findings = _findings(
            evaluate_import_boundary_rules(indexed, [_rule(_exemption(LONG_PAST))])
        )

        assert len(findings) == 1, [f.message for f in findings]
        assert LONG_PAST in findings[0].message
        assert "expired" in findings[0].message.lower()
        assert findings[0].severity == "warn"

    def test_a_deadline_that_has_not_passed_is_not_reported(
        self, indexed: sqlite3.Connection
    ) -> None:
        """Non-vacuity: only the date differs from the test above."""
        findings = _findings(
            evaluate_import_boundary_rules(indexed, [_rule(_exemption(FAR_FUTURE))])
        )

        assert findings == [], [f.message for f in findings]

    def test_today_is_the_last_day_an_exemption_holds(self, indexed: sqlite3.Connection) -> None:
        """A deadline names the last day it covers, not the first day it fails."""
        today = date.today().isoformat()
        findings = _findings(evaluate_import_boundary_rules(indexed, [_rule(_exemption(today))]))

        assert findings == [], [f.message for f in findings]

    def test_yesterday_has_passed(self, indexed: sqlite3.Connection) -> None:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        findings = _findings(
            evaluate_import_boundary_rules(indexed, [_rule(_exemption(yesterday))])
        )

        assert len(findings) == 1

    def test_an_event_exit_condition_is_never_expired(self, indexed: sqlite3.Connection) -> None:
        """An unparseable ``until`` is not a licence and not an expiry — it is prose."""
        findings = _findings(
            evaluate_import_boundary_rules(indexed, [_rule(_exemption("BDL-UX #150 lands"))])
        )

        assert findings == []

    def test_the_finding_says_how_many_crossings_are_still_excused(
        self, indexed: sqlite3.Connection
    ) -> None:
        """Two crossings hide behind this one entry; the number is the whole point."""
        findings = _findings(
            evaluate_import_boundary_rules(indexed, [_rule(_exemption(LONG_PAST))])
        )

        assert "2" in findings[0].message

    def test_an_expired_exemption_still_suppresses(self, indexed: sqlite3.Connection) -> None:
        """Expiry is a finding, never a time bomb: no build turns red on a date.

        A crossing that reappears at ``error`` severity because a calendar day
        passed would redden a pipeline with no commit behind it — the failure
        mode BDL-061.48 rejected for inert rules, in its harsher form.
        """
        violations = [
            v
            for v in evaluate_import_boundary_rules(indexed, [_rule(_exemption(LONG_PAST))])
            if v.rule_type == "forbid_import"
        ]

        assert violations == []

    def test_a_dead_and_expired_exemption_is_reported_once(
        self, indexed: sqlite3.Connection
    ) -> None:
        """One entry, one finding: the dead half already says "delete it"."""
        dead = _exemption(LONG_PAST, to_glob="pkg/infrastructure/health")
        findings = _findings(evaluate_import_boundary_rules(indexed, [_rule(dead)]))

        assert len(findings) == 1, [f.message for f in findings]
        assert "suppresses nothing" in findings[0].message


# ---------------------------------------------------------------------------
# The suppressed count
# ---------------------------------------------------------------------------


class TestASuppressedCrossingIsCounted:
    """What an exemption swallowed is reported on EVERY run, expired or not."""

    def test_every_suppressed_crossing_is_listed(self, indexed: sqlite3.Connection) -> None:
        crossings = suppressed_crossings(indexed, [_rule(_exemption(FAR_FUTURE))])

        assert [(c.file_path, c.line_number) for c in crossings] == [
            ("src/pkg/onboarding/prime.py", 12),
            ("src/pkg/onboarding/scan.py", 11),
        ]
        assert {c.rule_name for c in crossings} == {"onboarding-no-direct-infra"}
        assert {c.until for c in crossings} == {FAR_FUTURE}
        assert {c.expired for c in crossings} == {False}

    def test_a_rule_with_no_exemptions_suppresses_nothing(
        self, indexed: sqlite3.Connection
    ) -> None:
        """Non-vacuity: the counter must be able to say zero."""
        assert suppressed_crossings(indexed, [_rule()]) == []

    def test_an_expired_entry_marks_what_it_swallowed(self, indexed: sqlite3.Connection) -> None:
        crossings = suppressed_crossings(indexed, [_rule(_exemption(LONG_PAST))])

        assert {c.expired for c in crossings} == {True}


# ---------------------------------------------------------------------------
# What the run says out loud
# ---------------------------------------------------------------------------


_NODES = """\
nodes:
  - ref_id: alpha
    kind: component
    summary: Alpha component
    source: src/app/alpha/
  - ref_id: beta
    kind: component
    summary: Beta component
    source: src/app/beta/
edges: []
"""

_ALPHA_CLEAN = (
    "# beadloom:component=alpha\n'''Alpha.'''\n\n"
    "import os\n\n\ndef run() -> int:\n    return len(os.sep)\n"
)
_ALPHA_CROSSING = (
    "# beadloom:component=alpha\n'''Alpha.'''\n\n"
    "import os\n\nfrom app.beta import tokens\n\n\n"
    "def run() -> int:\n    return tokens.verify() + len(os.sep)\n"
)
_BETA = (
    "# beadloom:component=beta\n'''Beta.'''\n\n"
    "from app.beta import util\n\n\ndef verify() -> int:\n    return util.two()\n"
)
_BETA_UTIL = "# beadloom:component=beta\n'''Beta util.'''\n\n\ndef two() -> int:\n    return 2\n"


def _rules_yml(until: str, *, exempt: bool = True) -> str:
    """One error-severity boundary, wholly neutralised by one wildcard exemption."""
    rule = (
        "version: 1\n"
        "rules:\n"
        "  - name: alpha-no-beta-import\n"
        "    description: Alpha must not import beta\n"
        "    severity: error\n"
        "    forbid_import:\n"
        "      from: 'src/app/alpha/*'\n"
        "      to: 'app/beta*'\n"
    )
    if not exempt:
        return rule
    return rule + (
        "      exempt:\n"
        "        - from: '*'\n"
        "          to: '*'\n"
        "          reason: a blanket exemption that names every crossing at once\n"
        f"          until: '{until}'\n"
    )


def _project(root: Path, *, until: str, crossing: bool = True, exempt: bool = True) -> Path:
    """A tiny indexed project whose only rule is fully excused by one exemption.

    With *crossing* false the alpha module breaks nothing, so the rule is live
    (beta's own sibling import keeps the ``to:`` glob matching) and there is
    simply nothing to suppress — the fixture for every "and this is what a run
    with nothing to excuse looks like" assertion.
    """
    project = root / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n  - src\ndocs_dir: docs\n", encoding="utf-8"
    )
    (project / ".beadloom" / "_graph" / "services.yml").write_text(_NODES, encoding="utf-8")
    (project / ".beadloom" / "_graph" / "rules.yml").write_text(
        _rules_yml(until, exempt=exempt), encoding="utf-8"
    )
    (project / "docs").mkdir(parents=True)
    for pkg in ("alpha", "beta"):
        (project / "src" / "app" / pkg).mkdir(parents=True)
        (project / "src" / "app" / pkg / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "app" / "alpha" / "service.py").write_text(
        _ALPHA_CROSSING if crossing else _ALPHA_CLEAN, encoding="utf-8"
    )
    (project / "src" / "app" / "beta" / "tokens.py").write_text(_BETA, encoding="utf-8")
    (project / "src" / "app" / "beta" / "util.py").write_text(_BETA_UTIL, encoding="utf-8")
    reindex(project)
    return project


class TestTheRunSaysWhatItExcused:
    """The reviewer's probe, end to end: exit codes and ``--json``, never line counts (#148)."""

    def test_the_result_carries_the_count(self, tmp_path: Path) -> None:
        result = run_lint(_project(tmp_path, until=FAR_FUTURE))

        assert result.violations_suppressed == 1
        assert result.error_count == 0

    def test_the_clean_summary_no_longer_reads_as_untouched(self, tmp_path: Path) -> None:
        """"No violations found" beside a count of what was excused."""
        text = format_rich(run_lint(_project(tmp_path, until=FAR_FUTURE)))

        assert "No violations found" in text
        assert "1 crossing suppressed by an exemption" in text

    def test_a_run_with_nothing_suppressed_keeps_its_line(self, tmp_path: Path) -> None:
        """Non-vacuity: the common line must not grow a permanent ", 0 suppressed"."""
        text = format_rich(
            run_lint(_project(tmp_path, until=FAR_FUTURE, crossing=False, exempt=False))
        )

        assert "suppressed" not in text

    def test_json_carries_the_count_and_what_it_counted(self, tmp_path: Path) -> None:
        payload = json.loads(format_json(run_lint(_project(tmp_path, until=LONG_PAST))))

        assert payload["summary"]["violations_suppressed"] == 1
        assert [entry["file_path"] for entry in payload["suppressed"]] == [
            "src/app/alpha/service.py"
        ]
        assert payload["suppressed"][0]["expired"] is True
        assert payload["suppressed"][0]["until"] == LONG_PAST

    def test_the_piped_zero_line_says_what_it_excused(self, tmp_path: Path) -> None:
        """The exact line from the review: ``0 violations, N rules evaluated``."""
        project = _project(tmp_path, until=FAR_FUTURE)

        invocation = CliRunner().invoke(
            main, ["lint", "--no-reindex", "--strict", "--project", str(project)]
        )

        assert invocation.exit_code == 0
        assert "1 crossing suppressed by an exemption" in invocation.stdout

    def test_an_expired_wildcard_exemption_is_named_at_exit_zero(self, tmp_path: Path) -> None:
        """rc stays 0 — it is a configuration finding — but silence is over."""
        project = _project(tmp_path, until=LONG_PAST)

        invocation = CliRunner().invoke(
            main,
            ["lint", "--no-reindex", "--strict", "--format", "json", "--project", str(project)],
        )
        payload = json.loads(invocation.stdout)

        assert invocation.exit_code == 0
        assert payload["summary"]["error_count"] == 0
        assert [f["kind"] for f in payload["findings"]] == [LIVENESS_KIND]
        assert LONG_PAST in payload["findings"][0]["why"]

    def test_a_project_can_choose_to_fail_on_it(self, tmp_path: Path) -> None:
        """``--fail-on-warn`` is the lever for a team that wants a hard deadline."""
        project = _project(tmp_path, until=LONG_PAST)

        invocation = CliRunner().invoke(
            main, ["lint", "--no-reindex", "--fail-on-warn", "--project", str(project)]
        )

        assert invocation.exit_code == 1


class TestTheGateSaysItToo:
    """`beadloom ci` is the line a pre-push hook and a CI log show — it carries the count.

    Measured while closing this bead: the Gate's clean lint summary read
    ``12 rules, 0 violations`` on this repository while six crossings sat behind
    exemptions. Its OTHER counter needs no clause — an inert rule always emits a
    finding, so the clean branch is unreachable while ``rules_inert`` is non-zero
    and the summary already flips to ``0 error(s), 1 warning(s)``. A suppressed
    crossing is the one thing that can be non-zero with nothing to report.
    """

    def _lint_step_summary(self, project: Path) -> str:
        from beadloom.application.gate import _step_lint

        return _step_lint(project).summary

    def test_the_clean_gate_line_says_what_was_excused(self, tmp_path: Path) -> None:
        summary = self._lint_step_summary(_project(tmp_path, until=FAR_FUTURE))

        assert "0 violations" in summary
        assert "1 crossing suppressed by an exemption" in summary

    def test_a_gate_line_with_nothing_excused_keeps_its_shape(self, tmp_path: Path) -> None:
        """Non-vacuity: the everyday green line must not grow a permanent clause."""
        assert (
            self._lint_step_summary(
                _project(tmp_path, until=FAR_FUTURE, crossing=False, exempt=False)
            )
            == "1 rules, 0 violations"
        )


# ---------------------------------------------------------------------------
# The same grammar on the other surface
# ---------------------------------------------------------------------------


class TestAGuardExclusionSharesTheGrammar:
    """``flow.yml`` exclusions carry the identical promise, so they carry the identical check."""

    def _exclusion(self, until: str) -> GuardExclusion:
        return GuardExclusion(
            path="scripts/**", reason="operational scripts are not bead-scoped", until=until
        )

    def test_a_passed_deadline_is_expired(self) -> None:
        assert self._exclusion(LONG_PAST).expired() is True

    def test_a_future_deadline_is_not(self) -> None:
        assert self._exclusion(FAR_FUTURE).expired() is False

    def test_an_event_exit_condition_is_not_expired(self) -> None:
        assert self._exclusion("BDL-0xx introduces a scripts node").expired() is False

    def test_the_skip_reason_says_the_condition_has_passed(self) -> None:
        """The moment it suppresses something is the moment worth saying it."""
        assert "EXPIRED" in self._exclusion(LONG_PAST).describe()

    def test_a_live_exclusion_describes_itself_unchanged(self) -> None:
        described = self._exclusion(FAR_FUTURE).describe()

        assert "EXPIRED" not in described
        assert described.endswith(f"(until {FAR_FUTURE})")

    def test_the_liveness_report_names_it(self, tmp_path: Path) -> None:
        from beadloom.application.guards.liveness import build_liveness

        (tmp_path / ".beadloom").mkdir(parents=True)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            '      - path: "scripts/**"\n'
            '        reason: "operational scripts are not bead-scoped"\n'
            f'        until: "{LONG_PAST}"\n',
            encoding="utf-8",
        )

        rows = {row.guard: row for row in build_liveness(tmp_path)}

        assert rows["bead-claimed"].expired_exclusions == ("scripts/**",)
        assert rows["bead-claimed"].to_dict()["expired_exclusions"] == ["scripts/**"]

    def test_a_live_exclusion_is_not_named(self, tmp_path: Path) -> None:
        """Non-vacuity for the row above."""
        from beadloom.application.guards.liveness import build_liveness

        (tmp_path / ".beadloom").mkdir(parents=True)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            '      - path: "scripts/**"\n'
            '        reason: "operational scripts are not bead-scoped"\n'
            f'        until: "{FAR_FUTURE}"\n',
            encoding="utf-8",
        )

        rows = {row.guard: row for row in build_liveness(tmp_path)}

        assert rows["bead-claimed"].expired_exclusions == ()


# ---------------------------------------------------------------------------
# This repository's own exit conditions
# ---------------------------------------------------------------------------


class TestBeadloomsOwnExemptions:
    """The suite reddens the day one of this project's own baselines outlives its date."""

    def test_no_shipped_exemption_has_expired(self) -> None:
        root = Path(__file__).resolve().parents[1]
        rules = load_rules(root / ".beadloom" / "_graph" / "rules.yml")

        expired = [
            (rule.name, exemption.until)
            for rule in rules
            if isinstance(rule, ImportBoundaryRule)
            for exemption in rule.exempt
            if (deadline := exit_condition_deadline(exemption.until)) is not None
            and deadline < date.today()
        ]

        assert expired == [], f"exit conditions that have passed: {expired}"
