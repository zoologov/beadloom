"""A verdict that does not name its room, over the population of verdicts.

BDL-068 S3.3, over `beadloom-0mdo.23`.

`.23` shipped the instrument and covered each verdict surface by name: the
Gate's rich shape, its json shape, its github shape, and the MCP `complete_bead`
payload on a pass and on a refusal. That is four assertions against a list of
four surfaces, and it is the shape this epic exists to remove — a fifth surface
added later satisfies none of them and is judged by nothing.

So the tests here take POPULATIONS instead. The output shapes of `beadloom ci`
are read out of the command's own `--format` choices, and the axes a project
declares are read out of the census it produced. A fourth shape and a fifth axis
are covered by the act that adds them.

One surface was outside `.23`'s list and outside its own rule: `beadloom
mutation` named the room only on a report that carried a run. A report over a
declared target that no run covered exits 1 — it is a verdict — and it printed
`"room": null`, which is precisely the shape BDL-067 produced nine times.
Measured on the shipped console script before this bead.

The last class here is the census over a project that declares badly. A
derivation that raises where a project's packaging is a directory takes the
whole Gate down with it, and the Gate is where this instrument was installed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import click
import pytest
from click.testing import CliRunner, Result

from beadloom.application.rooms import RUNNER_PLATFORMS, current_room, take_census
from beadloom.services.cli import main
from tests.acceptance.steps.room_judgement import (
    legs_entered_that_do_not_match,
    legs_not_entered_naming_no_difference,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.rooms import RoomCensus


def _gate_formats() -> tuple[str, ...]:
    """Every shape `beadloom ci` can be asked for, from the command itself.

    Derived rather than spelled: a format added to the choice is held to the
    same rule without this file changing.
    """
    command = main.commands["ci"]
    for param in command.params:
        if param.name == "fmt" and isinstance(param.type, click.Choice):
            return tuple(str(c) for c in param.type.choices)
    message = "the `ci` command declares no --format choice to derive from"
    raise AssertionError(message)


def _declaring_project(root: Path) -> Path:
    """A project declaring two interpreters and two legs, in the two real homes."""
    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "adopter"\n'
        'requires-python = ">=3.10"\n'
        "classifiers = [\n"
        '  "Programming Language :: Python :: 3.10",\n'
        '  "Programming Language :: Python :: 3.11",\n'
        "]\n",
        encoding="utf-8",
    )
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n"
        "  tests:\n"
        "    runs-on: ubuntu-latest\n"
        "    strategy:\n"
        "      matrix:\n"
        '        python-version: ["3.10", "3.11"]\n'
        '        locale: ["C.UTF-8", "tr_TR.UTF-8"]\n',
        encoding="utf-8",
    )
    return root


def _beadloom_project(root: Path) -> Path:
    """The minimum a Gate run needs: an initialised project with one graph node."""
    beadloom = root / ".beadloom"
    (beadloom / "_graph").mkdir(parents=True, exist_ok=True)
    (beadloom / "config.yml").write_text("scan_paths:\n- src\n", encoding="utf-8")
    (beadloom / "_graph" / "domains.yml").write_text(
        "nodes:\n"
        "  core:\n"
        "    kind: domain\n"
        "    path: src/core\n"
        "    doc: docs/core.md\n",
        encoding="utf-8",
    )
    (root / "src" / "core").mkdir(parents=True, exist_ok=True)
    (root / "src" / "core" / "__init__.py").write_text("", encoding="utf-8")
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "core.md").write_text("# Core\n", encoding="utf-8")
    return root


def _invoke(*args: str) -> Result:
    return CliRunner().invoke(main, list(args))


class TestEveryShapeTheGateCanBeAskedForNamesItsRoom:
    """The population of output shapes, read out of the command's own choices."""

    def test_the_choices_are_derived_and_not_empty(self) -> None:
        """The guard against a derivation that quietly returns nothing.

        A population check whose population is empty is the same phantom gate
        this bead's other half is about, so the population is asserted before
        anything is asserted over it.
        """
        # Act
        formats = _gate_formats()

        # Assert
        assert len(formats) >= 2

    @pytest.mark.parametrize("fmt", _gate_formats())
    def test_the_shape_names_the_room_the_verdict_was_taken_in(
        self, tmp_path: Path, fmt: str
    ) -> None:
        # Arrange
        project = _beadloom_project(tmp_path)
        room = current_room()

        # Act
        result = _invoke(
            "ci", "--project", str(project), "--no-reindex", "--format", fmt
        )

        # Assert
        assert room.dimensions["os"] in result.stdout
        assert room.dimensions["python_full"] in result.stdout


