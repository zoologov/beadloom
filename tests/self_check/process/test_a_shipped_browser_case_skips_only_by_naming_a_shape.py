"""A shipped browser case skips only through the shape helper, which names what is missing.

BDL-076 (``beadloom-ujzb.17``). ``e2e/support/shape.js`` is the one way a case of
the shipped suite skips: it names the shape the served graph lacks, and under the
switch the ``site-e2e`` job sets it fails the case instead. A case that called
Playwright's own ``test.skip`` or ``test.fixme`` would skip on this repository's
portal as well, where that switch cannot see it, and would name no shape.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from tests.support.portal_browser_suite import SHAPE_HELPER, SHIPPED_E2E

if TYPE_CHECKING:
    from pathlib import Path

#: A skip that does not go through the helper: ``test.skip(``, ``test.describe.fixme(`` ...
_BYPASS = re.compile(r"\btest(?:\.describe)?\.(?:skip|fixme)\s*\(")

#: Every script of the shipped suite but the helper itself.
_SCRIPTS = sorted(
    path
    for pattern in ("*.js", "*.mjs")
    for path in SHIPPED_E2E.rglob(pattern)
    if path != SHAPE_HELPER
)


def _relative(path: Path) -> str:
    return path.relative_to(SHIPPED_E2E).as_posix()


def test_the_shipped_suite_is_read() -> None:
    assert len([path for path in _SCRIPTS if path.name.endswith(".spec.js")]) > 15


def test_the_shape_helper_is_where_a_case_skips() -> None:
    assert _BYPASS.search(SHAPE_HELPER.read_text(encoding="utf-8")) is not None


@pytest.mark.parametrize("script", _SCRIPTS, ids=_relative)
def test_a_shipped_script_skips_no_case_but_through_the_shape_helper(script: Path) -> None:
    assert _BYPASS.findall(script.read_text(encoding="utf-8")) == []
