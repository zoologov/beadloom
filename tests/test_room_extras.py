"""The extras dimension of a room (BDL-068 S6, BDL-UX #236).

The acceptance scenarios in ``tests/acceptance/features/room_extras.feature``
run against this interpreter's real metadata, which is the only way to prove the
answer is about the environment and not about a fixture. These tests cover what
that environment cannot show: a distribution whose backend does not flatten a
self-referential extra, a requirement whose marker carries a clause beyond
``extra ==``, and the install-step spellings this repository's own workflows do
not happen to use.

Every fake here is a fake DISTRIBUTION — the thing the derivation reads — and
never a fake of the derivation.
"""

from __future__ import annotations

import importlib.metadata as metadata
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.application import rooms
from beadloom.application.rooms import (
    EXTRAS_DIMENSION,
    ExtraSet,
    Room,
    extras_satisfied_by,
    installed_extras,
    project_distribution,
    take_census,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The distribution the fakes stand in for, so no test depends on a real one.
_NAME = "widget"


class _FakeMetadata:
    """The two headers the derivation reads, and nothing else."""

    def __init__(self, provides: list[str], requires: list[str]) -> None:
        self._provides = provides
        self._requires = requires

    def get_all(self, key: str) -> list[str] | None:
        if key == "Provides-Extra":
            return self._provides
        if key == "Requires-Dist":
            return self._requires
        return None


class _FakeDistribution:
    def __init__(self, provides: list[str], requires: list[str]) -> None:
        self.metadata = _FakeMetadata(provides, requires)


def _declare(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provides: list[str],
    requires: list[str],
    installed: set[str] | None = None,
) -> None:
    """Stand this interpreter up as one holding exactly the named distribution."""

    def _distribution(name: str) -> Any:
        if name == _NAME:
            return _FakeDistribution(provides, requires)
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "distribution", _distribution)
    monkeypatch.setattr(
        rooms, "_installed_distributions", lambda: frozenset(installed or set())
    )
    rooms._declared_requirements.cache_clear()


@pytest.fixture(autouse=True)
def _clear_caches() -> Any:
    """Both caches are per-interpreter facts, and a test changes the interpreter."""
    rooms._declared_requirements.cache_clear()
    rooms._installed_distributions.cache_clear()
    yield
    rooms._declared_requirements.cache_clear()
    rooms._installed_distributions.cache_clear()


def _project(tmp_path: Path, name: str = _NAME) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\n', encoding="utf-8"
    )
    return tmp_path


