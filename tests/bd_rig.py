"""A throwaway ``bd`` tracker, for tests that observe what the real binary answers.

BDL-074 A1: a test that pins bd's own spelling (a status, the shape of a JSON
answer) used to read it off THIS repository's tracker, so its result depended on
what happened to be in that tracker and it reached live state the suite must not
touch. A rig built in ``tmp_path`` answers the same question about bd and nothing
about this repository. Building one costs about five seconds (measured once, on
bd 1.0.4, embedded Dolt, macOS), so it is for the few tests that need the binary,
not a fixture for the suite.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def bd_in(rig: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``bd`` rooted at *rig*; the answer is decoded as UTF-8, as bd writes it."""
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["bd", *args],  # noqa: S607 - bd resolved on PATH
        cwd=rig,
        capture_output=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )


def _require(
    done: subprocess.CompletedProcess[str], what: str
) -> subprocess.CompletedProcess[str]:
    if done.returncode != 0:
        pytest.skip(f"bd could not {what} in a rig here: {done.stderr.strip()[:200]}")
    return done


def a_bd_rig(tmp_path: Path) -> Path:
    """A fresh bd tracker in its own git repository under *tmp_path*."""
    rig = tmp_path / "rig"
    rig.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=rig, check=True)  # noqa: S607 - git on PATH
    _require(bd_in(rig, "init", "--prefix", "rig", "-q"), "initialise a tracker")
    return rig


def a_bead(rig: Path, title: str) -> str:
    """Create a task bead in *rig* and return the id bd allocated."""
    created = _require(bd_in(rig, "create", title, "-t", "task", "--json"), "create a bead")
    return str(json.loads(created.stdout)["id"])
