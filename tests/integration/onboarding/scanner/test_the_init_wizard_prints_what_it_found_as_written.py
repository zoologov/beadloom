"""The interactive ``init`` prints the folders and the graph it found as they are named.

``beadloom-2mj3.19``: the wizard passed its scan summary and its review table to Rich as
markup. Rich read the review table's confidence tag, `` [high]``, as a style tag and
dropped it from every node on every run, and a source folder named like ``[beta]`` lost
its name from the ``Source dirs:`` line.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import patch

from beadloom.onboarding.scanner import interactive_init

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


@dataclass
class _FakeIndex:
    symbols_indexed: int = 0
    imports_indexed: int = 0
    edges_loaded: int = 0
    docs_indexed: int = 0


def _no_reindex(_project_root: Path) -> _FakeIndex:
    return _FakeIndex()


def _a_project_with_a_bracketed_folder(root: Path) -> None:
    for folder in ("src/api", "[beta]"):
        package = root / folder
        package.mkdir(parents=True)
        (package / "app.py").write_text("def main():\n    pass\n", encoding="utf-8")


def test_the_scan_and_the_review_print_as_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLUMNS", "200")
    _a_project_with_a_bracketed_folder(tmp_path)

    with patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "cancel"]):
        result = interactive_init(tmp_path, reindex=_no_reindex)

    printed = capsys.readouterr().out
    assert "Source dirs: [beta], src" in printed
    nodes = result["bootstrap"]["nodes"]
    confidences = {node["confidence"] for node in nodes if node.get("confidence")}
    assert confidences
    for confidence in confidences:
        assert f" [{confidence}]\n" in printed


def test_the_wizard_names_the_swift_files_it_did_not_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2 finding 7 (``beadloom-ujzb.19``): an Xcode project is named, not passed over.

    The non-interactive ``init`` says it; the wizard is the same command asked
    interactively and says the same sentence.
    """
    monkeypatch.setenv("COLUMNS", "300")
    (tmp_path / "Beacon.xcodeproj").mkdir()
    (tmp_path / "Beacon.xcodeproj" / "project.pbxproj").write_text("// pbx\n", encoding="utf-8")
    (tmp_path / "Beacon").mkdir()
    (tmp_path / "Beacon" / "Home.swift").write_text("struct Home {}\n", encoding="utf-8")

    # No node is written, so no review is put; the wizard's last question is the
    # skeletons one, answered no.
    with (
        patch("rich.prompt.Prompt.ask", side_effect=["bootstrap"]),
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        interactive_init(tmp_path, reindex=_no_reindex)

    printed = capsys.readouterr().out
    assert "Not read: 1 .swift file outside any Package.swift target" in printed
    assert "(Xcode: Beacon.xcodeproj)" in printed


def test_the_wizard_names_the_code_beside_a_module(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The re-review's finding m3 (``beadloom-ujzb.24``): the wizard says what init says.

    A folder scanned beside a Gradle module's sources, and a file no scan path can hold.
    """
    monkeypatch.setenv("COLUMNS", "400")
    files = {
        "backend/src/main/kotlin/com/acme/Api.kt": "package com.acme\n\nclass Api\n",
        "backend/scripts/deploy.py": "def deploy() -> None:\n    pass\n",
        "backend/run.py": "def run() -> None:\n    pass\n",
    }
    for rel_path, text in files.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    with patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "cancel"]):
        interactive_init(tmp_path, reindex=_no_reindex)

    printed = capsys.readouterr().out
    assert "Also scanned: backend/scripts - " in printed
    assert "Not read: backend/run.py - " in printed


def test_the_wizard_leaves_the_generated_portal_out_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The re-review's finding m4 (``beadloom-ujzb.24``): the wizard reads what init reads.

    Its scan summary and its bootstrap both leave out the folder the probe calls the
    portal, and it says so.
    """
    monkeypatch.setenv("COLUMNS", "400")
    for rel_path in ("src/orders/place.py", "site/.vitepress/theme/index.js"):
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")

    with patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "cancel"]):
        result = interactive_init(
            tmp_path, reindex=_no_reindex, is_portal=lambda folder: folder.name == "site"
        )

    printed = capsys.readouterr().out
    assert "Source dirs: src\n" in printed
    assert "Not scanned: site/ - " in printed
    sources = {node["source"] for node in result["bootstrap"]["nodes"]}
    assert not [source for source in sources if source.startswith("site")]
