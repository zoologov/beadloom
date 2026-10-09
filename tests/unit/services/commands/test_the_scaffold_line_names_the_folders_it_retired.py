"""``docs site``'s scaffold line says how many folders the run retired with their files.

BDL-080 S2d (``beadloom-af99.10``), from the S2 review (``beadloom-cp4u``, nitpick 5): a
portal written by 8.0.0 and rewritten after the viewer's slices were renamed lost 42
files and kept the folders they sat in. The scaffold writer now retires a folder its
retired files leave empty, and the one line the command prints counts those folders,
so a run that removed them says so. A report rendered as text, so unit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.site.scaffold import ScaffoldReport
from beadloom.services.commands.docs import _echo_scaffold_report

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_the_line_counts_the_folders_retired_beside_the_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = ScaffoldReport(
        version="9.0.0",
        unchanged=("package.json",),
        retired=("a/x/one.js", "a/y/two.js"),
        retired_folders=("a/x", "a/y", "a/y/z"),
    )

    _echo_scaffold_report(report, tmp_path)

    assert capsys.readouterr().out == (
        "Scaffold (beadloom 9.0.0): 0 written, 0 updated, 1 unchanged, 2 retired, "
        "3 empty folders retired, 0 copied from .beadloom/site/\n"
    )


def test_a_run_that_retired_no_folder_says_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _echo_scaffold_report(ScaffoldReport(version="9.0.0"), tmp_path)

    assert "0 retired, 0 empty folders retired, " in capsys.readouterr().out
