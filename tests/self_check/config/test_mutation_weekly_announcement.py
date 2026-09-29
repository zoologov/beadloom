"""A dead or red weekly sample says so outside the Actions tab (BDL-072, BDL-074 D1).

The retired nightly reached a verdict on 0 of 7 187 mutants every night from
2026-09-10 to 2026-09-18 and nobody saw it, because a scheduled workflow reports
no check-run and its red is visible only to whoever opens the Actions tab. The
announcement was built for it, and the weekly sample that replaced it inherits
it; these tests read it the way `test_mutation_ci_job.py` reads the jobs: as
data.

**Two states are announced, and they are not one** (BDL-074 G1, review M1): NO
VERDICT, where the job ended before it judged and scored every mutant it drew, and
A VERDICT UNDER THE FLOOR, where every mutant was judged and the whole interval of
the score lies below the floor. Both fail the job, so the score step names the
floor verdict it reached and the announcement titles and words the issue by it.

**What they measure, and what they cannot.** The verdict — "did this run judge
every mutant it drew" — is the adapter's `judge`, which is RUN over its shapes in
`test_mutation_adapter.py`; here the wiring from that step to the announcement is
pinned. The announcement calls `gh` against a live repository, so it is run
against a stubbed `gh`: the branch it takes is measured, GitHub is not. Only a
dispatched run proves an issue opens (`beadloom-paze`).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping

MUTATION = REPO_ROOT / ".github" / "workflows" / "mutation.yml"

#: The job the announcement speaks for.
SAMPLE = "mutation-sample"


def _workflow() -> dict[str, object]:
    data = yaml.safe_load(MUTATION.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _jobs() -> dict[str, object]:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _job(name: str) -> dict[str, object]:
    job = _jobs()[name]
    assert isinstance(job, dict)
    return job


def _steps(job: str) -> list[dict[str, object]]:
    steps = _job(job)["steps"]
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _step_with_id(job: str, step_id: str) -> dict[str, object]:
    for step in _steps(job):
        if step.get("id") == step_id:
            return step
    raise AssertionError(f"{job} has no step with id {step_id!r}")


def _announcement_script() -> str:
    """The announcement's shell, taken from the workflow rather than restated."""
    steps = _steps("announce")
    assert len(steps) == 1, "the announcement is one step; this reader assumes it"
    return str(steps[0]["run"])


#: What a stubbed `gh` records, so the calls can be read back. It answers
#: `issue list` from an environment variable, which is the one answer the
#: script branches on.
_GH_STUB = """#!/bin/bash
echo "${*//$'\n'/ }" >> "$GH_LOG"
if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
  echo "$FAKE_OPEN_ISSUE"
fi
exit 0
"""


#: The two titles the watch issue carries, one per state that is announced.
NO_VERDICT = "Mutation weekly sample: no verdict"
UNDER_FLOOR = "Mutation weekly sample: under its floor"

#: What the score step reports for a sample judged under its floor: T's run
#: 36406732958 in shape, 150 of 150 judged at 82.0% with the interval below 0.88.
UNDER_FLOOR_REPORT = (
    "Score: 82.0% of 150 scored mutants\n"
    "Sample: a random sample of 150 of 6992 mutants; 95% interval 75.1% to 87.3% (Wilson)\n"
    "Survivors: 27 over 5 node(s)\n"
    "  rule-engine: 15 survivor(s) — beadloom.graph.rules.liveness.x__cycle_reasons__mutmut_4\n"
    "Floor: 0.88 — the sample's interval lies wholly under it."
)


def _open(number: str, title: str) -> str:
    """The open watch issue as the announcement's lookup prints it."""
    return f"{number}\t{title}"


def _constants() -> dict[str, str]:
    """The announcement's literal environment, read from the workflow, not restated."""
    env = _steps("announce")[0]["env"]
    assert isinstance(env, dict)
    return {str(key): str(value) for key, value in env.items() if "${{" not in str(value)}


