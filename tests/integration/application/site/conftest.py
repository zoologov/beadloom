"""The adopter portals, built once per session and shared by the tests that read them.

BDL-076 B3 (``beadloom-hmqn``). A portal build is ``npm ci`` plus ``vitepress
build``, about half a minute each on a warm npm cache, so each claimed stack's
fixture is built once, on first use, and every test of it reads the same build.
Only ``slow`` tests ask for :func:`adopter_portals`; the default run never builds.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from tests.support.adopter_portals import (
    FIXTURES_BY_STACK,
    NODE_MAJOR,
    BuiltPortal,
    build_portal,
    node_major,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture(scope="session")
def npm_for_portals() -> str:
    """``npm``, with a ``node`` the scaffold accepts; the test is skipped without one."""
    npm_bin, node_bin = shutil.which("npm"), shutil.which("node")
    if npm_bin is None or node_bin is None:
        pytest.skip("npm and node are not on PATH, so no portal can be built in this room")
    if node_major(node_bin) < NODE_MAJOR:
        pytest.skip(f"node on PATH is older than the {NODE_MAJOR} the scaffold declares")
    return npm_bin


@pytest.fixture(scope="session")
def adopter_portals(
    tmp_path_factory: pytest.TempPathFactory, npm_for_portals: str
) -> Callable[[str], BuiltPortal]:
    """The built portal of a claimed stack, by its name; each stack is built once."""
    built: dict[str, BuiltPortal] = {}

    def portal_of(stack: str) -> BuiltPortal:
        if stack not in built:
            workdir = tmp_path_factory.mktemp(f"adopter-{stack}")
            built[stack] = build_portal(FIXTURES_BY_STACK[stack], workdir, npm_for_portals)
        return built[stack]

    return portal_of
