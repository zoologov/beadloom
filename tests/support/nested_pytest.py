"""Run pytest in a child process over a chosen set of this suite's files."""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def run_pytest(args: list[str], *, cwd: Path, report: Path) -> tuple[int, list[tuple[str, str]]]:
    """Run pytest in a subprocess and read per-test OUTCOMES from its JUnit report.

    Outcomes rather than the terminal summary: a count scraped from stdout cannot
    tell a scenario that ran from one that was collected and skipped, and telling
    those apart is the entire question.
    """
    completed = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            *args,
            "-p",
            "no:cacheprovider",
            "--junitxml",
            str(report),
            "-q",
        ],
        cwd=cwd,
        capture_output=True,
        # These two streams are only ever quoted into a failure message, so the
        # handler is tolerant while the codec is still stated: a child pytest
        # writes UTF-8 under a UTF-8 locale and backslash escapes under the C
        # one, and leaving the choice to the image is the defect BDL-068 `.49`
        # measured on the `tests-locale (C)` leg.
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if not report.exists():  # pragma: no cover - only on a collection crash
        pytest.fail(f"pytest produced no report:\n{completed.stdout}\n{completed.stderr}")
    outcomes: list[tuple[str, str]] = []
    # S314: the input is the JUnit report pytest just wrote in a temporary
    # directory, not untrusted data.
    for case in ET.parse(report).getroot().iter("testcase"):  # noqa: S314
        name = str(case.get("name"))
        children = {child.tag for child in case}
        if "skipped" in children:
            outcomes.append((name, "skipped"))
        elif children & {"failure", "error"}:
            detail = " ".join(
                str(child.get("message", "")) for child in case if child.tag != "skipped"
            )
            outcomes.append((name, f"failed: {detail}"))
        else:
            outcomes.append((name, "passed"))
    return completed.returncode, outcomes
