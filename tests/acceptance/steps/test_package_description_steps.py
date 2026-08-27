"""Step implementations for `features/package_description.feature` (BDL-062, `.15`).

The steps run the real Click group and the real sweep over the real repository.
Nothing is stubbed: the defect was a check reading a smaller population than the
fact had, so a fixture standing in for the tree would reproduce the defect rather
than catch it -- FAKES PROVE FAKES.

The module is named ``test_*`` so default pytest collection picks the scenarios
up, matching the rest of the acceptance suite.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

import beadloom
from beadloom.services.commands._root import main


def _load_sweep() -> Any:
    """The sweep module, loaded by PATH rather than by ``tests.`` import.

    ``test_bead14_s4_binding`` copies this suite out of the repository and runs
    it from another directory, where a ``tests.`` import does not resolve and the
    copy fails at COLLECTION — which would redden that test for a reason that has
    nothing to do with a step binding. `.3` hit the same wall and stated the rule:
    find the repository from the INSTALLED PACKAGE, not from this file's parents.

    Loading by path rather than copying the sweep in keeps one home for it. A
    second copy of a check about copies would be its own joke.
    """
    repo_root = Path(beadloom.__file__).resolve().parents[2]
    module_path = repo_root / "tests" / "test_package_description.py"
    spec = importlib.util.spec_from_file_location("_beadloom_description_sweep", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - a broken checkout
        pytest.skip(f"the sweep module is not readable at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_sweep = _load_sweep()
EXPECTED_LIVE_COPIES: int = _sweep.EXPECTED_LIVE_COPIES
RETIRED_DESCRIPTIONS: tuple[str, ...] = _sweep.RETIRED_DESCRIPTIONS
_manifest_description = _sweep._manifest_description
_sweep_for = _sweep._sweep_for
_swept_files = _sweep._swept_files

scenarios("../features/package_description.feature")


@pytest.fixture
def surface() -> dict[str, object]:
    """What one scenario carries from its `when` to its `then`."""
    return {}


@given("the installed distribution declares a one-line description")
def _distribution_declares_a_description(surface: dict[str, object]) -> None:
    description = _manifest_description()
    assert description, "the manifest declares no description, so there is nothing to check"
    surface["description"] = description


@given("a shipped surface still carries a description the product has retired")
def _a_retired_description_is_banned(surface: dict[str, object]) -> None:
    """The retired sentences are declared; whether any file states one is the measurement."""
    assert RETIRED_DESCRIPTIONS, "no retired sentence is declared, so the sweep guards nothing"
    surface["retired"] = RETIRED_DESCRIPTIONS


@given("the description is stated in more places than the check was written against")
def _the_population_is_recorded(surface: dict[str, object]) -> None:
    surface["recorded"] = EXPECTED_LIVE_COPIES


@when("a user runs `beadloom --help`")
def _run_help(surface: dict[str, object]) -> None:
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    surface["help"] = re.sub(r"\s+", " ", result.output)


@when("the description surface is swept")
def _sweep(surface: dict[str, object]) -> None:
    surface["files"] = _swept_files()
    surface["retired_hits"] = [
        (retired, where) for retired in RETIRED_DESCRIPTIONS for where in _sweep_for(retired)
    ]
    surface["copies"] = _sweep_for(_manifest_description())


@then("the summary line it prints states that same description")
def _help_states_the_description(surface: dict[str, object]) -> None:
    description = str(surface["description"])
    printed = str(surface["help"])
    assert description.casefold() in printed.casefold(), (
        "`beadloom --help` does not state the distribution's description.\n"
        f"  declared: {description}\n"
        f"  printed:  {printed[:200]}"
    )


@then("the sweep names that file and the retired sentence it still states")
def _the_sweep_names_the_offender(surface: dict[str, object]) -> None:
    hits = surface["retired_hits"]
    assert isinstance(hits, list)
    files = surface["files"]
    assert isinstance(files, list)
    listed = "\n".join(f"  {path}:{line} states {retired!r}" for retired, (path, line) in hits)
    assert not hits, (
        f"{len(hits)} of {len(files)} swept surface(s) still state a retired "
        f"description:\n{listed}"
    )


@then("the sweep reports how many copies it found and holds every one of them to the manifest")
def _the_population_is_stated(surface: dict[str, object]) -> None:
    copies = surface["copies"]
    assert isinstance(copies, list)
    files = surface["files"]
    assert isinstance(files, list)
    assert files, "the sweep read no files, so its count means nothing"
    listed = "\n".join(f"  {path}:{line}" for path, line in copies)
    assert len(copies) == surface["recorded"], (
        f"{len(files)} file(s) swept; the description is stated in {len(copies)} of them, "
        f"not the recorded {surface['recorded']}:\n{listed}"
    )
