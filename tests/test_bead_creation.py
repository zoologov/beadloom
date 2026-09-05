"""The bead-creation path: no id authored, one process (BDL-068 S5, #171, #165).

Every measurement quoted here was taken on bd 1.0.4 (``ce242a879``) in isolated
``bd init`` rigs, streams read separately and exit codes read without a pipe. The
suite does not invoke ``bd``: it exercises how a creation path of ours composes a
plan and reads an answer, which is the half that is ours to get right.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from beadloom.application.waves import title_references
from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_ALLOCATED_ID,
    ASSUMPTION_ECHOED_TITLES,
    ASSUMPTION_INTENDED_ID,
    ASSUMPTIONS,
    VERDICT_SECURED,
    VERDICT_UNSECURED,
    call_sites,
)
from beadloom.services.bd_seam.creation import (
    EDGE_BLOCKS,
    PLAN_THRESHOLD,
    AuthoredNumberError,
    PlannedBead,
    allocated_ids,
    created_id,
    graph_plan,
    plan_is_required,
)
from beadloom.services.bd_seam.invocations import text_invocations
from beadloom.services.bd_seam.population import project_report

_ROLES = ("dev", "test", "review", "tech-writer")


def _chain(count: int = 4) -> tuple[PlannedBead, ...]:
    """The mandatory role DAG, each bead blocked by the one before it."""
    return tuple(
        PlannedBead(
            key=role,
            title=f"[BDL-068] {role}: {role} work",
            depends_on=() if index == 0 else (_ROLES[index - 1],),
        )
        for index, role in enumerate(_ROLES[:count])
    )


def _judge(body: str) -> tuple[tuple[str, str], ...]:
    """Every ``(assumption, verdict)`` a one-artifact population reports."""
    sites = call_sites(text_invocations((("guide.md", body),)))
    return tuple(
        (entry.name, entry.verdict) for site in sites for entry in site.assumptions
    )


class TestThePlanNamesKeysAndNeverIds:
    """BDL-UX #171's root: a number authored before the tracker allocated one."""

    def test_every_edge_names_two_plan_keys(self) -> None:
        plan = graph_plan(_chain())
        keys = {node["key"] for node in plan["nodes"]}
        assert plan["edges"] == [
            {"from_key": "test", "to_key": "dev", "type": EDGE_BLOCKS},
            {"from_key": "review", "to_key": "test", "type": EDGE_BLOCKS},
            {"from_key": "tech-writer", "to_key": "review", "type": EDGE_BLOCKS},
        ]
        assert all(edge["from_key"] in keys and edge["to_key"] in keys for edge in plan["edges"])

    def test_a_plan_with_no_parent_carries_no_id_at_all(self) -> None:
        assert "_id" not in json.dumps(graph_plan(_chain()))

    def test_a_parent_the_tracker_already_answered_with_is_not_an_authored_id(self) -> None:
        """An allocated id read back from bd is a different fact from one authored.

        The plan schema key is ``parent_id`` and not ``parent``: measured on
        1.0.4, a node spelling it ``parent`` is accepted at exit 0 and the parent
        is silently not set.
        """
        plan = graph_plan((PlannedBead(key="dev", title="dev", parent_id="proj-af8"),))
        assert plan["nodes"][0]["parent_id"] == "proj-af8"
        assert "parent" not in {key for key in plan["nodes"][0] if key != "parent_id"}

    def test_an_optional_field_nobody_set_is_absent_rather_than_blank(self) -> None:
        node = graph_plan((PlannedBead(key="dev", title="dev"),))["nodes"][0]
        assert set(node) == {"key", "title", "type"}

    def test_a_priority_somebody_set_is_written(self) -> None:
        node = graph_plan((PlannedBead(key="dev", title="dev", priority=1),))["nodes"][0]
        assert node["priority"] == 1

    def test_an_empty_plan_is_a_document_with_no_nodes_and_no_edges(self) -> None:
        assert graph_plan(()) == {"nodes": [], "edges": []}


