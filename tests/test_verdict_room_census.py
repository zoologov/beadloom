"""Which declared rooms a run entered, and which it did not.

The rule under test is one rule, so it can be held: a run ENTERS a declared leg
only when every dimension of that leg is comparable and equal. Every other
outcome is "not entered", with the dimension that decided it named. The
direction matters more than the rule -- a comparison that cannot be made must
never resolve to a match, because a match manufactures coverage nobody has.
"""

from __future__ import annotations

from pathlib import Path

from beadloom.application.rooms import Room, current_room, take_census


def _workflow(root: Path, body: str) -> None:
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "ci.yml").write_text(body, encoding="utf-8")


def _leg(**dimensions: str) -> Room:
    return Room(dimensions=dimensions, source="a workflow: a job")


class TestTheCurrentRoomIsDerivedNotTyped:
    def test_it_reports_the_running_interpreter_and_platform(self) -> None:
        import platform
        import sys

        room = current_room()
        assert room.dimensions["os"] == platform.system()
        assert room.dimensions["python"] == f"{sys.version_info[0]}.{sys.version_info[1]}"
        assert room.dimensions["arch"] == platform.machine()

    def test_its_source_says_it_is_this_process(self) -> None:
        assert "process" in current_room().source


class TestARunEntersOnlyWhatItCanBeHeldTo:
    def test_a_leg_agreeing_on_every_comparable_dimension_is_entered(self) -> None:
        import platform
        import sys

        label = {
            "Linux": "ubuntu-latest",
            "Darwin": "macos-14",
            "Windows": "windows-latest",
        }[platform.system()]
        version = f"{sys.version_info[0]}.{sys.version_info[1]}"
        room = _leg(os=label, python=version)
        comparison = take_census(Path("/nonexistent"), declared=(room,)).comparisons[0]
        assert comparison.entered is True
        assert comparison.why == ""

    def test_a_leg_on_another_platform_is_not_entered_and_the_axis_is_named(
        self,
    ) -> None:
        import platform

        other = "windows-latest" if platform.system() != "Windows" else "ubuntu-latest"
        comparison = take_census(
            Path("/nonexistent"), declared=(_leg(os=other),)
        ).comparisons[0]
        assert comparison.entered is False
        assert "os" in comparison.why

    def test_a_leg_on_another_interpreter_is_not_entered(self) -> None:
        import platform
        import sys

        label = {
            "Linux": "ubuntu-latest",
            "Darwin": "macos-14",
            "Windows": "windows-latest",
        }[platform.system()]
        other = "3.9" if sys.version_info[:2] != (3, 9) else "3.8"
        comparison = take_census(
            Path("/nonexistent"), declared=(_leg(os=label, python=other),)
        ).comparisons[0]
        assert comparison.entered is False
        assert "python" in comparison.why

    def test_a_dimension_this_run_cannot_describe_is_not_a_match(self) -> None:
        """The locale legs are a real room this process cannot claim to be in."""
        import platform

        label = {
            "Linux": "ubuntu-latest",
            "Darwin": "macos-14",
            "Windows": "windows-latest",
        }[platform.system()]
        comparison = take_census(
            Path("/nonexistent"), declared=(_leg(os=label, locale="C"),)
        ).comparisons[0]
        assert comparison.entered is False
        assert "locale" in comparison.why

    def test_a_runner_label_with_no_known_platform_is_not_a_match(self) -> None:
        comparison = take_census(
            Path("/nonexistent"), declared=(_leg(os="self-hosted"),)
        ).comparisons[0]
        assert comparison.entered is False
        assert "self-hosted" in comparison.why

    def test_a_runner_label_with_no_known_platform_joins_the_unresolved(self) -> None:
        census = take_census(Path("/nonexistent"), declared=(_leg(os="self-hosted"),))
        assert any("self-hosted" in u.why for u in census.unresolved)


class TestTheCensusOverARealDeclaration:
    def test_the_legs_of_a_declaring_project_are_counted(self, tmp_path: Path) -> None:
        _workflow(
            tmp_path,
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            '        python-version: ["3.10", "3.11"]\n',
        )
        census = take_census(tmp_path)
        assert len(census.comparisons) == 2

    def test_a_project_declaring_no_leg_says_so_rather_than_reading_as_entered(
        self, tmp_path: Path
    ) -> None:
        census = take_census(tmp_path)
        assert census.comparisons == ()
        assert census.not_entered == ()
        assert any("workflow" in u.why or "workflow" in u.source for u in census.unresolved)

    def test_a_supported_interpreter_no_leg_enters_is_reported(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "classifiers = [\n"
            '  "Programming Language :: Python :: 3.10",\n'
            '  "Programming Language :: Python :: 3.13",\n'
            "]\n",
            encoding="utf-8",
        )
        _workflow(
            tmp_path,
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            '        python-version: ["3.10"]\n',
        )
        assert take_census(tmp_path).supported_without_a_leg == ("3.13",)

    def test_this_repository_is_not_in_any_of_its_own_ci_legs_unless_it_is(
        self,
    ) -> None:
        """The claim BDL-067 made nine times, computed instead of assumed."""
        import platform

        census = take_census(Path(__file__).resolve().parents[1])
        assert census.comparisons != ()
        if platform.system() != "Linux":
            assert census.entered == ()
            assert len(census.not_entered) == len(census.comparisons)
