"""A mutation check whose population is empty must not read as one that passed.

BDL-068 S3.3, over `beadloom-0mdo.22`.

`mutation_scope` has two halves and until this bead they never met. `scope`
answers **could this declared target run a single mutant** and reports three
findings when it could not. `score` answers **what did a run over it produce**
and reads a runner's counters. The command that prints the NUMBER only ever
called the second one, so a declared target that is not on disk, or is outside
the configured source paths, or holds no source file at all could be "measured"
at 100 percent and exit 0 — measured on the shipped console script before this
bead, all three of them.

That is the phantom gate. It is the same equation as BDL-UX #172/#173, where a
green count covered a surface nobody had measured, and it is why this project
could ship a mutation duty for two major releases with nothing able to answer
it: a check with no population and a check that passed print the same thing.

Two further empty populations are covered here. A run that produced ten mutants
and classified none of them stated `Score: none — see the findings below.` with
no findings below and exit 0. And a negative counter — `killed: -5` — produced
`125.0% of -4 scored mutants`, which is a number, and a number is what gets
pasted into a bead comment.

Every arrangement here is real files on disk against the real command. Nothing
is doubled: a report that passes against a double proves the double.
"""

from __future__ import annotations

import json
from pathlib import Path as _Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner, Result

from beadloom.application.mutation_scope import (
    MUTATION_COUNTERS_MISSING,
    MUTATION_OUTSIDE_SOURCE,
    MUTATION_RUN_ZERO_MUTANTS,
    MUTATION_TARGET_MISSING,
    MUTATION_TARGET_UNMEASURED,
    MUTATION_ZERO_MUTANTS,
    MutationRun,
    MutationScopeFinding,
    check_mutation_scope,
    describe_room,
    read_run_counters,
    report_mutation_score,
)
from beadloom.services.cli import main

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path


#: This repository, whose own declaration must survive the join unchanged.
REPO_ROOT = _Path(__file__).resolve().parents[1]


def _project(root: Path, *targets: str) -> Path:
    """A project declaring TARGETS, with nothing placed on disk for them.

    The declaration and the disk are deliberately separate here: every test in
    this file is about a target whose declaration promises something the disk
    does not deliver.
    """
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
    )
    declared = "".join(f"  - {t}\n" for t in targets)
    (root / ".beadloom" / "flow.yml").write_text(
        f"mutation:\n  targets:\n{declared}", encoding="utf-8"
    )
    return root


def _place_source(root: Path, target: str) -> None:
    """Give a declared target a Python file, so the scope check is satisfied."""
    directory = root / target
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "unit.py").write_text("VALUE = 1\n", encoding="utf-8")


def _place_without_source(root: Path, target: str) -> None:
    """Give a declared target a directory holding nothing a runner can mutate."""
    directory = root / target
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "NOTES.md").write_text("no code here\n", encoding="utf-8")


def _place_nothing(root: Path, target: str) -> None:
    """Leave the target off the disk entirely — the declaration is all there is."""


def _stats(root: Path, **values: int) -> Path:
    path = root / "stats.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def _run(root: Path, *, covered: tuple[str, ...], **values: int) -> MutationRun:
    return MutationRun(
        tool="a runner",
        room=describe_room(),
        covered=covered,
        counters=read_run_counters(_stats(root, **values)),
    )


def _invoke(root: Path, *args: str) -> Result:
    return CliRunner().invoke(main, ["mutation", "--project", str(root), *args])


def _checks(findings: Iterable[MutationScopeFinding]) -> set[str]:
    return {f.check for f in findings}


