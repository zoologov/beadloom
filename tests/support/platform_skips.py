"""Every platform mark in the suite, found in the source rather than by collection.

A mark that is inert on this platform is invisible to pytest's collection, which
is the property that let six of them sit unexamined; so the marks are parsed from
the source. ``tests/test_windows_dimension.py`` holds the ledger that judges
them, and ``tests/test_bead14_s4_binding.py`` proves the ledger's verdict bites.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tests.support.repository_root import TESTS_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True)
class WindowsSkip:
    """A skip that survives review: the facility is absent, not merely awkward."""

    #: The POSIX facility Windows does not provide, named specifically enough
    #: that a reader can check the claim.
    facility: str
    #: Why the behaviour under test cannot arise on Windows at all.
    why: str


@dataclass(frozen=True)
class Marker:
    """One ``pytest.mark.<kind>`` call found in a test module."""

    key: str
    kind: str
    condition: str
    keywords: dict[str, str]


class MarkerFinder(ast.NodeVisitor):
    """Collect ``pytest.mark.skipif`` / ``pytest.mark.xfail`` calls and where they sit."""

    def __init__(self, relative: str) -> None:
        self._relative = relative
        self._scope: list[str] = []
        self.markers: list[Marker] = []

    def _visit_scope(self, node: ast.AST, name: str) -> None:
        self._scope.append(name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scope(node, node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_scope(node, node.name)

    def visit_Call(self, node: ast.Call) -> None:
        kind = _mark_kind(node.func)
        if kind in {"skipif", "xfail"}:
            condition = " ".join(ast.unparse(arg) for arg in node.args)
            keywords = {kw.arg: ast.unparse(kw.value) for kw in node.keywords if kw.arg}
            condition = " ".join([condition, keywords.get("condition", "")]).strip()
            self.markers.append(
                Marker(
                    key=f"{self._relative}::{'::'.join(self._scope) or '<module>'}",
                    kind=kind,
                    condition=condition,
                    keywords=keywords,
                )
            )
        self.generic_visit(node)


def _mark_kind(func: ast.expr) -> str:
    """``pytest.mark.skipif`` -> ``"skipif"``; anything else -> ``""``."""
    if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Attribute):
        return ""
    if func.value.attr != "mark":
        return ""
    return func.attr


def markers_mentioning_platform(kind: str, tests_dir: Path = TESTS_ROOT) -> list[Marker]:
    """Every *kind* marker under *tests_dir* whose condition reads ``sys.platform``.

    Parsed from the source rather than collected from pytest on purpose: a mark
    that is inert on this platform is invisible to collection, which is the very
    property that let six of them sit unexamined.
    """
    found: list[Marker] = []
    for path in sorted(tests_dir.rglob("*.py")):
        finder = MarkerFinder(path.relative_to(tests_dir).as_posix())
        finder.visit(ast.parse(path.read_text(encoding="utf-8")))
        found.extend(
            marker
            for marker in finder.markers
            if marker.kind == kind and "sys.platform" in marker.condition
        )
    return found


def assert_every_platform_skip_is_judged(
    judged: Mapping[str, WindowsSkip], tests_dir: Path = TESTS_ROOT
) -> None:
    """Fail unless the platform skips under *tests_dir* are exactly the *judged* ones.

    Both directions: a skip with no judgement, and a judgement kept after the
    skip it excused was deleted — a stale entry is how a ledger stops describing
    the suite.
    """
    discovered = {marker.key for marker in markers_mentioning_platform("skipif", tests_dir)}
    unjudged = discovered - set(judged)
    stale = set(judged) - discovered
    assert discovered == set(judged), (
        "a platform skip is not accounted for in JUDGED_WINDOWS_SKIPS.\n"
        f"  skipped on a platform with no judgement: {sorted(unjudged)}\n"
        f"  judged but no longer present:            {sorted(stale)}\n"
        "A skip that can never fail proves nothing; either state the POSIX "
        "facility Windows does not have, or make the test platform-independent."
    )
