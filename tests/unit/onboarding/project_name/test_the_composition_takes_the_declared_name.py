"""The name a composition of ``CLAUDE.md`` takes (BDL-083 S2c, RFC D7, BDL-UX #334).

Measured on 9.0.0 at ``f3d6f293`` over a copy of the monorepo fixture, which names
itself in no root manifest: the flow composed in the main checkout carried the
checkout's directory name, so ``config-check`` was green there and red in a
``git worktree`` and in a clean room of the same files. The name is now read from
what the project declares, and the directory's name is the last resort of a first
composition only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.agentic_flow_setup import templates_root
from beadloom.onboarding.project_name import (
    DIRECTORY_SOURCE,
    PROJECT_HEADING_PREFIX,
    PROJECT_NAME_KEY,
    PROJECT_NAME_PLACEHOLDER,
    composition_project_name,
)

if TYPE_CHECKING:
    from pathlib import Path


def _root(tmp_path: Path, name: str = "room-x") -> Path:
    root = tmp_path / name
    (root / ".beadloom").mkdir(parents=True)
    return root


def _declare(root: Path, value: str) -> None:
    (root / ".beadloom" / "config.yml").write_text(
        f"{PROJECT_NAME_KEY}: {value}\nscan_paths:\n- src\n", encoding="utf-8"
    )


def _pyproject(root: Path, value: str) -> None:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{value}"\nversion = "0.1.0"\n', encoding="utf-8"
    )


def _composed_heading(root: Path, value: str) -> None:
    claude = root / ".claude" / "CLAUDE.md"
    claude.parent.mkdir(parents=True, exist_ok=True)
    claude.write_text(
        f"# CLAUDE.md\n\n{PROJECT_HEADING_PREFIX}{value}\n\n- body\n", encoding="utf-8"
    )


class TestTheDeclaredName:
    def test_config_yml_wins_over_the_manifest_and_the_directory(self, tmp_path: Path) -> None:
        root = _root(tmp_path)
        _declare(root, "metrics-desk")
        _pyproject(root, "backend-package")
        name = composition_project_name(root)
        assert (name.value, name.declared) == ("metrics-desk", True)
        assert name.source == f".beadloom/config.yml ({PROJECT_NAME_KEY}:)"

    def test_a_root_manifest_names_the_project_when_config_yml_does_not(
        self, tmp_path: Path
    ) -> None:
        root = _root(tmp_path)
        _pyproject(root, "acme")
        name = composition_project_name(root)
        assert (name.value, name.source, name.declared) == ("acme", "pyproject.toml", True)

    def test_a_package_json_that_is_not_utf_8_names_nothing(self, tmp_path: Path) -> None:
        root = _root(tmp_path, "first-checkout")
        (root / "package.json").write_bytes(b'{"name": "\xff"}')
        assert composition_project_name(root).source == DIRECTORY_SOURCE

    def test_a_blank_declaration_is_not_a_name(self, tmp_path: Path) -> None:
        root = _root(tmp_path)
        _declare(root, '""')
        _pyproject(root, "acme")
        assert composition_project_name(root).value == "acme"


class TestAProjectThatDeclaresNoName:
    def test_takes_the_name_its_last_composition_recorded(self, tmp_path: Path) -> None:
        root = _root(tmp_path, "room-beadloom-ixbd")
        _composed_heading(root, "desk-checkout")
        name = composition_project_name(root)
        assert (name.value, name.declared) == ("desk-checkout", False)
        assert name.source.startswith(".claude/CLAUDE.md")

    def test_takes_the_directory_name_only_when_nothing_recorded_one(self, tmp_path: Path) -> None:
        root = _root(tmp_path, "first-checkout")
        name = composition_project_name(root)
        assert (name.value, name.source, name.declared) == (
            "first-checkout",
            "the directory's name",
            False,
        )

    def test_a_heading_left_as_the_placeholder_records_no_name(self, tmp_path: Path) -> None:
        root = _root(tmp_path, "first-checkout")
        _composed_heading(root, PROJECT_NAME_PLACEHOLDER)
        assert composition_project_name(root).value == "first-checkout"


def test_the_shipped_core_carries_the_heading_the_reader_reads() -> None:
    core = (templates_root() / "CLAUDE.md.txt").read_text(encoding="utf-8")
    assert core.count(f"{PROJECT_HEADING_PREFIX}{PROJECT_NAME_PLACEHOLDER}\n") == 1