def _step_environment(bin_dir: Path, values: Mapping[str, str | Path]) -> dict[bytes, bytes]:
    """A step's environment as the Actions runner hands it to bash: bytes.

    `subprocess` encodes a `str` environment value with the filesystem codec,
    which the locale chooses outside macOS, so the score report's em dash raised
    `UnicodeEncodeError` on both locale legs of PR #86's first run and on no
    UTF-8 tree. The runner writes a step's environment as UTF-8 whatever the
    image's locale, so text is encoded as UTF-8 here; a path is encoded with the
    filesystem codec that produced it, and *bin_dir* goes first on `PATH` so the
    stub answers for the real command.
    """
    env = dict(os.environb)
    env[b"PATH"] = os.fsencode(bin_dir) + os.pathsep.encode() + env.get(b"PATH", b"")
    for key, value in values.items():
        env[key.encode("utf-8")] = (
            os.fsencode(value) if isinstance(value, Path) else value.encode("utf-8")
        )
    return env


def _announce(
    tmp_path: Path,
    *,
    result: str,
    verdict: str,
    detail: str = "",
    open_issue: str = "",
    floor: str = "",
    report: str = "",
) -> list[str]:
    """Run the announcement against a stubbed `gh` and return the calls it made.

    The stub is what makes this a measurement rather than a reading: the script
    is executed, its branches are taken, and the argument lists are read back.
    What it does NOT measure is `gh` itself — whether the label may be created,
    whether the mention notifies, whether the issue appears. Only a dispatched
    run measures that.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "gh"
    stub.write_text(_GH_STUB, encoding="utf-8")
    stub.chmod(0o755)
    log = tmp_path / "gh.log"
    env = _step_environment(
        bin_dir,
        {
            **_constants(),
            "GH_LOG": log,
            "GH_TOKEN": "stub",
            "REPO": "owner/repo",
            "OWNER": "owner",
            "RUN_URL": "https://example.invalid/run/1",
            "RESULT": result,
            "VERDICT": verdict,
            "DETAIL": detail,
            "FLOOR": floor,
            "REPORT": report,
            "FAKE_OPEN_ISSUE": open_issue,
        },
    )
    bash = shutil.which("bash")
    assert bash is not None
    # ON DISK, AND NOT IN THE ARGV. `encoding=` governs the child's streams;
    # an argv is encoded with `sys.getfilesystemencoding()`, which the locale
    # chooses — ascii under `LC_ALL=C`, iso8859-1 under `en_US.ISO-8859-1`.
    # The announcement's owner mention carries an em dash (the `announce` job's body),
    # so handing the script to bash as an argument raised UnicodeEncodeError on
    # both locale legs of run 35404835459 and on no UTF-8 tree. The script is
    # the workflow's text, so the encoding moves and the prose does not. The
    # environment is the other half of the same encoding, and it is bytes for
    # the same reason (`_step_environment`).
    script = tmp_path / "announce.sh"
    script.write_text(_announcement_script(), encoding="utf-8")
    subprocess.run(  # noqa: S603 — the argv is this repository's own workflow
        [bash, str(script)],
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return log.read_text(encoding="utf-8").splitlines() if log.is_file() else []


def _state_part(call: str) -> str:
    """The body of a `gh` call up to its standing footer, which names both states."""
    return call.split("--body", 1)[1].split("This issue is the one place")[0]


def _verbs(calls: list[str]) -> list[str]:
    """The `gh` subcommand of each call, which is what the branches differ in."""
    return [" ".join(call.split()[:3]) for call in calls]


class TestTheVerdictReachesTheAnnouncement:
    def test_the_reading_step_runs_after_a_failed_step(self) -> None:
        """Its interesting cases are the runs where something already went red."""
        assert _step_with_id(SAMPLE, "judged")["if"] == "always()"

    def test_the_reading_step_is_the_adapters_judge_over_the_names_drawn(self) -> None:
        """The verdict compares the counters with the names that were drawn, so a
        run whose mutants mostly never ran is silent while every step exited 0."""
        run = str(_step_with_id(SAMPLE, "judged")["run"])
        assert "mutmut_adapter.py judge" in run
        assert '--names "$RUNNER_TEMP/sample-names.txt"' in run
        assert "--stats mutants/sample-stats.json" in run
        assert '>> "$GITHUB_OUTPUT"' in run

    def test_the_job_publishes_what_the_step_read(self) -> None:
        outputs = _job(SAMPLE)["outputs"]
        assert isinstance(outputs, dict)
        assert outputs["verdict"] == "${{ steps.judged.outputs.verdict }}"
        assert outputs["detail"] == "${{ steps.judged.outputs.detail }}"

    def test_the_job_publishes_the_floor_and_the_score_report(self) -> None:
        """A judged sample can still miss its floor, and the announcement has to
        tell that from a run that judged nothing (BDL-074 G1, review M1)."""
        outputs = _job(SAMPLE)["outputs"]
        assert isinstance(outputs, dict)
        assert outputs["floor"] == "${{ steps.score.outputs.floor }}"
        assert outputs["report"] == "${{ steps.score.outputs.report }}"

    def test_the_score_step_names_the_floor_it_reached(self) -> None:
        run = str(_step_with_id(SAMPLE, "score")["run"])
        assert "floor=held" in run
        assert "floor=under" in run
        assert "floor=unscored" in run
        assert "interval lies wholly under it" in run
        assert '>> "$GITHUB_OUTPUT"' in run


_UV_STUB = """#!/bin/bash
printf '%s\\n' "$FAKE_SCORE"
exit "$FAKE_CODE"
"""


def _score(tmp_path: Path, *, code: int, text: str) -> dict[str, str]:
    """Run the score step against a stubbed `uv` and read back what it published."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(_UV_STUB, encoding="utf-8")
    stub.chmod(0o755)
    output, summary = tmp_path / "output", tmp_path / "summary"
    env = _step_environment(
        bin_dir,
        {
            "RUNNER_TEMP": tmp_path,
            "GITHUB_OUTPUT": output,
            "GITHUB_STEP_SUMMARY": summary,
            "POPULATION": "6992",
            "FAKE_SCORE": text,
            "FAKE_CODE": str(code),
        },
    )
    bash = shutil.which("bash")
    assert bash is not None
    script = tmp_path / "score.sh"
    script.write_text(str(_step_with_id(SAMPLE, "score")["run"]), encoding="utf-8")
    ran = subprocess.run(  # noqa: S603 — the argv is this repository's own workflow
        [bash, "-e", str(script)], env=env, capture_output=True, encoding="utf-8", check=False
    )
    assert ran.returncode == code, "the step must exit with the command's own code"
    lines = output.read_text(encoding="utf-8").splitlines()
    floor = next(line.removeprefix("floor=") for line in lines if line.startswith("floor="))
    start = lines.index("report<<MUTATION_SCORE_REPORT")
    end = lines.index("MUTATION_SCORE_REPORT", start + 1)
    return {"floor": floor, "report": "\n".join(lines[start + 1 : end])}


