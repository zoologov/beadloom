"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_bead14_s4_binding.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.graph.rules import (
    ScenarioCoverageRule,
    load_rules,
)
from tests.support.repository_root import REPO_ROOT

#: This repository, so the shipped configuration is read rather than restated.


GRAPH_DIR = REPO_ROOT / ".beadloom" / "_graph"


def _shipped_scenario_coverage_rule() -> ScenarioCoverageRule:
    """The rule THIS repository runs, read from the file it is configured in."""
    rules = load_rules(GRAPH_DIR / "rules.yml")
    matching = [r for r in rules if isinstance(r, ScenarioCoverageRule)]
    assert len(matching) == 1, (
        "expected exactly one scenario_coverage rule in the shipped rules.yml; "
        f"found {len(matching)}"
    )
    return matching[0]


class TestTheReferenceLegsWidestSurface:
    """A line beginning with a scenario keyword after markdown stripping.

    `.13` named this the widest surface in the slice, and it is: the suite half is
    bounded by Gherkin's grammar, while this half reads arbitrary prose. Every row
    below is one shape a real planning document contains. Two of them are
    findings — asserted as they SHOULD behave and marked `xfail(strict=True)`, so
    the runner adjudicates the prediction and a fix fails the suite instead of
    passing silently.
    """

    def test_the_shipped_reference_globs_read_more_than_the_document_that_added_them(
        self,
    ) -> None:
        """The leg's own population, so it cannot quietly become one file.

        33 missing references is a statement about intent only if the globs still
        reach every document that states intent. Narrowing `references:` to the one
        PRD that uses the convention would leave the number unchanged while making
        the check unable to find a new document — the population failure of the
        coverage leg, in the leg nobody would look at.
        """
        rule = _shipped_scenario_coverage_rule()
        matched = [
            path for glob in rule.references for path in REPO_ROOT.glob(glob) if path.is_file()
        ]

        assert rule.references, "the reference leg is switched off entirely"
        assert len(matched) >= 20, (
            f"the reference globs {rule.references} reach only {len(matched)} "
            "documents — the leg is checking a hand-picked file rather than the "
            "space where intent is written"
        )
