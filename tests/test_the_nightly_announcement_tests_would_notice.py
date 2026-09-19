"""BDL-072 — the announcement's tests go red when the announcement is broken.

`beadloom-95dm` states the seam plainly and it is the reason this file exists:
no test reaches `gh` itself. What its tests DO reach is the workflow's own
program — the reading step's Python, run over six counter shapes, and the
announcement's shell, run against a stubbed `gh`. A test that runs a program and
reads its output can still pass over every input if what it asserts is weaker
than what it claims, and that shape has a name in this repository: a phantom
gate.

So each break below edits `.github/workflows/mutation.yml` in a temporary copy,
points `tests/test_mutation_nightly_announcement.py` at it and RUNS one of its
tests. The test must fail. The control runs the same tests against an unedited
copy of the same file through the same machinery, so a red here is the break and
not the harness.

**What this still does not measure**, restated so it is not read as closed: `gh`
against a live repository — whether the label can be created, whether the issue
appears, whether the mention notifies. Only the dispatched run of
`beadloom-e8m4` measures that. This file measures that the tests which exist
would notice their own mechanism dying.
"""

from __future__ import annotations

import inspect
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import pytest

import tests.test_mutation_nightly_announcement as announcement

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_WORKFLOW = announcement.MUTATION


@dataclass(frozen=True)
class Break:
    """One edit to the workflow, and the test that has to notice it."""

    name: str
    old: str
    new: str
    case: str
    notices: str
    #: How the covering test goes red on this edit, checked when it is run. The
    #: field exists so `_A_RED_TEST` is a measurement rather than a claim: a
    #: spelling no row produces is a spelling nothing here has ever exercised.
    spelling: type[Exception]


#: The eight edits, each on a line the announcement's behaviour rests on. `old`
#: is required to occur EXACTLY once, so an edit that silently matched nothing —
#: which would make every assertion below pass over an unchanged workflow — is a
#: failure of this file rather than a pass of the suite.
#:
#: Two rows share the edit that removes `gh issue create` and differ in the test
#: they are read through, because the red it produces differs: the failed-night
#: case asserts on the call list, while the case for a night that judged nothing
#: picks the create call out of it first and so goes red as a `StopIteration`.
BREAKS: tuple[Break, ...] = (
    Break(
        name="the counters are read from the wrong directory",
        old='path = pathlib.Path("mutants") / name',
        new='path = pathlib.Path("nowhere") / name',
        case="TestTheReadingStepTellsAJudgedRunFromASilentOne::"
        "test_two_populations_that_differ_are_a_judged_run",
        notices="a judged run would be reported as silent",
        spelling=AssertionError,
    ),
    Break(
        name="the two populations are no longer compared",
        old="elif whole_total <= rules_total:",
        new="elif whole_total < 0:",
        case="TestTheReadingStepTellsAJudgedRunFromASilentOne::"
        "test_a_whole_scope_export_equal_to_the_slice_is_silent",
        notices="the green shape of silence would be reported as a verdict",
        spelling=AssertionError,
    ),
    Break(
        name="an interrupted run stops being one",
        old='whole.get("check_was_interrupted_by_user")',
        new="False",
        case="TestTheReadingStepTellsAJudgedRunFromASilentOne::"
        "test_an_interrupted_run_is_silent_even_with_a_full_population",
        notices="a score over a truncated population would be reported as a verdict",
        spelling=AssertionError,
    ),
    Break(
        name="a failed night opens no issue",
        old='gh issue create -R "$REPO" --label "$WATCH_LABEL"',
        new='gh issue view -R "$REPO" --label "$WATCH_LABEL"',
        case="TestTheAnnouncementTakesTheBranchTheRunCallsFor::test_a_red_job_opens_the_first_issue",
        notices="the nine nights would repeat with nothing said",
        spelling=AssertionError,
    ),
    Break(
        name="the owner is no longer mentioned",
        old='"@$OWNER — the nightly mutation run reached no verdict." \\',
        new='"The nightly mutation run reached no verdict." \\',
        case="TestTheAnnouncementTakesTheBranchTheRunCallsFor::test_a_red_job_opens_the_first_issue",
        notices="the issue would open and notify nobody",
        spelling=AssertionError,
    ),
    Break(
        name="a night that judged nothing opens no issue either",
        old='gh issue create -R "$REPO" --label "$WATCH_LABEL"',
        new='gh issue view -R "$REPO" --label "$WATCH_LABEL"',
        case="TestTheAnnouncementTakesTheBranchTheRunCallsFor::"
        "test_a_green_job_that_judged_nothing_opens_one_too",
        notices="the shape no job status can see would stay invisible",
        spelling=StopIteration,
    ),
    Break(
        name="a judged night reports its own step as failed",
        old="exit 0",
        new="exit 1",
        case="TestTheAnnouncementTakesTheBranchTheRunCallsFor::"
        "test_a_judged_run_with_nothing_open_says_nothing",
        notices="a recovered nightly would go red in the announcement it recovered into",
        spelling=subprocess.CalledProcessError,
    ),
    Break(
        name="a recovered nightly leaves its watch issue open",
        old='gh issue close "$number" -R "$REPO" --reason completed',
        new='gh issue comment "$number" -R "$REPO" --body completed',
        case="TestTheAnnouncementTakesTheBranchTheRunCallsFor::"
        "test_a_judged_run_closes_the_issue_the_outage_opened",
        notices="a stale watch issue would stay open and get muted",
        spelling=AssertionError,
    ),
)