@pytest.mark.skipif(shutil.which("bash") is None, reason="the score step is a bash step")
class TestTheScoreStepNamesItsFloorVerdict:
    """RUN, with `uv` stubbed to print a report and exit as `beadloom mutation` does."""

    def test_a_sample_under_its_floor_is_named_under(self, tmp_path: Path) -> None:
        published = _score(tmp_path, code=1, text=UNDER_FLOOR_REPORT)
        assert published["floor"] == "under"
        assert "95% interval 75.1% to 87.3%" in published["report"]

    def test_a_sample_at_or_over_its_floor_is_named_held(self, tmp_path: Path) -> None:
        text = "Floor: 0.88 — the sample's interval reaches it."
        assert _score(tmp_path, code=0, text=text)["floor"] == "held"

    def test_a_finding_that_is_not_the_floor_is_unscored(self, tmp_path: Path) -> None:
        text = "WARN [mutation-counters-missing] x: no counters"
        assert _score(tmp_path, code=1, text=text)["floor"] == "unscored"

    def test_an_unanswerable_command_is_unscored(self, tmp_path: Path) -> None:
        assert _score(tmp_path, code=2, text="Error: no index")["floor"] == "unscored"

    def test_the_phrase_the_step_reads_is_the_one_the_command_prints(self) -> None:
        """The step tells a missed floor from any other finding by the command's
        own floor line; reworded there, every miss would read as no verdict."""
        from beadloom.application.mutation_scope import SampleInterval
        from beadloom.services.commands.mutation import _floor_verdict

        missed = _floor_verdict(True, SampleInterval(6992, 150, 123, 0.751, 0.873))
        phrase = "interval lies wholly under it"
        assert phrase in missed
        assert f'grep -q "{phrase}"' in str(_step_with_id(SAMPLE, "score")["run"])


