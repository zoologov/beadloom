"""A dead or red nightly says so outside the Actions tab (BDL-072).

The nightly `Mutation` workflow reached a verdict on 0 of 7 187 mutants every
night from 2026-09-10 to 2026-09-18 and nobody saw it, because a scheduled
workflow reports no check-run and its red is visible only to whoever opens the
Actions tab. The workflow now carries an announcement, and these tests read it
the way `test_mutation_ci_job.py` reads the job: as data.

**What they measure, and what they cannot.** The verdict half — "did this run
judge anything" — is a program, so it is RUN here over the four counter shapes
it has to tell apart. The announcement half calls `gh` against a live
repository, so it is read as text: the branch structure is pinned, its behaviour
is not. No test here proves an issue was ever opened; only a dispatched run does
that (`beadloom-e8m4`).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MUTATION = REPO_ROOT / ".github" / "workflows" / "mutation.yml"

#: The mutant total mutmut 3.7 writes for the rules slice alone, rounded to the
#: order of magnitude the comparison cares about rather than to the measurement:
#: these fixtures test the relation between two populations, not either number.
RULES_POPULATION = 3989
WHOLE_POPULATION = 7187


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


def _reader_program() -> str:
    """The Python the reading step feeds to the interpreter on stdin.

    Taken out of the heredoc rather than kept as a second copy: a fixture
    spelling the same logic would pass while the workflow drifted away from it,
    which is the class this whole bead is about.
    """
    run = str(_step_with_id("mutation", "judged")["run"])
    _, _, rest = run.partition("<<'PY'")
    _, _, rest = rest.partition("\n")
    body, sep, _ = rest.partition("\nPY")
    assert sep, "the reading step no longer feeds its program on stdin"
    return body


def _run_reader(tmp_path: Path, files: dict[str, str]) -> dict[str, str]:
    """Run the reading step's own program over a `mutants/` directory."""
    mutants = tmp_path / "mutants"
    mutants.mkdir()
    for name, text in files.items():
        (mutants / name).write_text(text, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-"],
        input=_reader_program(),
        capture_output=True,
        encoding="utf-8",
        cwd=tmp_path,
        check=True,
    )
    pairs = [line.partition("=") for line in result.stdout.splitlines() if line]
    return {key: value for key, _, value in pairs}


def _stats(total: int, *, interrupted: bool = False) -> str:
    """An export in the shape mutmut 3.7 writes (`__main__.py:1177-1191`)."""
    return json.dumps(
        {
            "killed": max(total - 1, 0),
            "survived": 1 if total else 0,
            "total": total,
            "no_tests": 0,
            "skipped": 0,
            "suspicious": 0,
            "timeout": 0,
            "check_was_interrupted_by_user": interrupted,
            "segfault": 0,
        }
    )


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


def _announce(
    tmp_path: Path, *, result: str, verdict: str, detail: str = "", open_issue: str = ""
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
    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "GH_LOG": str(log),
            "GH_TOKEN": "stub",
            "REPO": "owner/repo",
            "OWNER": "owner",
            "WATCH_LABEL": "mutation-nightly",
            "WATCH_TITLE": "Mutation nightly: no verdict",
            "RUN_URL": "https://example.invalid/run/1",
            "RESULT": result,
            "VERDICT": verdict,
            "DETAIL": detail,
            "FAKE_OPEN_ISSUE": open_issue,
        }
    )
    bash = shutil.which("bash")
    assert bash is not None
    # ON DISK, AND NOT IN THE ARGV. `encoding=` governs the child's streams;
    # an argv is encoded with `sys.getfilesystemencoding()`, which the locale
    # chooses — ascii under `LC_ALL=C`, iso8859-1 under `en_US.ISO-8859-1`.
    # The announcement's owner mention carries an em dash (`mutation.yml:548`),
    # so handing the script to bash as an argument raised UnicodeEncodeError on
    # both locale legs of run 35404835459 and on no UTF-8 tree. The script is
    # the workflow's text, so the encoding moves and the prose does not.
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


def _verbs(calls: list[str]) -> list[str]:
    """The `gh` subcommand of each call, which is what the branches differ in."""
    return [" ".join(call.split()[:3]) for call in calls]


class TestTheReadingStepTellsAJudgedRunFromASilentOne:
    """The four shapes, run rather than reasoned about."""

    def test_two_populations_that_differ_are_a_judged_run(self, tmp_path: Path) -> None:
        output = _run_reader(
            tmp_path,
            {
                "rules-cicd-stats.json": _stats(RULES_POPULATION),
                "mutmut-cicd-stats.json": _stats(WHOLE_POPULATION),
            },
        )
        assert output["verdict"] == "judged"
        assert str(WHOLE_POPULATION) in output["detail"]

    def test_a_whole_scope_export_equal_to_the_slice_is_silent(self, tmp_path: Path) -> None:
        """The green shape: both runner invocations exit 0 because they carry
        `|| true`, the second produced nothing, and the cumulative export
        therefore carries the rules slice twice over."""
        output = _run_reader(
            tmp_path,
            {
                "rules-cicd-stats.json": _stats(RULES_POPULATION),
                "mutmut-cicd-stats.json": _stats(RULES_POPULATION),
            },
        )
        assert output["verdict"] == "silent"
        assert str(RULES_POPULATION) in output["detail"]

    def test_an_export_that_was_never_written_is_silent(self, tmp_path: Path) -> None:
        """What the nine nights left behind: `export-cicd-stats` finds no
        `.meta` file, prints its notice and returns 0 without writing."""
        output = _run_reader(tmp_path, {})
        assert output["verdict"] == "silent"
        assert "never exported" in output["detail"]

    def test_an_empty_population_is_silent(self, tmp_path: Path) -> None:
        output = _run_reader(
            tmp_path,
            {
                "rules-cicd-stats.json": _stats(0),
                "mutmut-cicd-stats.json": _stats(0),
            },
        )
        assert output["verdict"] == "silent"
        assert "0 mutants" in output["detail"]

    def test_an_interrupted_run_is_silent_even_with_a_full_population(
        self, tmp_path: Path
    ) -> None:
        """A score over a truncated population is a ratio over the part."""
        output = _run_reader(
            tmp_path,
            {
                "rules-cicd-stats.json": _stats(RULES_POPULATION),
                "mutmut-cicd-stats.json": _stats(WHOLE_POPULATION, interrupted=True),
            },
        )
        assert output["verdict"] == "silent"
        assert "interrupted" in output["detail"]

    def test_an_unreadable_export_is_an_absence_and_not_a_zero(self, tmp_path: Path) -> None:
        output = _run_reader(
            tmp_path,
            {
                "rules-cicd-stats.json": _stats(RULES_POPULATION),
                "mutmut-cicd-stats.json": "not json at all",
            },
        )
        assert output["verdict"] == "silent"
        assert "never exported" in output["detail"]


