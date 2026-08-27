# beadloom:domain=application
"""S2 verification — where a check can STILL report green over work it never did.

``tests/test_s2_lying_checks.py`` proves the three defects S2 was scoped around
(#142/#146/#147) are fixed. This file is the adversarial half: it attacks the
same checks from the outside and records, executably, the places where a green
result still does not mean "checked".

Every gap here was **measured** on a clean-room copy of this repo at
004487a before it was written down — never inferred from reading the code:

* ``lint`` reported ``16 rules, 0 violations`` over four rules that cannot match
  anything (a ``require`` about a node that does not exist, a ``deny`` between
  tags nobody carries, ``module_coverage`` over an absent source root, a
  cardinality ``check`` on a missing node), because BDL-061.43's ``rule_liveness``
  covered ``forbid_import`` **only**. CLOSED by ``beadloom-mr2l.48``, which
  extended liveness to all nine rule types; the assertions below are kept as
  live regression tests rather than deleted, and
  ``tests/test_rule_liveness_all_types.py`` owns the per-type pairs.
* A ``forbid_import`` ``exempt`` entry written ``from: "*" / to: "*"`` with an
  ``until:`` date already in the past swallowed a real error-severity crossing:
  ``12 rules, 0 violations``, exit 0, and nothing in the output said a crossing
  had been suppressed. CLOSED by ``beadloom-mr2l.49``: what an exemption excused
  is counted on every run, and an ``until:`` leading with an ISO date that has
  passed is a finding while the entry still suppresses something. The
  assertions below are kept as live regression tests;
  ``tests/test_exit_condition_expiry.py`` owns the grammar and both surfaces.
* ``sync-check`` reports ``status: ok`` for a pair whose code file — or whose
  doc — no longer exists, because ``_file_hash`` returns ``None`` for a missing
  file and both comparisons are guarded by the truthiness of that hash. Deleting
  a documented feature's whole ``SPEC.md`` from this repo left ``beadloom ci``
  at exit 0 with every step PASS.
* The Gate's doctor step prints ``N check(s) clean`` where *N* counts every
  check, warnings included. On the untouched repo that line read
  ``20 check(s) clean`` over 10 OK, 9 WARNING and 1 INFO that says verbatim
  "command count not verified".
* ``lint --no-reindex`` — the read-only form #147 introduced — answers about the
  INDEX and says nothing about the tree. With a real violation on disk and no
  reindex it printed ``12 rules, 0 violations`` at exit 0, silently.
* ``docs audit`` declares 9 facts and its green line ``13 mention(s) fresh``
  covers exactly one of them (``mcp_tool_count``); the other 8 verified nothing
  and the payload has no channel that says so.

Tests that assert a gap carry ``xfail(strict=True)``: the gap is recorded as an
executable statement, and the day it is fixed the marker fails the suite rather
than letting the finding be quietly forgotten. Each class also carries at least
one PASSING test using the same fixture, so an xfail can never be an artefact of
a broken helper (TESTS MUST BITE).
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.doctor import Severity, run_checks
from beadloom.application.gate import run_ci_gate
from beadloom.application.reindex import reindex
from beadloom.doc_sync.audit import run_audit
from beadloom.doc_sync.engine import check_sync
from beadloom.graph.linter import lint as run_lint
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.gate import GateStep
    from beadloom.graph.linter import LintResult

# ---------------------------------------------------------------------------
# Fixture project — two components, one boundary rule, one doc each
# ---------------------------------------------------------------------------

# The clean alpha still imports SOMETHING: `evaluate_import_boundary_rules` is
# deliberately silent when the index holds no imports at all (that is lint's
# "0 files scanned" header), so an import-free fixture would make every
# liveness assertion below vacuous.
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
#: Beta imports its own sibling so that the live rule's `to:` glob matches
#: SOMETHING in the index. Without it the rule is inert and BDL-061.43's
#: liveness finding fires on the fixture itself, drowning every assertion below.
_BETA_UTIL = "# beadloom:component=beta\n'''Beta util.'''\n\n\ndef two() -> int:\n    return 2\n"

#: The doc must NAME the module it documents: an unmentioned module is a
#: `missing_modules` staleness reason, which would make every Gate assertion
#: below red for a reason that has nothing to do with what is under test.
_ALPHA_DOC = "# Alpha\n\nThe `service` module runs alpha.\n"

_NODES = """\
nodes:
  - ref_id: alpha
    kind: component
    summary: Alpha component
    source: src/app/alpha/
    docs:
      - components/alpha.md
  - ref_id: beta
    kind: component
    summary: Beta component
    source: src/app/beta/
    docs:
      - components/beta.md
