"""CLI/hook verdict parity and the read-only invariant (BDL-061 S1).

Two claims S1 makes that are easy to test vacuously:

* *"A guard verdict is identical from the CLI and from the hook adapter."*
  Comparing exit codes proves almost nothing — three of the four outcomes share
  two codes. Parity here means the **whole verdict**: the JSON payload, the
  rendered text, and which stream it landed on, over every outcome.
* *"No guard writes to the index."* The absence of an obvious write is not
  evidence. These tests digest every byte of the project (and of a real
  Beadloom database) before and after, and name the one file that may change.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import warnings
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.application.guards.contract import ClaimedBead, GuardProbes
from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.firing import FIRINGS_RELPATH
from beadloom.services.cli import main
from tests.support.guard_parity import (
    _CONTROL_WINDOW_FLOOR_S,
    Attribution,
    _attribute_by_file,
    _moved_with_nothing_running,
    attribute,
    differing,
    report_attribution,
)

#: The ``bd`` subcommands a guard evaluation may issue. Exactly one, deliberately:
#: a wider "read-only" set would be an authored claim about bd, and ``comments``
#: alone reads or writes depending on its next word.
#: :class:`TestTheTrackerExportIsOutsideTheGuardsReach` holds the evaluation
#: against this set, which is what makes :data:`_TRACKER_EXPORT_NAMES` a derived
#: partition rather than an ignore list somebody wrote down once.
_READ_ONLY_BD_SUBCOMMANDS = frozenset({"list"})


@pytest.fixture()
def guard_cli(monkeypatch, make_guard_probes):
    """Invoke ``beadloom guard`` with stubbed probes; returns a runner callable.

    The probes are stubbed at the CLI seam (the boundary), never the evaluator —
    so both callers under comparison go through the identical decision path.
    """
    from beadloom.services.commands import guard as guard_cmd

    def run(args, *, beads=(), branch="features/BDL-061", stdin=None):
        monkeypatch.setattr(
            guard_cmd, "_probes", lambda _root: make_guard_probes(beads=beads, branch=branch)
        )
        return CliRunner().invoke(main, args, input=stdin)

    return run


def _payload(**tool_input: str) -> str:
    return json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": dict(tool_input),
        }
    )


# outcome name -> (probe beads, extra flow.yml, expected exit code)
_CELLS = {
    "pass": ((ClaimedBead(id="bd-1"),), "", 0),
    "warn": ((), "", 1),
    "block": ((), "guards:\n  bead-claimed:\n    strictness: {default: block}\n", 2),
    "skip": (None, "", 0),
}


@pytest.fixture(autouse=True)
def _tmp_path_is_the_project_under_test(guard_project):
    """Every test in this module points ``--project`` at ``tmp_path``.

    ``--project`` requires the marker since BDL-061.31, so the directory the
    tests treat as the project has to actually be one.
    """


class TestVerdictParityAcrossEveryOutcome:
    """Identical verdicts, not merely identical success."""

    @pytest.mark.parametrize("cell", sorted(_CELLS))
    def test_the_hook_and_the_shell_produce_the_same_json_verdict(
        self, tmp_path, write_flow_yml, guard_cli, cell
    ) -> None:
        # Arrange
        beads, flow, expected_code = _CELLS[cell]
        if flow:
            write_flow_yml(flow)
        target = tmp_path / "src" / "app.py"
        base = ["guard", "bead-claimed", "--project", str(tmp_path), "--json"]

        # Act
        via_hook = guard_cli(
            [*base, "--hook", "claude-code"],
            beads=beads,
            stdin=_payload(file_path=str(target)),
        )
        via_shell = guard_cli(
            [
                *base,
                "--context",
                f"path={target}",
                "--context",
                "tool=Edit",
                "--context",
                "event=PreToolUse",
            ],
            beads=beads,
        )

        # Assert
        assert json.loads(via_hook.stdout) == json.loads(via_shell.stdout)
        assert json.loads(via_hook.stdout)["outcome"] == cell
        assert via_hook.exit_code == via_shell.exit_code == expected_code

    @pytest.mark.parametrize("cell", sorted(_CELLS))
    def test_the_hook_and_the_shell_render_the_same_text_on_the_same_stream(
        self, tmp_path, write_flow_yml, guard_cli, cell
    ) -> None:
        """A warning the hook sends to stdout is invisible where it matters."""
        beads, flow, expected_code = _CELLS[cell]
        if flow:
            write_flow_yml(flow)
        target = tmp_path / "src" / "app.py"
        base = ["guard", "bead-claimed", "--project", str(tmp_path)]

        via_hook = guard_cli(
            [*base, "--hook", "claude-code"],
            beads=beads,
            stdin=_payload(file_path=str(target)),
        )
        via_shell = guard_cli(
            [*base, "--context", f"path={target}", "--context", "tool=Edit",
             "--context", "event=PreToolUse"],
            beads=beads,
        )

        assert via_hook.stdout == via_shell.stdout
        assert via_hook.stderr == via_shell.stderr
        assert via_hook.exit_code == via_shell.exit_code == expected_code
        loud = cell in ("warn", "block")
        assert bool(via_hook.stderr.strip()) is loud
        assert bool(via_hook.stdout.strip()) is not loud

    def test_an_exclusion_declared_relatively_also_exempts_the_hook_absolute_path(
        self, tmp_path, write_flow_yml, guard_cli
    ) -> None:
        """The harness only ever sends absolute paths; a relative-only match kills exclusions."""
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    strictness: {default: block}\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts are not bead-scoped'\n"
            "        until: 'BDL-999'\n"
        )
        args = ["guard", "bead-claimed", "--project", str(tmp_path), "--json"]

        via_hook = guard_cli(
            [*args, "--hook", "claude-code"],
            beads=(),
            stdin=_payload(file_path=str(tmp_path / "scripts" / "deploy.sh")),
        )

        assert via_hook.exit_code == 0, via_hook.output
        assert json.loads(via_hook.stdout)["outcome"] == "skip"

    def test_a_notebook_edit_yields_the_same_verdict_as_a_file_edit(
        self, tmp_path, guard_cli
    ) -> None:
        args = ["guard", "bead-claimed", "--project", str(tmp_path), "--json"]
        target = str(tmp_path / "analysis.ipynb")

        via_notebook = guard_cli(
            [*args, "--hook", "claude-code"], beads=(), stdin=_payload(notebook_path=target)
        )
        via_file = guard_cli(
            [*args, "--hook", "claude-code"], beads=(), stdin=_payload(file_path=target)
        )

        assert json.loads(via_notebook.stdout) == json.loads(via_file.stdout)

    def test_an_empty_hook_payload_matches_a_shell_call_with_no_context(
        self, tmp_path, guard_cli
    ) -> None:
        args = ["guard", "bead-claimed", "--project", str(tmp_path), "--json"]

        via_hook = guard_cli([*args, "--hook", "claude-code"], beads=(), stdin="")
        via_shell = guard_cli(args, beads=())

        assert json.loads(via_hook.stdout) == json.loads(via_shell.stdout)
        assert via_hook.exit_code == via_shell.exit_code == 1

    def test_an_explicit_context_flag_overrides_the_hook_supplied_value(
        self, tmp_path, guard_cli
    ) -> None:
        """A human debugging a hook verdict must be able to substitute one field."""
        result = guard_cli(
            [
                "guard", "bead-claimed", "--project", str(tmp_path), "--json",
                "--hook", "claude-code", "--context", "path=src/override.py",
            ],
            beads=(),
            stdin=_payload(file_path=str(tmp_path / "src" / "from_hook.py")),
        )

        payload = json.loads(result.stdout)
        assert payload["context"]["path"] == "src/override.py"
        assert payload["context"]["tool"] == "Edit"

    @pytest.mark.parametrize("raw", ["[]", '"a string"', "3", "null", "not json", "{"])
    def test_a_payload_that_is_not_an_event_object_blocks_and_is_recorded(
        self, tmp_path, guard_cli, raw
    ) -> None:
        """Exit 2, never 0: a hook Beadloom cannot read must not read as "nothing to check".

        It was exit 3 until BDL-061.29. Both codes are non-zero, but only 2
        blocks in the shipped adapter, and this input comes from the harness at
        edit time — so it is the guard failing to answer about *this* edit, not
        a defect in the project's declared configuration.
        """
        from beadloom.application.guards.firing import read_firings

        result = guard_cli(
            ["guard", "bead-claimed", "--project", str(tmp_path), "--hook", "claude-code"],
            beads=(),
            stdin=raw,
        )

        assert result.exit_code == 2, result.output
        assert [record.outcome for record in read_firings(tmp_path)] == ["error"]

    def test_a_config_error_never_borrows_the_warn_or_block_code(
        self, tmp_path, write_flow_yml, guard_cli
    ) -> None:
        """Regression (BDL-061.2): a malformed value crashed out on Click's exit 1 = warn."""
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: [warn]}\n")

        result = guard_cli(
            ["guard", "bead-claimed", "--project", str(tmp_path)], beads=()
        )

        assert result.exit_code == 3, result.output
        assert result.exception is None or isinstance(result.exception, SystemExit)


