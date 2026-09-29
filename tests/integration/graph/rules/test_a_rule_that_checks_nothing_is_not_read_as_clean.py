"""A rule that cannot match, or an exemption that excuses everything, is not read as clean.

* ``lint`` reported ``16 rules, 0 violations`` over four rules that cannot match
  anything (a ``require`` about a node that does not exist, a ``deny`` between
  tags nobody carries, ``module_coverage`` over an absent source root, a
  cardinality ``check`` on a missing node), because BDL-061.43's ``rule_liveness``
  covered ``forbid_import`` **only**. CLOSED by ``beadloom-mr2l.48``, which
  extended liveness to all nine rule types; the assertions below are kept as
  live regression tests rather than deleted, and
  ``tests/integration/graph/rules/test_rule_liveness_all_types.py`` owns the per-type pairs.
* A ``forbid_import`` ``exempt`` entry written ``from: "*" / to: "*"`` with an
  ``until:`` date already in the past swallowed a real error-severity crossing:
  ``12 rules, 0 violations``, exit 0, and nothing in the output said a crossing
  had been suppressed. CLOSED by ``beadloom-mr2l.49``: what an exemption excused
  is counted on every run, and an ``until:`` leading with an ISO date that has
  passed is a finding while the entry still suppresses something. The
  assertions below are kept as live regression tests;
  ``tests/integration/infrastructure/exit_condition/test_exit_condition_expiry.py`` owns the
  grammar and both surfaces.

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

from typing import TYPE_CHECKING

from beadloom.graph.linter import lint as run_lint

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.linter import LintResult
from tests.support.two_component_project import (
    ALPHA_CROSSING,
    LIVE_RULE,
    indexed_project,
    rules_yml,
)


def _liveness_messages(result: LintResult) -> list[str]:
    """Every message the lint reported about a rule that could not do its job."""
    return [v.message for v in result.violations if v.rule_type == "rule_liveness"]


def _rule_names_reported(result: LintResult) -> set[str]:
    """Names of the rules the lint said anything at all about."""
    return {v.rule_name for v in result.violations}


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


class TestARuleThatCannotMatchIsReported:
    """Every rule type reports its own inertness (was: ``forbid_import`` only)."""

    def test_a_dead_import_glob_is_reported(self, tmp_path: Path) -> None:
        """The one liveness channel that exists works — this file's non-vacuity guard."""
        # Arrange
        project = indexed_project(tmp_path, rules=rules_yml(_DEAD_IMPORT_GLOB))

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
        project = indexed_project(
            tmp_path,
            rules=rules_yml(LIVE_RULE, _DEAD_REQUIRE),
            alpha_source=ALPHA_CROSSING,
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
        project = indexed_project(
            tmp_path,
            rules=rules_yml(LIVE_RULE, _DEAD_DENY),
            alpha_source=ALPHA_CROSSING,
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
        project = indexed_project(
            tmp_path,
            rules=rules_yml(LIVE_RULE, _DEAD_COVERAGE),
            alpha_source=ALPHA_CROSSING,
        )

        # Act
        result = run_lint(project)

        # Assert
        assert "dead-coverage" in _rule_names_reported(result), (
            "module_coverage over an absent source root covers no module and must say so"
        )

    def test_the_dead_rules_are_named_instead_of_inflating_the_count(self, tmp_path: Path) -> None:
        """The count still grows by three — and now says the three checked nothing.

        Before ``beadloom-mr2l.48`` the ONLY thing three inert rules changed was
        the advertised count: same violations, bigger number, no signal. The
        count is left alone (they were loaded and dispatched, so ``evaluated``
        is true) and qualified instead, at ``warn`` so a green pipeline does not
        turn red on upgrade.
        """
        # Arrange
        live = indexed_project(
            tmp_path / "live", rules=rules_yml(LIVE_RULE), alpha_source=ALPHA_CROSSING
        )
        padded = indexed_project(
            tmp_path / "padded",
            rules=rules_yml(LIVE_RULE, _DEAD_REQUIRE, _DEAD_DENY, _DEAD_COVERAGE),
            alpha_source=ALPHA_CROSSING,
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


class TestAnExemptionCanSuppressEverythingAndReadClean:
    """An exemption is visible whatever it does: counted when live, named when stale."""

    def test_an_exemption_that_suppresses_nothing_is_reported(self, tmp_path: Path) -> None:
        """BDL-061.43's dead-exemption finding works — this class's non-vacuity guard."""
        # Arrange — the rule is live (a real crossing exists) and the exemption
        # points somewhere else, so it suppresses nothing
        project = indexed_project(
            tmp_path, rules=_UNUSED_EXEMPTION_RULES, alpha_source=ALPHA_CROSSING
        )

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
        project = indexed_project(
            tmp_path, rules=_BLANKET_EXEMPTION_RULES, alpha_source=ALPHA_CROSSING
        )

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
        project = indexed_project(
            tmp_path, rules=_BLANKET_EXEMPTION_RULES, alpha_source=ALPHA_CROSSING
        )

        # Act
        result = run_lint(project)

        # Assert
        assert any("1999" in m for m in _liveness_messages(result)), (
            "an exclusion whose stated exit condition has passed must be reported"
        )