class TestTheAnnouncementSpeaksForAJobThatCannotSpeak:
    def test_it_is_a_separate_job_that_runs_whatever_happened(self) -> None:
        """`timeout-minutes` and `concurrency` both END the mutation job, and a
        step inside a killed job is not guaranteed to run. A dependent job reads
        `needs.mutation.result` and runs either way."""
        announce = _job("announce")
        assert announce["needs"] == SAMPLE
        assert announce["if"] == "always() && github.event_name != 'pull_request'"

    def test_it_is_the_only_job_holding_the_token_that_can_write(self) -> None:
        """The mutation job executes mutated source. The smallest job that needs
        `issues: write` is the one that carries it."""
        assert _workflow()["permissions"] == {"contents": "read"}
        assert _job("announce")["permissions"] == {"issues": "write"}
        assert "permissions" not in _job(SAMPLE)
        assert "permissions" not in _job("mutation-per-change")

    def test_it_reads_both_shapes_of_silence(self) -> None:
        """`if: failure()` covers one shape. The announcement asks the job
        result AND the counters, so the green shape reaches it too."""
        script = "\n".join(str(step.get("run", "")) for step in _steps("announce"))
        assert "needs.mutation-sample.result" in str(_steps("announce"))
        assert "$RESULT" in script
        assert "$VERDICT" in script

    def test_a_second_failing_night_comments_instead_of_opening_a_second_issue(
        self,
    ) -> None:
        """Nine identical issues are the same silence in a louder form. The
        existing issue is found by label, so a retitling does not start a second
        thread, and `gh issue create` is reachable only when none was found."""
        script = "\n".join(str(step.get("run", "")) for step in _steps("announce"))
        assert "gh label create" in script
        assert '--label "$WATCH_LABEL"' in script
        create = script.index("gh issue create")
        guard = script.rindex('if [ -n "$number" ]; then', 0, create)
        comment = script.index("gh issue comment", guard)
        assert guard < comment < create, (
            "gh issue create must sit in the else branch of the lookup, or every "
            "failed night opens its own issue"
        )

    def test_a_run_that_judges_its_scope_closes_the_open_issue(self) -> None:
        """A watch issue left open after the thing it watches recovered is a
        second silence, of the kind that gets muted."""
        script = "\n".join(str(step.get("run", "")) for step in _steps("announce"))
        assert "gh issue close" in script


