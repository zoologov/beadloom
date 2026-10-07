"""An adopter's portal loads under the VitePress dev server, not only as a build.

BDL-078 (``beadloom-stcx``). Under ``vitepress dev`` every page of the portal
threw on load - Mermaid's ``fastdom``, a CommonJS module, reached the browser
unbundled and "does not provide an export named default" - while ``vitepress
build`` and the browser suite, which runs on the build, stayed green. The dev
check that ships in the scaffold only booted the server, so it stayed green too.

The check now opens a page with a Mermaid diagram and the architecture page in a
headless browser under the dev server and fails on a page error or a page that
never finishes. This test runs it on each claimed stack's portal as its adopter
would, ``npm run dev-check`` in ``site/``, so the check runs in CI rather than
only when somebody remembers it.

Marked ``slow``: it reuses the stack's portal build and adds one dev server boot
and two page loads, a few seconds on a warm cache. The ``site-adopters`` job runs
it with the browser installed, one claimed stack per leg.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

from tests.support.adopter_portals import FIXTURES_BY_STACK

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.support.adopter_portals import BuiltPortal

pytestmark = pytest.mark.slow

#: Every claimed stack, in the PRD's order.
_STACKS = list(FIXTURES_BY_STACK)

#: A dev-server port per stack, apart from the browser suite's and the check's default 5199.
_PORTS = {stack: str(5211 + index) for index, stack in enumerate(_STACKS)}

#: The environment variable through which the shipped dev check takes its port.
_PORT_ENV = "BEADLOOM_DEV_CHECK_PORT"

#: How long one dev check may take, in seconds: a boot, an optimizer run and two pages.
_TIMEOUT_S = 300


@pytest.mark.parametrize("stack", _STACKS)
def test_the_shipped_dev_check_loads_the_fixtures_pages_under_the_dev_server(
    adopter_portals: Callable[[str], BuiltPortal], npm_for_portals: str, stack: str
) -> None:
    portal = adopter_portals(stack)
    assert portal.failed_step() is None, portal.failed_step()

    done = subprocess.run(  # noqa: S603 - the scaffold's own npm script in the fixture's portal
        [npm_for_portals, "run", "dev-check"],
        cwd=portal.site,
        env={**os.environ, _PORT_ENV: _PORTS[stack]},
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_S,
    )

    assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-4000:]
