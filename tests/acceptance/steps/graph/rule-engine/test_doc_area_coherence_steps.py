"""Steps for `graph/rule-engine/doc_area_coherence.feature` (BDL-062 `.2`; BDL-074 E1).

The steps build a real index — real ``nodes`` and ``docs`` rows — and run the
real rule against it. Nothing is doubled: the whole claim of this rule is that it
reads a convention out of a graph it has never seen, and a double would be a
graph written by the person asserting the answer (FAKES PROVE FAKES).

Every tree below is deliberately NOT this repository's: the source root is
``app/`` and the areas are ``billing``/``shipping``, so a rule that passed by
knowing Beadloom's own layout would fail here.

The index is written and judged by :class:`~tests.support.rule_engine_driver.DocPlacements`;
the evaluation and what a reader sees of a stand-down are the shared vocabulary
(:mod:`tests.support.rule_engine_vocabulary`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, scenarios, then

from beadloom.graph.rules import DOC_AREA_RULE_TYPE
from tests.support.rule_engine_driver import DocPlacements, Outcome
from tests.support.rule_engine_vocabulary import (
    use_doc_area_vocabulary,
    use_findings_vocabulary,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/doc_area_coherence.feature")
use_findings_vocabulary()
use_doc_area_vocabulary()

#: The areas a graph with no convention is laid out over.
AREAS = ("billing", "shipping", "catalogue", "search", "payments", "audit")


@pytest.fixture()
def placements(tmp_path: Path) -> DocPlacements:
    return DocPlacements(tmp_path)


@pytest.fixture()
def outcome() -> Outcome:
    return Outcome()


@given(
    parsers.parse(
        'a graph where {count:d} nodes under source area "{area}" '
        'are documented under "{docs_area}"'
    )
)
def _agreeing_nodes(placements: DocPlacements, count: int, area: str, docs_area: str) -> None:
    for index in range(count):
        ref_id = f"{area}-{index}"
        placements.place(
            ref_id, f"app/{area}/{ref_id}.py", f"reference/{docs_area}/{ref_id}/SPEC.md"
        )


@given(
    parsers.parse(
        '{count:d} stray node under source area "{area}" is documented under "{docs_area}"'
    )
)
def _stray_nodes(placements: DocPlacements, count: int, area: str, docs_area: str) -> None:
    for index in range(count):
        ref_id = f"{area}-stray-{index}"
        placements.place(
            ref_id, f"app/{area}/{ref_id}.py", f"reference/{docs_area}/{ref_id}/SPEC.md"
        )


@given("the documentation is laid out flat at the root of the docs tree")
def _flat_docs(placements: DocPlacements) -> None:
    for area in ("billing", "shipping"):
        for index in range(4):
            ref_id = f"{area}-{index}"
            placements.place(ref_id, f"app/{area}/{ref_id}.py", f"{ref_id}.md")


@given("the documentation is laid out as one documented node per source area")
def _one_node_per_area(placements: DocPlacements) -> None:
    for area in AREAS:
        placements.place(area, f"app/{area}/service.py", f"reference/{area}/service/SPEC.md")


@then("the stray node is reported")
def _stray_reported(outcome: Outcome) -> None:
    reported = DocPlacements.reported(outcome.run)
    assert reported == ["billing-stray-0"], f"expected exactly the stray node, got {reported}"


@then("the finding states the sample size and the threshold")
def _states_population(outcome: Outcome) -> None:
    reported = outcome.run.of_type(DOC_AREA_RULE_TYPE)
    assert reported, "no doc-area finding to inspect"
    message = reported[0].message
    assert "8 node/doc pairs" in message, message
    assert "0.60" in message, message
