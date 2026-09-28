"""Steps for `graph/rule-engine/source_root_minority.feature` (BDL-074 E1 rewrite).

BDL-062 `.9`. The steps run the real rule against real indexes on disk; nothing
about the derivation is stubbed, because a stub would agree with whatever the
derivation currently does and that is the thing under test.

**FAKES PROVE FAKES.** Every graph here uses a source root and area names this
repository does not have (`platform/orders`, `atelier/`), so a rule that passed
by recognising Beadloom's own tree would fail these.

The index is written and judged by :class:`~tests.support.rule_engine_driver.DocPlacements`;
the evaluation and what a reader sees of a stand-down are the shared vocabulary
(:mod:`tests.support.rule_engine_vocabulary`).
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

scenarios("../../../graph/rule-engine/source_root_minority.feature")
use_findings_vocabulary()
use_doc_area_vocabulary()

#: The outlier's source. One segment, sharing nothing with the main root — the
#: shape of a committed asset tree beside the code (`site/`, `tooling/`).
OUTLIER_SOURCE = "atelier/"


@pytest.fixture()
def placements(tmp_path: Path) -> DocPlacements:
    return DocPlacements(tmp_path)


@pytest.fixture()
def outcome() -> Outcome:
    return Outcome()


def _coherent(area: str, count: int) -> list[tuple[str, str, str]]:
    return [
        (
            f"{area}-{index}",
            f"platform/{area}/{area}_{index}.py",
            f"reference/{area}/{area}-{index}/SPEC.md",
        )
        for index in range(count)
    ]


@given("a graph whose sources all sit under one root except a single outlier")
def _with_outlier(placements: DocPlacements) -> None:
    """The main tree, with its documents in TWO top-level buckets.

    The second bucket is what makes this fixture bite. Under the correct root
    the compared segment is the area (`orders`, `gateway`) and both buckets are
    coherent. Under a collapsed root the compared segment becomes the BUCKET,
    the majority bucket wins a bogus majority, and the minority bucket's nodes
    are reported as contradicting a convention that does not exist. A fixture
    with one docs bucket cannot exhibit that and would pass either way.
    """
    placements.pairs = (
        _coherent("orders", 5)
        + _coherent("billing", 4)
        + [
            (
                f"gateway-{index}",
                f"platform/gateway/g{index}.py",
                f"endpoints/gateway/gateway-{index}.md",
            )
            for index in range(2)
        ]
    )


@given("the outlier is documented under a directory named after the outlier")
def _outlier_names_itself(placements: DocPlacements) -> None:
    """The `site/vitepress-site/DOC.md` shape, which produced seven false errors.

    The doc path carries the outlier's own source segment, so a collapsed root
    still finds an area depth and derives a convention — the wrong one.
    """
    placements.pairs += [("atelier", OUTLIER_SOURCE, "atelier/atelier-doc/DOC.md")]


@given("the outlier is documented under a directory that names no source area")
def _outlier_names_nothing(placements: DocPlacements) -> None:
    """The `guides/vitepress-site.md` shape, which blanked the whole population.

    No doc path anywhere carries a segment from the collapsed vocabulary, so no
    area depth can be found and every pair becomes uncomparable at once.
    """
    placements.pairs += [("atelier", OUTLIER_SOURCE, "manual/atelier.md")]


@given("a graph no convention can be read from")
def _underivable(placements: DocPlacements) -> None:
    # One documented node per area: every area is "unanimous" at one observation,
    # which `min_support` refuses to call a convention.
    placements.pairs = [
        (area, f"platform/{area}/service.py", f"reference/{area}/service/SPEC.md")
        for area in ("orders", "billing", "catalogue", "search", "payments", "audit")
    ]


@given("the project declared the doc-area-coherence rule blocking")
def _blocking(placements: DocPlacements) -> None:
    placements.severity = "error"


@given("the project left the doc-area-coherence rule at its shipped severity")
def _shipped(placements: DocPlacements) -> None:
    placements.severity = None


@then("the population it states accounts for the outlier")
def _population_names_outlier(placements: DocPlacements) -> None:
    """The outlier is EXCLUDED from comparison, so it must be counted and said.

    A pair dropped without a number is the shape this whole feature removes: the
    reader cannot tell a graph with no outliers from one whose outliers were
    quietly discarded.
    """
    convention = placements.convention
    assert convention is not None
    assert convention.outside_root == 1, (
        f"the outlier was not counted: outside_root={convention.outside_root}"
    )
    population = convention.population()
    assert "1 sit outside" in population, population
    assert convention.examined == len(placements.pairs), (
        "the stated population does not add up to the pairs the graph offered: "
        f"{convention.examined} vs {len(placements.pairs)}"
    )