class TestTheEmittedAdapterAgreesWithTheCli:
    """A stub proves the stub — this runs the real emitted shell script."""

    @staticmethod
    def _env() -> dict[str, str]:
        env = dict(os.environ)
        env["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{env.get('PATH', '')}"
        return env

    @pytest.fixture()
    def repo_on_trunk(self, tmp_path) -> Path:
        """A git working copy that is also a Beadloom project.

        The marker directory is not decoration: since BDL-061.29 the project
        root is discovered by walking up for ``.beadloom/`` rather than taken
        from the working directory, and a guard that finds no project answers
        ``error`` instead of guessing that ``cwd`` is one.
        """
        subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", "init", "-b", "main", str(tmp_path)],  # noqa: S607
            check=True,
            capture_output=True,
        )
        (tmp_path / ".beadloom").mkdir(exist_ok=True)
        return tmp_path

    def test_the_generated_hook_script_and_a_direct_call_agree_byte_for_byte(
        self, repo_on_trunk
    ) -> None:
        from beadloom.onboarding.guard_hooks import GUARD_HOOK_RELPATH, scaffold_guard_hooks

        env = self._env()
        if not (Path(sys.executable).parent / "beadloom").exists():
            pytest.skip("beadloom console script not installed in this environment")
        scaffold_guard_hooks(repo_on_trunk, guard_names=["working-branch"])
        script = repo_on_trunk / GUARD_HOOK_RELPATH
        payload = _payload(file_path=str(repo_on_trunk / "src" / "app.py"))

        via_script = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [str(script), "working-branch"],
            cwd=str(repo_on_trunk),
            input=payload,
            capture_output=True,
            # The child speaks UTF-8 by contract (our own CLI, a JSON payload, a shell
            # block from a YAML file); `text=True` would have decoded it with the
            # image's locale instead (BDL-061.42).
            encoding="utf-8",
            env=env,
            check=False,
        )
        via_cli = subprocess.run(  # fixed argv, no shell
            ["beadloom", "guard", "working-branch", "--hook", "claude-code"],  # noqa: S607
            cwd=str(repo_on_trunk),
            input=payload,
            capture_output=True,
            encoding="utf-8",
            env=env,
            check=False,
        )

        # The real trunk violation: warn, on stderr, exit 1 — identical from both.
        assert via_script.returncode == via_cli.returncode == 1
        assert via_script.stdout == via_cli.stdout == ""
        assert via_script.stderr == via_cli.stderr
        assert "working-branch: WARN" in via_script.stderr