#: Every test a break above is checked through. Named separately so the control
#: below runs exactly the same cases against an unedited workflow.
CASES: tuple[str, ...] = tuple(dict.fromkeys(item.case for item in BREAKS))


def _case(case: str) -> Callable[..., None]:
    """The test named by ``Class::method``, bound to a fresh instance."""
    class_name, _, method = case.partition("::")
    return cast("Callable[..., None]", getattr(getattr(announcement, class_name)(), method))


#: How a red test in this file is legitimately spelled, and nothing wider.
#: Catching every exception made the harness indistinguishable from the break it
#: planted: on both locale legs of run 35404835459 each call below raised
#: `UnicodeEncodeError` before the edited workflow could matter, and all six
#: break tests the file then carried read green over a mechanism that never ran.
#: That is this file's own subject — a gate passing while the thing under it is
#: dead — one level up.
#:
#: Each entry is PRODUCED by a row of `BREAKS` and checked there, so the tuple
#: states what this file has exercised rather than what an exception could in
#: principle be. Three rows were declared before the review measured them and
#: only one spelling was real; the two rows that make the others real were added
#: rather than the claim narrowed, because a break CAN go red as either and a
#: harness that reported it as its own failure would be the wrong answer twice.
_A_RED_TEST: tuple[type[Exception], ...] = (
    AssertionError,  # an `assert` in the test under measurement
    StopIteration,  # a `gh` call list with no entry to pick
    subprocess.CalledProcessError,  # a script that exits non-zero under `set -e`
)


def _run(case: str, *, workflow: Path, at: Path) -> Exception | None:
    """Run *case* against *workflow* and return what it raised, or ``None``.

    Only the spellings in `_A_RED_TEST` count as the test going red. Anything
    else — a workflow that cannot be read, an argv the image's codec cannot
    hold — is the harness failing, and it propagates rather than being reported
    as a break that was caught.

    Every case here RUNS a program and so takes a room to run it in. A case that
    only read the workflow as data would take no argument, and running it would
    say nothing about a mechanism, so the signature is checked rather than
    branched on.
    """
    at.mkdir(parents=True, exist_ok=True)
    test = _case(case)
    parameters = inspect.signature(test).parameters
    assert len(parameters) == 1, f"{case} takes {len(parameters)} arguments, not a room"
    previous = announcement.MUTATION
    announcement.MUTATION = workflow
    try:
        test(at)
    except _A_RED_TEST as failure:
        return failure
    else:
        return None
    finally:
        announcement.MUTATION = previous


