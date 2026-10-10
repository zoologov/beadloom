"""The release harness's own logic: what it accepts, how it reports, and which exit it returns.

The harness itself installs an artifact and runs it on a throwaway project, which takes
minutes and a network. These tests stop short of that: they exercise the parts that decide
what a run SAYS — the artifact argument, the exit code a report maps to, and that a step
which fails after the checks have started leaves the checks that ran in the report.

The file sits under ``tests/self_check/`` because the harness is this repository's release
tooling rather than product code, so no graph node owns it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.release import verify_the_release as harness
from tests.release.verify_the_release import (
    Artifact,
    CannotRunError,
    Done,
    Report,
    Room,
    check_activity,
    check_shallow_history,
    check_versions,
    parse_artifact,
)

if TYPE_CHECKING:
    from pathlib import Path

_RELEASE = "9.0.0"


def _report(*outcomes: tuple[str, str]) -> Report:
    """A report holding one check per ``(kind, status)`` pair, in order."""
    report = Report(artifact=f"beadloom=={_RELEASE}", release=_RELEASE)
    for number, (kind, status) in enumerate(outcomes):
        report.checks.append(harness.Check(f"check {number}", kind, status, "detail"))
    return report


class TestTheArtifactArgument:
    def test_an_exact_pin_names_its_version(self) -> None:
        assert parse_artifact("beadloom==9.0.0") == Artifact(
            "beadloom==9.0.0", "9.0.0", is_wheel=False
        )

    def test_a_wheel_names_the_version_in_its_file_name(self, tmp_path: Path) -> None:
        wheel = tmp_path / "beadloom-9.0.0-py3-none-any.whl"
        wheel.write_bytes(b"")

        artifact = parse_artifact(str(wheel))

        assert (artifact.claimed_version, artifact.is_wheel) == ("9.0.0", True)

    @pytest.mark.parametrize("argument", ["beadloom>=7", "beadloom", "other==9.0.0"])
    def test_anything_but_an_exact_pin_or_a_wheel_cannot_run(self, argument: str) -> None:
        with pytest.raises(CannotRunError) as raised:
            parse_artifact(argument)

        assert raised.value.exit_code == 2

    def test_a_wheel_path_with_no_file_cannot_run(self, tmp_path: Path) -> None:
        with pytest.raises(CannotRunError, match="no wheel"):
            parse_artifact(str(tmp_path / "beadloom-9.0.0-py3-none-any.whl"))


class TestTheExitCode:
    @pytest.mark.parametrize(
        ("outcomes", "expected"),
        [
            ((("version", "PASS"), ("behaviour", "PASS")), 0),
            ((("version", "PASS"), ("behaviour", "FAIL")), 4),
            ((("version", "PASS"), ("behaviour", "NOT RUN")), 4),
            ((("version", "FAIL"), ("behaviour", "FAIL")), 3),
            ((("version", "PASS"), ("behaviour", "CANNOT RUN")), 2),
            ((("version", "PASS"), ("behaviour", "FAIL"), ("behaviour", "CANNOT RUN")), 4),
            ((("version", "PASS"), ("behaviour", "CANNOT RUN"), ("behaviour", "NOT RUN")), 2),
            ((("version", "FAIL"), ("behaviour", "CANNOT RUN")), 3),
        ],
    )
    def test_the_exit_follows_the_most_telling_outcome(
        self, outcomes: tuple[tuple[str, str], ...], expected: int
    ) -> None:
        assert _report(*outcomes).exit_code() == expected

    def test_the_first_failure_is_the_earliest_check_that_did_not_pass(self) -> None:
        report = _report(("version", "PASS"), ("behaviour", "CANNOT RUN"), ("version", "FAIL"))

        first = report.first_failure()

        assert first is not None
        assert first.name == "check 1"


class _CloneFails(Room):
    """A room whose every git command fails, as a clone does on a broken file:// URL."""

    def git(self, project: Path, *args: str, when: int | None = None) -> harness.Done:
        raise CannotRunError(f"git {' '.join(args)} exited 128: fatal: repository not found")


