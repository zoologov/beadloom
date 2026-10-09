"""``init`` writes a ``lint:fsd`` script running Steiger when the project has none (BDL-080 S3c).

Steiger is the official FSD linter, and the file-level half of what the FSD rules judge
on the graph. A project whose ``package.json`` already runs it keeps its own script; one
that runs none is given ``lint:fsd`` over its FSD root, and ``init`` says what it wrote
and what is left to install.
"""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.scanner import steiger_script
from beadloom.onboarding.scanner.steiger_script import ensure_steiger_script

if TYPE_CHECKING:
    from pathlib import Path


def _package(root: Path, data: dict[str, object]) -> None:
    (root / "package.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _scripts(root: Path) -> dict[str, str]:
    return dict(json.loads((root / "package.json").read_text(encoding="utf-8"))["scripts"])


def test_a_project_without_steiger_is_given_the_script_over_its_fsd_root(
    tmp_path: Path,
) -> None:
    _package(tmp_path, {"name": "web", "scripts": {"dev": "vite"}})

    result = ensure_steiger_script(tmp_path, "src")

    assert result.written
    assert _scripts(tmp_path) == {"dev": "vite", "lint:fsd": "steiger ./src"}
    assert "lint:fsd" in result.sentence()
    assert "npm install -D steiger @feature-sliced/steiger-plugin" in result.sentence()


def test_layers_at_the_root_are_linted_from_the_root(tmp_path: Path) -> None:
    _package(tmp_path, {"name": "web"})

    ensure_steiger_script(tmp_path, "")

    assert _scripts(tmp_path) == {"lint:fsd": "steiger ."}


def test_a_project_that_runs_steiger_keeps_its_own_script(tmp_path: Path) -> None:
    _package(tmp_path, {"name": "web", "scripts": {"lint:arch": "steiger src --fix"}})
    before = (tmp_path / "package.json").read_text(encoding="utf-8")

    result = ensure_steiger_script(tmp_path, "src")

    assert not result.written
    assert (tmp_path / "package.json").read_text(encoding="utf-8") == before
    assert "lint:arch" in result.sentence()


def test_an_existing_lint_fsd_script_is_never_replaced(tmp_path: Path) -> None:
    _package(tmp_path, {"name": "web", "scripts": {"lint:fsd": "eslint ."}})

    result = ensure_steiger_script(tmp_path, "src")

    assert not result.written
    assert _scripts(tmp_path) == {"lint:fsd": "eslint ."}


def test_installed_steiger_is_not_asked_for_again(tmp_path: Path) -> None:
    _package(
        tmp_path,
        {
            "name": "web",
            "devDependencies": {"steiger": "0.7.0", "@feature-sliced/steiger-plugin": "0.8.0"},
        },
    )

    result = ensure_steiger_script(tmp_path, "src")

    assert result.written
    assert "npm install" not in result.sentence()


def test_a_project_without_a_package_json_is_left_alone(tmp_path: Path) -> None:
    result = ensure_steiger_script(tmp_path, "src")

    assert not result.written
    assert not (tmp_path / "package.json").exists()
    assert result.sentence() == ""


def test_an_unreadable_package_json_is_named_and_not_rewritten(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{ not json", encoding="utf-8")

    result = ensure_steiger_script(tmp_path, "src")

    assert not result.written
    assert (tmp_path / "package.json").read_text(encoding="utf-8") == "{ not json"
    assert "package.json" in result.sentence()


# BDL-080 S3f (beadloom-af99.14), the S3 review's minor 2: the file keeps its own indent,
# is written whole or not at all, and keeps its permissions.


@pytest.mark.parametrize("indent", ["\t", "    ", "  "])
def test_the_file_keeps_its_own_indentation(tmp_path: Path, indent: str) -> None:
    data = {"name": "web", "scripts": {"dev": "vite"}, "dependencies": {"vue": "3.5.0"}}
    (tmp_path / "package.json").write_text(json.dumps(data, indent=indent) + "\n", "utf-8")

    ensure_steiger_script(tmp_path, "src")

    expected = {**data, "scripts": {"dev": "vite", "lint:fsd": "steiger ./src"}}
    written = (tmp_path / "package.json").read_text(encoding="utf-8")
    assert written == json.dumps(expected, indent=indent, ensure_ascii=False) + "\n"


def test_a_one_line_file_is_written_with_two_spaces(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "web"}', encoding="utf-8")

    ensure_steiger_script(tmp_path, "src")

    expected = {"name": "web", "scripts": {"lint:fsd": "steiger ./src"}}
    written = (tmp_path / "package.json").read_text(encoding="utf-8")
    assert written == json.dumps(expected, indent=2) + "\n"


def test_the_file_is_written_through_the_atomic_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _package(tmp_path, {"name": "web"})
    written: list[Path] = []
    monkeypatch.setattr(
        steiger_script, "write_text_atomic", lambda path, text: written.append(path)
    )

    ensure_steiger_script(tmp_path, "src")

    assert written == [tmp_path / "package.json"]


def test_the_file_keeps_its_permissions(tmp_path: Path) -> None:
    _package(tmp_path, {"name": "web"})
    path = tmp_path / "package.json"
    path.chmod(0o644)

    ensure_steiger_script(tmp_path, "src")

    assert stat.S_IMODE(path.stat().st_mode) == 0o644
