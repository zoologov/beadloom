"""The landing-lock derivation, and this repository's own instructions held to it.

BDL-068 S5, BDL-UX #194 and #237. The acceptance suite states the guarantee; this
module holds the edges a scenario would only obscure — where a site may sit, what
ends an invocation, and which subcommands this derivation has actually measured.

The last class is the one that keeps the fix from decaying: the shipped
templates, the project layer and the composed artifacts of THIS repository are
run through the derivation and must produce no defective site. That assertion is
red on the tree this bead started from (four defective sites of five) and green
on the tree it leaves, which is what makes it a check rather than a decoration.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.application.waves import (
    DEFECT_ANONYMOUS_HOLDER,
    DEFECT_QUEUE_ONLY_WAIT,
    DEFECT_UNGUARDED_RELEASE,
    DEFECT_UNKNOWN_FORM,
    LOCK_COMMAND,
    LockSite,
    defect_detail,
    lock_sites,
)
from beadloom.services.bd_seam.assumptions import lock_invocations
from beadloom.services.bd_seam.invocations import text_invocations


def _lock_sites(sources: list[tuple[str, str]]) -> tuple[LockSite, ...]:
    """Judge the lock instructions in *sources*, through the one shared grammar.

    `beadloom-0mdo.51` moved the grammar to the seam and left the judgement here,
    so a test that starts from TEXT composes the two the same way the services
    edge does. Composing them here rather than mocking keeps these tests over the
    real path.
    """
    return lock_sites(lock_invocations(text_invocations(sources)))


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestTheDerivationReadsAShapeAndNotASpelling:
    """A site is an invocation, wherever the artifact happens to put it."""

    def test_a_site_in_prose_and_a_site_in_a_fence_are_both_found(self) -> None:
        sites = _lock_sites(
            [
                ("a.md", "Run `bd merge-slot acquire` first.\n"),
                ("b.md", "```bash\nbd merge-slot acquire\n```\n"),
            ]
        )
        assert len(sites) == 2
        assert {site.source for site in sites} == {"a.md", "b.md"}

    def test_the_line_number_is_the_line_a_reader_opens(self) -> None:
        sites = _lock_sites([("a.md", "one\ntwo\nbd merge-slot release\n")])
        assert [(s.source, s.line) for s in sites] == [("a.md", 3)]

    def test_two_invocations_on_one_line_are_two_sites(self) -> None:
        text = "`bd merge-slot acquire --holder x` then `bd merge-slot release`"
        sites = _lock_sites([("a.md", text)])
        assert [s.subcommand for s in sites] == ["acquire", "release"]

    def test_a_sentence_after_the_command_does_not_become_flags(self) -> None:
        """A closing backtick ends the invocation, so following prose is prose.

        Without a terminator the word ``--wait`` anywhere later in the sentence
        would be read as a flag of this call, which is the false-positive
        direction: a site reported defective for text it does not contain.
        """
        text = "Run `bd merge-slot acquire --holder x`, and never pass --wait.\n"
        sites = _lock_sites([("a.md", text)])
        assert sites[0].defects == ()

    def test_the_command_named_without_a_subcommand_is_not_a_site(self) -> None:
        """`bd merge-slot` inside backticks names the tool; it instructs nothing."""
        assert _lock_sites([("a.md", "The `bd merge-slot` primitive.\n")]) == ()

    def test_order_is_the_order_the_artifacts_were_handed_over(self) -> None:
        sites = _lock_sites(
            [("z.md", "bd merge-slot check\n"), ("a.md", "bd merge-slot check\n")]
        )
        assert [site.source for site in sites] == ["z.md", "a.md"]


class TestWhatEachCallFormGrants:
    """The three defects, each measured on bd 1.0.4 before it was encoded."""

    def test_an_acquire_with_no_holder_cannot_tell_holder_from_claimant(self) -> None:
        sites = _lock_sites([("a.md", "bd merge-slot acquire\n")])
        assert sites[0].defects == (DEFECT_ANONYMOUS_HOLDER,)

    def test_a_release_with_no_holder_frees_a_neighbours_hold(self) -> None:
        sites = _lock_sites([("a.md", "bd merge-slot release\n")])
        assert sites[0].defects == (DEFECT_UNGUARDED_RELEASE,)

    def test_the_wait_flag_is_reported_even_when_the_holder_is_named(self) -> None:
        """The two defects are independent: naming the holder does not make it block."""
        sites = _lock_sites([("a.md", "bd merge-slot acquire --holder b --wait\n")])
        assert sites[0].defects == (DEFECT_QUEUE_ONLY_WAIT,)

    def test_an_acquire_that_names_no_holder_and_waits_reports_both(self) -> None:
        sites = _lock_sites([("a.md", "bd merge-slot acquire --wait\n")])
        assert sites[0].defects == (DEFECT_ANONYMOUS_HOLDER, DEFECT_QUEUE_ONLY_WAIT)

    @pytest.mark.parametrize("subcommand", ["check", "create"])
    def test_reading_and_creating_the_slot_claim_no_exclusion(
        self, subcommand: str
    ) -> None:
        sites = _lock_sites([("a.md", f"bd merge-slot {subcommand}\n")])
        assert sites[0].defects == ()

    def test_the_named_form_grants_what_it_is_relied_on_for(self) -> None:
        text = (
            "bd merge-slot acquire --holder my-bead\n"
            "bd merge-slot release --holder my-bead\n"
        )
        sites = _lock_sites([("a.md", text)])
        assert [site.defects for site in sites] == [(), ()]


class TestASubcommandNobodyMeasuredIsUnjudged:
    """The unresolved population is part of the answer, never dropped from it."""

    def test_an_unmeasured_subcommand_is_reported_rather_than_passed(self) -> None:
        sites = _lock_sites([("a.md", "bd merge-slot steal --holder b\n")])
        assert sites[0].defects == (DEFECT_UNKNOWN_FORM,)

    def test_its_detail_says_the_site_is_unjudged_and_not_clean(self) -> None:
        assert "unjudged rather than clean" in defect_detail(DEFECT_UNKNOWN_FORM)

    def test_an_unrecognised_defect_name_is_said_rather_than_silently_empty(
        self,
    ) -> None:
        assert "unrecognised defect" in defect_detail("no-such-defect")


class TestEveryDefectNamesItsCostAndItsMove:
    """A finding with no remedy is a finding somebody argues with."""

    @pytest.mark.parametrize(
        "defect",
        [
            DEFECT_ANONYMOUS_HOLDER,
            DEFECT_QUEUE_ONLY_WAIT,
            DEFECT_UNGUARDED_RELEASE,
        ],
    )
    def test_the_detail_names_the_flag_that_fixes_it(self, defect: str) -> None:
        detail = defect_detail(defect)
        assert "--holder" in detail or "exit" in detail


def _this_projects_instructions() -> list[tuple[str, str]]:
    """Every artifact of this repository that INSTRUCTS an agent, plus what it ships.

    Two halves, and the boundary between them matters. The composed half is
    exactly the population :func:`beadloom.application.waves` checks through the
    command — imported rather than restated, so a tool added to the flow is
    covered here by the same act. The second half is the templates this project
    ships, which reach an adopter's agents without ever being composed in this
    tree.

    **What is deliberately outside it.** ``.claude/development/`` holds the issue
    log and the epic documents, and both QUOTE the defective call form because
    quoting it is how the defect was recorded (BDL-UX #194, #237). A record of a
    defect is not an instruction to repeat it. The cost of the exclusion is real
    and is stated rather than hidden: an instruction written into a planning
    document is invisible to this assertion, which is the same limit
    ``role-duties`` states about the coordinator's launch prompt.
    """
    from beadloom.services.bd_seam.population import flow_artifacts, shipped_templates

    found: list[tuple[str, str]] = list(flow_artifacts(REPO_ROOT))
    found.extend(
        (label, text) for label, text in shipped_templates() if LOCK_COMMAND in text
    )
    return found


class TestThisRepositoryInstructsOnlyTheFormThatGrantsIt:
    """The fix, held in place. Red before this bead, green after it."""

    def test_the_lock_is_instructed_somewhere_at_all(self) -> None:
        """Otherwise the assertion below would pass over an empty population."""
        assert _this_projects_instructions()

    def test_no_instruction_this_project_ships_or_composes_is_defective(self) -> None:
        defective = [
            f"{site.source}:{site.line} `{site.invocation}` {site.defects}"
            for site in _lock_sites(_this_projects_instructions())
            if site.defects
        ]
        assert defective == []