@pytest.mark.skipif(shutil.which("bash") is None, reason="the announcement is a bash step")
class TestTheAnnouncementTakesTheBranchTheRunCallsFor:
    """The script, RUN, over the states a weekly run can hand it.

    Calls to a stubbed `gh`, so what is measured here is which branch the
    script takes and with what arguments. It is not measured against GitHub.
    """

    def test_a_judged_run_with_nothing_open_says_nothing(self, tmp_path: Path) -> None:
        calls = _announce(tmp_path, result="success", verdict="judged", floor="held")
        assert _verbs(calls) == ["label create mutation-weekly", "issue list -R"]

    def test_a_judged_run_closes_the_issue_the_outage_opened(self, tmp_path: Path) -> None:
        calls = _announce(
            tmp_path,
            result="success",
            verdict="judged",
            floor="held",
            open_issue=_open("12", NO_VERDICT),
        )
        assert "issue close 12" in _verbs(calls)
        assert "issue create -R" not in _verbs(calls)
        comment = next(call for call in calls if call.startswith("issue comment 12"))
        assert "judged its sample, and the sample's interval reaches its floor" in comment
        assert "again" not in comment
        # "held" means the interval reaches the floor, not that the score is at or
        # above it (review ``beadloom-b9ll`` m-new-1): 84.0% [77.4, 88.9] holds 0.88.
        assert "at or above" not in comment

    def test_a_run_back_over_its_floor_closes_the_under_floor_issue_saying_so(
        self, tmp_path: Path
    ) -> None:
        """The close is worded by the state it ends: a sample that was judged every
        week did not 'reach a verdict again' (review M1)."""
        calls = _announce(
            tmp_path,
            result="success",
            verdict="judged",
            floor="held",
            open_issue=_open("12", UNDER_FLOOR),
        )
        assert "issue close 12" in _verbs(calls)
        comment = next(call for call in calls if call.startswith("issue comment 12"))
        assert "This week's sample's interval reaches its floor" in comment
        assert "judged its sample" not in comment
        assert "at or above" not in comment

    def test_a_failed_job_that_judged_its_sample_is_a_verdict_under_the_floor(
        self, tmp_path: Path
    ) -> None:
        """Runs 36373061140 and 36406732958: 150 of 150 judged, 82.0% with the
        interval under 0.88, so the score step failed the job. That is a verdict,
        and the issue says which one, with the score, the interval, the sample size
        and the survivors by node."""
        calls = _announce(
            tmp_path,
            result="failure",
            verdict="judged",
            detail="150 mutant(s) judged: killed 123, survived 27, timeout 0, no_tests 0",
            floor="under",
            report=UNDER_FLOOR_REPORT,
        )
        create = next(call for call in calls if call.startswith("issue create"))
        assert f"--title {UNDER_FLOOR}" in create
        assert "no verdict" not in _state_part(create)
        assert "82.0% of 150 scored mutants" in create
        assert "95% interval 75.1% to 87.3%" in create
        assert "a random sample of 150" in create
        assert "rule-engine: 15 survivor(s)" in create

    def test_a_failed_job_with_no_verdict_is_titled_so(self, tmp_path: Path) -> None:
        calls = _announce(tmp_path, result="failure", verdict="")
        create = next(call for call in calls if call.startswith("issue create"))
        assert f"--title {NO_VERDICT}" in create
        assert "under its floor" not in _state_part(create)

    def test_a_judged_sample_the_score_step_could_not_score_is_no_verdict(
        self, tmp_path: Path
    ) -> None:
        calls = _announce(
            tmp_path, result="failure", verdict="judged", detail="150 judged", floor="unscored"
        )
        create = next(call for call in calls if call.startswith("issue create"))
        assert f"--title {NO_VERDICT}" in create
        assert "the score step reported no floor verdict" in create

    def test_an_open_issue_is_retitled_to_the_state_of_the_week(self, tmp_path: Path) -> None:
        """Issue #85 opened as 'no verdict' over a sample judged under its floor; the
        next run's comment carries the true state, and so does the title."""
        calls = _announce(
            tmp_path,
            result="failure",
            verdict="judged",
            floor="under",
            report=UNDER_FLOOR_REPORT,
            open_issue=_open("85", NO_VERDICT),
        )
        assert "issue comment 85" in _verbs(calls)
        edit = next(call for call in calls if call.startswith("issue edit 85"))
        assert f"--title {UNDER_FLOOR}" in edit
        assert "issue create -R" not in _verbs(calls)

    def test_an_issue_already_in_the_state_of_the_week_keeps_its_title(
        self, tmp_path: Path
    ) -> None:
        calls = _announce(
            tmp_path,
            result="failure",
            verdict="judged",
            floor="under",
            report=UNDER_FLOOR_REPORT,
            open_issue=_open("85", UNDER_FLOOR),
        )
        assert "issue comment 85" in _verbs(calls)
        assert "issue edit 85" not in _verbs(calls)

    def test_a_red_job_opens_the_first_issue(self, tmp_path: Path) -> None:
        """The shape the nine nights took, and the job output is empty because
        the reading step is not what went wrong."""
        calls = _announce(tmp_path, result="failure", verdict="")
        assert "issue create -R" in _verbs(calls)
        body = next(call for call in calls if call.startswith("issue create"))
        assert "@owner" in body
        assert "did not reach the step that reads its counters" in body

    def test_a_green_job_that_judged_nothing_opens_one_too(self, tmp_path: Path) -> None:
        """The shape no job status can see: every step exited 0."""
        calls = _announce(
            tmp_path, result="success", verdict="silent", detail="the second run added no mutants"
        )
        body = next(call for call in calls if call.startswith("issue create"))
        assert "the second run added no mutants" in body

    def test_a_second_failing_night_comments_on_the_first_issue(self, tmp_path: Path) -> None:
        calls = _announce(
            tmp_path,
            result="success",
            verdict="silent",
            detail="the second run added no mutants",
            open_issue=_open("12", NO_VERDICT),
        )
        assert "issue comment 12" in _verbs(calls)
        assert "issue create -R" not in _verbs(calls)

    def test_a_cancelled_job_is_an_outage_and_not_a_pass(self, tmp_path: Path) -> None:
        """`timeout-minutes: 340` and a cancellation by hand both end the job
        without a verdict, which is the state a `needs`-based announcement can
        report and a step inside that job cannot.

        The behaviour is unchanged and its reason moved (`beadloom-vd6r`).
        `cancel-in-progress` used to be the third way to reach this branch and
        the one that made it lie: a run superseded by a newer one is not an
        outage. The concurrency group is now scoped by event, so a dispatch
        cannot cancel the schedule; a supersession by a run of the SAME kind
        still reaches here, and the workflow's header names it among the cases
        the announcement does not cover.
        """
        calls = _announce(
            tmp_path, result="cancelled", verdict="", open_issue=_open("12", NO_VERDICT)
        )
        assert "issue comment 12" in _verbs(calls)


