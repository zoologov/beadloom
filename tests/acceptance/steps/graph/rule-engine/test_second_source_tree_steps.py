"""Steps for `graph/rule-engine/second_source_tree.feature` (BDL-076 K3, `beadloom-5o48`).

The steps run the real rule against real indexes on disk; the derivation is not
stubbed, because a stub would agree with whatever the derivation does today.

**FAKES PROVE FAKES.** The trees here are `platform/` beside `storefront/web/`,
documented under `reference/`, `handbook/` and `manual/`. This repository has none
of them, so a rule that passed by recognising `src/` and `site/` would fail here.

The index is written and judged by :class:`~tests.support.rule_engine_driver.DocPlacements`.
The evaluation step and the stand-down steps are the shared vocabulary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, scenarios, then

from tests.support.rule_engine_driver import DocPlacements, Outcome
from tests.support.rule_engine_vocabulary import (
    use_doc_area_vocabulary,
    use_findings_vocabulary,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/second_source_tree.feature")
use_findings_vocabulary()
use_doc_area_vocabulary()

#: The frontend tree's root: a tree whose areas begin two segments down.
FRONTEND = "storefront/web"

#: The two misplaced nodes the two-tree scenarios plant, one per tree.
BACKEND_STRAY = "orders-stray"
FRONTEND_STRAY = "widgets-stray"


@pytest.fixture()
def placements(tmp_path: Path) -> DocPlacements:
    return DocPlacements(tmp_path)


@pytest.fixture()
def outcome() -> Outcome:
    return Outcome()


def _backend(area: str, count: int) -> list[tuple[str, str, str]]:
    return [
        (
            f"{area}-{index}",
            f"platform/{area}/{area}_{index}.py",
            f"reference/{area}/{area}-{index}/SPEC.md",
        )
        for index in range(count)
    ]


def _frontend(area: str, count: int, doc: str) -> list[tuple[str, str, str]]:
    """*count* frontend slices under *area*; *doc* is formatted with area and index."""
    return [
        (
            f"{area}-{index}",
            f"{FRONTEND}/{area}/{area}-{index}/",
            doc.format(area=area, index=index),
        )
        for index in range(count)
    ]


@given("a backend tree and a frontend tree of several nodes each")
def _two_trees(placements: DocPlacements) -> None:
    placements.pairs = _backend("orders", 5) + _backend("billing", 4)


@given("the frontend's documents name the frontend's own areas")
def _frontend_names_its_areas(placements: DocPlacements) -> None:
    placements.pairs += _frontend(
        "widgets", 3, "handbook/{area}/{area}-{index}/README.md"
    ) + _frontend("entities", 3, "handbook/{area}/{area}-{index}/README.md")


@given("the frontend's documents sit together under one shared directory")
def _frontend_sits_together(placements: DocPlacements) -> None:
    """The shape this repository's site has: every slice under one directory.

    No document names a frontend area, so the frontend's own documents cannot say
    at which depth areas are named; the depth the backend's documents name areas
    at is read instead, and that segment is the shared directory.
    """
    placements.pairs += _frontend(
        "widgets", 3, "reference/storefront/{area}-{index}.md"
    ) + _frontend("entities", 3, "reference/storefront/{area}-{index}.md")


@given("one backend node is documented under another backend area")
def _backend_stray(placements: DocPlacements) -> None:
    placements.place(BACKEND_STRAY, "platform/orders/stray.py", "reference/billing/stray/SPEC.md")


@given("one frontend node is documented under another frontend area")
def _frontend_stray_in_frontend(placements: DocPlacements) -> None:
    placements.place(
        FRONTEND_STRAY, f"{FRONTEND}/widgets/stray/", "handbook/entities/stray/README.md"
    )


@given("one frontend node is documented under a backend area")
def _frontend_stray_in_backend(placements: DocPlacements) -> None:
    placements.place(
        FRONTEND_STRAY, f"{FRONTEND}/widgets/stray/", "reference/orders/stray/SPEC.md"
    )


@given("a graph whose areas are top-level directories named by the documents")
def _top_level_areas(placements: DocPlacements) -> None:
    """A repository of top-level packages, each package an area (`ledger/`, `catalogue/`).

    The descent forks at the top here exactly as it does for two source trees,
    and reading each package as a tree of its own would leave every node with no
    area below its root. The documents name the packages, so the fork is where
    the areas begin, which is how the rule read this graph before trees existed.
    """
    placements.pairs = [
        (f"{area}-{index}", f"{area}/{area}_{index}.py", f"manual/{area}/{area}-{index}.md")
        for area, count in (("ledger", 4), ("catalogue", 3))
        for index in range(count)
    ]


@given("one node is documented under another area")
def _top_level_stray(placements: DocPlacements) -> None:
    placements.place("ledger-stray", "ledger/stray.py", "manual/catalogue/stray.md")


@then("exactly the two misplaced nodes are reported")
def _both_strays(outcome: Outcome) -> None:
    reported = sorted(str(ref) for ref in DocPlacements.reported(outcome.run))
    assert reported == sorted([BACKEND_STRAY, FRONTEND_STRAY]), reported


@then("only that node is reported")
def _only_the_stray(outcome: Outcome) -> None:
    assert DocPlacements.reported(outcome.run) == ["ledger-stray"]


@then("the population it states names both source trees and their counts")
def _population_per_tree(placements: DocPlacements) -> None:
    convention = placements.convention
    assert convention is not None
    population = convention.population()
    assert "`platform`: 9 of 9 pairs compare" in population, population
    assert f"`{FRONTEND}`: 6 of 6 pairs compare" in population, population


@then("the population it states names no source tree")
def _population_single(placements: DocPlacements) -> None:
    convention = placements.convention
    assert convention is not None
    assert "per source tree" not in convention.population(), convention.population()
