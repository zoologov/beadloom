"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_s3_decomposition.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.graph.rule_engine import LAYER_POPULATION_RULE_TYPE
from beadloom.graph.rules import (
    SUITE_POPULATION_RULE_TYPE,
    TEST_BINDING_RULE_TYPE,
    DocAreaCoherenceRule,
    load_rules,
)
from beadloom.graph.rules.doc_area import derive_convention
from beadloom.infrastructure.db import open_db
from beadloom.services.cli import main
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path


class TestLintRecalibrationGuard:
    """Guard the domain-size-limit recalibration (200 -> 280) on the live repo."""

    def _live_findings(self, repo_root: Path) -> list[dict[str, object]]:
        """Return the live repo's lint findings as parsed JSON.

        Uses ``--no-reindex`` against the session ``self_check_snapshot`` fixture
        so the snapshot's index is NOT re-mutated (keeping order-independence
        under pytest-randomly, per the S1 lesson in conftest).
        """
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["lint", "--format", "json", "--project", str(repo_root), "--no-reindex"],
        )
        # 0 = clean, 1 = violations present (e.g. a warn under --fail-on-warn);
        # here we run neither --strict nor --fail-on-warn, so exit is 0.
        assert result.exit_code in (0, 1), result.output
        payload = json.loads(result.stdout)
        violations = payload["violations"]
        assert isinstance(violations, list)
        return violations

    def test_live_repo_has_no_violation_outside_the_declared_scenario_debt(
        self, self_check_snapshot: Path
    ) -> None:
        """The live repo lints clean apart from two findings it deliberately opted into.

        This assertion used to read "zero violations of ANY rule/severity", which
        was true by luck: every rule in ``rules.yml`` happened to be satisfied.
        BDL-061 S4 added ``scenario-coverage`` over the honest population — every
        ``feature`` node — and Beadloom's own acceptance suite covers two of them.
        The rest is real, measured debt, reported at ``warn`` so it blocks nothing.

        BDL-070 A2 added the second: ``architecture-layers`` states how much of
        its edge set it judged. The exclusion is keyed on the finding's TYPE and
        not on its rule name, which is the whole difference between an accepted
        advisory and a blind spot — a real layer violation carries
        ``rule_type: layer`` and still fails here.

        Weakening the assertion to "ignore these rules" would be the false green
        this epic exists to remove, so the debt is asserted in BOTH directions
        instead: nothing else may fire, and each of the two must still fire.

        BDL-074 C3 added two more, the same two shapes. The suite rules state
        their population (``suite_population``, an advisory keyed on its TYPE, as
        the layer population is), and ``features-have-bound-tests`` reports the
        features no test file is bound to — measured debt at ``warn``, keyed on
        rule AND type, so an exemption that went dead (``rule_liveness``) or a
        file leg that fired would still fail here.

        BDL-076 A2 added a fifth, ``doc-area-coherence`` stating that it checked
        nothing once the site's slices made ``site/`` a second source tree, and
        ``beadloom-5o48`` removed it again: the rule judges each source tree
        against its own documents and is back at ``error``. Its other direction
        is ``test_doc_area_coherence_blocks_and_judges_both_source_trees``.
        """
        findings = self._live_findings(self_check_snapshot)
        other = [
            f
            for f in findings
            if f.get("rule_name") != "scenario-coverage"
            and f.get("rule_type") not in {LAYER_POPULATION_RULE_TYPE, SUITE_POPULATION_RULE_TYPE}
            and not (
                f.get("rule_name") == "features-have-bound-tests"
                and f.get("rule_type") == TEST_BINDING_RULE_TYPE
            )
        ]
        assert other == [], other

    def test_doc_area_coherence_blocks_and_judges_both_source_trees(
        self, self_check_snapshot: Path
    ) -> None:
        """The rule is at ``error`` and checks pairs in ``src/`` AND in ``site/``.

        Silence from a rule is a pass only beside what it checked. From BDL-076 A2
        until ``beadloom-5o48`` it checked none of this repository's pairs; a
        regression to that, or to a reading that drops one tree, fails here even
        though ``lint`` would print nothing.
        """
        (rule,) = [
            r
            for r in load_rules(self_check_snapshot / ".beadloom" / "_graph" / "rules.yml")
            if r.name == "doc-area-coherence"
        ]
        assert isinstance(rule, DocAreaCoherenceRule)
        assert rule.severity == "error"

        conn = open_db(self_check_snapshot / ".beadloom" / "beadloom.db")
        try:
            convention = derive_convention(
                conn, threshold=rule.threshold, min_support=rule.min_support
            )
        finally:
            conn.close()
        trees_checked = {p.tree for p in convention.checked}
        assert sorted(trees_checked) == ["site/.vitepress/theme", "src/beadloom"], (
            convention.population()
        )
        assert convention.contradicting == (), convention.population()

    def test_each_suite_rule_states_its_population(self, self_check_snapshot: Path) -> None:
        """The other direction for the suite rules: each says what it judged, every run."""
        findings = self._live_findings(self_check_snapshot)
        stated = sorted(
            str(f["rule_name"])
            for f in findings
            if f.get("rule_type") == SUITE_POPULATION_RULE_TYPE
        )
        assert stated == [
            "domain-unit-tests-import-no-infrastructure",
            "features-have-bound-tests",
            "scenarios-live-in-their-node-folder",
            "test-files-bind-to-a-node",
        ]

    def test_the_feature_test_debt_is_reported_and_blocks_nothing(
        self, self_check_snapshot: Path
    ) -> None:
        """Silence here would mean every feature gained a bound test, or the leg died."""
        findings = self._live_findings(self_check_snapshot)
        debt = [
            f
            for f in findings
            if f.get("rule_name") == "features-have-bound-tests"
            and f.get("rule_type") == TEST_BINDING_RULE_TYPE
        ]
        assert debt, "features-have-bound-tests reported nothing — it is inert or mis-scoped"
        assert {f["severity"] for f in debt} == {"warn"}

    def test_the_layer_rules_population_is_reported_and_blocks_nothing(
        self, self_check_snapshot: Path
    ) -> None:
        """The other direction for the layer population: silence here is a regression.

        The rule judges a minority of this repository's ``depends_on`` edges —
        16 of 363 when this was written — and the number is stated rather than
        left to be inferred from a green line. A run that stopped stating it
        would read exactly like a run that had nothing to state.
        """
        findings = self._live_findings(self_check_snapshot)
        population = [f for f in findings if f.get("rule_type") == LAYER_POPULATION_RULE_TYPE]
        # One statement per layered rule: the package layers, and since BDL-076 A2
        # the site theme's Feature-Sliced layers.
        assert sorted(str(f["rule_name"]) for f in population) == [
            "architecture-layers",
            "site-fsd-layers",
        ], population
        assert {f["severity"] for f in population} == {"warn"}

    def test_the_scenario_debt_is_reported_and_blocks_nothing(
        self, self_check_snapshot: Path
    ) -> None:
        """The other direction: a rule that went silent here would be a regression.

        A count of zero would mean the suite covers every feature node (it does
        not) or that the rule stopped firing (which is what ``.48`` measured on
        four rule types at once). Either way it is a finding, not a pass.
        """
        findings = self._live_findings(self_check_snapshot)
        scenario = [f for f in findings if f.get("rule_name") == "scenario-coverage"]
        assert scenario, "scenario-coverage reported nothing — it is inert or mis-scoped"
        assert {f["severity"] for f in scenario} == {"warn"}

    def test_no_domain_size_limit_warning(
        self, self_check_snapshot: Path
    ) -> None:
        """No ``domain-size-limit`` finding — the 280 recalibration holds.

        This is the specific recalibration guard: ``lint --strict`` ignores
        warn-severity findings, so we assert directly that the warn-severity
        ``domain-size-limit`` rule produces nothing over the live graph. A
        regression (a domain crossing 280, or a botched recalibration revert)
        fails HERE rather than slipping past the green exit code.
        """
        findings = self._live_findings(self_check_snapshot)
        size_findings = [
            f for f in findings if f.get("rule_name") == "domain-size-limit"
        ]
        assert size_findings == [], size_findings


    def test_recalibrated_rule_threshold_is_180(self) -> None:
        """The repo's ``domain-size-limit`` rule is loaded as a warn at max 180.

        Pins the threshold at the rule-config level (independent of the graph
        state) so a silent revert is caught even on a small graph. Recalibrated
        290 -> 180 because the METRIC CHANGED MEANING (BDL-UX #144):
        ``max_symbols`` now counts the symbols a node OWNS rather than every
        file under its path prefix, so the observed maximum fell from 284 to
        150 and 290 could never fire again.
        """

        from beadloom.graph.rules import CardinalityRule, load_rules

        # Named from this file rather than the cwd (BDL-074 A1).
        rules_path = REPO_ROOT / ".beadloom" / "_graph" / "rules.yml"
        rules = load_rules(rules_path)
        size_rules = [
            r
            for r in rules
            if isinstance(r, CardinalityRule) and r.name == "domain-size-limit"
        ]
        assert len(size_rules) == 1
        rule = size_rules[0]
        assert rule.max_symbols == 180
        assert rule.severity == "warn"