class TestEveryReportTheMutationCommandProducesNamesItsRoom:
    """The surface `.23`'s by-name list did not reach.

    A report with no run exits 1 and printed no room at all — a verdict without
    an address, which is the whole defect the room census exists to answer.
    """

    def _project(self, root: Path, *targets: str) -> Path:
        (root / ".beadloom").mkdir(parents=True, exist_ok=True)
        (root / ".beadloom" / "config.yml").write_text(
            "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
        )
        declared = "".join(f"  - {t}\n" for t in targets)
        (root / ".beadloom" / "flow.yml").write_text(
            f"mutation:\n  targets:\n{declared}" if targets else "tools:\n- claude\n",
            encoding="utf-8",
        )
        for target in targets:
            (root / target).mkdir(parents=True, exist_ok=True)
            (root / target / "unit.py").write_text("VALUE = 1\n", encoding="utf-8")
        return root

    def test_a_verdict_over_a_target_no_run_covered_names_its_room(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = self._project(tmp_path, "src/core/")

        # Act
        result = _invoke("mutation", "--project", str(project))

        # Assert
        assert result.exit_code == 1
        assert current_room().dimensions["python_full"] in result.stdout

    def test_the_machine_shape_of_that_verdict_carries_it_too(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = self._project(tmp_path, "src/core/")

        # Act
        result = _invoke("mutation", "--project", str(project), "--json")
        payload = json.loads(result.stdout)

        # Assert
        assert payload["room"] is not None
        assert current_room().dimensions["python_full"] in payload["room"]

    def test_a_project_declaring_no_scope_still_says_where_it_looked(
        self, tmp_path: Path
    ) -> None:
        """Nothing is graded, and the report is still answerable about its room."""
        # Arrange
        project = self._project(tmp_path)

        # Act
        result = _invoke("mutation", "--project", str(project))

        # Assert
        assert result.exit_code == 0
        assert current_room().dimensions["python_full"] in result.stdout

    def test_both_shapes_of_every_report_name_the_same_room(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = self._project(tmp_path, "src/core/")

        # Act
        human = _invoke("mutation", "--project", str(project))
        machine = _invoke("mutation", "--project", str(project), "--json")

        # Assert
        assert json.loads(machine.stdout)["room"] in human.stdout


class TestEveryAxisADeclaredRoomCarriesCanBeAskedFor:
    """`--dimension` over the axes the census produced, not over a spelled list."""

    @pytest.fixture()
    def census(self, tmp_path: Path) -> RoomCensus:
        return take_census(_declaring_project(tmp_path))

    def test_the_declaration_produces_more_than_one_axis(
        self, census: RoomCensus
    ) -> None:
        """Again the guard against an empty population."""
        # Assert
        assert len(self._axes(census)) >= 3

    def test_every_axis_is_answered_rather_than_refused(
        self, tmp_path: Path, census: RoomCensus
    ) -> None:
        # Arrange
        project = _declaring_project(tmp_path)

        # Act / Assert
        for axis in self._axes(census):
            result = _invoke("rooms", "--project", str(project), "--dimension", axis)
            assert result.exit_code == 0, axis
            assert result.stdout.strip(), axis

    def test_every_value_a_declared_room_carries_on_an_axis_is_printed(
        self, tmp_path: Path, census: RoomCensus
    ) -> None:
        """The answer is the axis's own values, not a subset of them."""
        # Arrange
        project = _declaring_project(tmp_path)

        # Act / Assert
        for axis in self._axes(census):
            expected = {
                c.room.dimensions[axis]
                for c in census.comparisons
                if axis in c.room.dimensions
            }
            result = _invoke("rooms", "--project", str(project), "--dimension", axis)
            assert set(result.stdout.split()) >= expected, axis

    def test_an_axis_no_declared_room_carries_is_still_refused(
        self, tmp_path: Path
    ) -> None:
        """The guard against an answer that widened until it answers anything."""
        # Arrange
        project = _declaring_project(tmp_path)

        # Act
        result = _invoke(
            "rooms", "--project", str(project), "--dimension", "compiler"
        )

        # Assert
        assert result.exit_code == 2

    @staticmethod
    def _axes(census: RoomCensus) -> tuple[str, ...]:
        return tuple(
            sorted({key for c in census.comparisons for key in c.room.dimensions})
        )


class TestTheCensusSurvivesAProjectThatDeclaresBadly:
    """The derivation is inside the Gate, so what it cannot read it must report.

    Each of these is an absence with a different cause, and the rule is one: an
    unresolved entry is the answer's other half and never an exception.
    """

    def test_a_project_with_no_packaging_and_no_workflows_is_still_a_census(
        self, tmp_path: Path
    ) -> None:
        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.current.dimensions["os"]
        assert census.comparisons == ()
        assert len(census.unresolved) == 2

    def test_packaging_metadata_that_is_a_directory_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        (tmp_path / "pyproject.toml").mkdir()

        # Act
        census = take_census(tmp_path)

        # Assert
        assert any("pyproject" in u.source for u in census.unresolved)

    def test_packaging_metadata_that_is_not_utf_eight_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        (tmp_path / "pyproject.toml").write_bytes(b"\xff\xfe[project]\x00")

        # Act
        census = take_census(tmp_path)

        # Assert
        assert any("pyproject" in u.source for u in census.unresolved)
        assert census.supported == ()

    def test_a_workflow_directory_that_is_a_file_declares_no_leg(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "workflows").write_text("not a dir\n", encoding="utf-8")

        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.comparisons == ()
        assert any(".github" in u.source for u in census.unresolved)

    def test_an_empty_workflow_file_is_named_rather_than_dropped(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("", encoding="utf-8")

        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.comparisons == ()
        assert any("ci.yml" in u.source for u in census.unresolved)

    def test_a_gate_over_such_a_project_still_carries_a_room(
        self, tmp_path: Path
    ) -> None:
        """The point of the four above: the Gate must not fall over on any of them."""
        # Arrange
        project = _beadloom_project(tmp_path)
        (project / "pyproject.toml").mkdir()

        # Act
        result = _invoke("ci", "--project", str(project), "--no-reindex")

        # Assert
        assert current_room().dimensions["python_full"] in result.stdout


class TestThisRepositorysOwnRoomsStayDerived:
    """The property a hand-written list would satisfy and then lose."""

    def test_the_declared_legs_come_from_files_that_exist(self) -> None:
        # Arrange
        from pathlib import Path as _Path

        repo = _Path(__file__).resolve().parents[1]

        # Act
        census = take_census(repo)

        # Assert
        sources = {c.room.source.split(":", 1)[0] for c in census.comparisons}
        assert sources
        for source in sources:
            assert (repo / source).is_file(), source

    def test_every_leg_this_run_did_not_enter_says_which_axis_decided_it(
        self,
    ) -> None:
        """A leg dismissed without a reason is a leg nobody can act on.

        Over the whole declared population rather than over one synthetic leg,
        so a leg whose axis this report cannot describe is caught here and not
        only in the arrangement that anticipated it.
        """
        # Arrange
        from pathlib import Path as _Path

        repo = _Path(__file__).resolve().parents[1]

        # Act
        census = take_census(repo)

        # Assert
        assert census.not_entered
        for comparison in census.not_entered:
            assert comparison.why.strip(), comparison.room.label
            assert ":" in comparison.why, comparison.room.label


class TestTheScenarioIsJudgedInsideADeclaredLegToo:
    """`a run names the declared rooms it did not enter`, over a leg this run IS in.

    The scenario's third step judges what `entered` means, and no run on a
    developer machine can reach it: this repository's legs are ubuntu-latest and
    the owner's machine is Darwin. Until this bead the step did not run in CI
    either -- the scenario skipped on Linux, which is the one place a leg is
    entered -- so the branch was unreachable in every room the suite is run in.

    Nothing is doubled to reach it. The project written here declares a runner
    label for THIS run's platform and the interpreter version THIS run is on, so
    `take_census` reports one leg entered and one not, for real, in whatever room
    the suite is executed in.
    """

    def _project_declaring_this_run(self, tmp_path: Path) -> Path:
        """A workflow declaring THIS run's platform and interpreter.

        The runner label is inverted from the report's own vocabulary, so a
        platform added there is exercised here by that act rather than by
        somebody remembering this file.
        """
        current = current_room()
        label = next(
            f"{family}-latest"
            for family, platform in RUNNER_PLATFORMS.items()
            if platform == current.dimensions["os"]
        )
        here = current.dimensions["python"]
        elsewhere = "3.9" if here != "3.9" else "3.8"
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text(
            "jobs:\n"
            "  tests:\n"
            f"    runs-on: {label}\n"
            "    strategy:\n"
            "      matrix:\n"
            f'        python-version: ["{here}", "{elsewhere}"]\n',
            encoding="utf-8",
        )
        return tmp_path

    def _payload(self, project: Path) -> dict[str, Any]:
        outcome = CliRunner().invoke(main, ["rooms", "--project", str(project), "--json"])
        assert outcome.exit_code == 0, outcome.stdout
        payload: dict[str, Any] = json.loads(outcome.stdout)
        return payload

    def test_this_run_is_inside_exactly_one_of_the_two_declared_legs(
        self, tmp_path: Path
    ) -> None:
        """The arrangement, asserted before the judgement rests on it.

        Two legs differing only in the interpreter, one of them this run's: an
        arrangement that stopped producing an entered leg would make the test
        below vacuous rather than red, which is the failure this epic keeps
        finding.
        """
        # Arrange / Act
        payload = self._payload(self._project_declaring_this_run(tmp_path))

        # Assert
        assert [room["entered"] for room in payload["declared"]].count(True) == 1

    def test_the_scenario_holds_over_the_leg_this_run_entered(self, tmp_path: Path) -> None:
        """Both judgements the scenario makes, driven inside a declared leg."""
        # Arrange
        payload = self._payload(self._project_declaring_this_run(tmp_path))

        # Act / Assert
        assert legs_entered_that_do_not_match(payload) == []
        assert legs_not_entered_naming_no_difference(payload) == []

    def test_a_leg_claiming_a_run_it_does_not_match_is_reported(self, tmp_path: Path) -> None:
        """TESTS MUST BITE: the judgement's failing branch, which nothing reached.

        A report that called a leg entered while the run differs from it is the
        false green the whole instrument exists to remove, and the step that
        catches it never executed anywhere before this bead.
        """
        # Arrange
        payload = self._payload(self._project_declaring_this_run(tmp_path))
        entered = next(room for room in payload["declared"] if room["entered"])
        entered["dimensions"]["python"] = "2.7"

        # Act / Assert
        assert legs_entered_that_do_not_match(payload) == [entered]

    def test_a_leg_dismissed_without_naming_the_difference_is_reported(
        self, tmp_path: Path
    ) -> None:
        """The other judgement's failing branch, over a leg this run is not in."""
        # Arrange
        payload = self._payload(self._project_declaring_this_run(tmp_path))
        dismissed = next(room for room in payload["declared"] if not room["entered"])
        dismissed["why"] = "the leg is not this one"

        # Act / Assert
        assert legs_not_entered_naming_no_difference(payload) == [dismissed]
