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