class TestProjectDistribution:
    """The extras are the ANALYSED project's, so its name has to be read."""

    def test_the_name_comes_from_the_packaging(self, tmp_path: Path) -> None:
        assert project_distribution(_project(tmp_path, "some-project")) == "some-project"

    def test_a_project_with_no_packaging_names_no_distribution(
        self, tmp_path: Path
    ) -> None:
        assert project_distribution(tmp_path) is None

    def test_packaging_naming_nothing_names_no_distribution(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        assert project_distribution(tmp_path) is None


class TestInstalledExtras:
    """What this interpreter has, told apart from what it could not look at."""

    def test_an_extra_whose_requirements_are_present_is_installed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(
            monkeypatch,
            provides=["dev", "tui"],
            requires=["pytest>=8; extra == 'dev'", "textual>=0.80; extra == 'tui'"],
            installed={"pytest"},
        )
        found = installed_extras(_project(tmp_path))
        assert found.resolved
        assert found.installed == ("dev",)
        assert [(a.extra, a.absent) for a in found.absent] == [("tui", ("textual",))]
        assert found.label == "dev"

    def test_a_base_requirement_belongs_to_no_extra(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(
            monkeypatch,
            provides=["dev"],
            requires=["click>=8.1", "pytest>=8; extra == 'dev'"],
            installed={"pytest"},
        )
        found = installed_extras(_project(tmp_path))
        assert found.installed == ("dev",)

    def test_a_distribution_this_interpreter_lacks_is_unresolved_not_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(monkeypatch, provides=[], requires=[])
        found = installed_extras(_project(tmp_path, "absent-thing"))
        assert not found.resolved
        assert found.installed == ()
        assert any("absent-thing" in entry.why for entry in found.unresolved)

    def test_a_project_naming_no_distribution_is_unresolved(self, tmp_path: Path) -> None:
        found = installed_extras(tmp_path)
        assert not found.resolved
        assert found.unresolved

    def test_a_marker_beyond_extra_leaves_the_extra_undecided(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(
            monkeypatch,
            provides=["dev"],
            requires=["tomli>=2; python_version < '3.11' and extra == 'dev'"],
            installed={"tomli"},
        )
        found = installed_extras(_project(tmp_path))
        assert found.installed == ()
        assert found.absent == ()
        assert any("marker beyond" in entry.why for entry in found.unresolved)

    def test_an_extra_naming_no_requirement_is_undecided(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(monkeypatch, provides=["empty"], requires=[], installed=set())
        found = installed_extras(_project(tmp_path))
        assert found.installed == ()
        assert any("names no requirement" in entry.why for entry in found.unresolved)

    def test_a_self_referential_extra_is_followed_rather_than_read_as_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # setuptools writes `widget[dev,tui]; extra == "all"` rather than
        # flattening it. Read as a plain requirement, `widget` is installed and
        # `all` would resolve to satisfied in every environment there is.
        _declare(
            monkeypatch,
            provides=["all", "dev", "tui"],
            requires=[
                f"{_NAME}[dev,tui]; extra == 'all'",
                "pytest>=8; extra == 'dev'",
                "textual>=0.80; extra == 'tui'",
            ],
            installed={_NAME, "pytest"},
        )
        found = installed_extras(_project(tmp_path))
        assert found.installed == ("dev",)
        assert [a.extra for a in found.absent] == ["all", "tui"]


class TestExtrasSatisfiedBy:
    """A leg's environment is what its requirements make it, not what was typed."""

    def test_a_leg_installing_the_parts_also_satisfies_the_whole(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(
            monkeypatch,
            provides=["all", "dev", "tui"],
            requires=[
                "pytest>=8; extra == 'all'",
                "textual>=0.80; extra == 'all'",
                "pytest>=8; extra == 'dev'",
                "textual>=0.80; extra == 'tui'",
            ],
        )
        assert extras_satisfied_by(_NAME, frozenset({"pytest", "textual"})) == (
            "all",
            "dev",
            "tui",
        )

    def test_an_unknown_distribution_satisfies_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(monkeypatch, provides=[], requires=[])
        assert extras_satisfied_by("absent-thing", frozenset({"pytest"})) == ()


class TestInstallSteps:
    """Which shell lines declare an environment, and which only look like it."""

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("uv sync --extra dev --extra languages", {"dev", "languages"}),
            ("uv sync --extra=dev", {"dev"}),
            ("uv sync", set()),
            ("uv sync --all-extras", {"*"}),
            ("pip install -e '.[all,dev]'", {"all", "dev"}),
            ("uv pip install .[tui]", {"tui"}),
            ("uv pip install -e .", set()),
            ("python -m pip install -e .[dev]", {"dev"}),
        ],
    )
    def test_a_line_that_installs_the_project(self, line: str, expected: set[str]) -> None:
        assert rooms._extras_of_command(line) == expected

    @pytest.mark.parametrize(
        "line",
        [
            "uv python install 3.12",  # carries the word, installs no project
            "uv tool install dist/widget.whl",
            "pip install -r requirements.txt",
            "npm install",
            "uv run pytest",
        ],
    )
    def test_a_line_that_installs_no_project_declares_nothing(self, line: str) -> None:
        assert rooms._extras_of_command(line) is None

    def test_all_extras_expands_to_what_the_project_declares(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(
            monkeypatch,
            provides=["dev", "tui"],
            requires=["pytest>=8; extra == 'dev'", "textual>=0.80; extra == 'tui'"],
        )
        label, unresolved = rooms._leg_extras(
            _NAME,
            "ci.yml: tests",
            {"steps": [{"run": "uv sync --all-extras"}]},
        )
        assert label == "dev+tui"
        assert unresolved == []


class TestLegExtras:
    """A job's declared environment, and the two ways it can fail to declare one."""

    def test_a_job_that_installs_nothing_declares_no_extras(self) -> None:
        label, unresolved = rooms._leg_extras(
            _NAME, "ci.yml: deploy", {"steps": [{"run": "echo done"}]}
        )
        assert label is None
        assert unresolved == []

    def test_a_job_installing_through_a_local_action_is_unresolved(self) -> None:
        label, unresolved = rooms._leg_extras(
            _NAME,
            "ci.yml: gate",
            {"steps": [{"uses": "./.github/actions/beadloom-gate"}]},
        )
        assert label is None
        assert len(unresolved) == 1
        assert "local action" in unresolved[0].why

    def test_a_third_party_action_is_not_a_local_one(self) -> None:
        label, unresolved = rooms._leg_extras(
            _NAME, "ci.yml: gate", {"steps": [{"uses": "actions/checkout@v5"}]}
        )
        assert label is None
        assert unresolved == []

    def test_an_extra_the_packaging_does_not_declare_is_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _declare(
            monkeypatch,
            provides=["dev"],
            requires=["pytest>=8; extra == 'dev'"],
        )
        _, unresolved = rooms._leg_extras(
            _NAME,
            "ci.yml: tests",
            {"steps": [{"run": "uv sync --extra dev --extra typo"}]},
        )
        assert len(unresolved) == 1
        assert "typo" in unresolved[0].why

    def test_no_distribution_means_no_dimension(self) -> None:
        label, unresolved = rooms._leg_extras(
            None, "ci.yml: tests", {"steps": [{"run": "uv sync --extra dev"}]}
        )
        assert label is None
        assert unresolved == []


class TestTheComparison:
    """What a leg's extras being different says, in both directions."""

    def test_the_same_extras_enter_the_room(self, tmp_path: Path) -> None:
        current = rooms.current_room()
        declared = Room(
            dimensions={
                "os": _runner_for(current.dimensions["os"]),
                EXTRAS_DIMENSION: _current_extras(tmp_path),
            },
            source="ci.yml: tests",
        )
        census = take_census(_here(tmp_path), declared=(declared,))
        assert census.comparisons[0].entered, census.comparisons[0].why

    def test_an_extra_the_leg_installs_and_this_run_has_not_is_named(
        self, tmp_path: Path
    ) -> None:
        difference = rooms._extras_difference("dev", "dev+tui")
        assert difference is not None
        assert "the leg installs tui and this run has not" in difference

    def test_an_extra_this_run_has_and_the_leg_does_not_is_named(self) -> None:
        difference = rooms._extras_difference("dev+mutation", "dev")
        assert difference is not None
        assert "this run has mutation and the leg does not" in difference

    def test_equal_extras_are_no_difference(self) -> None:
        assert rooms._extras_difference("dev+tui", "dev+tui") is None

    def test_a_run_that_cannot_describe_its_extras_does_not_enter(self) -> None:
        difference = rooms._extras_difference(None, "dev")
        assert difference is not None
        assert "cannot describe" in difference


class TestTheCurrentRoom:
    """An unresolved answer adds no dimension, rather than one spelling `unknown`."""

    def test_an_unresolved_set_adds_no_dimension(self) -> None:
        bare = Room(dimensions={"os": "Darwin"}, source="this process")
        assert rooms._room_with_extras(bare, ExtraSet()) is bare

    def test_a_resolved_set_adds_the_label(self) -> None:
        bare = Room(dimensions={"os": "Darwin"}, source="this process")
        carried = rooms._room_with_extras(
            bare, ExtraSet(distribution="widget", installed=("dev",), resolved=True)
        )
        assert carried.dimensions[EXTRAS_DIMENSION] == "dev"

    def test_a_resolved_set_with_no_extras_says_none(self) -> None:
        bare = Room(dimensions={"os": "Darwin"}, source="this process")
        carried = rooms._room_with_extras(
            bare, ExtraSet(distribution="widget", resolved=True)
        )
        assert carried.dimensions[EXTRAS_DIMENSION] == "none"


def _here(tmp_path: Path) -> Path:
    """A project root whose packaging names THIS interpreter's own distribution."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "beadloom"\n', encoding="utf-8"
    )
    return tmp_path


def _current_extras(tmp_path: Path) -> str:
    return installed_extras(_here(tmp_path)).label


def _runner_for(system: str) -> str:
    """A runner label naming the platform this run is on, so only extras decide."""
    return {"Linux": "ubuntu-latest", "Darwin": "macos-latest", "Windows": "windows-latest"}[
        system
    ]