class TestWhichCancellationsCanReachTheAnnouncement:
    """A run cancelled because a newer one superseded it is not an outage.

    The announcement reads `cancelled` as an outage, deliberately: a timed-out
    or killed weekly run is exactly what it exists to report, and the job status is
    all it has to read from. GitHub tells nobody WHY a run was cancelled, so the
    only place the distinction can be made is where the cancellation is caused.

    So the concurrency group is scoped by event as well as by ref. A hand
    dispatch and the schedule are then two groups, and the dispatch cannot cancel
    the scheduled run — which is the cancellation this work item would otherwise
    have caused itself, because `beadloom-e8m4` dispatches a run by hand to read
    the first real verdict.
    """

    def test_a_hand_dispatched_run_cannot_cancel_the_scheduled_one(self) -> None:
        concurrency = _workflow()["concurrency"]
        assert isinstance(concurrency, dict)
        group = str(concurrency["group"])

        assert "github.event_name" in group, (
            "a dispatch and the schedule share a concurrency group, so dispatching "
            "a run cancels the scheduled one and the announcement reports an "
            "outage that is a supersession"
        )
        assert "github.ref" in group, "two branches must not cancel each other either"

    def test_a_superseding_run_of_the_same_kind_still_cancels(self) -> None:
        """The property the group was set for in the first place is kept: two
        scheduled runs, or two dispatches, do not run the scope twice over."""
        concurrency = _workflow()["concurrency"]
        assert isinstance(concurrency, dict)

        assert concurrency["cancel-in-progress"] is True


class TestItStillCannotLockTheTrunk:
    def test_neither_job_is_a_required_status_check(self) -> None:
        """Re-asserted over the job this bead added: a scheduled workflow reports
        no check-run, so a required context naming either job makes `main`
        unmergeable. `test_mutation_ci_job.py` checks the same property; this
        test exists so the failure names the job that was added."""
        from beadloom.onboarding.branch_protection import DEFAULT_STATUS_CHECK_CONTEXTS

        for name in _jobs():
            assert str(name) not in DEFAULT_STATUS_CHECK_CONTEXTS


