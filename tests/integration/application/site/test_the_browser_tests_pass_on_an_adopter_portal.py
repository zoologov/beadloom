"""The portal's browser tests pass on the portal an adopter builds, not only on ours.

BDL-076, the PRD's US-5: "given that built portal, then the browser tests pass on
it". The Playwright suite that ships in the scaffold runs on each claimed stack's
fixture portal as its adopter runs it, ``npm run test:e2e`` in ``site/``: its web
server builds the portal and previews it under the project's own base path.

Nothing in this repository chooses which cases run on a portal's own graph
(``beadloom-ujzb.17``). A case whose shape the fixture's graph lacks, such as a
declared layer or a contract in the landscape, skips by itself and names that
shape, and the second test holds every skip to that.

The cases the suite tags as running on its made-up adopter-sized graph
(``beadloom-m6k7.7``) take nothing from a portal but its declared layer ranks.
They run on the first stack, in the PRD's order, of each count of declared
layers, and are left out on a stack that declares as many as an earlier one,
where they would draw the same graph and do the same work. Every other case runs
on every stack. The third test holds those cases to running where they are taken
and nowhere else.

Marked ``slow``: six portal builds and six Playwright runs. The advisory CI job
``site-adopters`` installs Chromium and runs them, one claimed stack per leg.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.adopter_portals import FIXTURES_BY_STACK
from tests.support.portal_browser_suite import (
    BrowserRun,
    adopter_sized_tag,
    run_shipped_suite,
    shape_constant,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.support.adopter_portals import BuiltPortal

pytestmark = pytest.mark.slow

#: Every claimed stack, in the PRD's order.
_STACKS = list(FIXTURES_BY_STACK)

#: A port per stack, apart from the default 4178 the suite uses on our own portal.
_PORTS = {stack: str(4191 + index) for index, stack in enumerate(_STACKS)}


def _takes_the_adopter_sized_cases(stack: str) -> bool:
    """Whether *stack* is the first stack, in the PRD's order, that declares as many layers."""
    count = len(FIXTURES_BY_STACK[stack].layers)
    return stack == next(s for s in _STACKS if len(FIXTURES_BY_STACK[s].layers) == count)


def _served_ranks(portal: BuiltPortal) -> list[object]:
    """The layer ranks the portal's data file declares: what the adopter-sized graph reads."""
    return [layer.get("rank") for layer in portal.data().get("layers") or []]


@pytest.fixture(scope="module")
def browser_runs(
    adopter_portals: Callable[[str], BuiltPortal],
    npm_for_portals: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[str], BrowserRun]:
    """The shipped suite's run on a stack's portal, by the stack's name; each runs once."""
    runs: dict[str, BrowserRun] = {}

    def run_of(stack: str) -> BrowserRun:
        if stack not in runs:
            portal = adopter_portals(stack)
            assert portal.failed_step() is None, portal.failed_step()
            # The choice above reads the declared layers; the graph reads the served ranks.
            assert _served_ranks(portal) == list(range(len(portal.fixture.layers)))
            report = tmp_path_factory.mktemp(f"browser-{stack}") / "report.json"
            runs[stack] = run_shipped_suite(
                npm_for_portals,
                portal.site,
                _PORTS[stack],
                report,
                adopter_sized=_takes_the_adopter_sized_cases(stack),
            )
        return runs[stack]

    return run_of


@pytest.mark.parametrize("stack", _STACKS)
def test_the_shipped_browser_suite_passes_on_the_fixtures_portal(
    browser_runs: Callable[[str], BrowserRun], stack: str
) -> None:
    run = browser_runs(stack)

    assert run.returncode == 0, run.failures()


@pytest.mark.parametrize("stack", _STACKS)
def test_every_case_skipped_on_the_fixtures_portal_names_the_shape_it_lacks(
    browser_runs: Callable[[str], BrowserRun], stack: str
) -> None:
    run = browser_runs(stack)

    unnamed = [
        f"{case.file}: {case.title} ({case.skip_reason!r})"
        for case in run.cases()
        if case.status == "skipped" and not _names_a_shape(case.skip_reason)
    ]

    assert unnamed == []


@pytest.mark.parametrize("stack", _STACKS)
def test_the_cases_on_the_adopter_sized_graph_run_once_per_count_of_declared_layers(
    browser_runs: Callable[[str], BrowserRun], stack: str
) -> None:
    run = browser_runs(stack)

    tagged = [case for case in run.cases() if adopter_sized_tag() in case.tags]

    if _takes_the_adopter_sized_cases(stack):
        assert tagged
    else:
        assert tagged == []


def _names_a_shape(reason: str | None) -> bool:
    """Whether *reason* is the shape helper's wording followed by a shape of four words or more."""
    prefix = f"{shape_constant('SKIP_PREFIX')} "
    text = reason or ""
    return text.startswith(prefix) and len(text.removeprefix(prefix).split()) >= 4
