# beadloom:domain=application
"""Checked-and-clean, checked-and-wrong and could-not-check print three things.

BDL-062 `.5`. Every rule in this feature tests its own three states against its
own evaluator. Nothing tested that the three survive the trip to the place a
person actually reads them — ``beadloom ci``. That trip is where they are most
likely to collapse, because the Gate summarises: a step reduces a list of
findings to one line, and a summary that reduces "the rule stood down" and "the
rule passed" to the same words hands back a green describing the checker's
ignorance, which is the defect this whole feature exists against.

The tests below run the real Gate over four adopter projects that differ in one
thing each, and assert the four outputs are four different texts. They assert on
**the output stream**, never on a rule's internal verdict: a verdict-level
assertion passes throughout the life of a defect that only loses the
distinction on the way out. (BDL-UX #195 was missed for exactly that reason —
the probe filtered on ``rule_type == "doc_area_coherence"`` and the stand-down
does not report under that type.)

Two families are covered, chosen because their unverifiable paths have
different causes:

``graph-summary-facts``
    ``agrees`` / ``disagrees`` / ``could not be verified`` (the project declined
    the fact) / ``checked nothing`` (no summary states a number at all).

the documentation audit
    ``verified`` / ``declared but unverified`` / ``not applicable``, which the
    Gate's docs-audit line carries as three separate clauses over disjoint sets
    of fact names.

Measured while writing, on ``invoice-svc`` with the version fact removed: the
audit denominator moves 7 -> 6 and ``version`` moves out of ``NOT VERIFIED``
and into ``NOT APPLICABLE``. A denominator that shrinks in silence is the
defect `.3` was written for, and this is the assertion that it does not.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.adopter_project import IndexedProjectSpec, indexed_python_project

if TYPE_CHECKING:
    from pathlib import Path

#: ``rules.yml`` declaring `.1`'s rule alone, so the four Gate outputs differ in
#: the state of ONE rule and in nothing else.
SUMMARY_FACTS_ONLY = (
    "version: 3\n"
    "rules:\n"
    "  - name: graph-summary-facts\n"
    "    description: a number in a node summary matches what the project computes\n"
    "    summary_facts: {}\n"
)

#: The four states, as ``(id, kwargs)``. Each differs from ``agrees`` in one
#: field, so a difference in the Gate's output has one possible cause.
STATES: dict[str, IndexedProjectSpec] = {
    "agrees": {"summaries": {"billing-m0": "The billing module of release v3.7.0"}},
    "disagrees": {"summaries": {"billing-m0": "The billing module of release v9.9.9"}},
    "unverifiable": {
        "version": None,
        "summaries": {"billing-m0": "The billing module of release v3.7.0"},
    },
    "no-claim": {},
}


def _gate(tmp_path: Path, state: str) -> tuple[str, dict[str, object]]:
    """``beadloom ci`` over one state: the text a reader sees, and the payload.

    The two are taken from separate invocations because they are separate
    formats, and both are asserted: the annotation stream is what a person
    reads in CI, the JSON is what a machine consumer reads, and a distinction
    that survives in one and not the other has still been lost.
    """
    spec: IndexedProjectSpec = {"rules": SUMMARY_FACTS_ONLY}
    spec.update(STATES[state])
    project = indexed_python_project(tmp_path / state, **spec)
    runner = CliRunner()
    human = runner.invoke(main, ["ci", "--project", str(project.root)])
    machine = runner.invoke(main, ["ci", "--project", str(project.root), "--format", "json"])
    payload = json.loads(machine.stdout)
    assert isinstance(payload, dict)
    return human.stdout, payload


def _lint_findings(payload: dict[str, object]) -> list[dict[str, str]]:
    """Every finding the lint step reported, whatever ``kind`` it carries.

    Deliberately unfiltered. A stand-down reports under a different ``kind``
    from a violation, so a filter written around the rule's own type is a filter
    that cannot see the state this file exists to keep visible.
    """
    steps = payload["steps"]
    assert isinstance(steps, list)
    for step in steps:
        if step["name"] == "lint":
            return list(step["findings"])
    raise AssertionError("the Gate ran no lint step")


# --------------------------------------------------------------------------- #
# a rule's three states, through the Gate
# --------------------------------------------------------------------------- #


class TestTheFourStatesReachTheReaderAsFourTexts:
    """One rule, four projects, four different things said about it."""

    def test_the_four_gate_outputs_are_pairwise_different(self, tmp_path: Path) -> None:
        """The whole contract in one assertion, before any wording is pinned.

        If two states ever produce the same text this fails without depending on
        which phrase either of them was supposed to use.
        """
        seen: dict[str, str] = {}
        for state in STATES:
            human, _ = _gate(tmp_path, state)
            rule_lines = "\n".join(
                line for line in human.splitlines() if "graph-summary-facts" in line
            )
            seen[state] = rule_lines

        collisions = [
            (a, b)
            for index, a in enumerate(seen)
            for b in list(seen)[index + 1 :]
            if seen[a] == seen[b]
        ]
        assert collisions == [], f"these states print the same words: {collisions}\n{seen}"

    def test_a_clean_check_says_nothing_about_the_rule(self, tmp_path: Path) -> None:
        human, payload = _gate(tmp_path, "agrees")

        assert "graph-summary-facts" not in human
        assert _lint_findings(payload) == []

    def test_a_contradiction_names_the_node_and_both_values(self, tmp_path: Path) -> None:
        human, payload = _gate(tmp_path, "disagrees")

        assert "billing-m0" in human
        assert "v9.9.9" in human and "3.7.0" in human
        assert [f["severity"] for f in _lint_findings(payload)] == ["error"]

    def test_a_declined_fact_says_it_could_not_be_verified(self, tmp_path: Path) -> None:
        """Not "wrong", not silence — a third word, naming the node it applies to.

        The phrase is asserted **bound to the node** rather than on its own. On
        its own it is satisfied by the population clause every finding carries
        ("0 agree, 0 disagree, 1 could not be verified"), so a rule that dropped
        the distinct verdict entirely would still contain the words. Measured:
        rewording the verdict to "checked nothing for `<node>`" leaves the loose
        form green and turns this one red.
        """
        human, payload = _gate(tmp_path, "unverifiable")

        assert "could not be verified for `billing-m0`" in human
        why = " ".join(str(f["why"]) for f in _lint_findings(payload))
        assert "could not be verified for `billing-m0`" in why
        assert "no manifest under this project declares a version" in why

    def test_a_graph_stating_no_number_says_the_rule_checked_nothing(self, tmp_path: Path) -> None:
        """A fourth word again, and it must not be the third one.

        "no summary states a number" and "one summary states a number nothing
        can check" are different facts about the project, and a reader who is
        told the wrong one will look in the wrong place.
        """
        human, payload = _gate(tmp_path, "no-claim")

        assert "checked nothing:" in human
        assert "could not be verified for" not in human
        why = " ".join(str(f["why"]) for f in _lint_findings(payload))
        assert "checked nothing:" in why
        assert "checked nothing for" not in why

    @pytest.mark.parametrize("state", ["unverifiable", "no-claim"])
    def test_an_unverifiable_state_is_never_reported_as_a_pass(
        self, tmp_path: Path, state: str
    ) -> None:
        """UNCHECKED IS NOT CLEAN: the Gate must say something, whatever it exits."""
        human, payload = _gate(tmp_path, state)

        assert _lint_findings(payload), "the Gate reported no finding at all"
        assert "graph-summary-facts" in human


# --------------------------------------------------------------------------- #
# the audit's three populations, through the Gate
# --------------------------------------------------------------------------- #


class TestTheThreePopulationsStayApartInTheGateLine:
    """``verified`` / ``declared but unverified`` / ``not applicable``, disjoint."""

    def _audit_line(self, tmp_path: Path, state: str) -> str:
        _, payload = _gate(tmp_path, state)
        steps = payload["steps"]
        assert isinstance(steps, list)
        for step in steps:
            if step["name"] == "docs-audit":
                return str(step["summary"])
        raise AssertionError("the Gate ran no docs-audit step")

    def test_the_line_carries_all_three_populations(self, tmp_path: Path) -> None:
        line = self._audit_line(tmp_path, "agrees")

        assert "declared fact(s) verified" in line
        assert "NOT VERIFIED:" in line
        assert "NOT APPLICABLE to this project:" in line

    def test_no_fact_is_named_in_two_populations(self, tmp_path: Path) -> None:
        line = self._audit_line(tmp_path, "agrees")

        unverified = _names_after(line, "NOT VERIFIED:")
        declined = _names_after(line, "NOT APPLICABLE to this project:")

        assert unverified and declined
        assert unverified.isdisjoint(declined), unverified & declined

    def test_a_declined_fact_leaves_the_denominator_and_is_named_where_it_went(
        self, tmp_path: Path
    ) -> None:
        """The measured instance: ``version`` moving between two populations.

        The same project with and without a resolvable version. Without the
        pair this asserts only that some fact is somewhere; with it, the
        denominator is shown to move BECAUSE that fact moved, and to say so.
        """
        resolvable = self._audit_line(tmp_path, "agrees")
        unresolvable = self._audit_line(tmp_path, "unverifiable")

        assert "version" in _names_after(resolvable, "NOT VERIFIED:")
        assert "version" not in _names_after(resolvable, "NOT APPLICABLE to this project:")
        assert "version" in _names_after(unresolvable, "NOT APPLICABLE to this project:")
        assert "version" not in _names_after(unresolvable, "NOT VERIFIED:")
        assert _denominator(resolvable) - _denominator(unresolvable) == 1

    def test_the_project_is_told_neither_of_our_own_surface_counts(self, tmp_path: Path) -> None:
        """A SELF-FACT IS NOT A PROJECT FACT, asserted where a user reads it.

        ``invoice-svc`` was measured being told it had 18 MCP tools and 43 CLI
        commands. Both facts are now declined; this holds the Gate line to
        naming them as declined rather than quietly counting them.
        """
        line = self._audit_line(tmp_path, "agrees")
        declined = _names_after(line, "NOT APPLICABLE to this project:")

        assert {"mcp_tool_count", "cli_command_count"} <= declined
        assert "18" not in line and "43" not in line


def _names_after(line: str, marker: str) -> set[str]:
    """The comma-separated fact names a Gate-line clause lists.

    The clauses are appended in a fixed order, so a clause ends at the next
    clause's marker or at the parenthetical that closes the line.
    """
    if marker not in line:
        return set()
    tail = line.split(marker, 1)[1]
    for stop in (", NOT VERIFIED:", ", NOT APPLICABLE to this project:", " ("):
        tail = tail.split(stop, 1)[0]
    return {name.strip() for name in tail.split(",") if name.strip()}


def _denominator(line: str) -> int:
    """The ``M`` of ``N/M declared fact(s) verified``."""
    fragment = line.split("declared fact(s) verified", 1)[0].strip()
    return int(fragment.rsplit("/", 1)[1])


# --------------------------------------------------------------------------- #
# the same contract for a second rule, whose unverifiable path has another cause
# --------------------------------------------------------------------------- #


#: ``rules.yml`` declaring `.2`'s rule alone.
DOC_AREA_ONLY = (
    "version: 3\n"
    "rules:\n"
    "  - name: doc-area-coherence\n"
    "    description: a node documents itself where the graph says it should\n"
    "    doc_area_coherence: {}\n"
)

#: Three projects differing only in where their documents are filed.
PLACEMENTS: dict[str, IndexedProjectSpec] = {
    "coherent": {},
    "contradicted": {"misfiled": ("billing-m0",)},
    "no-convention": {"docs_layout": "flat"},
}


def _doc_area_gate(tmp_path: Path, placement: str) -> str:
    """What ``beadloom ci`` says **about this rule** for one docs placement.

    Narrowed to the rule's own annotation lines. The Gate also reports every
    document as unbaselined on a first run, which mentions each node by name and
    would satisfy an assertion about a node being named without the rule having
    said anything at all.
    """
    spec: IndexedProjectSpec = {"rules": DOC_AREA_ONLY}
    spec.update(PLACEMENTS[placement])
    project = indexed_python_project(tmp_path / placement, **spec)
    output = CliRunner().invoke(main, ["ci", "--project", str(project.root)]).stdout
    return "\n".join(line for line in output.splitlines() if "doc-area-coherence" in line)


class TestAFlatDocsTreeIsNotAPass:
    """A tree with no convention to derive is a third outcome, not a clean one.

    The fixture is the same twelve nodes in all three projects. Only the doc
    paths move, so a difference in the Gate's output has exactly one cause —
    and the coherent project is the control without which the stand-down would
    prove only that the fixture was broken.
    """

    def test_the_three_placements_print_three_different_things(self, tmp_path: Path) -> None:
        """The wording-independent half, so a reword cannot quietly merge two."""
        seen = {placement: _doc_area_gate(tmp_path, placement) for placement in PLACEMENTS}

        collisions = [
            (a, b)
            for index, a in enumerate(seen)
            for b in list(seen)[index + 1 :]
            if seen[a] == seen[b]
        ]
        assert collisions == [], f"these placements print the same words: {collisions}"

    def test_a_derivable_convention_that_holds_says_nothing(self, tmp_path: Path) -> None:
        assert "doc-area-coherence" not in _doc_area_gate(tmp_path, "coherent")

    def test_a_contradicted_convention_names_the_node(self, tmp_path: Path) -> None:
        output = _doc_area_gate(tmp_path, "contradicted")

        assert "doc-area-coherence" in output
        assert "billing-m0" in output

    def test_a_flat_tree_says_the_rule_checked_nothing(self, tmp_path: Path) -> None:
        """The point of the rule, and the state its own README calls unverifiable.

        A flat docs tree is a legitimate house style. It is not a graph whose
        placement was checked and found correct, and the Gate must not describe
        it with the silence it uses for one.
        """
        output = _doc_area_gate(tmp_path, "no-convention")

        assert "doc-area-coherence" in output
        assert "checked nothing" in output
        assert "billing-m0" not in output
