"""A stale line names the pair it is about, and the summary counts pairs as pairs.

BDL-069 S1, bead `beadloom-h7b3`, the RFC's Q3 — decided by measurement, and not
the defect first named. The line was not printed twice. A pair is a document AND
a code file, so two files in one package give two pairs over one README; the text
line dropped the `code_path` that tells them apart, so two different pairs
rendered as two identical lines. Measured on a two-package project: four pair
entries, four distinct `code_path` values in `sync-check --json`, and the gate
summary `4 stale doc(s)` over two documents.

`--json` already carried `code_path`, and its shape is pinned here as unchanged.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from click.testing import CliRunner

from beadloom.application.gate import _sync_summary
from beadloom.doc_sync.surface_ledger import SurfaceVerdict
from beadloom.services.cli import main
from tests import stale_pair_project as project

if TYPE_CHECKING:
    from pathlib import Path

#: The keys a pair entry of `sync-check --json` carried before this bead.
_PAIR_KEYS = {"status", "ref_id", "doc_path", "code_path", "reason", "baseline", "details"}


def _sync_check(root: Path, *args: str) -> Any:
    return CliRunner().invoke(main, ["sync-check", *args, "--project", str(root)])


def _lines(result: Any, marker: str) -> list[str]:
    return [line for line in result.output.splitlines() if marker in line]


class TestEveryStaleLineNamesItsCodeFile:
    """One line per pair, and no two pairs print the same line."""

    def test_missing_modules_lines_are_distinguishable(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.unname_a_module(root)

        lines = _lines(_sync_check(root), "[stale]")

        stale = project.stale(root)
        assert len(stale) > 1, stale
        assert len(lines) == len(stale)
        assert len(set(lines)) == len(lines), lines
        for row in stale:
            assert any(f"{row['doc_path']} <-> {row['code_path']}" in ln for ln in lines)
        assert all("missing modules: beta" in ln for ln in lines), lines

    def test_untracked_files_lines_are_distinguishable(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.add_an_unannotated_module(root)

        lines = _lines(_sync_check(root), "[stale]")

        assert len(lines) == len(project.MODULES)
        assert len(set(lines)) == len(lines), lines
        assert all("untracked: gamma.py" in ln for ln in lines), lines

    def test_a_missing_code_file_line_names_the_file_that_is_gone(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        (root / project.SOURCE / "alpha.py").unlink()

        lines = _lines(_sync_check(root), "[missing]")

        assert len(lines) == 1, lines
        assert f"{project.DOC_PATH} <-> {project.SOURCE}alpha.py" in lines[0]


class TestTheSummaryCountsPairs:
    """`N stale pair(s)`, and N is the number of stale entries `--json` holds."""

    def test_the_gate_line_says_pairs(self) -> None:
        rows: list[dict[str, object]] = [
            {"status": "stale", "doc_path": "one.md", "code_path": f"src/{name}.py"}
            for name in ("a", "b", "c")
        ]
        line = _sync_summary(rows, [], SurfaceVerdict(True, False, ""))
        assert line == "3 stale pair(s)"

    def test_the_count_equals_the_stale_entries_of_the_json(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.unname_a_module(root)
        report = json.loads(_sync_check(root, "--json").stdout)
        entries = [pair for pair in report["pairs"] if pair["status"] == "stale"]
        documents = {pair["doc_path"] for pair in entries}
        assert len(entries) > len(documents), entries

        line = _sync_summary(entries, [], SurfaceVerdict(True, False, ""))

        assert line.startswith(f"{len(entries)} stale pair(s)"), line

    def test_the_json_pair_shape_did_not_change(self, tmp_path: Path) -> None:
        root = project.build(tmp_path / "proj")
        project.unname_a_module(root)
        report = json.loads(_sync_check(root, "--json").stdout)
        for pair in report["pairs"]:
            assert set(pair) <= _PAIR_KEYS, pair
            assert {"status", "ref_id", "doc_path", "code_path", "reason"} <= set(pair)