class TestATitleDoesNotRestateANumberNobodyHasAllocated:
    """The convention, enforced where the divergence is created rather than after."""

    def test_a_title_carrying_a_bead_number_is_refused(self) -> None:
        beads = (PlannedBead(key="dev", title="[BDL-061.39][dev] the split"),)
        with pytest.raises(AuthoredNumberError) as raised:
            graph_plan(beads)
        assert "BDL-061.39" in str(raised.value)

    def test_the_refusal_names_every_offending_title_not_only_the_first(self) -> None:
        beads = (
            PlannedBead(key="dev", title="[BDL-061.39][dev] one"),
            PlannedBead(key="test", title="[BDL-061.40][test] two"),
        )
        with pytest.raises(AuthoredNumberError) as raised:
            graph_plan(beads)
        message = str(raised.value)
        assert "BDL-061.39" in message
        assert "BDL-061.40" in message
        assert message.startswith("2 planned title(s)")

    def test_a_title_without_a_number_is_planned_without_complaint(self) -> None:
        assert graph_plan(_chain())["nodes"]

    def test_a_version_string_in_a_title_is_not_a_bead_number(self) -> None:
        """The grammar's bounding classes keep ``v2.2.0`` and ``3.10`` out."""
        beads = (PlannedBead(key="dev", title="bump mcp to 2.2.0 on python 3.10"),)
        assert graph_plan(beads)["nodes"]

    def test_the_grammar_is_the_wave_plan_s_and_not_a_second_one(self) -> None:
        """One grammar read twice: written here, compared in `beadloom waves`.

        This reddens the day a second reader of bead references appears, which is
        the duplication `beadloom-0mdo.51` deleted from the landing lock.
        """
        assert title_references("[BDL-061.39][dev] x") == ("BDL-061.39",)
        with pytest.raises(AuthoredNumberError):
            graph_plan((PlannedBead(key="k", title="[BDL-061.39][dev] x"),))


class TestTheAnswerIsReadFromBdRatherThanScraped:
    def test_the_key_to_id_mapping_is_read_from_the_json_answer(self) -> None:
        answer = json.dumps({"ids": {"dev": "proj-fac", "test": "proj-5lm"}, "schema_version": 1})
        assert allocated_ids(answer) == {"dev": "proj-fac", "test": "proj-5lm"}

    def test_an_unreadable_answer_is_not_a_plan_that_created_nothing(self) -> None:
        """``None`` and ``{}`` must not collapse — the same rule as ``ready_ids``.

        Returning an empty mapping for an unreadable answer would turn a failed
        read into "the tracker allocated nothing", and the caller would report a
        successful scaffold with no beads.
        """
        human = "Created 2 issues\n  dev -> proj-fac\n  test -> proj-5lm\n"
        assert allocated_ids(human) is None
        assert allocated_ids(json.dumps({"ids": {}})) == {}

    def test_an_answer_that_is_not_an_object_is_unreadable(self) -> None:
        assert allocated_ids("[]") is None
        assert allocated_ids(json.dumps({"ids": ["proj-fac"]})) is None

    def test_a_single_create_reports_the_id_it_allocated(self) -> None:
        answer = json.dumps({"id": "proj-bbl", "title": "a title", "status": "open"})
        assert created_id(answer) == "proj-bbl"

    def test_the_last_line_of_silent_output_is_not_an_answer(self) -> None:
        """``--silent`` prints the id, and reading it means trusting a layout."""
        assert created_id("proj-bbl\n") is None
        assert created_id(json.dumps({"title": "no id here"})) is None

    def test_the_creation_site_is_visible_to_the_derivation_that_judges_it(self) -> None:
        """The argv is spelled at the call, because a helper would hide it.

        `bd_seam.invocations` resolves a list literal handed to ``run_bd`` and
        cannot follow a function call, so an argv builder here would leave the
        scaffold reporting NOTHING rather than reporting `secured`. This reddens
        the day the literal is tidied into a helper.
        """
        report = project_report(Path(__file__).resolve().parents[1])
        creates = [
            site
            for site in report.sites
            if site.channel == "python" and site.subcommand == "create"
        ]
        assert creates, "the scaffold's `bd create` is invisible to the derivation"
        assert all("--graph" in site.flags and "--json" in site.flags for site in creates)


class TestTheThresholdIsAboutIdsAndNotAboutSpeed:
    def test_one_bead_is_created_directly_and_two_are_planned(self) -> None:
        assert plan_is_required(1) is False
        assert plan_is_required(2) is True

    def test_the_threshold_is_one_because_two_beads_imply_an_edge(self) -> None:
        """Stated as an assertion so the reason cannot drift from the number.

        Speed is the consequence: 69.45 s over 119 processes against 1.15 s over
        one, for a 60-bead DAG with 59 edges. The reason is that the second bead
        is the first one that needs an edge, and an edge wired by hand is an id
        somebody wrote down.
        """
        assert PLAN_THRESHOLD == 1


