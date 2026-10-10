"""The mutation workflow's two jobs, and the lockout they must not cause (BDL-074 D1).

The whole-scope nightly this file used to read was retired on 2026-09-27: ten of
its runs were killed by the runner mid-queue and none reached a verdict. Two
narrower jobs replace it — `mutation-per-change` on pull requests, over the
functions a change touched, and `mutation-sample` on a weekly schedule, over a
seeded random sample of the declared scope. Each has to say what it covered.

The scope the sample scores is DERIVED from `.beadloom/flow.yml` here rather
than spelled, and the size and timeouts are checked against the numbers the
workflow's header derives them from.

These tests read the workflow as data. None of them proves a job runs; the
verification bead (`beadloom-paze`) reads one real run of each.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
MUTATION = WORKFLOWS / "mutation.yml"
ADAPTER = ".github/scripts/mutmut_adapter.py"

PER_CHANGE = "mutation-per-change"
SAMPLE = "mutation-sample"

#: PyYAML reads the workflow key `on` as the boolean True (the Norway problem's
#: cousin). Named here so the tests read as the workflow does.
_ON = True

#: The most mutmut children one invocation may run; the reason is on the test
#: that holds it.
_MAX_CHILDREN = 2

#: The sample size the header derives: 22 minutes of mutant time at two
#: children over an 18.5 s mean worst-case cost per mutant.
_DERIVED_SAMPLE = "150"

#: The queue time at which the retired nightly's runner first killed it.
_FIRST_KILL_MINUTES = 73

#: The per-change budget the PRD states, in minutes on `ubuntu-latest`.
_PER_CHANGE_BUDGET_MINUTES = 10

#: The mutants a per-change run is capped at, as the workflow's header derives it.
_DERIVED_MUTANT_BUDGET = "350"

#: The measured cost of a mutant of the functions the cap takes, at two children,
#: in seconds: 600 of PR #98's ran in 1 807 s on Darwin arm64, a room level with
#: the runner on the stats pass (205 s against 202 s, `beadloom-af99.17`).
_RUNNER_SECONDS_PER_MUTANT = 3.0

#: The minutes before the first mutant on the runner (PR #98: 3 min 50 s, the
#: stats pass 3 min 22 s of it) and after the last (counters, score, judge, upload).
_FIXED_MINUTES = 5

#: What the job keeps between its last step and its limit, in minutes.
_MARGIN_MINUTES = 7


def _workflow() -> dict[object, object]:
    data = yaml.safe_load(MUTATION.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _triggers() -> dict[str, object]:
    """The workflow's `on:` block, which PyYAML hands back under the key True."""
    triggers = _workflow()[_ON]
    assert isinstance(triggers, dict)
    return triggers


def _jobs() -> dict[str, dict[str, object]]:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    return {str(name): job for name, job in jobs.items()}


def _declared_targets() -> list[str]:
    """The shipped declaration, read from the file `config-check` reads."""
    flow = yaml.safe_load((REPO_ROOT / ".beadloom" / "flow.yml").read_text(encoding="utf-8"))
    targets = flow["mutation"]["targets"]
    assert isinstance(targets, list)
    return [str(target) for target in targets]


def _run_steps(job: str | None = None) -> list[str]:
    """The `run:` body of each step, kept apart so a claim about ONE step is not
    checked against the concatenation of all of them."""
    names = [job] if job else list(_jobs())
    bodies: list[str] = []
    for name in names:
        steps = _jobs()[name].get("steps", [])
        assert isinstance(steps, list)
        bodies.extend(str(step["run"]) for step in steps if step.get("run"))
    return bodies


def _children(step: str) -> float:
    """The children one `mutmut run` step asks for; unbounded when it names none,
    because mutmut then runs one per CPU."""
    found = re.search(r"--max-children\s+(\d+)", step)
    return float("inf") if found is None else int(found.group(1))


def _steps_text(job: str | None = None) -> str:
    return "\n".join(_run_steps(job))


