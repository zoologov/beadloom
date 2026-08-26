"""Step implementations for `features/source_root_minority.feature`.

BDL-062 `.9`. The steps run the real rule against real indexes on disk; nothing
about the derivation is stubbed, because a stub would agree with whatever the
derivation currently does and that is the thing under test.

**FAKES PROVE FAKES.** Every graph here uses a source root and area names this
repository does not have (`platform/orders`, `atelier/`), so a rule that passed
by recognising Beadloom's own tree would fail these.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.graph.rules import (
    DOC_AREA_RULE_TYPE,
    LIVENESS_RULE_TYPE,
    DocAreaCoherenceRule,
    evaluate_doc_area_coherence_rules,
)
from beadloom.graph.rules.doc_area import derive_convention
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

scenarios("../features/source_root_minority.feature")

#: The outlier's source. One segment, sharing nothing with the main root — the
#: shape of a committed asset tree beside the code (`site/`, `tooling/`).
OUTLIER_SOURCE = "atelier/"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _index(tmp_path: Path, pairs: list[tuple[str, str, str]]) -> sqlite3.Connection:
    conn = open_db(tmp_path / "graph.db")
    create_schema(conn)
    for ref_id, source, doc in pairs:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, "feature", "", source),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            (doc, "feature", ref_id, ""),
        )
    conn.commit()
    return conn


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
def _with_outlier(world: dict[str, Any]) -> None:
    """The main tree, with its documents in TWO top-level buckets.

    The second bucket is what makes this fixture bite. Under the correct root
    the compared segment is the area (`orders`, `gateway`) and both buckets are
    coherent. Under a collapsed root the compared segment becomes the BUCKET,
    the majority bucket wins a bogus majority, and the minority bucket's nodes
    are reported as contradicting a convention that does not exist. A fixture
    with one docs bucket cannot exhibit that and would pass either way.
    """
    world["pairs"] = (
        _coherent("orders", 5)
        + _coherent("billing", 4)
        + [
            (f"gateway-{index}", f"platform/gateway/g{index}.py",
             f"endpoints/gateway/gateway-{index}.md")
            for index in range(2)
        ]
    )


@given("the outlier is documented under a directory named after the outlier")
def _outlier_names_itself(world: dict[str, Any]) -> None:
    """The `site/vitepress-site/DOC.md` shape, which produced seven false errors.

    The doc path carries the outlier's own source segment, so a collapsed root
    still finds an area depth and derives a convention — the wrong one.
    """
    world["pairs"] = world["pairs"] + [
        ("atelier", OUTLIER_SOURCE, "atelier/atelier-doc/DOC.md")
    ]


@given("the outlier is documented under a directory that names no source area")
def _outlier_names_nothing(world: dict[str, Any]) -> None:
    """The `guides/vitepress-site.md` shape, which blanked the whole population.

    No doc path anywhere carries a segment from the collapsed vocabulary, so no
    area depth can be found and every pair becomes uncomparable at once.
    """
    world["pairs"] = world["pairs"] + [
        ("atelier", OUTLIER_SOURCE, "manual/atelier.md")
    ]


@given("a graph no convention can be read from")
def _underivable(world: dict[str, Any]) -> None:
    # One documented node per area: every area is "unanimous" at one observation,
    # which `min_support` refuses to call a convention.
    world["pairs"] = [
        (area, f"platform/{area}/service.py", f"reference/{area}/service/SPEC.md")
        for area in ("orders", "billing", "catalogue", "search", "payments", "audit")
    ]


@given("the project declared the doc-area-coherence rule blocking")
def _blocking(world: dict[str, Any]) -> None:
    world["severity"] = "error"


@given("the project left the doc-area-coherence rule at its shipped severity")
def _shipped(world: dict[str, Any]) -> None:
    world["severity"] = None


@when("the doc-area-coherence rule is evaluated")
def _evaluate(world: dict[str, Any], tmp_path: Path) -> None:
    conn = _index(tmp_path, world["pairs"])
    kwargs: dict[str, Any] = {
        "name": "doc-area-coherence",
        "description": "a node documents itself where its graph says it should",
    }
    if world.get("severity") is not None:
        kwargs["severity"] = world["severity"]
    rule = DocAreaCoherenceRule(**kwargs)
    world["violations"] = evaluate_doc_area_coherence_rules(conn, [rule])
    world["convention"] = derive_convention(
        conn, threshold=rule.threshold, min_support=rule.min_support
    )
    conn.close()


def _reported(world: dict[str, Any]) -> list[Any]:
    return [v for v in world["violations"] if v.rule_type == DOC_AREA_RULE_TYPE]


def _liveness(world: dict[str, Any]) -> list[Any]:
    return [v for v in world["violations"] if v.rule_type == LIVENESS_RULE_TYPE]


@then("no node is reported")
def _none_reported(world: dict[str, Any]) -> None:
    named = [v.from_ref_id for v in _reported(world)]
    assert named == [], f"the rule reported {named}, which the outlier did not make wrong"


@then("the rule does not report that it checked nothing")
def _not_inert(world: dict[str, Any]) -> None:
    messages = [v.message for v in _liveness(world)]
    assert messages == [], f"the rule stood down: {messages}"


@then("the population it states accounts for the outlier")
def _population_names_outlier(world: dict[str, Any]) -> None:
    """The outlier is EXCLUDED from comparison, so it must be counted and said.

    A pair dropped without a number is the shape this whole feature removes: the
    reader cannot tell a graph with no outliers from one whose outliers were
    quietly discarded.
    """
    convention = world["convention"]
    assert convention.outside_root == 1, (
        f"the outlier was not counted: outside_root={convention.outside_root}"
    )
    population = convention.population()
    assert "1 sit outside" in population, population
    assert convention.examined == len(world["pairs"]), (
        "the stated population does not add up to the pairs the graph offered: "
        f"{convention.examined} vs {len(world['pairs'])}"
    )


@then("the rule reports that it checked nothing")
def _inert(world: dict[str, Any]) -> None:
    liveness = _liveness(world)
    assert len(liveness) == 1, f"expected one stand-down report, got {len(liveness)}"
    assert "checked nothing" in liveness[0].message


@then("that report carries the severity the project declared")
def _carries_declared(world: dict[str, Any]) -> None:
    assert _liveness(world)[0].severity == world["severity"]


@then("that report is advisory")
def _advisory(world: dict[str, Any]) -> None:
    assert _liveness(world)[0].severity == "warn"