def _digest_tree(root: Path, *, skip: tuple[str, ...] = ()) -> dict[str, str]:
    """sha256 of every file under *root*, keyed by project-relative POSIX path."""
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(skip):
            continue
        digests[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


class TestGuardsAreReadOnly:
    def test_evaluating_every_guard_changes_nothing_but_the_firing_record(
        self, tmp_path, write_flow_yml
    ) -> None:
        """Whole-tree byte digest, including a real Beadloom database file."""
        from beadloom.infrastructure.db import create_schema, open_db

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = open_db(db_path)
        create_schema(connection)
        connection.close()
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: block}\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

        before = _digest_tree(tmp_path)
        for name, beads, branch in (
            ("bead-claimed", (), "features/x"),
            ("bead-claimed", (ClaimedBead(id="bd-1"),), "features/x"),
            ("bead-claimed", None, "features/x"),
            ("working-branch", (), "main"),
            ("working-branch", (), None),
        ):
            evaluate_guard(
                name,
                project_root=tmp_path,
                context={"path": "src/app.py"},
                probes=GuardProbes(
                    tracker=_FixedTracker(beads), workspace=_FixedWorkspace(branch)
                ),
            )
        after = _digest_tree(tmp_path)

        assert after == before

    def test_the_cli_adds_the_firing_record_and_touches_nothing_else(
        self, tmp_path, guard_cli
    ) -> None:
        from beadloom.infrastructure.db import create_schema, open_db

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = open_db(db_path)
        create_schema(connection)
        connection.close()

        before = _digest_tree(tmp_path)
        guard_cli(["guard", "bead-claimed", "--project", str(tmp_path)], beads=())
        guard_cli(["guard", "working-branch", "--project", str(tmp_path)], branch="main")
        after = _digest_tree(tmp_path)

        firings = FIRINGS_RELPATH.as_posix()
        assert set(after) - set(before) == {firings}
        assert {k: v for k, v in after.items() if k != firings} == before


