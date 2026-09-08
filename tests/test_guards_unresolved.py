"""A guard that cannot evaluate itself warns and permits (BDL-061.33, BDL-UX #254).

Two entries, one file, because they are the same question answered twice from
opposite sides and the file exists so neither answer can be re-taken without
meeting the other.

**BDL-061.33** found the class fail-OPEN and silent. A defect in
``.beadloom/flow.yml`` — the single input an adopter edits by hand — exited ``3``,
``3`` blocks nothing in the harness the emitted adapter binds to, and so a
mistyped line switched every bound guard off while each invocation announced,
loudly and uselessly, that it could not answer. It sent the class to the blocking
code under a harness.

**BDL-UX #254** measured what the blocking code costs, live rather than in
argument. In BDL-068 S5 ``beadloom-0mdo.51`` ran ``git mv`` to split
``services/bd_seam.py`` into a package; the next call, creating ``__init__.py``,
was refused. Between those two moments the package does not import,
``services/guard_probes.py:79`` imports it to reach the tracker, so the guard
could not answer and answered ``error`` at 2. ``Bash``, ``Write`` and ``Edit``
were all on the guard's surface and all returned the same ``ImportError``;
``Read`` was the only tool outside it, and a read repairs nothing. The
remediation printed on every attempt read "fix the reported error, then re-run" —
a file write the same verdict had just disabled. The owner cleared it by typing a
heredoc in a shell outside the session.

**Both are true, and the resolution is a third thing rather than either.** The
class is now ``unresolved``: it PERMITS the edit, and it is loud in three places
at once — a named outcome on stderr, a firing record, and a ``--liveness`` row it
does not clear ``never-fired`` on. What made ``3`` fail-open was never the
permission, it was the silence.

**The surface is not narrowed and must not be.** ``beadloom-0mdo.31`` put
``Bash`` on the matcher in S4, which is the whole of BDL-UX #170 and is correct;
before it a shell write slipped past the guard and could have repaired the tree.
Closing a real coverage hole is what removed the last exit, and reopening it
would be paying for a repair path with a bypass.

**The line that did not move** is asserted here too, in
:class:`TestTheOtherClassStillStopsTheEdit`: a guard that ran and refuses to
interpret the TARGET it was handed has a real answer about this edit, so it still
blocks at 2. The two classes are told apart by one question — could the guard not
answer about the edit, or about itself?

The enumeration is not hand-maintained:
:class:`TestNoUnresolvedPathBlocksUnderAHarness` derives its rows from the shipped
exit-path table, so a path added later is covered on the day it is added rather
than on the day someone remembers this file.
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
    EXIT_CODE_BLOCK,
    EXIT_CODE_UNRESOLVED,
    EXIT_CODE_WARN,
    GuardOutcome,
)
from beadloom.services.cli import main

#: A flow.yml that parses and declares nothing surprising.
_VALID_FLOW = "guards:\n  bead-claimed:\n    strictness: {default: block}\n"

#: The five cases measured on the real binary in BDL-061.3 (N1) and re-measured
#: in .4: every one a verdict the guard could not reach about itself.
#: (label, guard name, argv after the name, flow.yml body)
_UNRESOLVED_CASES: tuple[tuple[str, str | None, list[str], str], ...] = (
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


class TestUnderAHarnessTheClassPermitsAndSaysSo:
    """The half BDL-UX #254 moved: bound to a harness, "I could not tell" lets it through."""

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow"),
        _UNRESOLVED_CASES,
        ids=[row[0] for row in _UNRESOLVED_CASES],
    )
    def test_the_case_does_not_exit_the_code_the_harness_blocks_on(
        self, guard_project, write_flow_yml, guard_cli, label, name, rest, flow
    ) -> None:
        write_flow_yml(flow)

        result = guard_cli(
            [*_argv(guard_project, name, rest), "--hook", "claude-code", "--json"],
            stdin="{}",
        )

        assert result.exit_code == EXIT_CODE_WARN, f"{label}: {result.output}"

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow"),
        _UNRESOLVED_CASES,
        ids=[row[0] for row in _UNRESOLVED_CASES],
    )
    def test_the_case_is_an_unresolved_verdict_and_still_says_why(
        self, guard_project, write_flow_yml, guard_cli, label, name, rest, flow
    ) -> None:
        """The code moved; the honesty did not. A permitted edit with no cause is worse."""
        write_flow_yml(flow)

        result = guard_cli(
            [*_argv(guard_project, name, rest), "--hook", "claude-code", "--json"],
            stdin="{}",
        )

        payload = json.loads(result.stdout)
        assert payload["outcome"] == GuardOutcome.UNRESOLVED.value, label
        assert payload["why"].strip(), label
        assert payload["not_covered"], label

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow"),
        _UNRESOLVED_CASES,
        ids=[row[0] for row in _UNRESOLVED_CASES],
    )
    def test_the_case_never_reads_as_a_guard_that_passed(
        self, guard_project, write_flow_yml, guard_cli, label, name, rest, flow
    ) -> None:
        """Permitting is not passing, and this is the assertion that keeps them apart."""
        write_flow_yml(flow)

        result = guard_cli(
            [*_argv(guard_project, name, rest), "--hook", "claude-code", "--json"],
            stdin="{}",
        )

        assert result.exit_code != 0, label
        assert json.loads(result.stdout)["outcome"] != GuardOutcome.PASS.value, label

    def test_the_permitted_edit_is_stated_on_the_stream_the_reader_watches(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        """The whole difference from the fail-open BDL-061.33 closed is this line."""
        from beadloom.application.guards.models import PERMITTED_UNGUARDED

        write_flow_yml("guards: [1, 2\n")

        result = guard_cli(
            [*_argv(guard_project, "bead-claimed", []), "--hook", "claude-code"],
            stdin="{}",
        )

        assert "UNRESOLVED" in result.stderr, result.stderr
        assert PERMITTED_UNGUARDED in result.stderr, result.stderr

    def test_the_remediation_does_not_ask_for_the_write_it_would_have_disabled(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        """BDL-UX #254's sharpest detail: the fix instruction was itself blocked."""
        write_flow_yml("guards: [1, 2\n")

        result = guard_cli(
            [*_argv(guard_project, "bead-claimed", []), "--hook", "claude-code", "--json"],
            stdin="{}",
        )

        assert "blocked" not in json.loads(result.stdout)["remediation"]

    def test_a_harness_beadloom_cannot_translate_is_unresolved_rather_than_blocking(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        """The one case that is *only* reachable through a hook.

        An unsupported harness is a wiring defect, and the wiring is what binds
        the guard — so the repair is an edit to ``settings.json`` or to the
        adapter, which is exactly what a block forbids. The honest limit, stated
        because it is real: Beadloom cannot know the exit vocabulary of a harness
        it does not support, so it cannot know that this harness carries on past
        1 either. What it knows is that every harness it DOES support does, and
        that a code which stops work makes the defect unrepairable in every
        harness at all.
        """
        write_flow_yml(_VALID_FLOW)

        result = guard_cli(
            [*_argv(guard_project, "bead-claimed", []), "--hook", "emacs"], stdin="{}"
        )

        assert result.exit_code != EXIT_CODE_BLOCK, result.output
        assert "UNRESOLVED" in result.stderr, result.stderr
        assert "claude-code" in result.stderr


class TestFromAShellTheDistinctionSurvives:
    """The half that must not be lost: ``3`` still means "the guard could not run"."""

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow"),
        _UNRESOLVED_CASES,
        ids=[row[0] for row in _UNRESOLVED_CASES],
    )
    def test_without_a_hook_the_case_still_exits_three(
        self, guard_project, write_flow_yml, guard_cli, label, name, rest, flow
    ) -> None:
        write_flow_yml(flow)

        result = guard_cli(_argv(guard_project, name, rest))

        assert result.exit_code == EXIT_CODE_UNRESOLVED, f"{label}: {result.output}"

    def test_a_genuine_block_from_a_shell_is_not_the_unresolved_code(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        """The distinction is only worth keeping if both sides of it are reachable."""
        write_flow_yml(_VALID_FLOW)

        result = guard_cli(
            [*_argv(guard_project, "bead-claimed", ["--context", "path=app.py"])]
        )

        assert result.exit_code == EXIT_CODE_BLOCK, result.output


class TestTheOtherClassStillStopsTheEdit:
    """The line #254 did NOT move, asserted so that "permit" cannot spread to it.

    A guard that ran and refuses to interpret the target it was handed has an
    answer about this edit: it does not know which file is being written.
    Permitting an unidentified write is the one thing a guard bound before a
    write must not do, and nothing a repair needs is waiting on the refusal — a
    different target clears it, and every other edit in the session is unaffected.
    """

    def test_a_hook_payload_that_cannot_be_read_still_blocks(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        write_flow_yml(_VALID_FLOW)

        result = guard_cli(
            [*_argv(guard_project, "bead-claimed", []), "--hook", "claude-code", "--json"],
            stdin="{not json",
        )

        assert result.exit_code == EXIT_CODE_BLOCK, result.output
        assert json.loads(result.stdout)["outcome"] == GuardOutcome.ERROR.value

    def test_a_target_the_shape_gate_refuses_still_blocks(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        write_flow_yml(_VALID_FLOW)

        result = guard_cli(
            [
                *_argv(guard_project, "bead-claimed", ["--context", "path=src/a\x00.py"]),
                "--hook",
                "claude-code",
                "--json",
            ],
            stdin="{}",
        )

        assert result.exit_code == EXIT_CODE_BLOCK, result.output
        assert json.loads(result.stdout)["outcome"] == GuardOutcome.ERROR.value


class TestNoUnresolvedPathBlocksUnderAHarness:
    """Derived from the shipped enumeration, so a new path cannot opt out of the rule."""

    @staticmethod
    def _hookable_unresolved_rows() -> list[tuple[str, str | None, list[str], str]]:
        from tests.test_guards_invocation import _EXIT_PATHS

        return [
            (row[0], row[1], row[2], row[3])
            for row in _EXIT_PATHS
            if row[5] == EXIT_CODE_UNRESOLVED and "--hook" not in row[2]
        ]

    def test_the_derivation_finds_rows_to_check(self) -> None:
        """A test derived from an empty set passes vacuously; this says it is not."""
        assert len(self._hookable_unresolved_rows()) >= 5

    def test_every_shipped_unresolved_row_permits_when_bound_to_a_harness(
        self, guard_project, write_flow_yml, guard_cli
    ) -> None:
        survivors = []
        for label, name, rest, flow in self._hookable_unresolved_rows():
            write_flow_yml(flow)
            result = guard_cli(
                [*_argv(guard_project, name, rest), "--hook", "claude-code"], stdin="{}"
            )
            if result.exit_code == EXIT_CODE_BLOCK:
                survivors.append((label, result.exit_code))

        assert survivors == []


class TestTheEmittedAdapterIsTrueAboutWhatItCanReturn:
    """The artifact adopters actually get — run for real, and read for its claims."""

    @staticmethod
    def _env() -> dict[str, str]:
        env = dict(os.environ)
        env["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{env.get('PATH', '')}"
        return env

    def _run_adapter(self, tmp_path: Path, flow: str) -> subprocess.CompletedProcess[str]:
        """The emitted adapter, on a real project, over a real PreToolUse payload."""
        from beadloom.onboarding.guard_hooks import (
            GUARD_HOOK_RELPATH,
            scaffold_guard_hooks,
        )

        if not (Path(sys.executable).parent / "beadloom").exists():
            pytest.skip("beadloom console script not installed in this environment")
        (tmp_path / ".beadloom").mkdir(exist_ok=True)
        (tmp_path / ".beadloom" / "flow.yml").write_text(flow, encoding="utf-8")
        scaffold_guard_hooks(tmp_path, guard_names=["bead-claimed"])
        payload = json.dumps(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": str(tmp_path / ".beadloom" / "flow.yml")},
            }
        )
        return subprocess.run(  # noqa: S603 — fixed argv, no shell
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

    def test_a_flow_yml_that_will_not_parse_leaves_that_file_editable(
        self, tmp_path
    ) -> None:
        """The reachable case, end to end: emitted adapter, real CLI, real subprocess.

        The edit target is ``flow.yml`` itself, which is the shape of the trap:
        the file that must be fixed is a file the guard is bound to. Blocking here
        is a project no session can repair. Measured at exit 3 on 2026-08-22, at
        exit 2 after BDL-061.33, and at the warn code now.
        """
        run = self._run_adapter(
            tmp_path, "guards:\n  bead-claimed:\n    strictness: {default: block\n"
        )

        assert run.returncode != EXIT_CODE_BLOCK, run.stderr
        assert "bead-claimed: UNRESOLVED" in run.stderr, run.stderr

    def test_the_adapter_still_reports_the_cause_it_could_not_get_past(
        self, tmp_path
    ) -> None:
        """Permitting is worth nothing if the reader cannot see what was skipped."""
        run = self._run_adapter(
            tmp_path, "guards:\n  bead-claimed:\n    strictness: {default: block\n"
        )

        assert "not checked" in run.stderr, run.stderr
        assert "flow.yml" in run.stderr, run.stderr

    def test_the_comment_names_no_exit_code_this_adapter_cannot_produce(self) -> None:
        """A generated file must not document a distinction its reader cannot observe.

        The comment said "3 = usage or configuration error" while 3 blocks
        nothing through this adapter — the same defect class as the invariant
        this file is about, one artifact over. It must still not name 3, and it
        must name both codes an invocation through it can actually return.
        """
        from beadloom.onboarding.guard_hooks import _HOOK_SCRIPT

        enumerated = {line for line in _HOOK_SCRIPT.splitlines() if " = " in line}
        assert enumerated, _HOOK_SCRIPT
        assert not any("3 = " in line for line in enumerated), _HOOK_SCRIPT
        assert any("2 = " in line for line in enumerated), _HOOK_SCRIPT
        assert any("1 = " in line for line in enumerated), _HOOK_SCRIPT
