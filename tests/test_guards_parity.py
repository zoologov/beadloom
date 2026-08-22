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
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.application.guards.contract import ClaimedBead, GuardProbes
from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.firing import FIRINGS_RELPATH
from beadloom.services.cli import main

_REPO_ROOT = Path(__file__).resolve().parent.parent


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
            text=True,
            env=env,
            check=False,
        )
        via_cli = subprocess.run(  # fixed argv, no shell
            ["beadloom", "guard", "working-branch", "--hook", "claude-code"],  # noqa: S607
            cwd=str(repo_on_trunk),
            input=payload,
            capture_output=True,
            text=True,
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

    def test_the_live_repo_index_is_byte_identical_after_a_real_evaluation(self) -> None:
        """The real database, the real bd/git probes — not a stub's contract.

        ``lint`` mutates the index today (#147, standing rule 3); a guard must
        not, which is why the read-only claim is measured here rather than
        assumed from the absence of a visible write.
        """
        from beadloom.services.guard_probes import build_probes

        db = _REPO_ROOT / ".beadloom" / "beadloom.db"
        if not db.is_file():
            pytest.skip("no live index in this checkout")
        tracked = [
            db,
            Path(f"{db}-wal"),
            Path(f"{db}-shm"),
            _REPO_ROOT / ".beads" / "issues.jsonl",
        ]

        def digest() -> dict[str, str]:
            return {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in tracked
                if path.is_file()
            }

        before = digest()
        for name in ("bead-claimed", "working-branch"):
            verdict = evaluate_guard(
                name,
                project_root=_REPO_ROOT,
                context={"path": "src/beadloom/application/guards/evaluation.py"},
                probes=build_probes(_REPO_ROOT),
            )
            assert verdict.why

        assert digest() == before
        assert not Path(f"{db}-wal").exists()


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
