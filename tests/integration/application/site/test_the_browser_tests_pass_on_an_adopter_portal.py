"""The portal's browser tests pass on the portal an adopter builds, not only on ours.

BDL-076 B3 (``beadloom-hmqn``), the PRD's US-5: "given that built portal, then
the browser tests pass on it". The Playwright suite that ships in the scaffold
runs against the Go and the TypeScript fixture's portal, as ``npm run test:e2e``
runs it: its web server builds the portal and previews it under the project's
own base path. The cases a single project cannot hold are left out by name in
:mod:`tests.support.portal_browser_tests`, each with its reason; the cases a
known defect holds back run on their own, as a strict xfail naming the bead.

Marked ``slow``: two portal builds and three Playwright runs, about five minutes.
The advisory CI job ``site-adopters`` installs Chromium and runs it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from tests.support.portal_browser_tests import (
    TITLES_HELD_BY_DEFECT,
    playwright_defect_selection,
    playwright_selection,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.support.adopter_portals import BuiltPortal

pytestmark = pytest.mark.slow

#: A port per run, apart from the default 4178 the suite uses on our own portal.
_PORTS = {"go": "4191", "typescript": "4192"}
_DEFECT_PORT = "4193"


def _playwright(
    portal: BuiltPortal, selection: list[str], port: str
) -> subprocess.CompletedProcess[str]:
    """The fixture portal's own Playwright suite, run on *selection* and served on *port*."""
    npx = shutil.which("npx")
    assert npx is not None
    # CI=1: a fresh server on the port, never one left running by somebody else.
    environment = {**os.environ, "CI": "1", "BEADLOOM_E2E_PORT": port}
    return subprocess.run(  # noqa: S603 - the fixture portal's own Playwright suite
        [npx, "playwright", "test", "-c", "e2e", "--reporter=line", *selection],
        cwd=portal.site,
        env=environment,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _failures(output: str) -> str:
    """The failed cases of a line-reporter run, from the first one on, or its tail."""
    first = output.find("  1) ")
    return output[first : first + 12000] if first >= 0 else output[-8000:]


@pytest.mark.parametrize("stack", ["go", "typescript"])
def test_the_browser_tests_pass_on_the_fixtures_portal(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = adopter_portals(stack)
    assert portal.failed_step() is None, portal.failed_step()

    run = _playwright(portal, playwright_selection(portal.site / "e2e", stack), _PORTS[stack])

    assert run.returncode == 0, _failures(run.stdout + run.stderr)


@pytest.mark.parametrize(
    "stack",
    [
        pytest.param(
            stack,
            marks=pytest.mark.xfail(reason=next(iter(held.values())), strict=True),
        )
        for stack, held in sorted(TITLES_HELD_BY_DEFECT.items())
    ],
)
def test_the_cases_a_defect_holds_back_run_on_their_own(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    """None today: B5 (``beadloom-ujzb.14``) released the two Go cases into the Go run."""
    portal = adopter_portals(stack)
    assert portal.failed_step() is None, portal.failed_step()

    run = _playwright(portal, playwright_defect_selection(stack), _DEFECT_PORT)

    assert run.returncode == 0, _failures(run.stdout + run.stderr)