class TestTheDerivationSeesBothSecuringShapes:
    """A call site fixed by this bead is visible to the report that found it."""

    def test_a_create_that_asks_for_the_allocated_id_is_secured(self) -> None:
        judged = _judge("Run `bd create --type task --parent <parent-id> --json`.\n")
        assert (ASSUMPTION_ALLOCATED_ID, VERDICT_SECURED) in judged

    def test_a_create_from_a_plan_is_secured_because_it_authors_no_id(self) -> None:
        judged = _judge("Run `bd create --graph plan.json --json`.\n")
        assert (ASSUMPTION_ALLOCATED_ID, VERDICT_SECURED) in judged

    def test_a_create_that_scrapes_its_id_is_unsecured(self) -> None:
        judged = _judge("Run `bd create --type task --parent <parent-id> --silent`.\n")
        assert (ASSUMPTION_ALLOCATED_ID, VERDICT_UNSECURED) in judged

    def test_the_allocated_id_detail_names_the_flat_id_the_plan_form_takes(self) -> None:
        sites = call_sites(text_invocations((("g.md", "`bd create --type task`\n"),)))
        detail = next(
            entry.detail
            for entry in sites[0].assumptions
            if entry.name == ASSUMPTION_ALLOCATED_ID
        )
        assert "FLAT id" in detail
        assert "measured on bd 1.0.4" in detail

    def test_a_wiring_the_artifact_tells_its_reader_to_verify_is_secured(self) -> None:
        body = "Run `bd dep add <blocked> <blocker>` then `bd dep tree <parent-id>`.\n"
        judged = _judge(body)
        assert (ASSUMPTION_INTENDED_ID, VERDICT_SECURED) in judged

    def test_a_wiring_nothing_verifies_is_unsecured(self) -> None:
        judged = _judge("Run `bd dep add <blocked> <blocker>`.\n")
        assert (ASSUMPTION_INTENDED_ID, VERDICT_UNSECURED) in judged

    def test_the_confirmation_does_not_leak_between_two_artifacts(self) -> None:
        """The unit is the artifact, because the artifact is what a reader reads."""
        sites = call_sites(
            text_invocations(
                (
                    ("wire.md", "Run `bd dep add <a> <b>`.\n"),
                    ("verify.md", "Run `bd dep tree <parent-id>`.\n"),
                )
            )
        )
        verdicts = {
            (site.source, entry.verdict)
            for site in sites
            for entry in site.assumptions
            if entry.name == ASSUMPTION_INTENDED_ID
        }
        assert ("wire.md", VERDICT_UNSECURED) in verdicts


class TestTheEchoIsPreservedAndTheFormThatDiscardsItIsNamed:
    """`bd dep add` echoes both titles; `--file` prints a count and no titles."""

    def test_bulk_wiring_is_reported_rather_than_silently_faster(self) -> None:
        judged = _judge("Run `bd dep add --file edges.ndjson`.\n")
        assert (ASSUMPTION_ECHOED_TITLES, VERDICT_UNSECURED) in judged

    def test_one_by_one_wiring_makes_no_such_claim(self) -> None:
        """The rule applies only to the form that discards the echo."""
        names = {name for name, _ in _judge("Run `bd dep add <a> <b>`.\n")}
        assert ASSUMPTION_ECHOED_TITLES not in names

    def test_the_detail_quotes_what_bd_prints_instead_of_the_titles(self) -> None:
        sites = call_sites(
            text_invocations((("g.md", "`bd dep add --file edges.ndjson`\n"),))
        )
        detail = next(
            entry.detail
            for entry in sites[0].assumptions
            if entry.name == ASSUMPTION_ECHOED_TITLES
        )
        assert "Added 2 dependencies" in detail
        assert "Added dependency" in detail

    def test_naming_the_verification_settles_the_bulk_form_too(self) -> None:
        body = "Run `bd dep add --file edges.ndjson` then `bd dep tree <id>`.\n"
        judged = _judge(body)
        assert (ASSUMPTION_ECHOED_TITLES, VERDICT_SECURED) in judged

    def test_the_new_assumption_is_in_the_report_s_vocabulary(self) -> None:
        """An assumption the report cannot name is one `--assumption` rejects."""
        assert ASSUMPTION_ECHOED_TITLES in ASSUMPTIONS


class TestThisProjectSOwnPopulation:
    """What the derived report says about this repository after the fix."""

    def test_no_python_call_site_of_ours_authors_a_bead_id(self) -> None:
        """The two sites BDL-UX #171 named in our own code are settled.

        This reddens the day a Python creation path goes back to scraping an id
        out of ``--silent`` or wiring an edge from an id it authored.
        """
        report = project_report(Path(__file__).resolve().parents[1])
        offending = [
            f"{site.source}:{site.line} {site.subcommand}"
            for site in report.sites
            if site.channel == "python"
            for entry in site.assumptions
            if entry.name in (ASSUMPTION_ALLOCATED_ID, ASSUMPTION_INTENDED_ID)
            and entry.verdict == VERDICT_UNSECURED
        ]
        assert offending == []
