"""S4 verification: is the 68 honest, and can a path change buy a silent green?

BDL-061 S4 (`beadloom-mr2l.14`). `.13` shipped `scenario-coverage` and reported 68
findings on this repository — 35 behaviour-bearing nodes with no scenario and 33
scenarios our own PRD names that the suite does not contain. A large number is
exactly where a check most easily becomes decoration, so this file attacks the
number rather than the code that produces it.

Four questions, one class each.

**Is the population honest?** The rule's `for` matcher must be a *kind the graph
declares*, not a list somebody wrote by hand — a hand-picked list reports zero by
construction, which is the false green this epic exists to remove. So the matcher
is read out of the shipped `rules.yml` and checked against the nodes `services.yml`
declares, and the hand-picked shape is measured beside it so the difference is a
number rather than an argument.

**Does binding fail in both directions?** A scenario naming no bead, a `@node:`
left behind by a deleted node, two scenarios claiming one node, a `.feature` file
outside the configured location. Two honest limits are pinned here rather than
described: the bead id is never verified against a tracker, and a scenario with no
steps counts as coverage. Both are stated in `scenarios.py`; a stated limit that
nothing measures drifts into an unstated one.

**Can moving the configured location (Q3) make the rule quiet?** This is the
epic's signature failure — a path change that makes a check pass by finding
nothing. Measured through the real `lint` command and its JSON, on a project that
is not this one, because a claim proved only here is proved only here.

**Do the scenarios execute?** `scenario-coverage` checks that a `.feature` file
*exists*; the decision it enforces — an executable artifact cannot silently lie —
holds only while the artifact runs. The shipped suite is run in a subprocess and
its per-test outcomes are read from a JUnit report, and a step the suite no longer
implements is shown to redden that run.

The `.39` half — the measured symlink-capability probe that replaced six
`skipif(win32)` marks, and the ledger that refuses an unjudged platform skip — is
verified in the last class. TESTS MUST BITE applies to a ledger too: its failing
branch had no test, only its scanner did.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner

from beadloom.graph.rules import (
    BEAD_NOT_VERIFIED,
    LIVENESS_RULE_TYPE,
    NodeMatcher,
    ScenarioCoverageRule,
    evaluate_scenario_coverage_rules,
    load_rules,
)
from beadloom.graph.scenarios import load_suite
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules import Violation

#: This repository, so the shipped configuration is read rather than restated.
REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = REPO_ROOT / ".beadloom" / "_graph"

SCENARIO_COVERAGE = "scenario_coverage"


# --------------------------------------------------------------------------- #
# Factories
# --------------------------------------------------------------------------- #


def _db(tmp_path: Path, nodes: tuple[tuple[str, str], ...]) -> sqlite3.Connection:
    """An index holding exactly *nodes*, as ``(ref_id, kind)`` pairs."""
    conn = open_db(tmp_path / "graph.db")
    create_schema(conn)
    for ref_id, kind in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            (ref_id, kind, ""),
        )
    conn.commit()
    return conn


def _feature_file(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rule(**kwargs: object) -> ScenarioCoverageRule:
    defaults: dict[str, object] = {
        "name": "scenario-coverage",
        "description": "behaviour carries an executable claim",
        "for_matcher": NodeMatcher(kind="feature"),
    }
    defaults.update(kwargs)
    return ScenarioCoverageRule(**defaults)  # type: ignore[arg-type]


def _messages(violations: list[Violation]) -> str:
    return "\n".join(f"{v.rule_type} {v.from_ref_id} {v.message}" for v in violations)


def _shipped_scenario_coverage_rule() -> ScenarioCoverageRule:
    """The rule THIS repository runs, read from the file it is configured in."""
    rules = load_rules(GRAPH_DIR / "rules.yml")
    matching = [r for r in rules if isinstance(r, ScenarioCoverageRule)]
    assert len(matching) == 1, (
        "expected exactly one scenario_coverage rule in the shipped rules.yml; "
        f"found {len(matching)}"
    )
    return matching[0]


def _declared_nodes() -> list[tuple[str, str]]:
    """Every node `services.yml` declares, as ``(ref_id, kind)``.

    Read from the tracked YAML rather than from `.beadloom/beadloom.db`: the index
    is gitignored, so a check that read it would ERROR in a clean room instead of
    measuring anything, and a shared tree may be reindexed mid-run by another
    agent.
    """
    data = yaml.safe_load((GRAPH_DIR / "services.yml").read_text(encoding="utf-8"))
    return [(str(n["ref_id"]), str(n["kind"])) for n in data["nodes"]]


# --------------------------------------------------------------------------- #
# Is the population honest?
# --------------------------------------------------------------------------- #


class TestThePopulationIsHonest:
    """35 uncovered nodes is only a finding if the denominator was not chosen to fit."""

    def test_the_population_is_a_graph_kind_and_not_a_hand_picked_list(self) -> None:
        """The shipped matcher selects by KIND, with nothing carved out of it.

        A `ref_id` matcher checks one node and an `exclude` list checks whatever is
        left after the awkward ones are removed. Either reports a small number
        honestly-looking, and neither is a statement about the system.
        """
        matcher = _shipped_scenario_coverage_rule().for_matcher

        assert matcher.kind == "feature", matcher
        assert matcher.ref_id is None, (
            "the population is pinned to a single node — that is one check wearing "
            "the name of a coverage rule"
        )
        assert not matcher.exclude, (
            f"nodes are carved out of the population: {matcher.exclude}. An "
            "exclusion here is invisible in the finding count; declare the node "
            "non_behavioural with a reason instead, where a dead declaration is "
            "itself reported"
        )

    def test_every_feature_node_the_graph_declares_is_in_the_population(self) -> None:
        """The matcher's reach is measured against the file that declares the nodes.

        Not "the matcher looks right": the two files are compared, so moving a node
        out of the population requires changing its KIND in `services.yml`, which is
        a visible architectural claim, rather than editing a list in `rules.yml`.
        """
        matcher = _shipped_scenario_coverage_rule().for_matcher
        declared = _declared_nodes()
        features = {ref_id for ref_id, kind in declared if kind == "feature"}
        selected = {ref_id for ref_id, kind in declared if matcher.matches(ref_id, kind)}

        assert selected == features
        assert len(features) >= 30, (
            f"only {len(features)} feature nodes are declared — the population this "
            "rule reports a fraction OF has collapsed, and a small denominator makes "
            "any coverage claim look better than it is"
        )

    def test_a_hand_picked_population_would_report_almost_nothing(self, tmp_path: Path) -> None:
        """Why the row above is worth asserting, stated as a measurement.

        The same graph and the same suite, checked by a `ref_id` matcher instead of a
        `kind` one: the finding count falls to zero while every uncovered node stays
        uncovered. That is the shape a green count buys, and it costs one line of
        configuration.
        """
        conn = _db(
            tmp_path,
            (("billing", "feature"), ("shipping", "feature"), ("invoicing", "feature")),
        )
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )
        try:
            honest = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
            picked = evaluate_scenario_coverage_rules(
                conn,
                [_rule(for_matcher=NodeMatcher(ref_id="billing"))],
                project_root=tmp_path,
            )
        finally:
            conn.close()

        assert sorted(str(v.from_ref_id) for v in honest) == ["invoicing", "shipping"]
        assert [v.from_ref_id for v in picked] == []

    def test_a_node_outside_the_population_is_not_reported_and_is_not_counted_covered(
        self, tmp_path: Path
    ) -> None:
        """A kind the rule does not measure must not be silently credited either.

        `component` nodes (24 of them here) are outside the population by the
        architecture model's own definition — plumbing rather than a capability. The
        check is that they are ABSENT from the verdict, not that they pass it: a rule
        that counted them clean would report a coverage figure it never measured.
        """
        conn = _db(tmp_path, (("billing", "feature"), ("db", "component")))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert violations == [], _messages(violations)


# --------------------------------------------------------------------------- #
# Binding, both ways — including the two limits that are only stated
# --------------------------------------------------------------------------- #


class TestBindingFailsInBothDirections:
    def test_a_scenario_naming_a_bead_that_does_not_exist_is_accepted_and_says_so(
        self, tmp_path: Path
    ) -> None:
        """The limit `scenarios.py` states, pinned so it cannot become unstated.

        The rule checks that a scenario NAMES a bead, never that the bead exists —
        reading the tracker from the rule engine would make a domain depend on the
        application layer. A reader who assumed otherwise would treat a green as
        evidence the work item is real, so the limit travels on the finding.
        """
        conn = _db(tmp_path, (("billing", "feature"), ("shipping", "feature")))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:no-such-bead-anywhere-42\n"
            "Feature: billing\n"
            "  Scenario: a card is charged\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert [v.from_ref_id for v in violations] == ["shipping"], _messages(violations)

    def test_the_unbound_scenario_finding_carries_the_limit_on_its_own_face(
        self, tmp_path: Path
    ) -> None:
        """The limit is not only in a docstring; it travels with the finding.

        A reader who meets `scenario X names no bead` and fixes it by adding any tag
        at all has to be told that adding a tag is all that was checked — otherwise
        the next reader takes a clean run as evidence that every scenario points at
        a live work item.
        """
        conn = _db(tmp_path, (("billing", "feature"),))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing\nFeature: billing\n  Scenario: a card is charged\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert [v.file_path for v in violations] == [
            "tests/acceptance/features/billing.feature"
        ], _messages(violations)
        assert "names no bead" in violations[0].message
        assert BEAD_NOT_VERIFIED in str(violations[0].remediation)

    def test_a_node_tag_left_behind_by_a_deleted_node_is_reported(self, tmp_path: Path) -> None:
        """The realistic drift: the node is removed and the tag stays.

        Both halves are asserted, because only reporting the dangling tag would let
        the scenario go on looking like coverage of something.
        """
        conn = _db(tmp_path, (("billing", "feature"),))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/legacy.feature",
            "@node:invoicing @bead:proj-1\nFeature: invoicing\n  Scenario: an invoice is issued\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        text = _messages(violations)
        assert "`@node:invoicing`" in text, text
        assert "not a node in the graph" in text, text
        assert "no scenario binds to `billing`" in text, text

    def test_a_scenario_whose_only_binding_is_unknown_covers_no_node(self, tmp_path: Path) -> None:
        """A dangling tag must not spend its coverage on a node with a similar name."""
        conn = _db(tmp_path, (("billing", "feature"),))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/legacy.feature",
            "@node:billing-v2 @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        uncovered = [v.from_ref_id for v in violations if v.from_ref_id == "billing"]
        assert uncovered == ["billing"], _messages(violations)

    def test_two_scenarios_claiming_one_node_leave_it_covered_exactly_once(
        self, tmp_path: Path
    ) -> None:
        """Duplicate coverage is allowed and must not be double-counted either way.

        Two scenarios binding to one node is ordinary — a capability with more than
        one acceptance criterion. What would be wrong is a second finding, or a
        second entry in the covered set that hides a node behind an arithmetic
        coincidence.
        """
        conn = _db(tmp_path, (("billing", "feature"), ("shipping", "feature")))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:proj-1\n"
            "Feature: billing\n"
            "  Scenario: a card is charged\n"
            "  Scenario: a card is refused\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert [v.from_ref_id for v in violations] == ["shipping"], _messages(violations)

    def test_a_feature_file_outside_the_configured_location_covers_nothing(
        self, tmp_path: Path
    ) -> None:
        """A scenario the runner never sees is prose, and the node is still reported.

        The file exists, it is valid Gherkin and it names the node. It is one
        directory away from the configured suite, so nothing executes it — and the
        rule's verdict on the node it claims to cover does not change.
        """
        conn = _db(tmp_path, (("billing", "feature"),))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/kept.feature",
            "@node:kept @bead:proj-1\nFeature: kept\n  Scenario: something else\n",
        )
        _feature_file(
            tmp_path,
            "docs/drafts/billing.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert "no scenario binds to `billing`" in _messages(violations)

    def test_a_scenario_with_no_steps_still_counts_as_coverage(self, tmp_path: Path) -> None:
        """The second stated limit, measured: only STRUCTURE is parsed.

        A scenario that binds correctly and asserts nothing is invisible to this
        rule — `scenarios.py` says so, and the mutation duty is what covers it. The
        row exists so the sentence in the docstring is a measurement: if the parser
        ever started requiring a step, the limit would have changed and the guide
        that repeats it would be wrong.
        """
        conn = _db(tmp_path, (("billing", "feature"),))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )
        suite = load_suite(tmp_path, "tests/acceptance/features/**/*.feature")
        try:
            violations = evaluate_scenario_coverage_rules(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert [s.name for s in suite.scenarios] == ["a card is charged"]
        assert violations == [], _messages(violations)


# --------------------------------------------------------------------------- #
# Q3: the configurable location
# --------------------------------------------------------------------------- #


class TestTheConfiguredLocationCannotBuyASilentGreen:
    """A path change that makes a check pass by finding nothing is the failure."""

    def test_the_rule_follows_the_location_to_a_directory_that_is_not_the_default(
        self, tmp_path: Path
    ) -> None:
        conn = _db(tmp_path, (("billing", "feature"), ("shipping", "feature")))
        _feature_file(
            tmp_path,
            "qa/gherkin/billing/charge.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn,
                [_rule(features="qa/gherkin/**/*.feature")],
                project_root=tmp_path,
            )
        finally:
            conn.close()

        assert [v.from_ref_id for v in violations] == ["shipping"], _messages(violations)

    def test_a_location_holding_no_feature_file_reports_the_glob_not_a_clean_run(
        self, tmp_path: Path
    ) -> None:
        """The suite still exists; the configuration no longer points at it.

        Two assertions, and the second is the one that matters: the run is not
        SILENT. The coverage leg is deliberately stood down — one configuration
        error printing as N architecture findings buries the finding that fixes it —
        so the dead glob has to be reported in its place, by name, or the whole rule
        has gone quiet with nothing said.
        """
        conn = _db(tmp_path, (("billing", "feature"), ("shipping", "feature")))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn,
                [_rule(features="qa/gherkin/**/*.feature")],
                project_root=tmp_path,
            )
        finally:
            conn.close()

        assert violations, "the rule went completely silent when its glob was moved"
        liveness = [v for v in violations if v.rule_type == LIVENESS_RULE_TYPE]
        assert len(liveness) == 1, _messages(violations)
        assert "qa/gherkin/**/*.feature" in liveness[0].message
        assert "an absent suite is not a covered one" in str(liveness[0].remediation)

    def test_a_glob_that_stops_recursing_still_reports_what_it_can_no_longer_see(
        self, tmp_path: Path
    ) -> None:
        """The subtler path change: the glob still matches, just not everything.

        `*.feature` instead of `**/*.feature` keeps the glob alive — so no liveness
        finding fires — while every nested scenario becomes invisible. The rule is
        honest anyway, because the nodes those scenarios covered come back as
        uncovered rather than as nothing at all. That is the property that makes a
        partial path change loud instead of silent.
        """
        conn = _db(tmp_path, (("billing", "feature"), ("shipping", "feature")))
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )
        _feature_file(
            tmp_path,
            "tests/acceptance/features/nested/shipping.feature",
            "@node:shipping @bead:proj-2\nFeature: shipping\n  Scenario: a parcel ships\n",
        )
        try:
            violations = evaluate_scenario_coverage_rules(
                conn,
                [_rule(features="tests/acceptance/features/*.feature")],
                project_root=tmp_path,
            )
        finally:
            conn.close()

        assert [v.rule_type for v in violations] == [SCENARIO_COVERAGE]
        assert violations[0].from_ref_id == "shipping"
        assert "in 1 file" in violations[0].message, violations[0].message

    def test_moving_the_location_through_the_real_lint_command_is_not_a_clean_run(
        self, tmp_path: Path
    ) -> None:
        """The whole command, on a project that is not this one, read as JSON.

        The unit rows above prove the rule; this proves the PRODUCT — that the
        liveness finding survives the reindex, the formatter and the summary, and
        that `violations_count` does not fall to zero when the acceptance suite is
        configured out of reach. Exit codes and JSON, never line counts.
        """
        project = tmp_path / "orders-web"
        (project / ".beadloom" / "_graph").mkdir(parents=True)
        (project / ".beadloom" / "_graph" / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: billing\n"
            "    kind: feature\n"
            "    summary: Billing\n"
            "  - ref_id: shipping\n"
            "    kind: feature\n"
            "    summary: Shipping\n"
            "edges: []\n",
            encoding="utf-8",
        )
        _feature_file(
            project,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )

        def _write_rules(glob: str) -> None:
            (project / ".beadloom" / "_graph" / "rules.yml").write_text(
                "version: 3\n"
                "rules:\n"
                "  - name: scenario-coverage\n"
                '    description: "behaviour carries an executable claim"\n'
                "    severity: warn\n"
                "    scenario_coverage:\n"
                "      for: { kind: feature }\n"
                f'      features: "{glob}"\n',
                encoding="utf-8",
            )

        def _lint() -> dict[str, object]:
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "--format", "json", "--project", str(project)])
            assert result.exit_code == 0, result.output
            return json.loads(result.output)  # type: ignore[no-any-return]

        _write_rules("tests/acceptance/features/**/*.feature")
        before = _lint()

        _write_rules("qa/gherkin/**/*.feature")
        after = _lint()

        summary_before = before["summary"]
        summary_after = after["summary"]
        assert isinstance(summary_before, dict)
        assert isinstance(summary_after, dict)
        assert summary_before["violations_count"] == 1, before["violations"]
        assert summary_after["violations_count"] >= 1, (
            "moving the acceptance suite out of reach produced a clean lint run — "
            "the check now passes by finding nothing, which is the failure this "
            "epic is named after"
        )
        violations_after = after["violations"]
        assert isinstance(violations_after, list)
        kinds_after = [violation["rule_type"] for violation in violations_after]
        assert LIVENESS_RULE_TYPE in kinds_after, violations_after


# --------------------------------------------------------------------------- #
# The scenarios execute, and a broken one reddens
# --------------------------------------------------------------------------- #


def _run_pytest(args: list[str], *, cwd: Path, report: Path) -> tuple[int, list[tuple[str, str]]]:
    """Run pytest in a subprocess and read per-test OUTCOMES from its JUnit report.

    Outcomes rather than the terminal summary: a count scraped from stdout cannot
    tell a scenario that ran from one that was collected and skipped, and telling
    those apart is the entire question.
    """
    completed = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            *args,
            "-p",
            "no:cacheprovider",
            "--junitxml",
            str(report),
            "-q",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if not report.exists():  # pragma: no cover - only on a collection crash
        pytest.fail(f"pytest produced no report:\n{completed.stdout}\n{completed.stderr}")
    outcomes: list[tuple[str, str]] = []
    # S314: the input is the JUnit report pytest just wrote in a temporary
    # directory, not untrusted data.
    for case in ET.parse(report).getroot().iter("testcase"):  # noqa: S314
        name = str(case.get("name"))
        children = {child.tag for child in case}
        if "skipped" in children:
            outcomes.append((name, "skipped"))
        elif children & {"failure", "error"}:
            detail = " ".join(
                str(child.get("message", "")) for child in case if child.tag != "skipped"
            )
            outcomes.append((name, f"failed: {detail}"))
        else:
            outcomes.append((name, "passed"))
    return completed.returncode, outcomes


class TestTheScenariosExecute:
    """A `.feature` file nothing runs is prose, and the rule would be checking text."""

    def test_the_shipped_acceptance_suite_runs_every_scenario_and_skips_none(
        self, tmp_path: Path
    ) -> None:
        """Seven scenarios, and each one RAN.

        `.13` reports seven executable scenarios. Collected-and-skipped would give
        the same reassuring green with nothing executed, so the outcome of every row
        is read individually and a skip is a failure of this test.
        """
        code, outcomes = _run_pytest(
            ["tests/acceptance"], cwd=REPO_ROOT, report=tmp_path / "report.xml"
        )

        assert code == 0, outcomes
        assert [name for name, outcome in outcomes if outcome == "skipped"] == []
        passed = [name for name, outcome in outcomes if outcome == "passed"]
        assert len(passed) == 7, outcomes

    def test_a_step_the_suite_no_longer_implements_reddens_the_run(self, tmp_path: Path) -> None:
        """Sabotage as a test: the runner must adjudicate the scenario, not host it.

        The shipped suite is copied out, one step implementation is renamed so the
        Gherkin no longer matches it, and the copy is run. If a broken binding still
        produced a green, `scenario-coverage` would be counting files that execute
        nothing — the false green the rule exists to remove, one level down.
        """
        suite = tmp_path / "acceptance"
        shutil.copytree(
            REPO_ROOT / "tests" / "acceptance",
            suite,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        steps = suite / "steps" / "test_scenario_coverage_steps.py"
        source = steps.read_text(encoding="utf-8")
        broken = source.replace(
            "the scenario-coverage rule is evaluated",
            "the scenario-coverage rule is evaluated somehow",
        )
        assert broken != source, "the anchor for the sabotage is gone"
        steps.write_text(broken, encoding="utf-8")

        code, outcomes = _run_pytest([str(suite)], cwd=tmp_path, report=tmp_path / "report.xml")

        assert code != 0, outcomes
        failures = [outcome for _, outcome in outcomes if outcome.startswith("failed")]
        assert failures, outcomes
        assert any("StepDefinitionNotFound" in failure for failure in failures), (
            "the run went red, but not because the step binding broke — a sabotage "
            f"that fails for the wrong reason proves nothing: {failures}"
        )
        survivors = [name for name, outcome in outcomes if outcome == "passed"]
        assert len(survivors) < 7, (
            "every scenario still passed while a step was missing, which would mean "
            f"the Gherkin is not what drives the run: {outcomes}"
        )


# --------------------------------------------------------------------------- #
# `.39`: the capability probe and the ledger
# --------------------------------------------------------------------------- #


class TestTheProbeAndTheLedger:
    """The measured skip must not be able to answer "no capability" everywhere."""

    def test_the_probe_agrees_with_the_directory_the_guard_rows_actually_use(
        self, tmp_path: Path
    ) -> None:
        """The probe measures a temp dir; the six rows link inside `tmp_path`.

        If those two ever sit on different filesystems — a `TMPDIR` on a mount
        without symlink support, a `--basetemp` elsewhere — the probe answers "no
        capability" for a volume the rows never touch and six live tests skip on a
        measurement taken in the wrong place. Two-sided on purpose: where the
        fixture CAN link the probe must say so, and where it cannot the probe must
        not claim otherwise. Neither direction is satisfiable by a probe that always
        answers the same thing.
        """
        from tests.symlink_capability import SYMLINK_CAPABILITY

        target = tmp_path / "target.txt"
        target.write_text("x\n", encoding="utf-8")
        link = tmp_path / "link.txt"
        try:
            link.symlink_to(target)
            fixture_can_link = link.resolve() == target.resolve()
        except (OSError, NotImplementedError):
            fixture_can_link = False

        assert SYMLINK_CAPABILITY.files == fixture_can_link, (
            "the capability probe and the fixture directory the guard rows use "
            f"disagree: probe={SYMLINK_CAPABILITY.files!r}, tmp_path={fixture_can_link!r}, "
            f"refusal={SYMLINK_CAPABILITY.refusal!r}"
        )

    def test_the_ledger_reports_a_platform_skip_nobody_judged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Add one, and it reddens — the ledger's FAILING branch, which had no test.

        Its scanner is covered; its verdict was not, and a ledger whose failure is
        never executed is exactly the "green count is not a checked count" it was
        written to prevent. The scan is redirected at a throwaway tree instead of
        editing a real test file, so the row is repeatable and leaves nothing behind.
        """
        from tests import test_windows_dimension as ledger

        (tmp_path / "test_new_thing.py").write_text(
            "import pytest, sys\n"
            "class TestSomething:\n"
            '    @pytest.mark.skipif(sys.platform == "win32", reason="not worth it")\n'
            "    def test_it(self):\n"
            "        pass\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(ledger, "TESTS_DIR", tmp_path)
        monkeypatch.setattr(ledger, "JUDGED_WINDOWS_SKIPS", {})

        with pytest.raises(AssertionError) as caught:
            ledger.test_no_win32_skip_is_unjudged()

        assert "test_new_thing.py::TestSomething::test_it" in str(caught.value)
        assert "no judgement" in str(caught.value)

    def test_the_ledger_reports_an_entry_whose_skip_has_gone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The other direction: a judgement kept after the skip it excused was deleted.

        A stale entry is how a ledger stops describing the suite — it accumulates
        verdicts on rows nobody can find, and the next reader trusts the list rather
        than the code.
        """
        from tests import test_windows_dimension as ledger

        monkeypatch.setattr(ledger, "TESTS_DIR", tmp_path)
        monkeypatch.setattr(
            ledger,
            "JUDGED_WINDOWS_SKIPS",
            {"test_gone.py::<module>": ledger.WindowsSkip(facility="f", why="w")},
        )

        with pytest.raises(AssertionError) as caught:
            ledger.test_no_win32_skip_is_unjudged()

        assert "test_gone.py::<module>" in str(caught.value)
        assert "no longer present" in str(caught.value)


# --------------------------------------------------------------------------- #
# The reference leg's widest surface
# --------------------------------------------------------------------------- #


class TestTheReferenceLegsWidestSurface:
    """A line beginning with a scenario keyword after markdown stripping.

    `.13` named this the widest surface in the slice, and it is: the suite half is
    bounded by Gherkin's grammar, while this half reads arbitrary prose. Every row
    below is one shape a real planning document contains. Two of them are
    findings — asserted as they SHOULD behave and marked `xfail(strict=True)`, so
    the runner adjudicates the prediction and a fix fails the suite instead of
    passing silently.
    """

    @pytest.mark.parametrize(
        ("label", "text", "expected"),
        [
            (
                "a checkbox bullet",
                "- [ ] `Scenario: an order is placed`\n",
                ["an order is placed"],
            ),
            (
                "a completed bullet",
                "- [x] `Scenario: an order is placed`\n",
                ["an order is placed"],
            ),
            ("a nested bullet", "  - `Scenario: an order is placed`\n", ["an order is placed"]),
            ("a blockquote", "> Scenario: an order is placed\n", ["an order is placed"]),
            ("bold emphasis", "**Scenario: an order is placed**\n", ["an order is placed"]),
            (
                "an outline",
                "- `Scenario Outline: an order is placed`\n",
                ["an order is placed"],
            ),
            ("the russian keyword", "- `Сценарий: заказ размещён`\n", ["заказ размещён"]),
            ("a keyword mid-word", "MyScenario: not a reference\n", []),
            ("a bare colon", "Scenario:\n", []),
            ("a table row", "| Scenario: an order is placed | done |\n", []),
            ("an html comment", "<!-- Scenario: an order is placed -->\n", []),
            (
                "a backtick fence",
                "```gherkin\nScenario: an order is placed\n```\n",
                [],
            ),
            ("a tilde fence", "~~~gherkin\nScenario: an order is placed\n~~~\n", []),
            (
                "prose mentioning one mid-sentence",
                "proved by one scenario: the inert one\n",
                [],
            ),
        ],
    )
    def test_the_shapes_a_planning_document_really_contains(
        self, label: str, text: str, expected: list[str]
    ) -> None:
        from beadloom.graph.scenarios import parse_scenario_references

        found = [reference.name for reference in parse_scenario_references(text, path="PRD.md")]

        assert found == expected, label

    def test_the_shipped_reference_globs_read_more_than_the_document_that_added_them(
        self,
    ) -> None:
        """The leg's own population, so it cannot quietly become one file.

        33 missing references is a statement about intent only if the globs still
        reach every document that states intent. Narrowing `references:` to the one
        PRD that uses the convention would leave the number unchanged while making
        the check unable to find a new document — the population failure of the
        coverage leg, in the leg nobody would look at.
        """
        rule = _shipped_scenario_coverage_rule()
        matched = [
            path for glob in rule.references for path in REPO_ROOT.glob(glob) if path.is_file()
        ]

        assert rule.references, "the reference leg is switched off entirely"
        assert len(matched) >= 20, (
            f"the reference globs {rule.references} reach only {len(matched)} "
            "documents — the leg is checking a hand-picked file rather than the "
            "space where intent is written"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-061.14-1: `Example:` is a Gherkin scenario keyword, so a "
            "bare prose line starting with it is read as a claim that a scenario "
            "exists. Measured: `Example: a nested import inside a function` yields "
            "the reference 'a nested import inside a function'. Zero false "
            "positives on this repo today (all 33 come from `Scenario:` lines) and "
            "a large one for any adopter, because `Example:` opens an ordinary "
            "explanatory paragraph. Every real reference in this project is either "
            "backticked or bulleted, so that is the discriminator the keyword needs."
        ),
    )
    def test_a_prose_paragraph_opening_with_example_is_not_a_reference(self) -> None:
        from beadloom.graph.scenarios import parse_scenario_references

        text = "Example: a nested import inside a function is still an import.\n"

        assert parse_scenario_references(text, path="PRD.md") == ()

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-061.14-2: an indented code block is read as a reference "
            "while a fenced one is not. Markdown has two code-block syntaxes and "
            "the parser knows one. The docstring's own reason — a form is not a "
            "claim that a scenario exists — applies identically to four-space "
            "indentation, and `templates.md` is exactly the kind of document that "
            "carries a Gherkin form."
        ),
    )
    def test_an_indented_code_block_is_a_form_and_not_a_reference(self) -> None:
        from beadloom.graph.scenarios import parse_scenario_references

        text = "The shape to write:\n\n    Scenario: an order is placed\n        Given a cart\n"

        assert parse_scenario_references(text, path="PRD.md") == ()

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-061.14-3: a document the reference leg cannot DECODE "
            "contributes zero references and nothing is reported — not a dead "
            "glob (the glob matched), not an unreadable file. `load_suite` reports "
            "an undecodable `.feature`; `load_references` swallows the same failure "
            "one function away. Measured: a cp1251 PRD naming one scenario yields "
            "`refs=() dead=()`, so the rule states the document's intent is fully "
            "met. That is BDL-061 CONTEXT's 'absence is not evidence' — nothing an "
            "editor's encoding does may make a check quieter."
        ),
    )
    def test_a_document_that_cannot_be_decoded_is_reported_rather_than_read_as_empty(
        self, tmp_path: Path
    ) -> None:
        from beadloom.graph.scenarios import load_references

        document = tmp_path / "docs" / "PRD.md"
        document.parent.mkdir(parents=True)
        document.write_bytes("- `Сценарий: заказ размещён`\n".encode("cp1251"))

        references, dead = load_references(tmp_path, ["docs/**/PRD.md"])

        assert (references, dead) != ((), ()), (
            "an undecodable document read as a document with no intent in it"
        )


# --------------------------------------------------------------------------- #
# Filesystem and syntax edges the globs really meet
# --------------------------------------------------------------------------- #


class TestTheReadersAtTheirEdges:
    """Input a real tree produces and a hand-written fixture usually does not."""

    def test_a_directory_named_like_a_feature_file_is_not_a_scenario_file(
        self, tmp_path: Path
    ) -> None:
        """A glob matches names, not files. A directory is neither read nor counted.

        It must not enter `files` either: `files` is the denominator every
        statement about the suite is a fraction of, and a directory in it would
        inflate "N scenarios in M files" with something that holds no scenario.
        """
        (tmp_path / "tests" / "acceptance" / "features" / "archive.feature").mkdir(parents=True)
        _feature_file(
            tmp_path,
            "tests/acceptance/features/billing.feature",
            "@node:billing @bead:proj-1\nFeature: billing\n  Scenario: a card is charged\n",
        )

        suite = load_suite(tmp_path, "tests/acceptance/features/**/*.feature")

        assert suite.files == ("tests/acceptance/features/billing.feature",)
        assert suite.unreadable == ()
        assert suite.empty_files == ()

    def test_a_reference_glob_that_matches_only_a_directory_reports_itself(
        self, tmp_path: Path
    ) -> None:
        """Liveness is about documents READ, not about names matched.

        A glob whose only match is a directory read nothing, so no referenced
        scenario was checked by it — and a leg that checked nothing must say so
        rather than return the empty tuple that a clean document would also
        return. Measured because the two readings are one `is_file()` apart: the
        flag is set after the check, not before it.
        """
        from beadloom.graph.scenarios import load_references

        (tmp_path / "docs" / "PRD.md").mkdir(parents=True)

        references, dead = load_references(tmp_path, ["docs/**/PRD.md"])

        assert references == ()
        assert dead == ("docs/**/PRD.md",)

    def test_a_keyword_without_its_colon_is_prose(self) -> None:
        """`Scenario Outline of the release` is a sentence, not a claim.

        Both spellings are tried in turn, longest first, and neither may accept a
        line that never had a colon: a reference the author did not make would be
        reported as a scenario they must write.
        """
        from beadloom.graph.scenarios import parse_scenario_references

        text = "Scenario Outline of the release is discussed below.\n"

        assert parse_scenario_references(text, path="PRD.md") == ()

    def test_a_fence_ends_only_on_its_own_marker(self) -> None:
        """A tilde fence is not closed by backticks, and what is inside stays a form.

        Markdown allows either delimiter, and a reader that closed a block on the
        wrong one would start treating the rest of a document's forms as claims —
        the noisiest possible failure, in the document that carries the template.
        """
        from beadloom.graph.scenarios import parse_scenario_references

        text = (
            "~~~gherkin\n"
            "```\n"
            "Scenario: an order is placed\n"
            "~~~\n"
            "- `Scenario: an order is refunded`\n"
        )

        found = [r.name for r in parse_scenario_references(text, path="PRD.md")]

        assert found == ["an order is refunded"]
