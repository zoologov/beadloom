"""Every CI job that runs pytest collects the suite in the environment it builds.

``beadloom-ujzb.26``. ``site-adopters`` synced ``dev`` and ``languages`` and ran
``pytest -m slow``; two test modules imported ``beadloom.tui`` without the
``textual`` guard their siblings carry, collection stopped on two errors, and none
of the slow tests the job exists for ran. The job is advisory, so the pull request
showed it as one red line among greens.

Each job's environment is derived from the extras its ``uv sync`` step types, and
the suite is collected in a child interpreter in which every distribution that
environment lacks is unimportable (``tests/support/job_environments.py`` says how
and what it cannot see). Jobs that build the same environment are collected once.
A failure names the jobs, the modules made absent and the test modules that
failed, and the remedy is the one the TUI tests use: ``pytest.importorskip`` before
the import, or the extra in the job's install step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.job_environments import (
    absent_import_names,
    collect_without,
    environment_of,
    pytest_jobs,
)
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: Two jobs the derivation must find, so a reader that finds none cannot pass.
_KNOWN_PYTEST_JOBS = {"ci.yml: tests", "site-adopters.yml: site-adopters"}

#: pytest's exit code when the session collected nothing; not an error here.
_NO_TESTS_COLLECTED = 5

#: How much of a child's output a failure quotes when it names no erroring module.
_OUTPUT_TAIL = 2000


def test_the_jobs_that_run_pytest_are_found_with_their_extras() -> None:
    jobs = {job.source: job.extras for job in pytest_jobs()}

    assert set(jobs) >= _KNOWN_PYTEST_JOBS, sorted(jobs)
    assert "dev" in jobs["site-adopters.yml: site-adopters"]


def test_a_job_that_does_not_sync_the_tui_extra_lacks_textual() -> None:
    without_tui = environment_of(("dev", "languages"))
    with_tui = environment_of(("dev", "languages", "tui"))

    assert {"beadloom", "pytest", "tree-sitter-go", "rich"} <= without_tui
    assert "textual" not in without_tui
    assert "textual" in with_tui
    assert environment_of(("*",)) >= with_tui


def test_a_module_made_absent_fails_collection_unless_it_is_guarded(tmp_path: Path) -> None:
    """The simulation bites on a package this interpreter really holds."""
    (tmp_path / "test_unguarded.py").write_text(
        "import yaml\n\n\ndef test_it():\n    assert yaml\n", encoding="utf-8"
    )
    (tmp_path / "test_guarded.py").write_text(
        "import pytest\n\nyaml = pytest.importorskip('yaml')\n\n\n"
        "def test_it():\n    assert yaml\n",
        encoding="utf-8",
    )

    (absent, present) = collect_without(
        [("yaml",), ()], cwd=tmp_path, args=("--rootdir", str(tmp_path), str(tmp_path))
    )

    assert absent.errors == ("test_unguarded.py",), absent.output
    assert present.errors == (), present.output
    assert present.returncode == 0, present.output


def test_every_job_that_runs_pytest_collects_the_suite_in_its_own_environment() -> None:
    jobs_by_absent: dict[tuple[str, ...], list[str]] = {}
    for job in pytest_jobs():
        absent = absent_import_names(environment_of(job.extras))
        jobs_by_absent.setdefault(absent, []).append(job.source)

    collections = collect_without(jobs_by_absent, cwd=REPO_ROOT, args=())

    failures = [
        f"{', '.join(jobs_by_absent[c.absent])} (rc {c.returncode}; absent there: "
        f"{', '.join(c.absent) or 'nothing'}): "
        + (", ".join(c.errors) or c.output[-_OUTPUT_TAIL:])
        for c in collections
        if c.returncode not in (0, _NO_TESTS_COLLECTED) or c.errors
    ]
    assert not failures, (
        "these jobs cannot collect the suite in the environment they build; guard "
        "each module with pytest.importorskip before the import, or sync the extra:\n"
        + "\n".join(failures)
    )