class TestAttributionDistinguishesTheWriter:
    """The m4 apparatus itself, because a wrong verdict here hides a real write.

    These are unit checks on the two helpers the live-index test leans on. If
    ``differing`` under-reports, a guard that writes reads green; if
    ``_moved_with_nothing_running`` over-reports, every run skips and the
    read-only invariant is never measured at all. Both directions are checked.
    """

    def test_a_changed_digest_is_reported(self) -> None:
        assert differing({"a": "1"}, {"a": "2"}) == ["a"]

    def test_an_appearing_and_a_vanishing_file_are_both_reported(self) -> None:
        assert differing({}, {"wal": "1"}) == ["wal"]
        assert differing({"wal": "1"}, {}) == ["wal"]

    def test_identical_snapshots_report_nothing(self) -> None:
        assert differing({"a": "1", "b": "2"}, {"a": "1", "b": "2"}) == []

    def test_a_still_repository_yields_no_excuse_to_skip(self) -> None:
        """A stable snapshot must NOT look like a concurrent writer."""
        assert _moved_with_nothing_running(lambda: {"a": "1"}, 0.0) == []

    def test_a_moving_repository_is_detected_as_another_writer(self) -> None:
        """A snapshot that changes over the idle window names what moved."""
        counter = iter(range(10))
        assert _moved_with_nothing_running(lambda: {"a": str(next(counter))}, 0.0) == ["a"]

    def test_the_control_window_is_never_shorter_than_the_floor(self) -> None:
        """A zero-length control would rule out a writer it never waited for."""
        started = time.monotonic()
        _moved_with_nothing_running(lambda: {"a": "1"}, 0.0)
        assert time.monotonic() - started >= _CONTROL_WINDOW_FLOOR_S

    def test_the_control_window_covers_the_measurement_window(self) -> None:
        """A long evaluation gets an equally long control, not just the floor."""
        window = _CONTROL_WINDOW_FLOOR_S + 0.2
        started = time.monotonic()
        _moved_with_nothing_running(lambda: {"a": "1"}, window)
        assert time.monotonic() - started >= window


class TestAttributionByFile:
    """The half of attribution timing cannot make (BDL-UX #233).

    A control window can only see a writer that is still writing. A ``bd``
    export is a burst the tracker defers, so it lands in the measurement window
    and is gone before the control window opens — which is why every observed
    failure of the live-index test named
    ``.beads/issues.jsonl`` and never ``beadloom.db``. The digest already knows
    which path moved, so the attribution is made from the path.
    """

    def test_a_tracker_export_is_not_charged_to_the_guard(self) -> None:
        assert _attribute_by_file(["issues.jsonl"]) == ([], ["issues.jsonl"])

    def test_an_index_write_is_still_the_guards_to_answer_for(self) -> None:
        assert _attribute_by_file(["beadloom.db"]) == (["beadloom.db"], [])

    def test_a_file_nobody_recognises_is_the_guards_until_something_says_otherwise(
        self,
    ) -> None:
        """A default of "somebody else's" would let the next new write in silently."""
        assert _attribute_by_file(["surprise.jsonl"]) == (["surprise.jsonl"], [])

    def test_no_changed_path_is_dropped_from_the_comparison(self) -> None:
        """The distinction this bead exists for: attributed, never excluded.

        An ignore list would make the live test green by making it blind — the
        guard genuinely must not write the tracker export either. Every name
        handed in comes back out in exactly one half, so a change there is still
        detected and still named; only the writer it is charged to differs.
        """
        moved = ["beadloom.db", "beadloom.db-wal", "issues.jsonl"]
        ours, theirs = _attribute_by_file(moved)
        assert sorted(ours + theirs) == sorted(moved)
        assert not set(ours) & set(theirs)


