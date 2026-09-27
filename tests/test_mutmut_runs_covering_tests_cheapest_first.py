"""The installed mutmut still runs each mutant's covering tests cheapest-first.

Written for BDL-073 F1 (bead ``beadloom-nzlc.1``), from review ``beadloom-8cbm``
Minor 3. The ``Mutation`` job's cost model rests on an upstream behaviour this
project does not own: inside the forked child, mutmut sorts a mutant's covering
tests by their recorded durations (3.7.0 ``__main__.py:1478-1479``, 3.8.0
``workers/isolation.py:860``) and hands them to pytest with ``-p no:randomly``,
which keeps that order. A killed mutant then costs its cheapest killer, not its
whole covering set. pyproject asks for ``mutmut>=3.7``, so an upgrade that drops
either half would make the workflow header false with nothing red. This file is
that red.

It reads the installed package's source text and never imports mutmut, so no
runner code executes here. mutmut is installed only by the ``mutation`` extra,
which no CI test leg installs; there the pin skips and says why. It runs wherever
the extra is installed — the environment in which ``uv lock --upgrade`` is
followed by ``uv sync --all-extras``, which is where an upgrade arrives. The
matchers themselves are held on every leg by the stand-in sources below.
"""

from __future__ import annotations

import importlib.util
import re
from importlib.metadata import version
from pathlib import Path

import pytest

#: ``sorted(tests, key=lambda t: <...>duration_by_test[t])`` with nothing after the
#: key, so a ``reverse=True`` (costliest first) does not match. 3.7.0 reads the
#: durations from ``mutmut.duration_by_test``, 3.8.0 from ``state().duration_by_test``.
_SORTS_BY_RECORDED_DURATION = re.compile(
    r"sorted\(\s*\w+\s*,\s*key\s*=\s*lambda\s+(\w+)\s*:\s*[\w.()]*"
    r"duration_by_test\[\s*\1\s*\]\s*\)"
)

#: The plugin argument that stops pytest-randomly reshuffling the sorted tests.
_KEEPS_THE_ORDER = re.compile(r"""["']-p["']\s*,\s*["']no:randomly["']""")

_SORT_IN_3_7_0 = (
    "sorted_tests = sorted(tests, key=lambda test_name: mutmut.duration_by_test[test_name])"
)
_SORT_IN_3_8_0 = (
    "tests_sorted = sorted(tests, key=lambda test_name: state().duration_by_test[test_name])"
)
_PYTEST_ARGS = 'pytest_args = ["-x", "-q", "-p", "no:randomly", "-p", "no:random-order"]'


def _sorts_cheapest_first(sources: list[str]) -> bool:
    return any(_SORTS_BY_RECORDED_DURATION.search(source) for source in sources)


def _keeps_the_order(sources: list[str]) -> bool:
    return any(_KEEPS_THE_ORDER.search(source) for source in sources)


def _installed_mutmut_sources() -> list[str]:
    """Every module of the installed mutmut, as text; skips where it is absent."""
    spec = importlib.util.find_spec("mutmut")
    if spec is None or not spec.submodule_search_locations:
        pytest.skip(
            "mutmut is not installed: only the `mutation` extra installs it, and no "
            "CI test leg installs that extra"
        )
    return [
        path.read_text(encoding="utf-8")
        for location in spec.submodule_search_locations
        for path in sorted(Path(location).rglob("*.py"))
    ]


class TestTheInstalledRunner:
    """What the ``Mutation`` job's cost model assumes of the mutmut it installs."""

    def test_it_sorts_each_mutants_covering_tests_by_their_recorded_durations(
        self,
    ) -> None:
        sources = _installed_mutmut_sources()

        assert _sorts_cheapest_first(sources), (
            f"mutmut {version('mutmut')} no longer sorts a mutant's covering tests by "
            f"duration_by_test: the cost model in .github/workflows/mutation.yml "
            f"assumes a killed mutant costs its cheapest killer"
        )

    def test_it_asks_pytest_to_keep_that_order(self) -> None:
        sources = _installed_mutmut_sources()

        assert _keeps_the_order(sources), (
            f"mutmut {version('mutmut')} no longer passes `-p no:randomly`, so "
            f"pytest-randomly may reshuffle the tests it sorted"
        )


class TestTheMatchersOnStandIns:
    """The matchers answer for the shapes they claim, on every leg."""

    @pytest.mark.parametrize("line", [_SORT_IN_3_7_0, _SORT_IN_3_8_0])
    def test_both_released_spellings_of_the_sort_match(self, line: str) -> None:
        assert _sorts_cheapest_first(["# Run fast tests first", line])

    @pytest.mark.parametrize(
        "line",
        [
            "sorted_tests = list(tests)",
            "sorted_tests = sorted(tests)",
            "sorted_tests = sorted(tests, key=lambda t: mutmut.duration_by_test[t], reverse=True)",
            "total = sum(mutmut.duration_by_test[t] for t in tests)",
        ],
    )
    def test_a_source_without_the_ascending_sort_does_not_match(self, line: str) -> None:
        assert not _sorts_cheapest_first([line])

    def test_the_pytest_arguments_match(self) -> None:
        assert _keeps_the_order([_PYTEST_ARGS])

    def test_arguments_without_the_plugin_switch_do_not_match(self) -> None:
        assert not _keeps_the_order(['pytest_args = ["-x", "-q"]'])