class TestEachJobRunsOnItsOwnEvent:
    def test_the_sample_runs_weekly(self) -> None:
        """The cron's day-of-week field names one day: weekly, not nightly."""
        schedule = _triggers()["schedule"]
        assert isinstance(schedule, list)
        fields = str(schedule[0]["cron"]).split()
        assert fields[2:4] == ["*", "*"]
        assert fields[4] != "*"

    def test_the_sample_can_be_dispatched_by_hand(self) -> None:
        """A weekly run with no manual trigger cannot be run when it matters."""
        assert "workflow_dispatch" in _triggers()

    def test_the_per_change_job_runs_on_a_pull_request_and_only_there(self) -> None:
        assert "pull_request" in _triggers()
        assert _jobs()[PER_CHANGE]["if"] == "github.event_name == 'pull_request'"

    def test_the_sample_never_runs_on_a_pull_request(self) -> None:
        """Its budget is 50 minutes; on a pull request it would be the pipeline's
        whole critical path, which is what withdrew `tests-windows`."""
        assert _jobs()[SAMPLE]["if"] == "github.event_name != 'pull_request'"

    def test_the_per_change_diff_has_a_merge_base_to_reach(self) -> None:
        """A shallow checkout has no `origin/<base>` history to diff against."""
        steps = _jobs()[PER_CHANGE]["steps"]
        assert isinstance(steps, list)
        checkout = next(step for step in steps if "checkout" in str(step.get("uses", "")))
        assert checkout["with"]["fetch-depth"] == 0


class TestItCannotLockTheTrunk:
    def test_no_job_is_a_required_status_check(self) -> None:
        """A scheduled job reports no check-run on a PR, and a disabled workflow
        reports nothing at all. Requiring either context under `strict: true`
        makes every PR — and `main` — unmergeable, which is the trap
        `DEFAULT_STATUS_CHECK_CONTEXTS` already documents for the withdrawn
        Windows leg."""
        from beadloom.onboarding.branch_protection import DEFAULT_STATUS_CHECK_CONTEXTS

        for name, job in _jobs().items():
            assert name not in DEFAULT_STATUS_CHECK_CONTEXTS
            assert str(job.get("name", name)) not in DEFAULT_STATUS_CHECK_CONTEXTS


