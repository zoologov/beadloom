"""``init`` reads no top-level folder holding the portal ``beadloom docs site`` wrote.

The re-review's finding m4 (``beadloom-ujzb.22``), fixed by ``beadloom-ujzb.24``: ``init
--force`` after ``docs site`` scanned ``site/`` as the project's code - a scan path, the
theme and the browser tests as nodes, their languages as the project's. Whether a folder
is the portal is asked of the probe the caller hands in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.project_scan import generated_portals, scan_project

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, *paths: str) -> None:
    for rel_path in paths:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")


def _project(root: Path) -> None:
    _write(
        root,
        "src/orders/place.py",
        "site/.vitepress/theme/index.js",
        "site/e2e/graph.spec.js",
        "portal/.vitepress/theme/index.js",
        ".hidden/x.js",
        "notes.txt",
    )


def _marked(folder: Path) -> bool:
    return (folder / ".vitepress").is_dir()


class TestTheGeneratedPortalsAreFound:
    def test_each_top_level_folder_the_probe_accepts(self, tmp_path: Path) -> None:
        _project(tmp_path)

        assert generated_portals(tmp_path, _marked) == ("portal", "site")

    def test_hidden_folders_and_files_are_not_asked(self, tmp_path: Path) -> None:
        _project(tmp_path)
        asked: list[str] = []

        def probe(folder: Path) -> bool:
            asked.append(folder.name)
            return False

        assert generated_portals(tmp_path, probe) == ()
        assert sorted(asked) == ["portal", "site", "src"]


class TestTheScanSkipsThem:
    def test_a_skipped_folder_is_no_source_dir_and_counts_no_file(self, tmp_path: Path) -> None:
        _project(tmp_path)

        scan = scan_project(tmp_path, skip=("site", "portal"))

        assert scan["source_dirs"] == ["src"]
        assert scan["file_count"] == 1
        assert scan["languages"] == [".py"]

    def test_without_a_skip_the_scan_is_what_it_was(self, tmp_path: Path) -> None:
        _project(tmp_path)

        scan = scan_project(tmp_path)

        assert scan["source_dirs"] == ["portal", "site", "src"]
        assert scan["languages"] == [".js", ".py"]
