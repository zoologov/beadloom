"""The portal's browser tests pass on the portal an adopter builds, not only on ours.

BDL-076, the PRD's US-5: "given that built portal, then the browser tests pass on
it". The Playwright suite that ships in the scaffold runs on each claimed stack's
fixture portal as its adopter runs it, ``npm run test:e2e`` in ``site/``: its web
server builds the portal and previews it under the project's own base path.

Nothing in this repository chooses which cases run (``beadloom-ujzb.17``). A case
whose shape the fixture's graph lacks, such as a declared layer or a contract in
the landscape, skips by itself and names that shape, and the second test holds
every skip to that.

Marked ``slow``: six portal builds and six Playwright runs, about fifteen minutes.
The advisory CI job ``site-adopters`` installs Chromium and runs it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.adopter_portals import FIXTURES_BY_STACK
from tests.support.portal_browser_suite import BrowserRun, run_shipped_suite, shape_constant

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.support.adopter_portals import BuiltPortal

pytestmark = pytest.mark.slow

#: Every claimed stack, in the PRD's order.
_STACKS = list(FIXTURES_BY_STACK)

#: A port per stack, apart from the default 4178 the suite uses on our own portal.
_PORTS = {stack: str(4191 + index) for index, stack in enumerate(_STACKS)}


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
            report = tmp_path_factory.mktemp(f"browser-{stack}") / "report.json"
            runs[stack] = run_shipped_suite(npm_for_portals, portal.site, _PORTS[stack], report)
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


def _names_a_shape(reason: str | None) -> bool:
    """Whether *reason* is the shape helper's wording followed by a shape of four words or more."""
    prefix = f"{shape_constant('SKIP_PREFIX')} "
    text = reason or ""
    return text.startswith(prefix) and len(text.removeprefix(prefix).split()) >= 4