@pytest.fixture
def intact(tmp_path: Path) -> Path:
    """The workflow, copied unedited, so the control runs the same machinery."""
    copy = tmp_path / "intact.yml"
    copy.write_text(_WORKFLOW.read_text(encoding="utf-8"), encoding="utf-8")
    return copy


@pytest.mark.skipif(shutil.which("bash") is None, reason="the announcement is a bash step")
class TestTheAnnouncementsTestsGoRedWhenItIsBroken:
    """Each break, and the test that has to report it."""

    @pytest.mark.parametrize("edit", BREAKS, ids=lambda edit: edit.name)
    def test_the_break_edits_the_workflow_exactly_once(self, edit: Break) -> None:
        """Stated first: an edit that matches nothing proves nothing.

        Every assertion in the test below would pass over an unchanged workflow,
        and the file would read as a guard while measuring the tree.
        """
        text = _WORKFLOW.read_text(encoding="utf-8")

        assert text.count(edit.old) == 1, edit.old
        assert edit.new not in text

    @pytest.mark.parametrize("edit", BREAKS, ids=lambda edit: edit.name)
    def test_the_test_that_covers_it_fails(self, edit: Break, tmp_path: Path) -> None:
        text = _WORKFLOW.read_text(encoding="utf-8")
        broken = tmp_path / "broken.yml"
        broken.write_text(text.replace(edit.old, edit.new, 1), encoding="utf-8")

        failure = _run(edit.case, workflow=broken, at=tmp_path / "room")

        assert failure is not None, (
            f"{edit.case} passes against a workflow where {edit.name}, so "
            f"{edit.notices} and nothing in the suite would say so"
        )
        assert isinstance(failure, edit.spelling), (
            f"{edit.case} goes red as {type(failure).__name__} and the row declares "
            f"{edit.spelling.__name__} — `_A_RED_TEST` is measured through these rows, "
            "so a row whose spelling drifts makes the harness's accepted set a claim again"
        )

    @pytest.mark.parametrize("case", CASES)
    def test_it_passes_against_the_workflow_as_it_stands(
        self, case: str, intact: Path, tmp_path: Path
    ) -> None:
        """The control. Without it every red above could be the harness."""
        failure = _run(case, workflow=intact, at=tmp_path / "room")

        assert failure is None, failure

    def test_every_spelling_the_harness_accepts_is_produced_by_a_break(self) -> None:
        """`_A_RED_TEST` is a population, so it is held against one.

        A spelling accepted there and produced by no row is a widening nothing
        measured — which is how the tuple was first written, and the review
        found all three rows spelled the same. The rows that produce the other
        two run in `test_the_test_that_covers_it_fails`, where the spelling each
        declares is checked against what it raised.
        """
        declared = {edit.spelling for edit in BREAKS}

        assert set(_A_RED_TEST) <= declared, (
            "the harness accepts a spelling no break produces: "
            f"{sorted(spelling.__name__ for spelling in set(_A_RED_TEST) - declared)}"
        )

    def test_the_population_of_breaks_is_not_empty(self) -> None:
        """A parametrisation that collected nothing reports no tests and no red."""
        assert len(BREAKS) >= 6
        assert len(CASES) >= 4
        assert all(hasattr(announcement, item.case.partition("::")[0]) for item in BREAKS)


class TestTheHarnessCannotPassItselfOffAsTheBreakItPlanted:
    """The same defect this file is about, one level up (beadloom-3js4.1).

    `_run` used to report any exception as the break, so a harness that never
    reached the break read as a gate that had caught it. Measured on both
    locale legs of run 35404835459: every call raised `UnicodeEncodeError`
    while encoding the announcement's argv, the six break tests passed, and the
    only red came from the three control cases — the mechanism was dead and
    this file said the opposite.

    A red test here is spelled as an assertion, as a `gh` call list with no
    entry to pick, or as a script that exits non-zero under `set -e`. Anything
    else is the harness failing, and it propagates.
    """

    def test_a_workflow_that_cannot_be_read_is_not_a_red_test(self, tmp_path: Path) -> None:
        with pytest.raises(OSError):
            _run(CASES[0], workflow=tmp_path / "gone.yml", at=tmp_path / "room")
