"""The score a mutation run produced (BDL-068 S3.1).

The half `mutation_scope` shipped without. The scope check answers "could this
declared target run a single mutant"; nothing answered "and what did a run over
it produce", which is why four beads in BDL-067 could each report "mutation
checking" as prose in a bead comment and one of those reports -- "all 20
assertions red before the fix" -- was eleven guards that cannot fail.

Every test here arranges a real counters file on disk and calls the real
reader. Nothing is doubled: a report that passes against a double proves the
double.
"""

from __future__ import annotations

import json
import platform
from typing import TYPE_CHECKING

from beadloom.application.mutation_scope import (
    MUTATION_COUNTERS_MISSING,
    MUTATION_RUN_ZERO_MUTANTS,
    MUTATION_TARGET_UNMEASURED,
    MutationRun,
    describe_room,
    read_run_counters,
    report_mutation_score,
)

if TYPE_CHECKING:
    from pathlib import Path


def _project(root: Path, *targets: str) -> Path:
    """A project whose flow declares TARGETS as its mutation scope."""
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
    )
    declared = "".join(f"  - {t}\n" for t in targets)
    (root / ".beadloom" / "flow.yml").write_text(
        f"mutation:\n  targets:\n{declared}", encoding="utf-8"
    )
    return root


def _counters(root: Path, **values: int) -> Path:
    path = root / "stats.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def _run(root: Path, *, covered: tuple[str, ...], **values: int) -> MutationRun:
    return MutationRun(
        tool="a runner",
        room=describe_room(),
        covered=covered,
        counters=read_run_counters(_counters(root, **values)),
    )


class TestTheScore:
    """What the counters a run left behind add up to."""

    def test_a_run_over_the_declared_target_reports_a_score(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        report = report_mutation_score(
            root, _run(root, covered=("src/core/",), killed=8, survived=2)
        )
        assert report.score == 0.8
        assert report.findings == ()

    def test_a_timeout_counts_as_killed_and_a_mutant_no_test_covers_does_not(
        self, tmp_path: Path
    ) -> None:
        """The two classes that decide whether the ratio flatters the suite.

        A mutant that hung was DETECTED; a mutant no test executes was not, and
        counting it out of the denominator is how a slice with no tests at all
        scores 100%.
        """
        root = _project(tmp_path, "src/core/")
        report = report_mutation_score(
            root,
            _run(root, covered=("src/core/",), killed=6, timeout=2, survived=1, no_tests=1),
        )
        assert report.score == 0.8

    def test_the_report_names_the_room_the_run_was_measured_in(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        report = report_mutation_score(
            root, _run(root, covered=("src/core/",), killed=8, survived=2)
        )
        assert report.run is not None
        assert platform.python_version() in report.run.room
        assert platform.system() in report.run.room


class TestWhatCannotBeScored:
    """The states in which a number would be a claim rather than a measurement."""

    def test_a_run_that_produced_no_mutants_is_a_finding_not_a_full_score(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, "src/core/")
        report = report_mutation_score(
            root, _run(root, covered=("src/core/",), killed=0, survived=0, mutants=0)
        )
        assert report.score is None
        assert [f.check for f in report.findings] == [MUTATION_RUN_ZERO_MUTANTS]

    def test_a_declared_target_no_run_covered_is_reported(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        report = report_mutation_score(
            root, _run(root, covered=("src/other/",), killed=8, survived=2)
        )
        checks = [f.check for f in report.findings]
        assert MUTATION_TARGET_UNMEASURED in checks
        assert any("src/core/" in f.target for f in report.findings)

    def test_a_missing_counter_is_reported_rather_than_defaulted_to_zero(
        self, tmp_path: Path
    ) -> None:
        """A missing `killed` read as 0 scores 0%; read as absent it scores nothing.

        Both are wrong answers, but only one of them is a NUMBER, and a number
        is what gets pasted into a bead comment.
        """
        root = _project(tmp_path, "src/core/")
        report = report_mutation_score(root, _run(root, covered=("src/core/",), survived=2))
        assert report.score is None
        assert MUTATION_COUNTERS_MISSING in [f.check for f in report.findings]
        assert any("killed" in f.why for f in report.findings)

    def test_no_run_at_all_leaves_every_declared_target_unmeasured(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, "src/core/", "src/other/")
        report = report_mutation_score(root, None)
        assert report.score is None
        assert sorted(f.target for f in report.findings) == ["src/core/", "src/other/"]
        assert {f.check for f in report.findings} == {MUTATION_TARGET_UNMEASURED}


class TestReadingWhatARunnerLeftBehind:
    """The counter vocabulary, which is names rather than a tool."""

    def test_total_is_read_as_the_mutant_count(self, tmp_path: Path) -> None:
        """`total` and `mutants` are two spellings of one counter.

        mutmut writes `total`; the vocabulary is what is shipped, so a runner
        writing either is read.
        """
        counters = read_run_counters(_counters(tmp_path, killed=8, survived=2, total=10))
        assert counters.produced == 10
        assert counters.missing == ()

    def test_a_file_that_is_not_there_is_missing_every_counter(self, tmp_path: Path) -> None:
        counters = read_run_counters(tmp_path / "never-ran.json")
        assert "killed" in counters.missing
        assert counters.score is None

    def test_a_file_that_is_not_a_json_object_is_missing_every_counter(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "stats.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        assert "killed" in read_run_counters(path).missing

    def test_a_counter_that_is_not_a_number_is_missing_rather_than_zero(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "stats.json"
        path.write_text(json.dumps({"killed": "many", "survived": 2}), encoding="utf-8")
        assert "killed" in read_run_counters(path).missing

class TestASliceThatDoesNotClaimTheWholeScope:
    """`only` — the targets this run is answerable for.

    A first slice measures one target of several declared, and both wrong
    answers are available: report the unmeasured ones as findings and the job is
    permanently red, which is how a check stops being read; or drop them from
    the declaration and the duty disappears. The third answer is the one this
    project uses everywhere else — judge what the run covered, and NAME what was
    not judged.
    """

    def test_a_target_outside_the_slice_is_not_judged_and_is_named(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, "src/core/", "src/other/")
        report = report_mutation_score(
            root,
            _run(root, covered=("src/core/",), killed=8, survived=2),
            only=("src/core/",),
        )
        assert report.findings == ()
        assert report.not_judged == ("src/other/",)
        assert report.score == 0.8

    def test_a_target_inside_the_slice_is_still_judged(self, tmp_path: Path) -> None:
        """`only` narrows what is judged; it never excuses what it names."""
        root = _project(tmp_path, "src/core/", "src/other/")
        report = report_mutation_score(
            root,
            _run(root, covered=("src/other/",), killed=8, survived=2),
            only=("src/core/",),
        )
        assert [f.check for f in report.findings] == [MUTATION_TARGET_UNMEASURED]
        assert report.not_judged == ("src/other/",)

    def test_naming_no_slice_judges_every_declared_target(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/", "src/other/")
        report = report_mutation_score(
            root, _run(root, covered=("src/core/",), killed=8, survived=2)
        )
        assert [f.target for f in report.findings] == ["src/other/"]
        assert report.not_judged == ()
