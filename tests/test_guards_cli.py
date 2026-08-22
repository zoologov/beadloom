"""``beadloom guard`` — exit-code contract, hook parity, liveness, real probes (BDL-061 S1)."""

from __future__ import annotations

import json
import subprocess

import pytest
from click.testing import CliRunner

from beadloom.application.guards.contract import ClaimedBead, GuardProbes
from beadloom.services.cli import main


class _Tracker:
    def __init__(self, beads):
        self._beads = beads

    def claimed_beads(self):
        return self._beads


class _Workspace:
    def __init__(self, branch):
        self._branch = branch

    def current_branch(self):
        return self._branch


@pytest.fixture()
def stub_probes(monkeypatch):
    """Install stub probes into the CLI seam; returns a setter."""
    from beadloom.services.commands import guard as guard_cmd

    def install(*, beads=(), branch="features/BDL-061"):
        monkeypatch.setattr(
            guard_cmd,
            "_probes",
            lambda _root: GuardProbes(
                tracker=_Tracker(beads), workspace=_Workspace(branch)
            ),
        )

    return install


def _run(args):
    return CliRunner().invoke(main, args)


class TestExitCodeContract:
    def test_pass_exits_zero(self, tmp_path, stub_probes) -> None:
        stub_probes(beads=(ClaimedBead(id="bd-1"),))
        result = _run(["guard", "bead-claimed", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_warn_exits_one(self, tmp_path, stub_probes) -> None:
        stub_probes(beads=())
        result = _run(
            ["guard", "bead-claimed", "--project", str(tmp_path), "--context", "path=src/a.py"]
        )
        assert result.exit_code == 1, result.output

    def test_block_exits_two(self, tmp_path, stub_probes) -> None:
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "guards:\n  bead-claimed:\n    strictness: {default: block}\n"
        )
        stub_probes(beads=())
        result = _run(["guard", "bead-claimed", "--project", str(tmp_path)])
        assert result.exit_code == 2, result.output

    def test_skip_exits_zero(self, tmp_path, stub_probes) -> None:
        stub_probes(beads=None)
        result = _run(["guard", "bead-claimed", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_unknown_guard_exits_three_not_two(self, tmp_path) -> None:
        result = _run(["guard", "no-such-guard", "--project", str(tmp_path)])
        assert result.exit_code == 3, result.output

    def test_missing_name_exits_three(self, tmp_path) -> None:
        result = _run(["guard", "--project", str(tmp_path)])
        assert result.exit_code == 3, result.output

    def test_malformed_context_exits_three(self, tmp_path, stub_probes) -> None:
        stub_probes(beads=())
        result = _run(
            ["guard", "bead-claimed", "--project", str(tmp_path), "--context", "nokey"]
        )
        assert result.exit_code == 3, result.output

    def test_config_error_exits_three(self, tmp_path, stub_probes) -> None:
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "guards:\n  bead-claimed:\n    exclusions:\n      - path: 'x/**'\n"
        )
        stub_probes(beads=())
        result = _run(["guard", "bead-claimed", "--project", str(tmp_path)])
        assert result.exit_code == 3, result.output


class TestOutput:
    def test_json_payload_carries_the_verdict_shape(self, tmp_path, stub_probes) -> None:
        stub_probes(beads=())
        result = _run(
            [
                "guard", "bead-claimed", "--project", str(tmp_path),
                "--json", "--context", "path=src/a.py",
            ]
        )
        payload = json.loads(result.stdout)
        assert set(payload) == {
            "guard", "outcome", "why", "not_covered", "remediation", "context"
        }
        assert payload["outcome"] == "warn"
        assert payload["not_covered"]

    def test_warning_names_what_it_did_not_check(self, tmp_path, stub_probes) -> None:
        stub_probes(beads=())
        result = _run(["guard", "bead-claimed", "--project", str(tmp_path)])
        assert "not checked" in result.output

    def test_a_blocking_verdict_reaches_stderr(self, tmp_path, stub_probes) -> None:
        stub_probes(branch="main")
        result = _run(["guard", "working-branch", "--project", str(tmp_path)])
        assert "working-branch" in result.stderr


class TestHookParity:
    """The whole point of the primitive: one decision, two callers."""

    def test_hook_payload_and_explicit_context_give_the_same_verdict(
        self, tmp_path, stub_probes
    ) -> None:
        stub_probes(beads=())
        payload = json.dumps(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": str(tmp_path / "src" / "a.py")},
            }
        )
        via_hook = CliRunner().invoke(
            main,
            [
                "guard", "bead-claimed", "--project", str(tmp_path),
                "--json", "--hook", "claude-code",
            ],
            input=payload,
        )
        via_cli = _run(
            [
                "guard", "bead-claimed", "--project", str(tmp_path), "--json",
                "--context", f"path={tmp_path / 'src' / 'a.py'}",
                "--context", "tool=Edit",
                "--context", "event=PreToolUse",
            ]
        )
        assert via_hook.exit_code == via_cli.exit_code
        assert json.loads(via_hook.stdout) == json.loads(via_cli.stdout)

    def test_unparseable_hook_payload_exits_three(self, tmp_path, stub_probes) -> None:
        stub_probes(beads=())
        result = CliRunner().invoke(
            main,
            ["guard", "bead-claimed", "--project", str(tmp_path), "--hook", "claude-code"],
            input="not json",
        )
        assert result.exit_code == 3, result.output


class TestLiveness:
    def test_liveness_reports_every_guard_as_never_fired_on_a_fresh_project(
        self, tmp_path
    ) -> None:
        result = _run(["guard", "--liveness", "--project", str(tmp_path), "--json"])
        assert result.exit_code == 0, result.output
        rows = {row["guard"]: row for row in json.loads(result.stdout)}
        assert rows["bead-claimed"]["never_fired"] is True
        assert rows["working-branch"]["never_fired"] is True

    def test_cli_evaluation_is_recorded_and_shows_up_in_liveness(
        self, tmp_path, stub_probes
    ) -> None:
        stub_probes(beads=())
        _run(["guard", "bead-claimed", "--project", str(tmp_path)])
        result = _run(["guard", "--liveness", "--project", str(tmp_path), "--json"])
        rows = {row["guard"]: row for row in json.loads(result.stdout)}
        assert rows["bead-claimed"]["fired_count"] == 1
        assert rows["bead-claimed"]["last_outcome"] == "warn"

    def test_liveness_flags_a_guard_excluded_everywhere(self, tmp_path) -> None:
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "guards:\n  working-branch:\n    strictness: {default: 'off'}\n"
        )
        result = _run(["guard", "--liveness", "--project", str(tmp_path)])
        assert "working-branch" in result.output
        assert "excluded-everywhere" in result.output

    def test_liveness_with_a_guard_name_is_a_usage_error(self, tmp_path) -> None:
        result = _run(["guard", "bead-claimed", "--liveness", "--project", str(tmp_path)])
        assert result.exit_code == 3, result.output