edges: []
"""

#: The live boundary rule the fixture is built around: alpha must not import beta.
_LIVE_RULE = """\
  - name: alpha-no-beta-import
    description: Alpha must not import beta
    severity: error
    forbid_import:
      from: 'src/app/alpha/*'
      to: 'app/beta*'
"""


def _rules_yml(*rule_blocks: str) -> str:
    """Assemble a ``rules.yml`` from rule blocks, live rule first."""
    return "version: 1\nrules:\n" + "".join(rule_blocks)


def make_project(
    root: Path,
    *,
    rules: str | None = None,
    alpha_source: str = _ALPHA_CLEAN,
) -> Path:
    """Build a minimal indexable project and return its root.

    Defaults give a clean project with one live ``forbid_import`` rule; each
    test overrides only the axis it is about.
    """
    project = root / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / "docs" / "components").mkdir(parents=True)
    (project / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n  - src\ndocs_dir: docs\n", encoding="utf-8"
    )
    (project / ".beadloom" / "_graph" / "services.yml").write_text(_NODES, encoding="utf-8")
    (project / ".beadloom" / "_graph" / "rules.yml").write_text(
        rules if rules is not None else _rules_yml(_LIVE_RULE), encoding="utf-8"
    )
    (project / "docs" / "components" / "alpha.md").write_text(_ALPHA_DOC, encoding="utf-8")
    (project / "docs" / "components" / "beta.md").write_text(
        "# Beta\n\nThe `tokens` and `util` modules verify beta.\n", encoding="utf-8"
    )
    for pkg in ("alpha", "beta"):
        (project / "src" / "app" / pkg).mkdir(parents=True)
        (project / "src" / "app" / pkg / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "app" / "alpha" / "service.py").write_text(alpha_source, encoding="utf-8")
    (project / "src" / "app" / "beta" / "tokens.py").write_text(_BETA, encoding="utf-8")
    (project / "src" / "app" / "beta" / "util.py").write_text(_BETA_UTIL, encoding="utf-8")
    return project


def _indexed(root: Path, **kwargs: str) -> Path:
    """Build the project and index it once."""
    project = make_project(root, **kwargs)
    reindex(project)
    return project


def _liveness_messages(result: LintResult) -> list[str]:
    """Every message the lint reported about a rule that could not do its job."""
    return [v.message for v in result.violations if v.rule_type == "rule_liveness"]


def _rule_names_reported(result: LintResult) -> set[str]:
    """Names of the rules the lint said anything at all about."""
    return {v.rule_name for v in result.violations}


# ---------------------------------------------------------------------------
# A GREEN COUNT IS NOT A CHECKED COUNT — rules that cannot match
# ---------------------------------------------------------------------------

_DEAD_REQUIRE = """\
  - name: dead-require
    description: require rule about a node that does not exist
    require:
      for: { ref_id: no-such-node }
      has_edge_to: { ref_id: alpha }
      edge_kind: part_of
"""

_DEAD_DENY = """\
  - name: dead-deny
    description: deny rule between tags nobody carries
    deny:
      from: { tag: layer-nonexistent }
      to: { tag: layer-also-not }
"""

_DEAD_COVERAGE = """\
  - name: dead-coverage
    description: coverage over a source root that does not exist
    severity: error
    module_coverage:
      source_root: src/nowhere/
      min_symbols: 1
"""

_DEAD_IMPORT_GLOB = """\
  - name: dead-import-glob
    description: the src/-prefixed to-glob that can never match an import path
    severity: error
    forbid_import:
      from: 'src/app/alpha/*'
      to: 'src/app/beta/**'