class TestTheWorkflowsProseNeverCrossesTheLocalesCodec:
    """What the two locale legs found, held where every leg can see it.

    `subprocess` encodes an argv with the FILESYSTEM codec, and outside macOS
    the locale chooses it: ASCII under `LC_ALL=C`, iso8859-1 under
    `en_US.ISO-8859-1`, and neither holds the em dash the announcement's owner
    mention carries (the `announce` job's body). So run 35404835459 was red on both
    locale legs with `UnicodeEncodeError` and green on the UTF-8 tree, which is
    the difference those legs exist for.

    The character is the WORKFLOW's, not a test's, so the fix is where the
    encoding is decided and not in the prose: the script reaches bash through a
    file this module writes as UTF-8, and the argv is then a path. The
    environment went the same way on PR #86's first run, through the score
    report, and is handed to bash as UTF-8 bytes, as the runner hands it. The
    tests below hold both halves on every leg rather than only on the two that
    vary the locale.
    """

    def test_the_announcement_carries_a_character_neither_locale_can_encode(self) -> None:
        """Stated first: over ASCII prose the test below would pass vacuously."""
        script = _announcement_script()

        for codec in ("ascii", "iso8859-1"):
            with pytest.raises(UnicodeEncodeError):
                script.encode(codec)

    def test_no_argument_handed_to_bash_carries_the_workflows_prose(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The argv may hold what the filesystem gave it, and not the workflow.

        The subject is the ANNOUNCEMENT's characters, so that is what this
        measures. Requiring the whole argv to be ASCII would fail on a machine
        whose `TMPDIR` carries a non-ASCII character while the code was right:
        a path the filesystem codec produced can always be encoded back by it.
        """
        recorded: list[list[str]] = []

        def _record(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            recorded.append([str(arg) for arg in argv])
            return subprocess.CompletedProcess(argv, 0, "", "")

        monkeypatch.setattr(subprocess, "run", _record)
        _announce(tmp_path, result="failure", verdict="")

        assert recorded, "the announcement was never invoked, so nothing was measured"
        prose = {char for char in _announcement_script() if not char.isascii()}
        carried = sorted(
            {char for argv in recorded for arg in argv for char in arg if char in prose}
        )
        assert not carried, (
            "an argument carries the workflow's own prose, whose codec is then the "
            "locale's rather than this file's, so the call raises UnicodeEncodeError "
            f"on a non-UTF-8 leg and nowhere else: {carried}"
        )

    @pytest.mark.skipif(shutil.which("bash") is None, reason="both steps are bash steps")
    @pytest.mark.parametrize("step", ["announce", "score"])
    def test_no_environment_value_handed_to_bash_carries_the_reports_prose(
        self, step: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The environment is the argv's other half, and PR #86 found it.

        `subprocess` encodes an environment value with the same filesystem codec
        it encodes an argv with, so the score report — whose floor line carries
        the em dash `beadloom mutation` prints — raised `UnicodeEncodeError` on
        both locale legs of PR #86's first run through `REPORT` and `FAKE_SCORE`,
        ten tests, while the argv guard above held. The runner hands a step its
        environment as UTF-8 bytes whatever the image's locale, so the tests
        hand bash bytes too; a `str` value carrying the report's characters is
        the defect, measured on every leg rather than only on the two that vary
        the locale.
        """
        real_run = subprocess.run
        recorded: list[dict[object, object]] = []

        def _record(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            env = kwargs.get("env")
            assert isinstance(env, dict)
            recorded.append(env)
            return real_run(argv, **kwargs)  # type: ignore[call-overload,no-any-return]  # the spy forwards the caller's own keywords unchanged

        monkeypatch.setattr(subprocess, "run", _record)
        if step == "announce":
            _announce(
                tmp_path,
                result="failure",
                verdict="judged",
                floor="under",
                report=UNDER_FLOOR_REPORT,
            )
        else:
            _score(tmp_path, code=1, text=UNDER_FLOOR_REPORT)

        assert recorded, "the step was never invoked, so nothing was measured"
        prose = {char for char in UNDER_FLOOR_REPORT if not char.isascii()}
        assert prose, "over an ASCII report this test would pass vacuously"
        carried = sorted(
            {
                char
                for env in recorded
                for value in env.values()
                if isinstance(value, str)
                for char in value
                if char in prose
            }
        )
        assert not carried, (
            "an environment value carries the score report as text, whose codec is "
            "then the locale's rather than the runner's UTF-8, so the call raises "
            f"UnicodeEncodeError on a non-UTF-8 leg and nowhere else: {carried}"
        )
