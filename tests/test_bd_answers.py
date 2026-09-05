"""What population a ``bd`` answer covers (BDL-068 S5, `beadloom-0mdo.52`).

BDL-UX #187 and #97, both External against bd 1.0.4 and both answered at our own
call sites per CONTEXT Q4. ``bd list`` returns less than the tracker and ``bd
close --suggest-next`` returns more than the question, and neither answer has
room to say so.

**Every notice these tests parse was measured, not quoted.** ``Showing 50
issues; more results matched but were hidden by --limit.`` came from ``bd list
--json`` against this repository's tracker (50 rows of 843), and ``Showing 100 of
120 ready issues.`` from ``bd ready --json`` against a rig grown past the cap
with ``bd create --graph``. The ``Newly unblocked:`` block came from a rig where
closing the last blocker genuinely unblocked its target. Streams separated, exit
codes read without a pipe.

**#97 was re-measured over twenty-three dependency shapes in twenty-three
separate rigs**, because it has now been characterised three times and no
characterisation survived the next measurement. It named a still-blocked bead in
sixteen; ``bd ready`` was correct in all twenty-three. So these tests assert the
observation and never a mechanism.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from beadloom.services.bd_seam.answers import (
    COVERAGE_AS_ASKED,
    COVERAGE_FILTERED,
    COVERAGE_TRUNCATED,
    COVERAGE_UNCHECKED,
    NOT_COMPARED,
    NOTHING_TO_CHECK,
    confirmed_suggestion,
    coverage_of,
    ready_ids,
    suggested_beads,
)
from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_UNBLOCKED_IS_READY,
    VERDICT_SECURED,
    VERDICT_UNSECURED,
    call_sites,
    population_flags,
)
from beadloom.services.bd_seam.invocations import text_invocations
from beadloom.services.bd_seam.population import project_report

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Measured on this repository: `bd list --json` returned 50 rows of 843.
_LIST_NOTICE = (
    "\nShowing 50 issues; more results matched but were hidden by --limit. "
    "Use --limit 0 for all, or --limit N to raise the cap.\n"
)

#: Measured on a rig grown to 120 ready beads with `bd create --graph`.
_READY_NOTICE = (
    "Showing 100 of 120 ready issues. Use --limit 0 for all, or --limit N to raise the cap.\n"
)

#: Measured: the block `--suggest-next` writes on STDOUT when it names anything.
_SUGGESTED = (
    "✓ Closed rig52-4c6 — blocker c: Closed\n"
    "\nNewly unblocked:\n"
    "  • rig52-rm9 — target T (P2)\n"
    "  • rig52-q2a — another target (P1)\n"
)

#: Measured: a close that unblocked nothing prints the confirmation and stops.
_SUGGESTED_NOTHING = "✓ Closed rig52-z2u — blocker b: Closed\n"


# ---------------------------------------------------------------------------
# coverage_of — how much of the tracker one answer covers
# ---------------------------------------------------------------------------


def test_a_truncated_list_is_truncated_however_wide_the_call_form_asked() -> None:
    """bd's own notice outranks our intention, which is what makes `--all` measured.

    This is the half of the bead that turns "we passed the widening flag" into
    "the widening flag worked". If a later bd stops honouring `--all`, the three
    call sites that pass it stop reading their answer as the whole.
    """
    answer = coverage_of(("list", "--all", "--json"), _LIST_NOTICE)
    assert answer.coverage == COVERAGE_TRUNCATED
    assert answer.shown == 50
    assert answer.total is None
    assert "50" in answer.stated


def test_the_ready_notice_carries_both_numbers_and_both_are_reported() -> None:
    """`bd ready` announces its cap in a different sentence from `bd list`."""
    answer = coverage_of(("ready", "--json"), _READY_NOTICE)
    assert answer.coverage == COVERAGE_TRUNCATED
    assert (answer.shown, answer.total) == (100, 120)
    assert "100 of 120" in answer.stated


def test_a_call_form_that_named_its_population_covers_what_it_asked_for() -> None:
    answer = coverage_of(("list", "--all", "--json"), "")
    assert answer.coverage == COVERAGE_AS_ASKED
    assert answer.as_asked is True


def test_the_answer_that_covers_what_it_asked_for_does_not_claim_the_tracker() -> None:
    """`--status open` names a population; every open bead is not every bead.

    The constant is called `as-asked` and not `complete` for this reason, and
    the sentence has to carry it or the distinction lives only in a name.
    """
    answer = coverage_of(("list", "--status", "open", "--json"), "")
    assert answer.coverage == COVERAGE_AS_ASKED
    assert "not the same claim as covering the tracker" in answer.stated


def test_a_call_form_that_named_no_population_is_filtered_even_when_bd_is_silent() -> None:
    """The status filter is the half bd announces on NEITHER stream.

    Measured: `bd list --limit 0` alone returned 55 rows of 842 in this
    repository with both streams silent. So silence is not evidence, and the
    call form is the only thing left to read.
    """
    answer = coverage_of(("list", "--json"), "")
    assert answer.coverage == COVERAGE_FILTERED
    assert "--all" in answer.stated


def test_a_subcommand_whose_population_is_unmeasured_is_unchecked_and_not_complete() -> None:
    """`bd swarm` and `bd gate` are 48 sites this derivation has not measured.

    They are the two commands `/coordinator` orchestrates every wave with, and
    guessing at them is the false confidence this epic exists to remove. An
    unchecked answer must never read like a clean one.
    """
    answer = coverage_of(("swarm", "status", "--json"), "")
    assert answer.coverage == COVERAGE_UNCHECKED
    assert "UNCHECKED" in answer.stated


def test_a_read_by_id_carries_no_population_question_and_says_so() -> None:
    """`bd show` is IN the measured table and carries no population rule.

    That is a different fact from `bd swarm`, which nobody measured, and both
    are reported as unchecked because neither can be read as the whole. The
    distinction between them lives in the derivation's verdicts, not here.
    """
    assert population_flags("show") is None
    assert coverage_of(("show", "bd-1", "--json"), "").coverage == COVERAGE_UNCHECKED


# ---------------------------------------------------------------------------
# ready_ids / suggested_beads — reading bd's own output, never re-deciding it
# ---------------------------------------------------------------------------


def test_an_unreadable_ready_answer_is_none_and_an_empty_one_is_empty() -> None:
    """`None` and `()` are opposite facts and collapsing them is the defect.

    An empty ready queue is a measurement. An answer nobody could parse is not,
    and returning `()` for it turns a failed confirmation into "every candidate
    is still blocked".
    """
    assert ready_ids('[{"id": "bd-1"}, {"id": "bd-2"}]') == ("bd-1", "bd-2")
    assert ready_ids("[]") == ()
    assert ready_ids("Showing 100 of 120 ready issues") is None
    assert ready_ids('{"id": "bd-1"}') is None
    assert ready_ids('[{"title": "no id here"}]') is None


def test_the_suggested_block_is_read_from_bds_own_stdout() -> None:
    assert suggested_beads(_SUGGESTED) == ("rig52-rm9", "rig52-q2a")
    assert suggested_beads(_SUGGESTED_NOTHING) == ()


def test_prose_after_the_suggested_block_does_not_become_a_bead_id() -> None:
    """A line that is not a bullet ends the block, so a footer is not a candidate."""
    text = _SUGGESTED + "\nRun `bd ready` to confirm.\n"
    assert suggested_beads(text) == ("rig52-rm9", "rig52-q2a")


# ---------------------------------------------------------------------------
# confirmed_suggestion — BDL-UX #97 answered where it reaches us
# ---------------------------------------------------------------------------


def test_a_candidate_the_ready_list_does_not_hold_is_reported_as_still_blocked() -> None:
    answer = confirmed_suggestion(_SUGGESTED, ("rig52-rm9",))
    assert answer.candidates == ("rig52-rm9", "rig52-q2a")
    assert answer.confirmed == ("rig52-rm9",)
    assert answer.still_blocked == ("rig52-q2a",)
    assert "1 ready, 1 still blocked" in answer.stated


def test_a_suggestion_nobody_confirmed_is_not_compared_rather_than_empty() -> None:
    """The anti-vacuity direction: an unread `bd ready` is not a clean pass."""
    answer = confirmed_suggestion(_SUGGESTED, None)
    assert answer.compared is False
    assert answer.confirmed == ()
    assert answer.still_blocked == ()
    assert NOT_COMPARED in answer.stated


def test_a_close_that_suggested_nothing_has_nothing_to_check() -> None:
    answer = confirmed_suggestion(_SUGGESTED_NOTHING, ("rig52-rm9",))
    assert answer.candidates == ()
    assert NOTHING_TO_CHECK in answer.stated


def test_every_candidate_ready_is_still_stated_as_a_confirmation_not_as_bds_answer() -> None:
    """Even the all-clear names what was compared, so the two are never one word."""
    answer = confirmed_suggestion(_SUGGESTED, ("rig52-rm9", "rig52-q2a"))
    assert answer.still_blocked == ()
    assert answer.compared is True
    assert "confirmed against `bd ready`" in answer.stated


# ---------------------------------------------------------------------------
# the derivation learns the securing shape, so the fix is visible to the report
# ---------------------------------------------------------------------------


def _close_verdict(text: str) -> tuple[str, str]:
    sites = call_sites(text_invocations([("role.md", text)]))
    close = next(site for site in sites if site.subcommand == "close")
    found = next(a for a in close.assumptions if a.name == ASSUMPTION_UNBLOCKED_IS_READY)
    return found.verdict, found.detail


def test_an_artifact_naming_the_suggestion_and_not_its_confirmation_is_unsecured() -> None:
    verdict, _ = _close_verdict("Close it:\n\n    bd close <id> --suggest-next\n")
    assert verdict == VERDICT_UNSECURED


def test_an_artifact_that_also_names_the_confirmation_is_secured() -> None:
    verdict, detail = _close_verdict(
        "Close it:\n\n    bd close <id> --suggest-next\n\nThen:\n\n    bd ready --limit 0\n"
    )
    assert verdict == VERDICT_SECURED
    assert "COMPARED" in detail


def test_the_confirmation_secures_the_artifact_whichever_order_it_is_written_in() -> None:
    """The artifact is the unit, so a confirmation above the call still counts.

    A single-pass derivation could only secure a confirmation written first,
    which is a fact about ordering and not about what the artifact tells its
    reader.
    """
    verdict, _ = _close_verdict(
        "Confirm with:\n\n    bd ready --limit 0\n\n"
        "Then close:\n\n    bd close <id> --suggest-next\n"
    )
    assert verdict == VERDICT_SECURED


def test_the_confirmation_does_not_leak_between_artifacts() -> None:
    """`CLAUDE.md` naming `bd ready` does not reach a role core read on its own.

    This is the whole reason the unit is the artifact and not the project: a
    subagent runs from `.claude/agents/<role>.md`, and three of the four role
    cores instructed the suggestion while the mitigation lived elsewhere.
    """
    sites = call_sites(
        text_invocations(
            [
                ("CLAUDE.md", "Take work from:\n\n    bd ready\n"),
                ("agents/test.md", "Close it:\n\n    bd close <id> --suggest-next\n"),
            ]
        )
    )
    close = next(site for site in sites if site.subcommand == "close")
    verdict = next(a.verdict for a in close.assumptions if a.name == ASSUMPTION_UNBLOCKED_IS_READY)
    assert verdict == VERDICT_UNSECURED


def test_no_artifact_of_ours_instructs_the_suggestion_without_its_confirmation() -> None:
    """The project-wide check, red on the tree this bead started from.

    Measured at that point: NINE artifacts instructed `bd close --suggest-next`
    and named `bd ready` nowhere — `.claude/agents/{test,review,tech-writer}.md`,
    their three sources under `templates/roles/core/`, their three vendored
    snapshots under `templates/agentic_flow/agents/`, and `services/mcp_server.py`.
    `dev.md`, `CLAUDE.md`, `checkpoint.md` and `coordinator.md` already carried it.
    A role core added later without the confirmation fails here.
    """
    report = project_report(_PROJECT_ROOT)
    unsecured = sorted(
        {
            site.source
            for site in report.sites
            if any(
                a.name == ASSUMPTION_UNBLOCKED_IS_READY and a.verdict == VERDICT_UNSECURED
                for a in site.assumptions
            )
        }
    )
    assert unsecured == [], (
        "these artifacts instruct `bd close --suggest-next` and name `bd ready` "
        "nowhere, so a reader of them alone is never told the suggestion can "
        "include still-blocked beads: " + ", ".join(unsecured)
    )


# ---------------------------------------------------------------------------
# the concrete defect: our own MCP surface handed bd's false signal to an agent
# ---------------------------------------------------------------------------


class TestCompleteBeadConfirmsWhatItReturns:
    """`handle_complete_bead` closed with `--suggest-next` and returned the raw text.

    An agent finishing a bead through our own tool was handed a list that can
    name still-blocked beads, unqualified, under the key `next` and with no
    `bd ready` behind it. That is BDL-UX #97 reaching an agent through OUR
    surface.
    """

    @staticmethod
    def _green() -> object:
        from beadloom.application.gate import GateResult, GateStep

        return GateResult(steps=[GateStep("lint", passed=True, summary="clean")])

    def _run(self, project: Path, ready: object) -> dict[str, object]:
        from beadloom.services.bd_seam import BdResult
        from beadloom.services.mcp_server import handle_complete_bead

        def fake_bd(argv: list[str], **_: object) -> object:
            if argv[0] == "close":
                return BdResult(0, _SUGGESTED, "")
            if argv[0] == "ready":
                if isinstance(ready, Exception):
                    raise ready
                return ready
            return BdResult(0, "{}", "")

        with (
            patch("beadloom.services.mcp_server.run_ci_gate", return_value=self._green()),
            patch("beadloom.services.mcp_server.run_bd", side_effect=fake_bd),
        ):
            return handle_complete_bead(project, bead="bd-1", run_tests=False)

    def test_the_suggestion_is_returned_confirmed_and_never_as_bds_raw_text(
        self, tmp_path: Path
    ) -> None:
        from beadloom.services.bd_seam import BdResult

        result = self._run(tmp_path, BdResult(0, '[{"id": "rig52-rm9"}]', ""))

        assert result["status"] == "PASS"
        assert result["next"] != _SUGGESTED.strip()
        assert result["next"] == ["rig52-rm9"]
        assert result["next_candidates"] == ["rig52-rm9", "rig52-q2a"]
        assert result["next_still_blocked"] == ["rig52-q2a"]
        assert "still blocked" in str(result["next_stated"])

    def test_an_unreadable_ready_answer_leaves_the_suggestion_not_compared(
        self, tmp_path: Path
    ) -> None:
        from beadloom.services.bd_seam import BdResult

        result = self._run(tmp_path, BdResult(0, "Showing 100 of 120 ready issues", ""))

        assert result["next"] == []
        assert result["next_candidates"] == ["rig52-rm9", "rig52-q2a"]
        assert NOT_COMPARED in str(result["next_stated"])

    def test_a_ready_that_cannot_run_does_not_undo_the_close(self, tmp_path: Path) -> None:
        """The close already happened, so a failed confirmation is not an error.

        It is a confirmation nobody made, which is exactly `not compared`.
        """
        from beadloom.services.bd_seam import BdUnavailableError

        result = self._run(tmp_path, BdUnavailableError("bd vanished"))

        assert result["status"] == "PASS"
        assert result["next"] == []
        assert NOT_COMPARED in str(result["next_stated"])

    def test_a_nonzero_ready_is_not_read_as_an_empty_ready_queue(self, tmp_path: Path) -> None:
        """A failed command whose stdout is empty must not confirm nothing ready."""
        from beadloom.services.bd_seam import BdResult

        result = self._run(tmp_path, BdResult(1, "", "boom"))

        assert result["next_candidates"] == ["rig52-rm9", "rig52-q2a"]
        assert NOT_COMPARED in str(result["next_stated"])


def test_the_project_asks_bd_ready_for_its_whole_answer_wherever_it_asks_at_all() -> None:
    """Any `bd ready` in our Python names the limit, because the cap is 100.

    This flow calls `bd ready` authoritative at forty sites. The moment our own
    code depends on it, the call form has to lift the cap or the confirmation is
    itself narrowed.
    """
    report = project_report(_PROJECT_ROOT)
    ready = [
        site for site in report.sites if site.channel == "python" and site.subcommand == "ready"
    ]
    assert ready, "no python call site asks `bd ready` at all"
    for site in ready:
        assert not site.unsettled, f"{site.source}:{site.line} `{site.text}` is capped"


if __name__ == "__main__":  # pragma: no cover - convenience only
    pytest.main([__file__])
