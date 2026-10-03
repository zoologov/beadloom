"""The environment each CI job that runs pytest builds, and the suite collected in it.

``beadloom-ujzb.26``. The advisory ``site-adopters`` job synced ``dev`` and
``languages`` and ran ``pytest -m slow``. A marker deselects AFTER collection, so
every test module was imported first, and two of them imported ``beadloom.tui``,
which needs ``textual`` from the ``tui`` extra. Collection failed with two errors
and none of the slow tests the job exists for ran. Every local run had ``textual``
installed, so no local run could see it.

**How a job's environment is derived.** The extras a job's ``uv sync`` step types
are read with the same reader the room census uses
(:func:`beadloom.application.rooms.typed_extras_of_job`). From those, the
distributions the step installs are followed through the installed metadata: the
project's own requirements whose marker holds for no extra or for one the job
asked for, then the requirements of each of those, transitively, honouring the
extras each requirement names. That set is what ``uv sync`` makes exact.

**How the suite is collected in it.** Every distribution THIS interpreter holds and
that environment does not is absent there, and its top-level import names are
made unimportable in a child interpreter by a finder at the head of
``sys.meta_path`` that raises ``ModuleNotFoundError``. pytest then collects the
whole suite. ``pytest.importorskip`` sees the same exception a missing package
raises, so a guarded module skips and an unguarded one is a collection error,
exactly as on the runner.

**What it cannot see.** A distribution the job installs and this interpreter does
not hold cannot be added, so a local environment synced with fewer extras than a
job measures a stricter room than the job's, never a looser one. Markers are
evaluated for this platform, so a dependency that only one operating system
installs is judged as this machine would install it. A job that installs the
project through a local action is not followed (the reader reports it).
"""

from __future__ import annotations

import importlib.metadata as metadata
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from beadloom.application.rooms import ALL_EXTRAS, typed_extras_of_job
from tests.support.ci_workflows import WORKFLOWS_DIR, jobs_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

#: The distribution every job installs, whose extras the ``uv sync`` steps name.
PROJECT = "beadloom"

#: A ``run:`` line that invokes pytest, as a command and not as a word in an echo.
_PYTEST_COMMAND_RE = re.compile(r"(?:^|&&|\|\||;)\s*(?:uv run |python -m )?pytest\b")

#: A collection error as pytest's short summary states it.
_COLLECTION_ERROR_RE = re.compile(r"^ERROR (\S+)", re.MULTILINE)

#: The child interpreter's whole program: make the named top-level modules
#: unimportable, then hand the remaining arguments to pytest.
_ABSENT_PACKAGES_BOOTSTRAP = """
import importlib.abc
import sys

_ABSENT = frozenset(name for name in sys.argv[1].split(",") if name)


class _AbsentInThisJob(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.partition(".")[0] in _ABSENT:
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return None


sys.meta_path.insert(0, _AbsentInThisJob())

import pytest

sys.exit(pytest.main(sys.argv[2:]))
"""

#: Bounds one child collection; the whole suite collects in about 20 s.
_COLLECTION_TIMEOUT_SECONDS = 600


@dataclass(frozen=True)
class PytestJob:
    """One workflow job that runs pytest, and the extras its install step types."""

    source: str
    extras: tuple[str, ...]


@dataclass(frozen=True)
class Collection:
    """One child collection: the modules made absent, its exit code and its errors."""

    absent: tuple[str, ...]
    returncode: int
    errors: tuple[str, ...]
    output: str


def _runs_pytest(job: Mapping[str, Any]) -> bool:
    """Whether a step of *job* runs pytest as a command."""
    steps = job.get("steps")
    if not isinstance(steps, list):
        return False
    for step in steps:
        run = step.get("run") if isinstance(step, dict) else None
        if isinstance(run, str) and _PYTEST_COMMAND_RE.search(run):
            return True
    return False