class TestATargetThatCannotProduceAMutantIsNeverScoredAsMeasured:
    """The three states `scope` already knows about, now reaching the number.

    Each of these scored 100 percent and exited 0 before this bead, measured on
    the shipped console script over a temporary project.
    """

    def test_a_declared_target_not_on_disk_is_reported(self, tmp_path: Path) -> None:
        # Arrange: the declaration names a path the code moved away from.
        project = _project(tmp_path, "src/gone/")
        run = _run(project, covered=("src/gone/",), killed=10, survived=0)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert MUTATION_TARGET_MISSING in _checks(report.findings)

    def test_a_declared_target_outside_the_source_paths_is_reported(
        self, tmp_path: Path
    ) -> None:
        # Arrange: real code, mutated, and outside everything this project indexes.
        project = _project(tmp_path, "vendor/pkg/")
        _place_source(project, "vendor/pkg/")
        run = _run(project, covered=("vendor/pkg/",), killed=10, survived=0)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert MUTATION_OUTSIDE_SOURCE in _checks(report.findings)

    def test_a_declared_target_inside_them_holding_no_source_is_reported(
        self, tmp_path: Path
    ) -> None:
        """The bead's own sentence: inside the paths, and yielding nothing."""
        # Arrange
        project = _project(tmp_path, "src/empty/")
        _place_without_source(project, "src/empty/")
        run = _run(project, covered=("src/empty/",), killed=10, survived=0)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert MUTATION_ZERO_MUTANTS in _checks(report.findings)

    def test_a_perfect_score_over_a_target_that_is_not_there_is_still_a_finding(
        self, tmp_path: Path
    ) -> None:
        """The counters are believed; the claim that they cover the scope is not."""
        # Arrange
        project = _project(tmp_path, "src/gone/")
        run = _run(project, covered=("src/gone/",), killed=10, survived=0)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert report.score == pytest.approx(1.0)
        assert report.findings != ()

    def test_a_healthy_target_reports_no_scope_finding(self, tmp_path: Path) -> None:
        """The guard against a check that fires on everything."""
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        run = _run(project, covered=("src/core/",), killed=8, survived=2)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert report.findings == ()
        assert report.score == pytest.approx(0.8)


class TestTheTwoHalvesOfTheComponentAgree:
    """Derived rather than listed, so a fourth scope finding is covered too."""

    def test_every_scope_finding_reaches_the_report_that_produces_the_number(
        self, tmp_path: Path
    ) -> None:
        """Set equality against `check_mutation_scope`, not against a code list.

        A finding the scope half learns to report later is held to the same
        rule by this act, which is the property a spelled-out list of the three
        codes would not have.
        """
        # Arrange: one project carrying every state the scope check knows.
        project = _project(tmp_path, "src/gone/", "vendor/pkg/", "src/empty/")
        _place_source(project, "vendor/pkg/")
        _place_without_source(project, "src/empty/")
        run = _run(
            project,
            covered=("src/gone/", "vendor/pkg/", "src/empty/"),
            killed=10,
            survived=0,
        )

        # Act
        scope_findings = check_mutation_scope(project)
        report = report_mutation_score(project, run)

        # Assert
        assert {(f.check, f.target) for f in scope_findings} == {
            (f.check, f.target)
            for f in report.findings
            if f.check not in {MUTATION_RUN_ZERO_MUTANTS, MUTATION_COUNTERS_MISSING}
        }
        assert len(scope_findings) == 3

    def test_a_target_this_run_is_not_answerable_for_carries_no_scope_finding(
        self, tmp_path: Path
    ) -> None:
        """`--only` narrows what is judged, and the scope half obeys it too.

        Reporting a target the run never claimed is how a job becomes
        permanently red, which is how a check stops being read — the reasoning
        `.22` recorded for `not_judged`.
        """
        # Arrange
        project = _project(tmp_path, "src/core/", "src/gone/")
        _place_source(project, "src/core/")
        run = _run(project, covered=("src/core/",), killed=8, survived=2)

        # Act
        report = report_mutation_score(project, run, only=("src/core/",))

        # Assert
        assert report.findings == ()
        assert report.not_judged == ("src/gone/",)