class TestTheTwoInstrumentsInOrder:
    """``attribute`` — the file decides what it can, the clock decides the rest.

    Three outcomes and three words, because they are three different facts: the
    guard wrote it, another process wrote it (and we know which class of
    process), and the repository is moving so nobody can say. Collapsing the
    second into the third is what reported a ``bd`` burst as the guard's write.
    """

    @staticmethod
    def _still() -> dict[str, str]:
        return {"a": "1"}

    @staticmethod
    def _moving() -> dict[str, str]:
        return {"a": str(time.monotonic_ns())}

    def test_a_burst_is_attributed_elsewhere_without_consulting_the_clock(self) -> None:
        """The whole bug: a control window cannot see a writer that has finished.

        A ``bd`` export is over in milliseconds, so the control window is quiet
        and the change was charged to the guard. The file answers instead — and
        answers without waiting, which is checked here rather than assumed,
        because a control window that still ran would still be the wrong
        instrument even where its verdict happened not to be used.
        """
        started = time.monotonic()
        verdict = attribute(["issues.jsonl"], snapshot=self._moving, window_s=0.0)
        assert time.monotonic() - started < _CONTROL_WINDOW_FLOOR_S
        assert verdict.charged == []
        assert verdict.elsewhere == ["issues.jsonl"]
        assert verdict.unattributable == []

    def test_an_index_write_on_a_still_repository_is_the_guards(self) -> None:
        verdict = attribute(["beadloom.db"], snapshot=self._still, window_s=0.0)
        assert verdict.charged == ["beadloom.db"]
        assert verdict.elsewhere == verdict.unattributable == []

    def test_an_index_write_on_a_moving_repository_is_unattributable(self) -> None:
        """Not ``elsewhere``: nothing here knows who wrote it, only that somebody did."""
        verdict = attribute(["beadloom.db"], snapshot=self._moving, window_s=0.0)
        assert verdict.charged == []
        assert verdict.unattributable == ["beadloom.db"]
        assert verdict.elsewhere == []

    def test_a_burst_beside_an_index_write_does_not_excuse_the_index_write(self) -> None:
        """Attributing one path elsewhere must not carry the other with it."""
        verdict = attribute(["beadloom.db", "issues.jsonl"], snapshot=self._still, window_s=0.0)
        assert verdict.charged == ["beadloom.db"]
        assert verdict.elsewhere == ["issues.jsonl"]

    def test_a_still_repository_that_moved_nothing_charges_nobody(self) -> None:
        verdict = attribute([], snapshot=self._moving, window_s=0.0)
        assert verdict.charged == verdict.elsewhere == verdict.unattributable == []


