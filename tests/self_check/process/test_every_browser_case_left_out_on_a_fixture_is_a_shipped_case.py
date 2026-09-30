"""Each browser case left out on an adopter fixture names a case that ships, with a reason.

BDL-076 B3 (``beadloom-hmqn``). ``tests.support.portal_browser_tests`` leaves some
of the shipped Playwright cases out of the fixture runs, by file or by title. A
title that no longer matches a case would leave out nothing and still read as a
decision; a case renamed would silently start running, or silently stop. So each
name is checked against the specs as they ship, and each reason is a sentence.
"""

from __future__ import annotations

import re

import pytest

from tests.support.portal_browser_tests import (
    FILES_NOT_RUN,
    SHIPPED_SPECS,
    TITLES_HELD_BY_DEFECT,
    TITLES_NOT_RUN,
    TITLES_NOT_RUN_BY_STACK,
)

#: A test's title as a spec writes it: the first argument of ``test(``, in any quote.
_TITLE = re.compile(r"""\btest\(\s*(["'`])(.+?)\1\s*,""", re.DOTALL)

#: A template literal's substitution, which stands for any text in the title.
_SUBSTITUTION = re.compile(r"\$\{[^}]*\}")


def _title_patterns() -> list[re.Pattern[str]]:
    """Every shipped case's title, as a pattern its rendered titles match."""
    patterns = []
    for spec in sorted(SHIPPED_SPECS.glob("*.spec.js")):
        for _, title in _TITLE.findall(spec.read_text(encoding="utf-8")):
            parts = _SUBSTITUTION.split(title)
            patterns.append(re.compile(".+".join(re.escape(part) for part in parts)))
    return patterns


def _left_out() -> dict[str, str]:
    titles = dict(TITLES_NOT_RUN)
    for by_title in (*TITLES_NOT_RUN_BY_STACK.values(), *TITLES_HELD_BY_DEFECT.values()):
        titles.update(by_title)
    return titles


def test_the_shipped_specs_are_read() -> None:
    assert len(_title_patterns()) > 50


@pytest.mark.parametrize("name", sorted(FILES_NOT_RUN))
def test_a_spec_file_left_out_ships_in_the_scaffold(name: str) -> None:
    assert (SHIPPED_SPECS / name).is_file()


@pytest.mark.parametrize("title", sorted(_left_out()))
def test_a_case_left_out_is_a_shipped_case(title: str) -> None:
    assert any(pattern.fullmatch(title) for pattern in _title_patterns())


@pytest.mark.parametrize("title", sorted(_left_out()))
def test_a_case_left_out_is_not_in_a_file_already_left_out(title: str) -> None:
    """A title inside a file left out whole leaves out nothing more, and misleads."""
    in_files = [
        name
        for name in FILES_NOT_RUN
        if any(
            re.compile(".+".join(map(re.escape, _SUBSTITUTION.split(t)))).fullmatch(title)
            for _, t in _TITLE.findall((SHIPPED_SPECS / name).read_text(encoding="utf-8"))
        )
    ]

    assert in_files == []


@pytest.mark.parametrize("reason", sorted({*FILES_NOT_RUN.values(), *_left_out().values()}))
def test_every_reason_names_the_shape_the_fixture_lacks(reason: str) -> None:
    assert len(reason.split()) >= 8


@pytest.mark.parametrize(
    "reason", sorted(r for held in TITLES_HELD_BY_DEFECT.values() for r in held.values())
)
def test_a_case_held_back_by_a_defect_names_its_bead(reason: str) -> None:
    assert re.match(r"beadloom-[a-z0-9]+(\.\d+)?: ", reason)