"""


class TestARuleThatCannotMatchIsReported:
    """Every rule type reports its own inertness (was: ``forbid_import`` only)."""

    def test_a_dead_import_glob_is_reported(self, tmp_path: Path) -> None:
        """The one liveness channel that exists works — this file's non-vacuity guard."""
        # Arrange
        project = _indexed(tmp_path, rules=_rules_yml(_DEAD_IMPORT_GLOB))

        # Act
        result = run_lint(project)

        # Assert
        assert any("dead-import-glob" in m for m in _liveness_messages(result)), (
            "the forbid_import liveness channel from BDL-061.43 must still fire — "
            f"got {result.violations}"
        )

    def test_a_require_rule_about_a_node_that_does_not_exist_is_reported(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _indexed(
            tmp_path,
            rules=_rules_yml(_LIVE_RULE, _DEAD_REQUIRE),
            alpha_source=_ALPHA_CROSSING,
        )

        # Act
        result = run_lint(project)

        # Assert
        assert "dead-require" in _rule_names_reported(result), (
            "a rule whose subject does not exist checks nothing and must say so, "
            f"but lint reported {result.rules_evaluated} rules and "
            f"{len(result.violations)} violations"
        )

    def test_a_deny_rule_between_tags_nobody_carries_is_reported(self, tmp_path: Path) -> None:
        # Arrange
        project = _indexed(
            tmp_path,
            rules=_rules_yml(_LIVE_RULE, _DEAD_DENY),
            alpha_source=_ALPHA_CROSSING,
        )

        # Act
        result = run_lint(project)

        # Assert
        assert "dead-deny" in _rule_names_reported(result), (
            "a deny rule whose matchers select no node is inert and must be reported"
        )

    def test_module_coverage_over_a_source_root_that_does_not_exist_is_reported(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _indexed(
            tmp_path,
            rules=_rules_yml(_LIVE_RULE, _DEAD_COVERAGE),
            alpha_source=_ALPHA_CROSSING,
        )

        # Act
        result = run_lint(project)

        # Assert
        assert "dead-coverage" in _rule_names_reported(result), (
            "module_coverage over an absent source root covers no module and must say so"
        )

    def test_the_dead_rules_are_named_instead_of_inflating_the_count(
        self, tmp_path: Path
    ) -> None:
        """The count still grows by three — and now says the three checked nothing.

        Before ``beadloom-mr2l.48`` the ONLY thing three inert rules changed was
        the advertised count: same violations, bigger number, no signal. The
        count is left alone (they were loaded and dispatched, so ``evaluated``
        is true) and qualified instead, at ``warn`` so a green pipeline does not
        turn red on upgrade.
        """
        # Arrange
        live = _indexed(
            tmp_path / "live", rules=_rules_yml(_LIVE_RULE), alpha_source=_ALPHA_CROSSING
        )
        padded = _indexed(
            tmp_path / "padded",
            rules=_rules_yml(_LIVE_RULE, _DEAD_REQUIRE, _DEAD_DENY, _DEAD_COVERAGE),
            alpha_source=_ALPHA_CROSSING,
        )

        # Act
        lean = run_lint(live)
        fat = run_lint(padded)

        # Assert — the numbers are on record, in their corrected relationship
        assert fat.rules_evaluated == lean.rules_evaluated + 3
        assert fat.rules_inert == 3
        assert lean.rules_inert == 0
        assert {v.rule_name for v in fat.violations if v.rule_type == "rule_liveness"} == {
            "dead-require",
            "dead-deny",
            "dead-coverage",
        }
        assert fat.error_count == lean.error_count, (
            "naming an inert rule must not fail a build that was passing — the "
            "finding is about the configuration, not the code"
        )


# ---------------------------------------------------------------------------
# An exclusion that suppresses everything
# ---------------------------------------------------------------------------

_BLANKET_EXEMPTION = """\
  - name: alpha-no-beta-import
    description: Alpha must not import beta
    severity: error
    forbid_import:
      from: 'src/app/alpha/*'
      to: 'app/beta*'
      exempt:
        - from: '*'
          to: '*'
          reason: a blanket exemption that names every crossing at once
          until: 1999-01-01 — an exit condition that passed a quarter-century ago
"""


_BLANKET_EXEMPTION_RULES = "version: 1\nrules:\n" + _BLANKET_EXEMPTION

#: The same rule with an exemption aimed at a crossing that does not exist — the
#: shape BDL-061.43 DOES report, and this class's proof that the helper works.
_UNUSED_EXEMPTION = """\
  - name: alpha-no-beta-import
    description: Alpha must not import beta
    severity: error
    forbid_import:
      from: 'src/app/alpha/*'
      to: 'app/beta*'
      exempt:
        - from: '*'
          to: 'app/gamma*'
          reason: a crossing that was removed while this entry stayed behind
          until: gamma is deleted
"""

_UNUSED_EXEMPTION_RULES = "version: 1\nrules:\n" + _UNUSED_EXEMPTION


class TestAnExemptionCanSuppressEverythingAndReadClean:
    """An exemption is visible whatever it does: counted when live, named when stale."""

    def test_an_exemption_that_suppresses_nothing_is_reported(self, tmp_path: Path) -> None:
        """BDL-061.43's dead-exemption finding works — this class's non-vacuity guard."""
        # Arrange — the rule is live (a real crossing exists) and the exemption
        # points somewhere else, so it suppresses nothing
        project = _indexed(tmp_path, rules=_UNUSED_EXEMPTION_RULES, alpha_source=_ALPHA_CROSSING)

        # Act
        result = run_lint(project)

        # Assert
        assert any("suppresses nothing" in m for m in _liveness_messages(result)), (
            f"a dead exemption must announce its own exit condition — got {result.violations}"
        )

    def test_a_blanket_exemption_swallowing_a_real_crossing_is_reported(
        self, tmp_path: Path
    ) -> None:
        """CLOSED by ``beadloom-mr2l.49`` — kept as a live regression test.

        The crossing is still suppressed (an exemption that stops working on a
        date would redden a build with no commit behind it), but the run no
        longer reads as untouched: what was excused is counted on the result and
        said in the summary line.
        """
        # Arrange — a real, error-severity crossing under a wildcard exemption
        project = _indexed(tmp_path, rules=_BLANKET_EXEMPTION_RULES, alpha_source=_ALPHA_CROSSING)

        # Act
        result = run_lint(project)

        # Assert
        assert result.violations_suppressed == 1, (
            "a suppressed crossing is still a crossing: the count of what an exemption "
            "silenced must appear somewhere in the result"
        )
        assert result.violations, (
            "and the entry that silenced it — a wildcard dated 1999 — must be named"
        )

    def test_an_exemption_whose_until_has_passed_is_reported(self, tmp_path: Path) -> None:
        """CLOSED by ``beadloom-mr2l.49`` — ``until`` leading with an ISO date is parsed."""
        # Arrange
        project = _indexed(tmp_path, rules=_BLANKET_EXEMPTION_RULES, alpha_source=_ALPHA_CROSSING)

        # Act
        result = run_lint(project)

        # Assert
        assert any("1999" in m for m in _liveness_messages(result)), (
            "an exclusion whose stated exit condition has passed must be reported"
        )


# ---------------------------------------------------------------------------
# sync-check over a file it could not read
# ---------------------------------------------------------------------------


def _pair_status(project: Path, *, code_suffix: str) -> list[str]:
    """Statuses reported for every pair whose code path ends with *code_suffix*."""
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        return [
            str(row["status"])
            for row in check_sync(conn, project)
            if str(row.get("code_path") or "").endswith(code_suffix)
        ]
    finally:
        conn.close()


class TestSyncCheckOverAFileItCouldNotRead:
    """``_file_hash`` returns ``None`` for a missing file, and ``None`` reads as "unchanged"."""

    def test_a_pair_whose_code_changed_is_reported_stale(self, tmp_path: Path) -> None:
        """The freshness comparison works — this class's non-vacuity guard."""
        # Arrange
        project = _indexed(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(
            _ALPHA_CLEAN + "\n\ndef added() -> int:\n    return 3\n", encoding="utf-8"
        )

        # Act
        statuses = _pair_status(project, code_suffix="alpha/service.py")

        # Assert
        assert statuses and all(s == "stale" for s in statuses), (
            f"a changed code file must make its pair stale — got {statuses}"
        )

    # FIXED in BDL-061.46/.47 (BDL-UX #174): the code side reads ``missing`` too.
    def test_a_pair_whose_code_file_was_deleted_is_not_reported_fresh(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _indexed(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").unlink()

        # Act
        statuses = _pair_status(project, code_suffix="alpha/service.py")

        # Assert
        assert "ok" not in statuses, (
            "a file that is not there was not checked, and must not be called fresh"
        )

    # FIXED in BDL-061.46/.47 (BDL-UX #174): a pair whose doc file is gone is
    # reported ``missing`` — a failure, not an absence.
    def test_a_pair_whose_doc_was_deleted_is_not_reported_fresh(self, tmp_path: Path) -> None:
        # Arrange
        project = _indexed(tmp_path)
        (project / "docs" / "components" / "alpha.md").unlink()

        # Act
        statuses = _pair_status(project, code_suffix="alpha/service.py")

        # Assert
        assert "ok" not in statuses, "a doc that is not there cannot be fresh against anything"


# ---------------------------------------------------------------------------
# The Gate over a declared doc that is gone
# ---------------------------------------------------------------------------


def _gate(project: Path) -> tuple[bool, list[str]]:
    """Run the whole Gate and return ``(ok, [finding text, ...])``.

    Deliberately NOT the step summaries: a count that silently moves from
    ``275 pair(s) fresh`` to ``264 pair(s) fresh`` inside a PASS line is the
    defect, not the report of it. What a reader can act on is the verdict and
    the findings.
    """
    result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
    return result.ok, [json.dumps(f, sort_keys=True, default=str) for f in result.findings]


def _steps(project: Path) -> list[GateStep]:
    """Run the whole Gate and return its steps."""
    return run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False).steps


class TestTheGateOverADeclaredDocThatIsGone:
    """A node declares ``docs:``; deleting the file it names changes no verdict."""

    def test_the_gate_reacts_to_a_real_boundary_violation(self, tmp_path: Path) -> None:
        """The Gate's verdict moves on this fixture — this class's non-vacuity guard."""
        # Arrange
        clean = _indexed(tmp_path / "clean")
        crossing = _indexed(tmp_path / "crossing", alpha_source=_ALPHA_CROSSING)

        # Act — compare the lint STEP rather than the whole verdict: a freshly
        # built fixture has never been sync-baselined, which is a property of the
        # fixture and not of the thing under test
        clean_lint = next(s for s in _steps(clean) if s.name == "lint")
        crossing_lint = next(s for s in _steps(crossing) if s.name == "lint")

        # Assert
        assert clean_lint.passed is True, f"clean fixture: {clean_lint.summary}"
        assert crossing_lint.passed is False, "a real crossing must fail lint in the Gate"

    # FIXED in BDL-061.46/.47 (BDL-UX #174): the DECLARATION outlives the file,
    # so deleting the doc fails the Gate by name instead of shrinking a count.
    def test_deleting_a_declared_doc_is_reported_by_the_gate(self, tmp_path: Path) -> None:
        # Arrange
        project = _indexed(tmp_path)
        # The untouched fixture must not FAIL. It does carry warnings — it is not
        # a git repo and its index was just built, so its pairs are honestly
        # `unverified` rather than fresh (BDL-UX #175); that is the fix, not a
        # regression, and the assertion is about errors.
        before_ok, before_findings = _gate(project)
        assert before_ok is True
        assert not [f for f in before_findings if '"severity": "error"' in f]
        (project / "docs" / "components" / "alpha.md").unlink()

        # Act
        ok, findings = _gate(project)

        # Assert
        assert ok is False or any("alpha.md" in f for f in findings), (
            "a node declares this doc and the file is gone: the Gate must fail or name "
            f"it — got ok={ok} with {len(findings)} finding(s)"
        )


# ---------------------------------------------------------------------------
# "N check(s) clean" where N counts warnings
# ---------------------------------------------------------------------------


class TestTheDoctorSummaryCountsWarningsAsClean:
    """The Gate's doctor line reports how many checks RAN, under the word "clean"."""

    def test_the_fixture_really_does_produce_a_doctor_warning(self, tmp_path: Path) -> None:
        """This class's non-vacuity guard: without a warning the next test proves nothing."""
        # Arrange
        project = _indexed(tmp_path)
        (project / "docs" / "orphan.md").write_text("# Orphan\n\nNo node owns me.\n")
        reindex(project)

        # Act
        conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
        conn.row_factory = sqlite3.Row
        try:
            checks = run_checks(conn, project_root=project)
        finally:
            conn.close()

        # Assert
        assert [c for c in checks if c.severity is Severity.WARNING]

    # FIXED in BDL-061.46 (BDL-UX #174, third item): the summary counts the
    # CHECKS that ran and reports their severities, so it can no longer rise
    # while the tree shrinks and can no longer call a warning clean.
    def test_the_doctor_step_does_not_call_a_warning_clean(self, tmp_path: Path) -> None:
        # Arrange
        project = _indexed(tmp_path)
        (project / "docs" / "orphan.md").write_text("# Orphan\n\nNo node owns me.\n")

        # Act
        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
        doctor_step = next(s for s in result.steps if s.name == "doctor")

        # Assert
        assert "clean" not in doctor_step.summary, (
            "a run with warnings is not clean; the summary must count what passed, "
            f"not what ran — got {doctor_step.summary!r}"
        )


# ---------------------------------------------------------------------------
# The read-only lint answers about the index, not about the tree
# ---------------------------------------------------------------------------


class TestReadOnlyLintOverAStaleIndex:
    """#147's read-only form is a new way to lint a graph that is not the code."""

    def test_read_only_lint_leaves_the_index_file_byte_identical(self, tmp_path: Path) -> None:
        """The load-bearing half of #147, plus the one qualification it carries."""
        # Arrange
        project = _indexed(tmp_path)
        db = project / ".beadloom" / "beadloom.db"
        for sidecar in ("-wal", "-shm"):
            db.with_name(db.name + sidecar).unlink(missing_ok=True)
        before_bytes = db.read_bytes()
        before_files = {p.name for p in (project / ".beadloom").iterdir()}

        # Act
        run_lint(project)

        # Assert
        assert db.read_bytes() == before_bytes
        new_files = {p.name for p in (project / ".beadloom").iterdir()} - before_files
        assert all(n.endswith(("-wal", "-shm")) for n in new_files), (
            "a read-only lint may leave SQLite's own sidecars behind (measured: it does, "
            f"on a WAL index) but nothing else — got {sorted(new_files)}"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S2/.6-6: `lint --no-reindex` reports on the INDEX and never says the "
            "index predates the tree. Measured on this repo: with a real "
            "tui -> infrastructure import on disk and no reindex it printed "
            "'12 rules, 0 violations' at exit 0, silent on stdout and stderr, while plain "
            "`lint --strict` on the same tree exited 1. file_index already holds a sha256 "
            "per path, so the answer is one query away."
        ),
    )
    def test_read_only_lint_over_a_stale_index_does_not_report_clean(self, tmp_path: Path) -> None:
        # Arrange — index the clean tree, then introduce a crossing WITHOUT reindexing
        project = _indexed(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(
            _ALPHA_CROSSING, encoding="utf-8"
        )

        # Act — --format json, never a line count: piped output changes shape (#148)
        runner = CliRunner()
        invocation = runner.invoke(
            main,
            ["lint", "--no-reindex", "--strict", "--format", "json", "--project", str(project)],
        )
        payload = json.loads(invocation.stdout)
        crossings = [v for v in payload["violations"] if v["rule_type"] == "forbid_import"]
        said_stale = "stale" in (invocation.stdout + invocation.stderr).lower()

        # Assert
        assert crossings or said_stale, (
            "an index older than the working tree cannot answer for the working tree: "
            "the read-only lint must report the crossing or say the index predates the "
            f"code — got exit {invocation.exit_code}, {payload['summary']}, and no "
            "staleness signal on either stream"
        )


# ---------------------------------------------------------------------------
# docs-audit: what a green line covers
# ---------------------------------------------------------------------------


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
        _ALPHA_DOC + "\n" + sentence.format(value) + "\n", encoding="utf-8"
    )


class TestDocsAuditNamesWhatItVerifiedNothingFor:
    """``13 mention(s) fresh`` was 13 restatements of one of nine declared facts."""

    def test_a_fact_the_docs_do_state_is_verified(self, tmp_path: Path) -> None:
        """The audit does check something — this class's non-vacuity guard."""
        # Arrange — state one declared fact truthfully, reading its value from the
        # audit itself so the test does not hard-code a number that will move
        project = _indexed(tmp_path)
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
        project = _indexed(tmp_path)
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