class TestARunThatClassifiedNothingIsNotAPass:
    """Ten mutants and no verdict about any of them is an empty population."""

    def test_a_run_that_classified_no_mutant_is_a_finding(
        self, tmp_path: Path
    ) -> None:
        # Arrange: the runner generated ten and reached a verdict on none.
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        run = _run(project, covered=("src/core/",), killed=0, survived=0, mutants=10)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert MUTATION_RUN_ZERO_MUTANTS in _checks(report.findings)
        assert report.score is None

    def test_a_run_whose_every_mutant_was_skipped_is_a_finding(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        run = _run(
            project, covered=("src/core/",), killed=0, survived=0, skipped=10, mutants=10
        )

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert MUTATION_RUN_ZERO_MUTANTS in _checks(report.findings)

    def test_the_finding_says_which_of_the_two_emptinesses_it_met(
        self, tmp_path: Path
    ) -> None:
        """Produced-nothing and classified-nothing are different repairs."""
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        produced_none = _run(project, covered=("src/core/",), killed=0, survived=0)
        classified_none = _run(
            project, covered=("src/core/",), killed=0, survived=0, mutants=10
        )

        # Act
        first = report_mutation_score(project, produced_none).findings
        second = report_mutation_score(project, classified_none).findings

        # Assert
        assert first[0].why != second[0].why
        assert "10" in second[0].why

    def test_every_mutant_surviving_is_a_score_of_zero_and_not_an_absence(
        self, tmp_path: Path
    ) -> None:
        """The boundary the empty-population rule must not swallow."""
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        run = _run(project, covered=("src/core/",), killed=0, survived=10)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert report.score == pytest.approx(0.0)
        assert report.findings == ()


class TestWhatTheMutationRunFoundSurvivingAndWasStrengthenedFor:
    """Three assertions added because a mutant lived, not because a line was bare.

    Measured with mutmut 3.7.0 over this slice's own modules: 381 mutants, 135
    survivors. Most are prose inside a `why` or a `--help` string. These three
    were not.
    """

    def test_a_target_written_with_a_leading_slash_is_still_covered(
        self, tmp_path: Path
    ) -> None:
        """`strip("/")` survived being replaced by `strip(None)`.

        Nothing normalised a leading separator, so the two spellings of one
        path were two paths and a covered target would have been reported
        unmeasured.
        """
        # Arrange
        project = _project(tmp_path, "/src/core/")
        _place_source(project, "src/core/")
        run = _run(project, covered=("src/core",), killed=8, survived=2)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert MUTATION_TARGET_UNMEASURED not in _checks(report.findings)

    def test_a_counter_written_as_a_boolean_does_not_hide_its_other_spelling(
        self, tmp_path: Path
    ) -> None:
        """`continue` survived being replaced by `break`.

        A runner writing `timeout: true` beside `timed_out: 4` would have lost
        the count, because the loop stopped at the spelling it had to skip
        rather than trying the next one.
        """
        # Arrange
        path = tmp_path / "stats.json"
        path.write_text(
            json.dumps({"killed": 6, "survived": 2, "timeout": True, "timed_out": 2}),
            encoding="utf-8",
        )

        # Act
        counters = read_run_counters(path)

        # Assert
        assert counters.values["timeout"] == 2
        assert counters.score == pytest.approx(0.8)

    def test_an_unmeasured_finding_names_what_the_run_did_cover(
        self, tmp_path: Path
    ) -> None:
        """Passing `None` in place of the covered scope survived.

        The finding then read "measured by no run" for a run that existed and
        was pointed elsewhere, which is the one fact a reader needs to repair
        it.
        """
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        run = _run(project, covered=("src/other/",), killed=8, survived=2)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        unmeasured = [
            f for f in report.findings if f.check == MUTATION_TARGET_UNMEASURED
        ]
        assert len(unmeasured) == 1
        assert "src/other/" in unmeasured[0].why


class TestACounterThatIsNotACountIsNotRead:
    """`killed: -5` scored 125.0% of -4 mutants before this bead."""

    def test_a_negative_required_counter_is_missing_rather_than_read(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        counters = read_run_counters(_stats(tmp_path, killed=-5, survived=1))

        # Act / Assert
        assert "killed" in counters.missing
        assert counters.score is None

    def test_a_negative_optional_counter_is_not_read_as_a_class(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        counters = read_run_counters(_stats(tmp_path, killed=8, survived=2, timeout=-3))

        # Act / Assert
        assert "timeout" not in counters.values
        assert counters.score == pytest.approx(0.8)

    def test_a_negative_counter_never_produces_a_percentage(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        run = _run(project, covered=("src/core/",), killed=-5, survived=1)

        # Act
        report = report_mutation_score(project, run)

        # Assert
        assert report.score is None
        assert MUTATION_COUNTERS_MISSING in _checks(report.findings)

    def test_zero_is_a_count_and_stays_one(self, tmp_path: Path) -> None:
        """The boundary beside the negative one."""
        # Arrange
        counters = read_run_counters(_stats(tmp_path, killed=0, survived=4))

        # Act / Assert
        assert counters.missing == ()
        assert counters.score == pytest.approx(0.0)


class TestTheCommandRefusesToPrintACleanVerdictOverAnEmptyPopulation:
    """The exit code is what a nightly job reads, so it is asserted here."""

    @pytest.mark.parametrize(
        ("target", "place"),
        [
            ("src/gone/", _place_nothing),
            ("vendor/pkg/", _place_source),
            ("src/empty/", _place_without_source),
        ],
        ids=["not-on-disk", "outside-the-source-paths", "holding-no-source"],
    )
    def test_a_target_that_cannot_produce_a_mutant_exits_one(
        self,
        tmp_path: Path,
        target: str,
        place: Callable[[Path, str], None],
    ) -> None:
        # Arrange
        project = _project(tmp_path, target)
        place(project, target)
        stats = _stats(project, killed=10, survived=0)

        # Act
        result = _invoke(project, "--stats", str(stats), "--target", target)

        # Assert
        assert result.exit_code == 1
        assert "100.0%" in result.stdout

    def test_a_run_that_classified_nothing_exits_one(self, tmp_path: Path) -> None:
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        stats = _stats(project, killed=0, survived=0, mutants=10)

        # Act
        result = _invoke(project, "--stats", str(stats), "--target", "src/core/")

        # Assert
        assert result.exit_code == 1

    def test_no_report_states_a_missing_score_without_a_finding_under_it(
        self, tmp_path: Path
    ) -> None:
        """The dangling sentence, which is the phantom gate in one line.

        `Score: none — see the findings below.` printed with nothing below it
        is a reader being sent to look at an empty list.
        """
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        stats = _stats(project, killed=0, survived=0, mutants=10)

        # Act
        result = _invoke(project, "--stats", str(stats), "--target", "src/core/")

        # Assert
        assert "Score: none" in result.stdout
        assert "WARN [" in result.stdout

    def test_both_shapes_report_the_same_findings(self, tmp_path: Path) -> None:
        """BDL-UX #148: a monitoring surface and a reader are told the same thing."""
        # Arrange
        project = _project(tmp_path, "src/gone/")
        stats = _stats(project, killed=10, survived=0)

        # Act
        human = _invoke(project, "--stats", str(stats), "--target", "src/gone/")
        machine = _invoke(
            project, "--stats", str(stats), "--target", "src/gone/", "--json"
        )
        payload = json.loads(machine.stdout)

        # Assert
        assert human.exit_code == machine.exit_code == 1
        for finding in payload["findings"]:
            assert f"[{finding['check']}]" in human.stdout

    def test_a_healthy_project_still_exits_clean(self, tmp_path: Path) -> None:
        """The guard against a gate that can only be red."""
        # Arrange
        project = _project(tmp_path, "src/core/")
        _place_source(project, "src/core/")
        stats = _stats(project, killed=8, survived=2)

        # Act
        result = _invoke(project, "--stats", str(stats), "--target", "src/core/")

        # Assert
        assert result.exit_code == 0
        assert "80.0%" in result.stdout


class TestThisRepositorysOwnDeclarationSurvivesTheJoin:
    """The nightly job's own invocation must stay answerable, not become red."""

    def test_every_declared_target_of_this_project_could_run_a_mutant(self) -> None:
        # Arrange
        project = REPO_ROOT

        # Act
        findings = check_mutation_scope(project)

        # Assert
        assert findings == []