class TestAStepThatFailsAfterTheChecksStarted:
    def test_a_failed_clone_is_recorded_and_raises_nothing(self, tmp_path: Path) -> None:
        report = _report(("version", "PASS"))

        check_shallow_history(_CloneFails(tmp_path, None), tmp_path / "quayside", report)

        shallow = report.checks[-1]
        assert (shallow.name.split(":")[0], shallow.status) == ("shallow history", "CANNOT RUN")
        assert "repository not found" in shallow.detail
        assert report.exit_code() == 2

    def test_the_report_of_what_ran_is_printed_and_the_run_exits_2(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        wheel = tmp_path / "beadloom-9.0.0-py3-none-any.whl"
        wheel.write_bytes(b"")
        record = tmp_path / "record.json"

        def ran_the_versions(room: Room, artifact: Artifact, report: Report) -> None:
            report.record("version: beadloom --version", "version", passed=True, detail="9.0.0")

        def project_cannot_be_committed(room: Room, report: Report) -> None:
            raise CannotRunError("git commit exited 128: fatal: unable to write")

        monkeypatch.setattr(harness, "prepare", lambda *_args: None)
        monkeypatch.setattr(harness, "check_versions", ran_the_versions)
        monkeypatch.setattr(harness, "check_project", project_cannot_be_committed)

        code = harness.main([str(wheel), "--record-json", str(record)])

        printed = capsys.readouterr().out
        assert code == 2
        assert "PASS     version: beadloom --version" in printed
        assert "CANNOT RUN" in printed
        assert "unable to write" in printed
        assert '"exit": 2' in record.read_text(encoding="utf-8")


#: The checks of the adopter project, by the stage each check's name begins with.
_PROJECT_STAGES = (
    "init",
    "reindex",
    "activity",
    "shallow history",
    "portal scaffold",
    "portal build",
    "pages workflow",
)


def _verify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Report:
    """A run whose environment is taken as prepared and whose version checks hold."""

    def ran_the_versions(room: Room, artifact: Artifact, report: Report) -> None:
        report.record("version: beadloom --version", "version", passed=True, detail="9.0.0")

    monkeypatch.setattr(harness, "prepare", lambda *_args: None)
    monkeypatch.setattr(harness, "check_versions", ran_the_versions)
    return harness.verify(
        Artifact("beadloom==9.0.0", "9.0.0", is_wheel=False),
        release=_RELEASE,
        python="3.12",
        node_bin=None,
        workdir=tmp_path,
    )


def _status_of(report: Report) -> dict[str, str]:
    """Each project stage mapped to the status of the check that names it."""
    return {
        stage: next(
            (
                check.status
                for check in report.checks
                if check.name == stage or check.name.startswith(f"{stage}:")
            ),
            "ABSENT",
        )
        for stage in _PROJECT_STAGES
    }


class TestAProjectStepThatCannotRunListsTheChecksItStopped:
    def test_a_project_that_cannot_be_written_lists_every_project_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def cannot_write(room: Room, root: Path, now: int) -> None:
            raise CannotRunError("git init exited 128: fatal: cannot mkdir")

        monkeypatch.setattr(harness, "write_project", cannot_write)

        report = _verify(tmp_path, monkeypatch)

        assert set(_status_of(report).values()) == {"NOT RUN"}
        assert report.exit_code() == 2

    def test_a_commit_that_fails_after_init_lists_the_checks_after_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _InitHoldsCommitFails(_CloneFails):
            def beadloom(self, project: Path, *args: str) -> Done:
                return Done(0, "", "")

        monkeypatch.setattr(harness, "Room", _InitHoldsCommitFails)
        monkeypatch.setattr(harness, "write_project", lambda *_args: None)
        monkeypatch.setattr(harness, "declare_portal", lambda *_args: None)

        report = _verify(tmp_path, monkeypatch)

        statuses = _status_of(report)
        assert statuses.pop("init") == "PASS"
        assert set(statuses.values()) == {"NOT RUN"}
        assert report.exit_code() == 2


class _PrintsNoJson(Room):
    """A room whose every child exits 0 and prints text that is not JSON."""

    def run(self, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> Done:
        if command[-1] == "--version":
            return Done(0, "beadloom, version 9.0.0\n", "")
        if command[0].endswith("python") and "_graph" in command[-1]:
            return Done(0, '{"src/quayside/dock": "quayside-dock"}', "")
        return Done(0, "Warning: the index is older than the graph\n", "")


class TestAChildThatPrintsNoJson:
    def test_the_version_probe_is_a_failed_check_that_quotes_the_text(
        self, tmp_path: Path
    ) -> None:
        report = _report()

        check_versions(_PrintsNoJson(tmp_path, None), Artifact("x", "9.0.0", False), report)

        probed = [check for check in report.checks if "__version__" in check.name]
        assert [check.status for check in probed] == ["FAIL"]
        assert "the index is older than the graph" in probed[0].detail

    def test_ctx_json_is_a_failed_activity_check_that_quotes_the_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(harness, "_CHANGED_IN_90_DAYS", "src/quayside/dock")
        monkeypatch.setattr(harness, "_UNTOUCHED", "src/quayside/dock")
        report = _report()

        check_activity(_PrintsNoJson(tmp_path, None), tmp_path, report)

        activity = report.checks[-1]
        assert activity.status == "FAIL"
        assert "the index is older than the graph" in activity.detail

    def test_a_graph_probe_that_prints_no_json_is_a_failed_activity_check(
        self, tmp_path: Path
    ) -> None:
        class _GraphProbeFails(_PrintsNoJson):
            def run(
                self, command: list[str], cwd: Path, env: dict[str, str] | None = None
            ) -> Done:
                return Done(0, "ModuleNotFoundError: No module named 'yaml'\n", "")

        report = _report()

        check_activity(_GraphProbeFails(tmp_path, None), tmp_path, report)

        activity = report.checks[-1]
        assert activity.status == "FAIL"
        assert "No module named 'yaml'" in activity.detail
