"""A guard that cannot answer blocks in the harness it is bound to (BDL-061.33).

S1 shipped the sentence and not the behaviour. ``error`` never borrowed the
``warn`` code — that half held — but the configuration/command-line class exited
``3``, and ``3`` is a code the harness the emitted adapter binds to does not
block on. So the single input an adopter edits by hand, ``.beadloom/flow.yml``,
could disable every bound guard by a mistyped line while each invocation printed,
loudly and uselessly, that it could not answer. Fail-open on the most likely
defect.

These tests hold both halves of the fix at once, because either alone is a
different bug:

* **under a harness** (``--hook`` names one) the class exits the blocking code,
  so the edit stops;
* **from a shell** it still exits ``3``, so a defect in the project's declared
  configuration stays distinguishable from a guard that fired — and from Click's
  own usage exit, which is also ``2``.

The enumeration is not hand-maintained: :class:`TestNoConfigErrorPathSurvivesUnderAHarness`
derives its rows from the shipped exit-path table, so a config-error path added
later is covered on the day it is added rather than on the day someone remembers
this file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.application.guards.models import (
    EXIT_CODE_CONFIG_ERROR,
    GuardOutcome,
)
from beadloom.services.cli import main

#: A flow.yml that parses and declares nothing surprising.
_VALID_FLOW = "guards:\n  bead-claimed:\n    strictness: {default: block}\n"

#: The five cases measured on the real binary in BDL-061.3 (N1) and re-measured
#: in .4: every one an ``error`` verdict, every one at exit 3 before this bead.
#: (label, guard name, argv after the name, flow.yml body)
_CONFIG_ERROR_CASES: tuple[tuple[str, str | None, list[str], str], ...] = (
    ("a guards: block that will not parse", "bead-claimed", [], "guards: [1, 2\n"),
    (
        "an exclusion with neither reason nor until",
        "bead-claimed",
        [],
        "guards:\n  bead-claimed:\n    exclusions:\n      - path: 'x/**'\n",
    ),
    ("a guard name nobody registered", "no-such-guard", [], _VALID_FLOW),
    ("a malformed --context pair", "bead-claimed", ["--context", "nonsense"], _VALID_FLOW),
    ("--liveness given a guard name", "bead-claimed", ["--liveness"], _VALID_FLOW),
    ("no guard named at all", None, [], _VALID_FLOW),
)


@pytest.fixture()
def guard_cli(monkeypatch, make_guard_probes):
    """Invoke ``beadloom guard`` with the probes stubbed at the CLI seam."""
    from beadloom.services.commands import guard as guard_cmd

    def run(args: list[str], *, stdin: str | None = None):
        monkeypatch.setattr(
            guard_cmd, "_probes", lambda _root: make_guard_probes(beads=())
        )
        return CliRunner().invoke(main, args, input=stdin)

    return run


def _argv(root: Path, name: str | None, rest: list[str]) -> list[str]:
    """The command line for one row. ``None`` is "no name", ``""`` is a name."""
    return ["guard", *([] if name is None else [name]), "--project", str(root), *rest]


class TestUnderAHarnessTheClassBlocks:
    """The half that was missing: bound to a harness, "I could not tell" stops the edit."""

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow"),
        _CONFIG_ERROR_CASES,
        ids=[row[0] for row in _CONFIG_ERROR_CASES],
    )
    def test_the_case_exits_the_code_the_harness_blocks_on(
        self, guard_project, write_flow_yml, guard_cli, label, name, rest, flow
    ) -> None:
        write_flow_yml(flow)

        result = guard_cli(
            [*_argv(guard_project, name, rest), "--hook", "claude-code", "--json"],
            stdin="{}",
        )

        assert result.exit_code == 2, f"{label}: {result.output}"

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow"),
        _CONFIG_ERROR_CASES,
        ids=[row[0] for row in _CONFIG_ERROR_CASES],
    )
    def test_the_case_is_still_an_error_verdict_and_still_says_why(
        self, guard_project, write_flow_yml, guard_cli, label, name, rest, flow
    ) -> None:
        """The code moves; the verdict does not. A blocking code with no cause is worse."""
        write_flow_yml(flow)

        result = guard_cli(
            [*_argv(guard_project, name, rest), "--hook", "claude-code", "--json"],
            stdin="{}",
        )

        payload = json.loads(result.output)
        assert payload["outcome"] == GuardOutcome.ERROR.value, label
        assert payload["why"].strip(), label
        assert payload["not_covered"], label

    def test_a_harness_beadloom_cannot_translate_blocks_rather_than_passing(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        """The one config-error case that is *only* reachable through a hook.

        An unsupported harness is a wiring defect, and the wiring is what binds
        the guard: exiting a code that harness ignores is the failure mode this
        bead closes, and Beadloom cannot know the vocabulary of a harness it
        does not support, so it answers with the code that stops work.
        """
        write_flow_yml(_VALID_FLOW)

        result = guard_cli(
            [*_argv(guard_project, "bead-claimed", []), "--hook", "emacs"], stdin="{}"
        )

        assert result.exit_code == 2, result.output
        assert "claude-code" in result.stderr


class TestFromAShellTheDistinctionSurvives:
    """The half that must not be lost: ``3`` still means "your declared config is broken"."""

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow"),
        _CONFIG_ERROR_CASES,
        ids=[row[0] for row in _CONFIG_ERROR_CASES],
    )
    def test_without_a_hook_the_case_still_exits_three(
        self, guard_project, write_flow_yml, guard_cli, label, name, rest, flow
    ) -> None:
        write_flow_yml(flow)

        result = guard_cli(_argv(guard_project, name, rest))

        assert result.exit_code == EXIT_CODE_CONFIG_ERROR, f"{label}: {result.output}"

    def test_a_genuine_block_from_a_shell_is_not_the_config_error_code(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        """The distinction is only worth keeping if both sides of it are reachable."""
        write_flow_yml(_VALID_FLOW)

        result = guard_cli(
            [*_argv(guard_project, "bead-claimed", ["--context", "path=app.py"])]
        )

        assert result.exit_code == 2, result.output


class TestNoConfigErrorPathSurvivesUnderAHarness:
    """Derived from the shipped enumeration, so a new path cannot opt out of the rule."""

    @staticmethod
    def _hookable_config_error_rows() -> list[tuple[str, str | None, list[str], str]]:
        from tests.test_guards_invocation import _EXIT_PATHS

        return [
            (row[0], row[1], row[2], row[3])
            for row in _EXIT_PATHS
            if row[5] == EXIT_CODE_CONFIG_ERROR and "--hook" not in row[2]
        ]

    def test_the_derivation_finds_rows_to_check(self) -> None:
        """A test derived from an empty set passes vacuously; this says it is not."""
        assert len(self._hookable_config_error_rows()) >= 5

    def test_every_shipped_config_error_row_blocks_when_bound_to_a_harness(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        survivors = []
        for label, name, rest, flow in self._hookable_config_error_rows():
            write_flow_yml(flow)
            result = guard_cli(
                [*_argv(guard_project, name, rest), "--hook", "claude-code"], stdin="{}"
            )
            if result.exit_code != 2:
                survivors.append((label, result.exit_code))

        assert survivors == []


class TestTheEmittedAdapterIsTrueAboutWhatItCanReturn:
    """The artifact adopters actually get — run for real, and read for its claims."""

    @staticmethod
    def _env() -> dict[str, str]:
        env = dict(os.environ)
        env["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{env.get('PATH', '')}"
        return env

    def test_a_flow_yml_that_will_not_parse_stops_the_edit_through_the_real_script(
        self, tmp_path
    ) -> None:
        """The reachable case, end to end: emitted adapter, real CLI, real subprocess.

        This is the invocation the coordinator measured at exit 3 on 2026-08-22
        by appending invalid YAML to a live ``flow.yml``.
        """
        from beadloom.onboarding.guard_hooks import (
            GUARD_HOOK_RELPATH,
            scaffold_guard_hooks,
        )

        if not (Path(sys.executable).parent / "beadloom").exists():
            pytest.skip("beadloom console script not installed in this environment")
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "guards:\n  bead-claimed:\n    strictness: {default: block\n", encoding="utf-8"
        )
        scaffold_guard_hooks(tmp_path, guard_names=["bead-claimed"])
        payload = json.dumps(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": str(tmp_path / "src" / "app.py")},
            }
        )

        run = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [str(tmp_path / GUARD_HOOK_RELPATH), "bead-claimed"],
            cwd=str(tmp_path),
            input=payload,
            capture_output=True,
            # The child speaks UTF-8 by contract (our own CLI, a JSON payload, a shell
            # block from a YAML file); `text=True` would have decoded it with the
            # image's locale instead (BDL-061.42).
            encoding="utf-8",
            env=self._env(),
            check=False,
        )

        assert run.returncode == 2, run.stderr
        assert "bead-claimed: ERROR" in run.stderr

    def test_the_comment_names_no_exit_code_this_adapter_cannot_produce(self) -> None:
        """The adapter's comment said "3 = usage or configuration error" and 3 blocks nothing.

        A generated file that documents a code its own invocation can never
        return teaches the reader a distinction they cannot observe — the same
        defect class as the invariant this bead closes, one artifact over.
        """
        from beadloom.onboarding.guard_hooks import _HOOK_SCRIPT

        enumerated = {line for line in _HOOK_SCRIPT.splitlines() if " = " in line}
        assert enumerated, _HOOK_SCRIPT
        assert not any("3 = " in line for line in enumerated), _HOOK_SCRIPT
        assert any("2 = " in line for line in enumerated), _HOOK_SCRIPT