class TestTheVerdictReachesTheAnnouncement:
    def test_the_reading_step_runs_after_a_failed_step(self) -> None:
        """Its interesting cases are the runs where something already went red."""
        assert _step_with_id("mutation", "judged")["if"] == "always()"

    def test_the_job_publishes_what_the_step_read(self) -> None:
        outputs = _job("mutation")["outputs"]
        assert isinstance(outputs, dict)
        assert outputs["verdict"] == "${{ steps.judged.outputs.verdict }}"
        assert outputs["detail"] == "${{ steps.judged.outputs.detail }}"


class TestTheAnnouncementSpeaksForAJobThatCannotSpeak:
    def test_it_is_a_separate_job_that_runs_whatever_happened(self) -> None:
        """`timeout-minutes` and `concurrency` both END the mutation job, and a
        step inside a killed job is not guaranteed to run. A dependent job reads
        `needs.mutation.result` and runs either way."""
        announce = _job("announce")
        assert announce["needs"] == "mutation"
        assert announce["if"] == "always()"

    def test_it_is_the_only_job_holding_the_token_that_can_write(self) -> None:
        """The mutation job executes mutated source. The smallest job that needs
        `issues: write` is the one that carries it."""
        assert _workflow()["permissions"] == {"contents": "read"}
        assert _job("announce")["permissions"] == {"issues": "write"}
        assert "permissions" not in _job("mutation")

    def test_it_reads_both_shapes_of_silence(self) -> None:
        """`if: failure()` covers one shape. The announcement asks the job
        result AND the counters, so the green shape reaches it too."""
        script = "\n".join(str(step.get("run", "")) for step in _steps("announce"))
        assert "needs.mutation.result" in str(_steps("announce"))
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
    """The script, RUN, over the six states a nightly can hand it.

    Six calls to a stubbed `gh`, so what is measured here is which branch the
    script takes and with what arguments. It is not measured against GitHub.
    """

    def test_a_judged_run_with_nothing_open_says_nothing(self, tmp_path: Path) -> None:
        calls = _announce(tmp_path, result="success", verdict="judged")
        assert _verbs(calls) == ["label create mutation-nightly", "issue list -R"]

    def test_a_judged_run_closes_the_issue_the_outage_opened(self, tmp_path: Path) -> None:
        calls = _announce(tmp_path, result="success", verdict="judged", open_issue="12")
        assert "issue close 12" in _verbs(calls)
        assert "issue create -R" not in _verbs(calls)

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
            open_issue="12",
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
        calls = _announce(tmp_path, result="cancelled", verdict="", open_issue="12")
        assert "issue comment 12" in _verbs(calls)


class TestWhichCancellationsCanReachTheAnnouncement:
    """A run cancelled because a newer one superseded it is not an outage.

    The announcement reads `cancelled` as an outage, deliberately: a timed-out
    or killed nightly is exactly what it exists to report, and the job status is
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
    mention carries (`mutation.yml:548`). So run 35404835459 was red on both
    locale legs with `UnicodeEncodeError` and green on the UTF-8 tree, which is
    the difference those legs exist for.

    The character is the WORKFLOW's, not a test's, so the fix is where the
    encoding is decided and not in the prose: the script reaches bash through a
    file this module writes as UTF-8, and the argv is then a path. These two
    tests hold that on every leg rather than only on the two that vary the
    locale.
    """

    def test_the_announcement_carries_a_character_neither_locale_can_encode(self) -> None:
        """Stated first: over ASCII prose the test below would pass vacuously."""
        script = _announcement_script()

        for codec in ("ascii", "iso8859-1"):
            with pytest.raises(UnicodeEncodeError):
                script.encode(codec)

    def test_no_argument_handed_to_bash_needs_more_than_ascii(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded: list[list[str]] = []

        def _record(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            recorded.append([str(arg) for arg in argv])
            return subprocess.CompletedProcess(argv, 0, "", "")

        monkeypatch.setattr(subprocess, "run", _record)
        _announce(tmp_path, result="failure", verdict="")

        assert recorded, "the announcement was never invoked, so nothing was measured"
        carried = [arg for argv in recorded for arg in argv if not arg.isascii()]
        assert not carried, (
            "an argument carries a character the locale's filesystem codec need not "
            "hold, so this call raises UnicodeEncodeError on a non-UTF-8 leg and "
            f"nowhere else: {carried}"
        )
