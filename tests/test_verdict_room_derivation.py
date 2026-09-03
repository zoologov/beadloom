"""The rooms a project declares are DERIVED from where it declares them.

The failure this covers is not that a room list was wrong. It is that a room
list written by hand satisfies every test it was written beside and goes stale
the first time a leg changes -- which happened three times to
``DEFAULT_STATUS_CHECK_CONTEXTS`` in this repository. So every case here adds a
leg, a version or a dimension to the DECLARATION and asserts the report follows
without the report's own code being touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.application.rooms import derive_declared_rooms


def _pyproject(root: Path, body: str) -> None:
    (root / "pyproject.toml").write_text(body, encoding="utf-8")


def _workflow(root: Path, name: str, body: str) -> None:
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body, encoding="utf-8")


class TestTheInterpretersComeFromThePackaging:
    """`requires-python` is a floor; the classifiers are the enumerated set."""

    def test_the_classifiers_enumerate_the_supported_versions(
        self, tmp_path: Path
    ) -> None:
        _pyproject(
            tmp_path,
            'requires-python = ">=3.10"\n'
            "classifiers = [\n"
            '  "Programming Language :: Python :: 3",\n'
            '  "Programming Language :: Python :: 3.10",\n'
            '  "Programming Language :: Python :: 3.11",\n'
            "]\n",
        )
        declared = derive_declared_rooms(tmp_path)
        assert declared.supported == ("3.10", "3.11")

    def test_a_version_added_to_the_classifiers_is_reported_by_the_same_act(
        self, tmp_path: Path
    ) -> None:
        _pyproject(
            tmp_path,
            'requires-python = ">=3.10"\n'
            'classifiers = ["Programming Language :: Python :: 3.10"]\n',
        )
        assert derive_declared_rooms(tmp_path).supported == ("3.10",)
        _pyproject(
            tmp_path,
            'requires-python = ">=3.10"\n'
            "classifiers = [\n"
            '  "Programming Language :: Python :: 3.10",\n'
            '  "Programming Language :: Python :: 3.12",\n'
            "]\n",
        )
        assert derive_declared_rooms(tmp_path).supported == ("3.10", "3.12")

    def test_a_floor_without_classifiers_is_a_floor_and_not_a_set(
        self, tmp_path: Path
    ) -> None:
        """`>=3.10` enumerated upward would need a hardcoded newest Python."""
        _pyproject(tmp_path, 'requires-python = ">=3.10"\n')
        declared = derive_declared_rooms(tmp_path)
        assert declared.supported == ()
        assert declared.floor == ">=3.10"
        assert any("classifier" in u.why for u in declared.unresolved)

    def test_the_bare_major_classifier_is_not_a_version(self, tmp_path: Path) -> None:
        _pyproject(
            tmp_path,
            'classifiers = ["Programming Language :: Python :: 3"]\n',
        )
        assert derive_declared_rooms(tmp_path).supported == ()

    def test_no_packaging_metadata_is_reported_rather_than_read_as_none(
        self, tmp_path: Path
    ) -> None:
        assert derive_declared_rooms(tmp_path).supported == ()
        assert any(
            "pyproject.toml" in u.source for u in derive_declared_rooms(tmp_path).unresolved
        )


class TestTheLegsComeFromTheWorkflows:
    """One room per matrix combination, per job, per workflow file."""

    def test_a_job_without_a_matrix_is_one_room(self, tmp_path: Path) -> None:
        _workflow(tmp_path, "ci.yml", "jobs:\n  gate:\n    runs-on: ubuntu-latest\n")
        rooms = derive_declared_rooms(tmp_path).rooms
        assert [r.dimensions for r in rooms] == [{"os": "ubuntu-latest"}]
        assert rooms[0].source == ".github/workflows/ci.yml: gate"

    def test_a_matrix_is_expanded_into_one_room_per_combination(
        self, tmp_path: Path
    ) -> None:
        _workflow(
            tmp_path,
            "ci.yml",
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            '        python-version: ["3.10", "3.11"]\n',
        )
        rooms = derive_declared_rooms(tmp_path).rooms
        assert [r.dimensions["python"] for r in rooms] == ["3.10", "3.11"]

    def test_a_leg_added_to_the_matrix_is_reported_without_the_tool_changing(
        self, tmp_path: Path
    ) -> None:
        body = (
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            "        python-version: [{versions}]\n"
        )
        _workflow(tmp_path, "ci.yml", body.format(versions='"3.10"'))
        assert len(derive_declared_rooms(tmp_path).rooms) == 1
        _workflow(tmp_path, "ci.yml", body.format(versions='"3.10", "3.11", "3.12"'))
        assert len(derive_declared_rooms(tmp_path).rooms) == 3

    def test_two_matrix_axes_are_the_product_of_both(self, tmp_path: Path) -> None:
        _workflow(
            tmp_path,
            "ci.yml",
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            '        python-version: ["3.10", "3.11"]\n'
            '        locale: ["C", "en_US.ISO-8859-1"]\n',
        )
        assert len(derive_declared_rooms(tmp_path).rooms) == 4

    def test_every_workflow_file_is_read_not_only_the_one_named_ci(
        self, tmp_path: Path
    ) -> None:
        _workflow(tmp_path, "ci.yml", "jobs:\n  gate:\n    runs-on: ubuntu-latest\n")
        _workflow(
            tmp_path, "mutation.yml", "jobs:\n  mutation:\n    runs-on: ubuntu-24.04\n"
        )
        sources = {r.source for r in derive_declared_rooms(tmp_path).rooms}
        assert sources == {
            ".github/workflows/ci.yml: gate",
            ".github/workflows/mutation.yml: mutation",
        }

    def test_runs_on_written_as_a_matrix_expression_is_resolved(
        self, tmp_path: Path
    ) -> None:
        _workflow(
            tmp_path,
            "ci.yml",
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ${{ matrix.os }}\n"
            "    strategy:\n"
            "      matrix:\n"
            '        os: ["ubuntu-latest", "windows-latest"]\n',
        )
        rooms = derive_declared_rooms(tmp_path).rooms
        assert [r.dimensions["os"] for r in rooms] == ["ubuntu-latest", "windows-latest"]


class TestTheUnresolvedPopulationIsPartOfTheAnswer:
    """A derivation that omits what it could not parse hands back a clean list."""

    def test_a_workflow_that_is_not_parseable_is_named(self, tmp_path: Path) -> None:
        _workflow(tmp_path, "broken.yml", "jobs: [unclosed\n")
        declared = derive_declared_rooms(tmp_path)
        assert declared.rooms == ()
        assert any("broken.yml" in u.source for u in declared.unresolved)

    def test_a_job_with_no_runs_on_is_named_rather_than_dropped(
        self, tmp_path: Path
    ) -> None:
        _workflow(tmp_path, "ci.yml", "jobs:\n  gate:\n    steps: []\n")
        declared = derive_declared_rooms(tmp_path)
        assert declared.rooms == ()
        assert any("gate" in u.source for u in declared.unresolved)

    def test_a_runner_selected_by_a_list_of_labels_stays_a_room(
        self, tmp_path: Path
    ) -> None:
        """Dropping the job would lose a leg; keeping it loses nothing."""
        _workflow(
            tmp_path,
            "ci.yml",
            "jobs:\n  publish:\n    runs-on: [self-hosted, publisher]\n",
        )
        rooms = derive_declared_rooms(tmp_path).rooms
        assert [r.dimensions["os"] for r in rooms] == ["self-hosted+publisher"]

    def test_an_unresolvable_runs_on_expression_is_named(self, tmp_path: Path) -> None:
        _workflow(
            tmp_path, "ci.yml", "jobs:\n  gate:\n    runs-on: ${{ inputs.runner }}\n"
        )
        declared = derive_declared_rooms(tmp_path)
        assert declared.rooms == ()
        assert any("inputs.runner" in u.why for u in declared.unresolved)

    def test_a_matrix_include_widens_the_set_and_says_so(self, tmp_path: Path) -> None:
        _workflow(
            tmp_path,
            "ci.yml",
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            '        python-version: ["3.10"]\n'
            "        include:\n"
            '        - python-version: "3.13"\n',
        )
        declared = derive_declared_rooms(tmp_path)
        assert any("include" in u.why for u in declared.unresolved)

    def test_an_unquoted_matrix_version_is_reported_as_the_number_yaml_made_of_it(
        self, tmp_path: Path
    ) -> None:
        """`python-version: [3.10]` is the float 3.1 by the time YAML is done."""
        _workflow(
            tmp_path,
            "ci.yml",
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            "        python-version: [3.10]\n",
        )
        declared = derive_declared_rooms(tmp_path)
        assert any("unquoted" in u.why for u in declared.unresolved)


class TestThisRepositorysOwnDeclaration:
    """The derivation over the tree it ships in, so a leg change is felt here."""

    @pytest.fixture()
    def declared(self) -> object:
        return derive_declared_rooms(Path(__file__).resolve().parents[1])

    def test_every_supported_interpreter_has_a_leg(self, declared: object) -> None:
        rooms = declared.rooms  # type: ignore[attr-defined]
        legs = {r.dimensions.get("python") for r in rooms}
        for version in declared.supported:  # type: ignore[attr-defined]
            assert version in legs, f"{version} is supported and no CI leg enters it"

    def test_every_hosted_leg_is_the_one_platform_this_project_declares(
        self, declared: object
    ) -> None:
        """The platform dimension was priced and declined, so this is one value.

        The assertion is not that Ubuntu is right. It is that the report reads
        the declaration: if a second platform is ever added, this fails and the
        room reporting is re-read rather than assumed. The self-hosted publisher
        is excluded by its label naming no platform, not by being named here.
        """
        from beadloom.application.rooms import RUNNER_PLATFORMS

        hosted = {
            r.dimensions["os"]
            for r in declared.rooms  # type: ignore[attr-defined]
            if r.dimensions["os"].split("-", 1)[0] in RUNNER_PLATFORMS
        }
        assert hosted == {"ubuntu-latest"}, hosted
