"""The Python projects a project holds, found from its scan paths (BDL-083 S2a, RFC D6).

BDL-UX #332: the room census opened ``<root>/pyproject.toml`` and nothing else, so a monorepo
whose Python project is ``backend/pyproject.toml`` declared no interpreter and no distribution.
A Python project is found at the root, under a scan path, or between the root and a scan
path -- the last because ``scan_paths: [backend/src]`` names the code and not the directory
that packages it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.infrastructure.python_projects import census_packaging, find_python_projects

if TYPE_CHECKING:
    from pathlib import Path


def _config(root: Path, *scan_paths: str) -> None:
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    listed = "".join(f"- {path}\n" for path in scan_paths)
    (root / ".beadloom" / "config.yml").write_text(f"scan_paths:\n{listed}", encoding="utf-8")


def _packaging(directory: Path, name: str = "pkg") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n', encoding="utf-8")


class TestFindingThePythonProjects:
    def test_the_root_project_is_found_first(self, tmp_path: Path) -> None:
        # Arrange
        _config(tmp_path, "src")
        _packaging(tmp_path)
        _packaging(tmp_path / "src" / "plugin")

        # Act
        found = find_python_projects(tmp_path)

        # Assert
        assert [project.packaging for project in found] == [
            "pyproject.toml",
            "src/plugin/pyproject.toml",
        ]

    def test_the_project_that_packages_a_scan_path_is_found(self, tmp_path: Path) -> None:
        # Arrange
        _config(tmp_path, "backend/src", "frontend/src")
        _packaging(tmp_path / "backend")
        (tmp_path / "backend" / "src").mkdir()
        (tmp_path / "frontend" / "src").mkdir(parents=True)

        # Act
        found = find_python_projects(tmp_path)

        # Assert
        assert [project.packaging for project in found] == ["backend/pyproject.toml"]
        assert found[0].directory == tmp_path / "backend"

    def test_dependency_and_hidden_directories_are_not_searched(self, tmp_path: Path) -> None:
        # Arrange
        _config(tmp_path, "app")
        _packaging(tmp_path / "app" / "node_modules" / "dep")
        _packaging(tmp_path / "app" / ".venv" / "lib")
        _packaging(tmp_path / "app" / "service")

        # Act
        found = find_python_projects(tmp_path)

        # Assert
        assert [project.packaging for project in found] == ["app/service/pyproject.toml"]

    def test_a_scan_path_outside_the_root_is_not_followed(self, tmp_path: Path) -> None:
        # Arrange
        root = tmp_path / "project"
        _config(root, "../elsewhere")
        _packaging(tmp_path / "elsewhere")

        # Act
        found = find_python_projects(root)

        # Assert
        assert found == ()


class TestThePackagingTheCensusReads:
    def test_a_root_project_is_read_with_no_note(self, tmp_path: Path) -> None:
        # Arrange
        _config(tmp_path, "src")
        _packaging(tmp_path)

        # Act
        packaging = census_packaging(tmp_path)

        # Assert
        assert packaging.directory == tmp_path
        assert packaging.source == "pyproject.toml"
        assert packaging.notes == ()

    def test_a_nested_project_is_read_when_the_root_has_none(self, tmp_path: Path) -> None:
        # Arrange
        _config(tmp_path, "backend/src")
        _packaging(tmp_path / "backend")

        # Act
        packaging = census_packaging(tmp_path)

        # Assert
        assert packaging.directory == tmp_path / "backend"
        assert packaging.source == "backend/pyproject.toml"
        assert packaging.notes == ()

    def test_several_nested_projects_are_named_beside_the_one_read(self, tmp_path: Path) -> None:
        # Arrange
        _config(tmp_path, "services")
        _packaging(tmp_path / "services" / "api", "api")
        _packaging(tmp_path / "services" / "worker", "worker")

        # Act
        packaging = census_packaging(tmp_path)

        # Assert
        assert packaging.source == "services/api/pyproject.toml"
        (note,) = packaging.notes
        assert "services/worker/pyproject.toml" in note

    def test_no_project_anywhere_reads_the_root(self, tmp_path: Path) -> None:
        # Act
        packaging = census_packaging(tmp_path)

        # Assert
        assert packaging.directory == tmp_path
        assert packaging.source == "pyproject.toml"