class TestRealProbes:
    """A stub proves the stub's contract — these run against the real git/bd."""

    def test_git_workspace_reads_a_real_branch(self, tmp_path) -> None:
        from beadloom.services.guard_probes import build_probes

        subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", "init", "-b", "features/real", str(tmp_path)],  # noqa: S607
            check=True,
            capture_output=True,
        )
        assert build_probes(tmp_path).workspace.current_branch() == "features/real"

    def test_git_workspace_reports_none_outside_a_repo(self, tmp_path) -> None:
        from beadloom.services.guard_probes import build_probes

        assert build_probes(tmp_path).workspace.current_branch() is None

    def test_bd_tracker_skips_a_project_with_no_beads_directory(self, tmp_path) -> None:
        from beadloom.services.guard_probes import build_probes

        # None (not an empty tuple) so the guard SKIPS with a reason instead of
        # reporting "no bead claimed" in a repo that does not use bd at all.
        assert build_probes(tmp_path).tracker.claimed_beads() is None

    def test_bd_tracker_reads_a_real_bead_claimed_in_a_real_bd_project(
        self, tmp_path
    ) -> None:
        """The probe against a real ``bd``, on a project built for this test.

        Replaces an assertion that could not fail: it read this repo, asserted
        ``all(bead.id for bead in claimed)``, and ``all(())`` is ``True`` — so it
        held whether the probe worked, returned nothing, or silently truncated,
        which is how the ``--limit`` defect survived 248 tests (review .3, M5).

        NOT covered here, deliberately: the >50 paging boundary against the real
        binary. Creating 51 beads costs ~1 s each on the embedded Dolt backend,
        which is not a price the default suite should pay; that boundary is
        proved against bd's documented contract in
        ``tests/test_guard_probes.py::TestTrackerReadsAllOfBdsAnswer``.
        """
        from beadloom.services.bd_seam import BdUnavailableError, run_bd
        from beadloom.services.guard_probes import build_probes

        try:
            run_bd(["--version"], cwd=str(tmp_path))
        except BdUnavailableError:
            pytest.skip("bd binary not installed")

        def bd(*args: str) -> str:
            result = run_bd(list(args), cwd=str(tmp_path))
            assert result.ok, f"bd {args}: {result.stderr}"
            return result.stdout

        bd("init", "--prefix", "tt", "--non-interactive")
        claimed_id = json.loads(bd("create", "claimed work", "--json"))["id"]
        idle_id = json.loads(bd("create", "untouched work", "--json"))["id"]

        before = build_probes(tmp_path).tracker.claimed_beads()
        assert before == (), "nothing is claimed yet, and that is not the same as unavailable"

        bd("update", claimed_id, "--status", "in_progress", "--claim")
        after = build_probes(tmp_path).tracker.claimed_beads()

        assert [bead.id for bead in after] == [claimed_id]
        assert idle_id not in [bead.id for bead in after]
        assert after[0].title == "claimed work"


class TestHookHarnessValidation:
    def test_unknown_harness_exits_three(self, tmp_path, stub_probes) -> None:
        stub_probes(beads=())
        result = CliRunner().invoke(
            main,
            ["guard", "bead-claimed", "--project", str(tmp_path), "--hook", "emacs"],
            input="{}",
        )
        assert result.exit_code == 3, result.output
        assert "claude-code" in result.stderr
