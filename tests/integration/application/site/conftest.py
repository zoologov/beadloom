"""The adopter portals, built once per session and shared by the tests that read them.

BDL-076 B3 (``beadloom-hmqn``). A portal build is ``npm ci`` plus ``vitepress
build``, about half a minute each on a warm npm cache, so each claimed stack's
fixture is built once, on first use, and every test of it reads the same build.
Only ``slow`` tests ask for :func:`adopter_portals`; the default run never builds.

``beadloom-m6k7.7``: six portals and six browser runs take longer, one after
another, than the CI job may run, so the job runs them in legs, and
``BEADLOOM_SLOW_PART`` names the part of the slow tests a leg takes: a claimed
stack's name takes every slow test of that stack, and ``projects`` takes the ones
that build a project of their own. A slow test belongs to exactly one part, so
the legs together run every slow test once. Unset, a run takes them all.
"""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

import pytest

from tests.support.adopter_portals import (
    FIXTURES_BY_STACK,
    NODE_MAJOR,
    PROJECTS_PART,
    SLOW_PART_ENV,
    SLOW_PARTS,
    BuiltPortal,
    build_portal,
    node_major,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def slow_part_of(item: pytest.Item) -> str | None:
    """The part of the slow tests *item* belongs to; ``None`` for a test that is not slow."""
    if item.get_closest_marker("slow") is None:
        return None
    callspec = getattr(item, "callspec", None)
    stack = callspec.params.get("stack") if callspec is not None else None
    return str(stack) if stack is not None else PROJECTS_PART


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Deselect every slow test outside the part ``BEADLOOM_SLOW_PART`` names, if it names one."""
    part = os.environ.get(SLOW_PART_ENV)
    if not part:
        return
    if part not in SLOW_PARTS:
        raise pytest.UsageError(f"{SLOW_PART_ENV}={part!r} is not one of the parts {SLOW_PARTS}")
    others = [item for item in items if slow_part_of(item) not in (None, part)]
    if others:
        config.hook.pytest_deselected(items=others)
        items[:] = [item for item in items if item not in others]


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