class TestTheVerdictIsTheProductsAndNotTheRunners:
    def test_no_runner_invocation_decides_the_verdict(self) -> None:
        """`mutmut run` exits non-zero whenever a mutant survives, which is a
        normal outcome. Checked over EVERY invocation in both jobs."""
        runs = [step for step in _run_steps() if "mutmut run" in step]
        assert len(runs) == 2
        undefended = [step for step in runs if "|| true" not in step]
        assert undefended == [], undefended

    def test_no_runner_invocation_runs_more_than_two_children(self) -> None:
        """At four children a mutant was counted killed by an IntegrityError from
        the live index the children share (beadloom-qq6m), and survived when run
        alone: 16 s "killed" against 49 s survived, measured on 2026-09-19. A
        false kill inflates the score the floors are held to.

        The ceiling is two, not one, because two is the owner's decision
        (BDL-073). An invocation that omits the flag gets mutmut's default of one
        child per CPU, so it fails here too.
        """
        runs = [step for step in _run_steps() if "mutmut run" in step]
        too_many = [step for step in runs if _children(step) > _MAX_CHILDREN]
        assert too_many == [], too_many

    def test_every_runner_invocation_takes_exact_names_from_the_adapter(self) -> None:
        """A glob ending `__mutmut_*` makes mutmut's clean run fall back to the
        whole selection (BDL-073), so no invocation names a pattern: each reads
        the names file the adapter wrote from `mutants/*.meta`."""
        runs = [step for step in _run_steps() if "mutmut run" in step]
        for step in runs:
            assert '"${names[@]}"' in step, step
            assert "mapfile -t names <" in step, step
            assert "*" not in step.split("mutmut run", 1)[1].replace("${names[@]}", ""), step

    def test_no_runner_invocation_can_be_handed_an_empty_name_list(self) -> None:
        """`mutmut run` with no names mutates the WHOLE declared scope — the run
        this workflow replaced because its runner was killed. Found on
        2026-09-27: `mapfile` does not exist in macOS's bash 3.2, the array came
        back empty, and a local run of this step started on all 6 992 mutants.
        Each step therefore refuses an empty list before the runner sees it."""
        runs = [step for step in _run_steps() if "mutmut run" in step]
        for step in runs:
            guard = step.find('if [ "${#names[@]}" -eq 0 ]; then')
            assert guard != -1, step
            assert guard < step.index("mutmut run"), step
            assert "exit 1" in step[guard : step.index("mutmut run")], step

    @pytest.mark.parametrize("names", ["\n", "", "\n  \n"], ids=["newline", "empty", "blanks"])
    def test_a_names_file_holding_no_name_is_refused(self, tmp_path: Path, names: str) -> None:
        """First review of ``beadloom-b9ll``, n1: a sample of size 0 writes a names
        file holding one newline, `mapfile` reads it as one empty name, and the
        guard above passed it on. The guard is run here, up to its `fi`, under a
        bash that has `mapfile`, against each file that holds no name."""
        bash = shutil.which("bash")
        version = subprocess.run(  # noqa: S603 - a fixed argv to the bash on PATH
            [bash or "bash", "-c", "echo ${BASH_VERSINFO[0]}"],
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        if bash is None or int(version.stdout.strip() or 0) < 4:
            pytest.skip("no bash with `mapfile` on PATH (macOS ships bash 3.2)")
        runs = [step for step in _run_steps() if "mutmut run" in step]
        assert runs
        for step in runs:
            guard = step[step.index("mapfile") : step.index("fi", step.index("-eq 0")) + 2]
            names_file = re.search(r'"\$RUNNER_TEMP/([\w.-]+)"', guard)
            assert names_file is not None, guard
            (tmp_path / names_file.group(1)).write_text(names, encoding="utf-8")
            result = subprocess.run(  # noqa: S603 - the script is this repository's workflow
                [bash, "-c", guard],
                env={"RUNNER_TEMP": str(tmp_path), "PATH": "/usr/bin:/bin"},
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            assert result.returncode == 1, (guard, result.stdout)
            assert "::error::" in result.stdout

    def test_the_counters_cover_exactly_the_names_that_were_selected(self) -> None:
        """`mutmut export-cicd-stats` counts every mutant in every `.meta`, run or
        not; the adapter counts the selected names and nothing else."""
        for job in (PER_CHANGE, SAMPLE):
            text = _steps_text(job)
            assert f"{ADAPTER} counters" in text, job
            assert "export-cicd-stats" not in text, job

    def test_the_score_is_produced_by_the_command(self) -> None:
        assert "--stats mutants/change-stats.json" in _steps_text(PER_CHANGE)
        assert "--stats mutants/sample-stats.json" in _steps_text(SAMPLE)
        for job in (PER_CHANGE, SAMPLE):
            assert "beadloom mutation" in _steps_text(job)

    def test_the_generated_selection_is_undone_before_the_change_is_scored(self) -> None:
        """`select` rewrites `pyproject.toml` in the checkout; the score step
        re-reads the change from git, and would count that rewrite as a changed
        file of the pull request. Measured on 2026-09-27: "2 file(s) changed" for
        a one-file change, until the committed file was restored first."""
        steps = _jobs()[PER_CHANGE]["steps"]
        assert isinstance(steps, list)
        runs = [str(step.get("run", "")) for step in steps]
        restore = next(i for i, run in enumerate(runs) if "git checkout -- pyproject.toml" in run)
        mutate = next(i for i, run in enumerate(runs) if "mutmut run" in run)
        score = next(
            i for i, run in enumerate(runs) if "beadloom mutation" in run and "--stats" in run
        )
        assert mutate < restore < score

    def test_the_per_change_score_covers_the_change_and_lists_survivors_by_node(self) -> None:
        scoring = [
            s
            for s in _run_steps(PER_CHANGE)
            if "beadloom mutation" in s and "--stats mutants/change-stats" in s
        ]
        assert len(scoring) == 1
        assert '--changed-since "$BASE"' in scoring[0]
        assert "--survivors mutants/change-survivors.json" in scoring[0]

    def test_the_sample_judges_every_target_the_declaration_names(self) -> None:
        """Derived from `mutation.targets`: a sample is drawn from the whole
        declared scope, so its scoring step names every target and narrows none
        away with `--only`."""
        declared = _declared_targets()
        scoring = [s for s in _run_steps(SAMPLE) if "beadloom mutation" in s]
        whole = [
            step
            for step in scoring
            if "--only" not in step and all(f"--target {t}" in step for t in declared)
        ]
        assert whole, f"no sample scoring step names all {len(declared)} declared target(s)"
        assert all("--sample-of" in step for step in whole)

    def test_each_score_is_held_to_a_floor(self) -> None:
        """A job that cannot fail reports nothing."""
        for job in (PER_CHANGE, SAMPLE):
            assert "--min-score" in _steps_text(job), job


class TestTheSizesAreTheDerivedOnes:
    def test_the_sample_size_is_the_derived_one_in_both_places_it_is_set(self) -> None:
        dispatch = _triggers()["workflow_dispatch"]
        assert isinstance(dispatch, dict)
        assert dispatch["inputs"]["size"]["default"] == _DERIVED_SAMPLE
        env = _jobs()[SAMPLE]["env"]
        assert isinstance(env, dict)
        assert env["SAMPLE_SIZE"] == f"${{{{ inputs.size || '{_DERIVED_SAMPLE}' }}}}"

    def test_the_sample_ends_before_the_point_the_nightly_was_first_killed(self) -> None:
        """A run that times out is announced; a run killed by the runner is not
        explained. The timeout stays under the first measured kill."""
        timeout = _jobs()[SAMPLE]["timeout-minutes"]
        assert isinstance(timeout, int)
        assert timeout < _FIRST_KILL_MINUTES

    def test_the_per_change_job_outlives_its_budget_and_states_it(self) -> None:
        """Over-budget is a number to report, not a run to cut off (RFC risk)."""
        job = _jobs()[PER_CHANGE]
        timeout = job["timeout-minutes"]
        assert isinstance(timeout, int)
        assert timeout > _PER_CHANGE_BUDGET_MINUTES
        env = job["env"]
        assert isinstance(env, dict)
        assert env["BUDGET_SECONDS"] == str(_PER_CHANGE_BUDGET_MINUTES * 60)
        assert "::warning::" in _steps_text(PER_CHANGE)

    def test_the_per_change_selection_is_capped_and_the_rest_is_named(self) -> None:
        """A 36-commit pull request selected 1 168 mutants and was cancelled at
        the job's limit before its judge ran (`beadloom-af99.17`): the select
        step is given the derived budget and writes what it left out, and the
        judge and the job's summary name that remainder."""
        job = _jobs()[PER_CHANGE]
        env = job["env"]
        assert isinstance(env, dict)
        assert env["MUTANT_BUDGET"] == _DERIVED_MUTANT_BUDGET
        steps = _run_steps(PER_CHANGE)
        select = [s for s in steps if f"{ADAPTER} select" in s]
        assert len(select) == 1
        assert '--budget "$MUTANT_BUDGET"' in select[0]
        assert '--left-out "$RUNNER_TEMP/unmeasured.txt"' in select[0]
        assert "GITHUB_STEP_SUMMARY" in select[0]
        # An unnamed shell is `bash -e`, without pipefail: a refusal piped into
        # `tee` would exit 0 and the job would run on with no names.
        assert "set -o pipefail" in select[0]
        judge = [s for s in steps if f"{ADAPTER} judge" in s]
        assert len(judge) == 1
        assert '--left "$RUNNER_TEMP/unmeasured.txt"' in judge[0]
        assert "GITHUB_STEP_SUMMARY" in judge[0]

    def test_the_budget_leaves_the_job_its_margin(self) -> None:
        """The header derives the budget; this holds the derivation's arithmetic:
        the fixed minutes plus the budget's mutants at the runner's measured rate
        end before the limit by the margin."""
        timeout = _jobs()[PER_CHANGE]["timeout-minutes"]
        assert isinstance(timeout, int)
        run_minutes = int(_DERIVED_MUTANT_BUDGET) * _RUNNER_SECONDS_PER_MUTANT / 60
        assert _FIXED_MINUTES + run_minutes + _MARGIN_MINUTES <= timeout

    def test_the_seed_defaults_to_the_iso_week(self) -> None:
        """Reproducible from the commit and the seed alone."""
        assert "date -u +%G-W%V" in _steps_text(SAMPLE)


class TestTheRunnerStaysOffEveryOtherLeg:
    def test_only_this_workflow_installs_the_mutation_extra(self) -> None:
        """Tool-agnosticism as a property of the pipeline: no leg an adopter
        would copy installs a mutation runner."""
        others = {
            path.name: path.read_text(encoding="utf-8")
            for path in WORKFLOWS.glob("*.yml")
            if path != MUTATION
        }
        for name, text in others.items():
            assert "--extra mutation" not in text, name
            assert "mutmut" not in text, name

    def test_both_jobs_install_it(self) -> None:
        for job in (PER_CHANGE, SAMPLE):
            assert "--extra mutation" in _steps_text(job), job
