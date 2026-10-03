"""Step implementations for `onboarding/agent-prime/init_on_an_xcode_project.feature`.

BDL-076 R2 finding 7, fixed by ``beadloom-ujzb.19``. The real ``beadloom init --yes``
runs through the CLI on an Xcode project written to disk (``project.pbxproj`` beside
a folder of Swift files, no ``Package.swift``), and on the same project with a local
Swift package beside it. What init prints is what an adopter reads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../onboarding/agent-prime/init_on_an_xcode_project.feature")


@pytest.fixture
def state(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "beacon"}


def _write(root: Path, files: dict[str, str]) -> None:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@given(parsers.parse('an Xcode project "{xcodeproj}" with 2 Swift files and no Package.swift'))
def _xcode(state: dict[str, Any], xcodeproj: str) -> None:
    _write(
        state["root"],
        {
            f"{xcodeproj}/project.pbxproj": "// !$*UTF8*$!\n{ archiveVersion = 1; }\n",
            "Beacon/Views/HomeView.swift": (
                "import SwiftUI\n\nstruct HomeView: View {\n"
                '    var body: some View { Text("Beacon") }\n}\n'
            ),
            "Beacon/Models/Reading.swift": "struct Reading {\n    let value: Double\n}\n",
        },
    )


@given(parsers.parse('a Swift package "{package}" with one target holding 1 Swift file'))
def _package(state: dict[str, Any], package: str) -> None:
    name = package.rsplit("/", 1)[-1]
    _write(
        state["root"],
        {
            f"{package}/Package.swift": (
                "// swift-tools-version:5.9\nimport PackageDescription\n\n"
                f'let package = Package(name: "{name}", targets: [.target(name: "{name}")])\n'
            ),
            f"{package}/Sources/{name}/Kit.swift": "public struct Kit {}\n",
        },
    )


@when("beadloom init is run without prompts")
def _init(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["init", "--yes", "--project", str(state["root"])])
    assert result.exit_code == 0, result.output
    state["output"] = result.output


@then(parsers.parse('init says it did not read {count:d} Swift files and names "{xcodeproj}"'))
def _says_unread(state: dict[str, Any], count: int, xcodeproj: str) -> None:
    output = state["output"]
    assert f"Not read: {count} .swift files" in output
    assert xcodeproj in output


@then("init says Swift is read through Package.swift only")
def _says_how(state: dict[str, Any]) -> None:
    assert "Package.swift" in state["output"]


@then(parsers.parse("the code nodes init writes have exactly the sources {sources}"))
def _sources(state: dict[str, Any], sources: str) -> None:
    written = {
        str(node.get("source") or "")
        for path in sorted((state["root"] / ".beadloom" / "_graph").glob("*.yml"))
        for node in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("nodes") or []
    }
    expected = {part.strip().strip('"') for part in sources.split(",")}
    assert written - {""} == expected