class TestTheThreeOutcomesReachTheReaderInDifferentWords:
    """``report_attribution`` — the wiring, checked deterministically rather than by sampling.

    The end-to-end path cannot be driven with a real burst: the tracker defers
    its export to a moment no command marks, so scheduling one inside a
    measurement window is a sampling game with poor odds, and six live runs
    under a burst loop exercised it zero times. The reporting step is therefore
    a function, and this is that function held against all four cases.
    """

    @staticmethod
    def _burst() -> Attribution:
        return Attribution(charged=[], elsewhere=["issues.jsonl"], unattributable=[])

    def test_a_burst_is_reported_and_does_not_fail_the_run(self) -> None:
        with pytest.warns(RuntimeWarning, match=re.escape("issues.jsonl")):
            report_attribution(self._burst(), window_s=0.0)

    def test_the_report_says_attributed_and_never_says_ignored(self) -> None:
        """The distinction the bead is about, in the words the reader gets.

        "This write was not the guard's" and "this path is not checked" are
        different facts. A reader who sees the second where the first is true
        learns to stop believing the check.
        """
        with pytest.warns(RuntimeWarning) as caught:
            report_attribution(self._burst(), window_s=0.0)
        message = str(caught[0].message)
        assert "NOT excluded from the comparison" in message
        assert "was still measured" in message

    def test_a_change_nobody_can_attribute_skips_and_names_the_files(self) -> None:
        with pytest.raises(pytest.skip.Exception) as excinfo:
            report_attribution(
                Attribution(charged=[], elsewhere=[], unattributable=["beadloom.db"]),
                window_s=0.0,
            )
        assert "beadloom.db" in str(excinfo.value)

    def test_a_write_charged_to_the_guard_fails_and_names_the_file(self) -> None:
        with pytest.raises(AssertionError, match=re.escape("beadloom.db")):
            report_attribution(
                Attribution(charged=["beadloom.db"], elsewhere=[], unattributable=[]),
                window_s=0.0,
            )

    def test_a_burst_beside_a_guard_write_reports_both_and_still_fails(self) -> None:
        """The anti-silencing property: warning about one path never excuses another."""
        with (
            pytest.warns(RuntimeWarning, match=re.escape("issues.jsonl")),
            pytest.raises(AssertionError, match=re.escape("beadloom.db")),
        ):
            report_attribution(
                Attribution(
                    charged=["beadloom.db"], elsewhere=["issues.jsonl"], unattributable=[]
                ),
                window_s=0.0,
            )

    def test_a_quiet_repository_is_reported_with_nothing_at_all(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            report_attribution(Attribution([], [], []), window_s=0.0)
        assert [str(w.message) for w in caught] == []


class TestTheTrackerExportIsOutsideTheGuardsReach:
    """Why ``.beads/issues.jsonl`` may be attributed elsewhere — derived, not asserted.

    :func:`_attribute_by_file` only tells the truth while the evaluation issues
    no ``bd`` command that writes. That is a property of the code, not a fact
    about this week, so it is checked here rather than stated in a comment: give
    a guard a mutating tracker call and this goes red, which is the difference
    between a path that is *attributed* and a path that is *excluded*.
    """

    def test_the_evaluation_issues_no_bd_command_that_could_write_the_export(
        self, tmp_path, monkeypatch, write_flow_yml
    ) -> None:
        from beadloom.services import bd_seam
        from beadloom.services.guard_probes import build_probes

        issued: list[tuple[str, ...]] = []

        def record(args: list[str], *, cwd: str | None = None) -> bd_seam.BdResult:
            issued.append(tuple(args))
            return bd_seam.BdResult(returncode=0, stdout="[]", stderr="")

        monkeypatch.setattr(bd_seam, "run_bd", record)
        (tmp_path / ".beads").mkdir(parents=True, exist_ok=True)

        for name in ("bead-claimed", "working-branch"):
            evaluate_guard(
                name,
                project_root=tmp_path,
                context={"path": "src/app.py"},
                probes=build_probes(tmp_path),
            )

        assert issued, (
            "the evaluation made no tracker call at all, so this test would pass "
            "whatever the probe did — the seam is patched in the wrong place"
        )
        assert [argv for argv in issued if argv[0] not in _READ_ONLY_BD_SUBCOMMANDS] == []


class _FixedTracker:
    def __init__(self, beads) -> None:
        self._beads = beads

    def claimed_beads(self):
        return self._beads


class _FixedWorkspace:
    def __init__(self, branch) -> None:
        self._branch = branch

    def current_branch(self):
        return self._branch


class TestHookPayloadCorners:
    """What the translator refuses to guess."""

    @pytest.mark.parametrize(
        "tool_input",
        [{}, {"file_path": ""}, {"file_path": None}, {"file_path": 7}, {"other": "x"}],
    )
    def test_a_payload_with_no_usable_path_omits_it_rather_than_guessing(
        self, tmp_path, guard_cli, tool_input
    ) -> None:
        """A guessed path would silently evaluate the wrong file; an absent one is stated."""
        payload = json.dumps(
            {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": tool_input}
        )

        result = guard_cli(
            ["guard", "bead-claimed", "--project", str(tmp_path), "--json",
             "--hook", "claude-code"],
            beads=(),
            stdin=payload,
        )

        verdict = json.loads(result.stdout)
        assert "path" not in verdict["context"]
        assert any("no path" in item for item in verdict["not_covered"])

    def test_a_tool_input_that_is_not_an_object_is_ignored_not_fatal(
        self, tmp_path, guard_cli
    ) -> None:
        payload = json.dumps(
            {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": "Edit"}
        )

        result = guard_cli(
            ["guard", "bead-claimed", "--project", str(tmp_path), "--json",
             "--hook", "claude-code"],
            beads=(),
            stdin=payload,
        )

        assert result.exit_code == 1, result.output
        assert json.loads(result.stdout)["context"] == {
            "tool": "Edit",
            "event": "PreToolUse",
        }
