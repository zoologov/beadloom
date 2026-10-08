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
    Report,
    Room,
    check_shallow_history,
    parse_artifact,
)

if TYPE_CHECKING:
    from pathlib import Path

_RELEASE = "8.0.0"


def _report(*outcomes: tuple[str, str]) -> Report:
    """A report holding one check per ``(kind, status)`` pair, in order."""
    report = Report(artifact=f"beadloom=={_RELEASE}", release=_RELEASE)
    for number, (kind, status) in enumerate(outcomes):
        report.checks.append(harness.Check(f"check {number}", kind, status, "detail"))
    return report


class TestTheArtifactArgument:
    def test_an_exact_pin_names_its_version(self) -> None:
        assert parse_artifact("beadloom==8.0.0") == Artifact(
            "beadloom==8.0.0", "8.0.0", is_wheel=False
        )

    def test_a_wheel_names_the_version_in_its_file_name(self, tmp_path: Path) -> None:
        wheel = tmp_path / "beadloom-8.0.0-py3-none-any.whl"
        wheel.write_bytes(b"")

        artifact = parse_artifact(str(wheel))

        assert (artifact.claimed_version, artifact.is_wheel) == ("8.0.0", True)

    @pytest.mark.parametrize("argument", ["beadloom>=7", "beadloom", "other==8.0.0"])
    def test_anything_but_an_exact_pin_or_a_wheel_cannot_run(self, argument: str) -> None:
        with pytest.raises(CannotRunError) as raised:
            parse_artifact(argument)

        assert raised.value.exit_code == 2

    def test_a_wheel_path_with_no_file_cannot_run(self, tmp_path: Path) -> None:
        with pytest.raises(CannotRunError, match="no wheel"):
            parse_artifact(str(tmp_path / "beadloom-8.0.0-py3-none-any.whl"))


class TestTheExitCode:
    @pytest.mark.parametrize(
        ("outcomes", "expected"),
        [
            ((("version", "PASS"), ("behaviour", "PASS")), 0),
            ((("version", "PASS"), ("behaviour", "FAIL")), 4),
            ((("version", "PASS"), ("behaviour", "NOT RUN")), 4),
            ((("version", "FAIL"), ("behaviour", "FAIL")), 3),
            ((("version", "PASS"), ("behaviour", "CANNOT RUN")), 2),
            ((("version", "PASS"), ("behaviour", "FAIL"), ("behaviour", "CANNOT RUN")), 2),
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
        wheel = tmp_path / "beadloom-8.0.0-py3-none-any.whl"
        wheel.write_bytes(b"")
        record = tmp_path / "record.json"

        def ran_the_versions(room: Room, artifact: Artifact, report: Report) -> None:
            report.record("version: beadloom --version", "version", passed=True, detail="8.0.0")

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