def pytest_jobs(workflows: Path = WORKFLOWS_DIR) -> tuple[PytestJob, ...]:
    """Every job of the workflows under *workflows* that runs pytest, with its extras.

    A job that runs pytest and installs the project nowhere the reader follows is
    an error rather than a job with no extras: an environment that cannot be named
    is not an empty one.
    """
    found: list[PytestJob] = []
    for path in sorted(workflows.glob("*.y*ml")):
        for name, job in jobs_of(path).items():
            if not isinstance(job, dict) or not _runs_pytest(job):
                continue
            source = f"{path.name}: {name}"
            typed, _ = typed_extras_of_job(job)
            if typed is None:
                raise AssertionError(
                    f"{source} runs pytest and installs the project through no step "
                    "this reader follows, so its environment cannot be derived"
                )
            found.append(PytestJob(source=source, extras=tuple(sorted(typed))))
    return tuple(found)


@cache
def _local_distributions() -> Mapping[str, metadata.Distribution]:
    """The distributions this interpreter holds, by canonical name."""
    held: dict[str, metadata.Distribution] = {}
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"]
        if name:
            held.setdefault(canonicalize_name(name), distribution)
    return held


def _requirements_of(name: str) -> list[str]:
    distribution = _local_distributions().get(name)
    if distribution is None:
        return []
    return list(distribution.requires or [])


def _declared_extras() -> frozenset[str]:
    distribution = _local_distributions()[PROJECT]
    return frozenset(
        canonicalize_name(extra) for extra in distribution.metadata.get_all("Provides-Extra") or []
    )


def environment_of(extras: Iterable[str]) -> frozenset[str]:
    """Every distribution a ``uv sync`` naming *extras* installs, canonically named."""
    asked = set(extras)
    if ALL_EXTRAS in asked:
        asked = (asked - {ALL_EXTRAS}) | _declared_extras()
    installed: dict[str, set[str]] = {}
    pending: list[tuple[str, frozenset[str]]] = [(PROJECT, frozenset(asked))]
    while pending:
        name, wanted = pending.pop()
        seen = installed.setdefault(name, set())
        fresh = ({""} | set(wanted)) - seen
        if not fresh:
            continue
        seen.update(fresh)
        for raw in _requirements_of(name):
            requirement = Requirement(raw)
            marker = requirement.marker
            if marker is None or any(marker.evaluate({"extra": extra}) for extra in fresh):
                pending.append(
                    (canonicalize_name(requirement.name), frozenset(requirement.extras))
                )
    return frozenset(installed)


def absent_import_names(environment: frozenset[str]) -> tuple[str, ...]:
    """The top-level modules of every distribution held here and absent from *environment*.

    A name two distributions provide is absent only when both are.
    """
    absent = set(_local_distributions()) - environment
    return tuple(
        sorted(
            module
            for module, providers in metadata.packages_distributions().items()
            if providers and all(canonicalize_name(p) in absent for p in providers)
        )
    )


def collect_without(
    groups: Iterable[tuple[str, ...]], *, cwd: Path, args: tuple[str, ...]
) -> list[Collection]:
    """Collect with each group of top-level modules made absent, concurrently.

    Each child is this interpreter, so what it holds besides the absent names is
    what the running suite holds.
    """
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    started = [
        (
            absent,
            subprocess.Popen(  # noqa: S603 - this interpreter, a program of this module
                [
                    sys.executable,
                    "-c",
                    _ABSENT_PACKAGES_BOOTSTRAP,
                    ",".join(absent),
                    "--collect-only",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "-p",
                    "no:randomly",
                    *args,
                ],
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
            ),
        )
        for absent in groups
    ]
    collections: list[Collection] = []
    try:
        for absent, child in started:
            output, _ = child.communicate(timeout=_COLLECTION_TIMEOUT_SECONDS)
            collections.append(
                Collection(
                    absent=absent,
                    returncode=child.returncode,
                    errors=tuple(_COLLECTION_ERROR_RE.findall(output)),
                    output=output,
                )
            )
    finally:
        for _, child in started:
            if child.poll() is None:
                child.kill()
                child.wait()
    return collections
