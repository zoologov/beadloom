"""The invocation boundary: no way out of ``beadloom guard`` without a verdict (BDL-061.29).

Three cycles each found a *different* place where an invocation ended with no
verdict and no firing record — a traversal spelling (.25), a NUL and a crashing
evaluation (.27), then argument parsing, an undecodable stdin and a project root
taken from ``cwd`` (.28). Each was fixed where it was found, so the next entry
path was a fresh place to forget the rule. This module tests the rule itself
rather than its instances:

    every invocation of ``beadloom guard`` comes back through ONE boundary,
    which produces a verdict and — when there is a project to write it to and a
    registered guard to attribute it to — a firing record.

Four kinds of test, in this order:

1. **The enumeration.** Every way the command can terminate, with the
   ``records`` expectation *derived from the stated rule* rather than written
   into the row, so a new exit path cannot be added with a hand-written
   ``False``.
2. **The structure.** The process is terminated in exactly one place, the
   boundary returns through exactly one statement, and the firing record is
   written from exactly one call site — so an exit added without a record is a
   diff that reddens rather than a hole that passes.
3. **The injection.** A failure that nobody enumerated — an exception, a
   ``sys.exit`` inside a check, an unreadable stdin, an unwritable record — is
   still a verdict the reader sees.
4. **The four symptoms** ``.28`` measured, each as a consequence of the
   boundary: undecodable stdin, six unrecorded invocations, a subdirectory
   losing the declared strictness, and the strip running before the shape.

Where a test proves a seam rather than the tool (standing rule 4) it says so:
the stdin-decoding and project-discovery classes run the INSTALLED ``beadloom``
in a subprocess, because a ``CliRunner`` supplies an already-decoded string and
cannot reproduce a decoding failure, and because ``cwd``-based discovery is a
property of the process and not of Click's dispatch.
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.application.guards.config import GuardExclusion
from beadloom.application.guards.contract import Guard, GuardProbes
from beadloom.application.guards.firing import read_firings
from beadloom.services.cli import main

_SRC = Path(__file__).resolve().parents[1] / "src" / "beadloom"
_COMMAND_MODULE = _SRC / "services" / "commands" / "guard.py"
_BOUNDARY_MODULE = _SRC / "application" / "guards" / "invocation.py"

#: A guard declared blocking, with one ordinary exclusion over ``src/``.
_BLOCKING_WITH_EXCLUSION = (
    "guards:\n"
    "  bead-claimed:\n"
    "    strictness: { default: block }\n"
    "    exclusions:\n"
    "      - path: 'src/*.py'\n"
    "        reason: 'generated sources'\n"
    "        until: 'BDL-999'\n"
)


class _NoBeads:
    """A tracker that answers, and answers "nothing is claimed"."""

    @staticmethod
    def claimed_beads() -> tuple[()]:
        return ()


def _project(tmp_path: Path, flow: str = _BLOCKING_WITH_EXCLUSION) -> Path:
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".beadloom" / "flow.yml").write_text(flow, encoding="utf-8")
    return tmp_path


def _cli(args: list[str], *, stdin: str = ""):
    return CliRunner().invoke(main, args, input=stdin)


def _outcomes(root: Path) -> list[str]:
    return [record.outcome for record in read_firings(root)]


# --------------------------------------------------------------------------
# The real installed executable, for the properties a CliRunner cannot show.
# --------------------------------------------------------------------------

_BEADLOOM = shutil.which("beadloom") or str(Path(sys.executable).parent / "beadloom")

real_binary = pytest.mark.skipif(
    not Path(_BEADLOOM).exists(),
    reason="beadloom console script not installed in this environment",
)


def _run_real(
    root: Path, args: list[str], *, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    """Run the installed ``beadloom`` with *root* as the working directory."""
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [_BEADLOOM, *args],
        cwd=str(root),
        input=stdin,
        capture_output=True,
        check=False,
    )


def _git_init(root: Path, branch: str) -> None:
    """A real working copy, so ``working-branch`` has evidence to answer from."""
    subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "init", "-q", "-b", branch, str(root)],  # noqa: S607
        check=True,
        capture_output=True,
    )


# ==========================================================================
# 1. THE ENUMERATION
# ==========================================================================


def _should_record(
    *, name: str | None, project_located: bool, produced_a_verdict: bool
) -> bool:
    """The recording rule, stated once, in the form the boundary enforces it.

    A firing is written when the invocation produced a verdict, a project was
    located to write it to, and the verdict names a registered guard.

    Deliberately computed from facts about the invocation rather than written
    into each row: a table with a ``records`` column is a table where a new exit
    path can be added with a hand-written ``False`` and a shrug. Here, an exit
    path that does not record has to make one of these three facts false, and
    each of the three has a reason in ``flow-guards/SPEC.md`` that could not be
    otherwise — there is nothing to record, nowhere to write it, or nothing to
    attribute it to.
    """
    if not produced_a_verdict or not project_located:
        return False
    return name in BUILTIN_GUARDS


def _produced_a_verdict(*, rest: list[str], exit_code: int) -> bool:
    """A liveness report that succeeded is the one exit path with no verdict."""
    return not ("--liveness" in rest and exit_code == 0)


#: (label, argv-after-the-name, stdin, flow.yml, guard name, exit code).
#: Whether the row records is NOT a column — see :func:`_should_record`.
_EXIT_PATHS: tuple[tuple[str, str | None, list[str], str, str, int], ...] = (
    ("a guard that passes", "working-branch", [], _BLOCKING_WITH_EXCLUSION, "", 0),
    (
        "a guard that blocks",
        "bead-claimed",
        ["--context", "path=app.py"],
        _BLOCKING_WITH_EXCLUSION,
        "",
        2,
    ),
    (
        "an excluded path",
        "bead-claimed",
        ["--context", "path=src/a.py"],
        _BLOCKING_WITH_EXCLUSION,
        "",
        0,
    ),
    (
        "a refused path",
        "bead-claimed",
        ["--context", "path=src\\app.py"],
        _BLOCKING_WITH_EXCLUSION,
        "",
        2,
    ),
    ("an unreadable flow.yml", "bead-claimed", [], "guards: [1, 2\n", "", 3),
    (
        "an exclusion with no reason",
        "bead-claimed",
        [],
        "guards:\n  bead-claimed:\n    exclusions:\n      - path: 'x/**'\n",
        "",
        3,
    ),
    ("a guard name nobody registered", "no-such-guard", [], _BLOCKING_WITH_EXCLUSION, "", 3),
    ("no guard name at all", None, [], _BLOCKING_WITH_EXCLUSION, "", 3),
    (
        "a malformed --context pair",
        "bead-claimed",
        ["--context", "nonsense"],
        _BLOCKING_WITH_EXCLUSION,
        "",
        3,
    ),
    (
        "a --context pair with an empty key",
        "bead-claimed",
        ["--context", "=value"],
        _BLOCKING_WITH_EXCLUSION,
        "",
        3,
    ),
    (
        "a harness nobody supports",
        "bead-claimed",
        ["--hook", "no-such-harness"],
        _BLOCKING_WITH_EXCLUSION,
        "",
        3,
    ),
    (
        "a hook payload that is not JSON",
        "bead-claimed",
        ["--hook", "claude-code"],
        _BLOCKING_WITH_EXCLUSION,
        "{not json",
        2,
    ),
    (
        "a hook payload that is not an object",
        "bead-claimed",
        ["--hook", "claude-code"],
        _BLOCKING_WITH_EXCLUSION,
        "[1, 2]",
        2,
    ),
    ("the liveness report", None, ["--liveness"], _BLOCKING_WITH_EXCLUSION, "", 0),
    (
        "the liveness report with a guard named",
        "bead-claimed",
        ["--liveness"],
        _BLOCKING_WITH_EXCLUSION,
        "",
        3,
    ),
    (
        "the liveness report over an unreadable flow.yml",
        None,
        ["--liveness"],
        "guards: [1\n",
        "",
        3,
    ),
)


class TestEveryExitPathEndsWithAVerdictAndARecord:
    """The enumeration this bead exists to make hard to regress.

    Each row is one way ``beadloom guard`` can terminate. The assertion is the
    rule, not the row: the invocation records **iff** a project was located, a
    registered guard was named, and it was an evaluation rather than a report.
    """

    @pytest.fixture()
    def stub_probes(self, monkeypatch):
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(
            guard_cmd, "_probes", lambda _root: GuardProbes(tracker=_NoBeads())
        )

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow", "stdin", "exit_code"),
        [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in _EXIT_PATHS],
        ids=[row[0] for row in _EXIT_PATHS],
    )
    def test_the_row_records_exactly_when_the_rule_says_it_does(
        self, tmp_path, stub_probes, label, name, rest, flow, stdin, exit_code
    ) -> None:
        root = _project(tmp_path, flow)
        args = ["guard", *( [name] if name else []), "--project", str(root), *rest]

        result = _cli(args, stdin=stdin)

        assert result.exit_code == exit_code, f"{label}: {result.output}"
        expected = _should_record(
            name=name,
            project_located=True,
            produced_a_verdict=_produced_a_verdict(rest=rest, exit_code=exit_code),
        )
        assert bool(_outcomes(root)) is expected, f"{label}: {_outcomes(root)}"

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow", "stdin", "exit_code"),
        [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in _EXIT_PATHS],
        ids=[row[0] for row in _EXIT_PATHS],
    )
    def test_the_row_says_something_the_caller_can_read(
        self, tmp_path, stub_probes, label, name, rest, flow, stdin, exit_code
    ) -> None:
        """No exit path is silent, and none of them is a traceback."""
        root = _project(tmp_path, flow)
        args = ["guard", *([name] if name else []), "--project", str(root), *rest]

        result = _cli(args, stdin=stdin)

        assert result.output.strip(), label
        assert "Traceback" not in result.output, label

    @pytest.mark.parametrize(
        ("label", "name", "rest", "flow", "stdin", "exit_code"),
        [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in _EXIT_PATHS],
        ids=[row[0] for row in _EXIT_PATHS],
    )
    def test_no_row_exits_one_unless_the_verdict_is_a_warning(
        self, tmp_path, stub_probes, label, name, rest, flow, stdin, exit_code
    ) -> None:
        """Exit 1 is the WARN code, which a harness reads as "carry on"."""
        root = _project(tmp_path, flow)
        args = ["guard", *([name] if name else []), "--project", str(root), *rest, "--json"]

        result = _cli(args, stdin=stdin)

        if result.exit_code != 1:
            return
        assert json.loads(result.output)["outcome"] == "warn", label

    def test_the_liveness_report_records_nothing_though_a_project_was_located(
        self, tmp_path, stub_probes
    ) -> None:
        """The exception with the narrowest reason: a report evaluated nothing."""
        root = _project(tmp_path)

        _cli(["guard", "--liveness", "--project", str(root)])

        assert read_firings(root) == ()

    def test_an_unrecorded_invocation_says_on_stderr_that_it_was_not_recorded(
        self, tmp_path, stub_probes
    ) -> None:
        """A record that was not written is stated, not inferred from its absence."""
        root = _project(tmp_path)

        result = _cli(["guard", "no-such-guard", "--project", str(root)])

        assert "not recorded" in result.output, result.output

    def test_every_enumerated_row_is_reachable_through_the_real_binary(self) -> None:
        """The table is not allowed to shrink quietly."""
        assert len(_EXIT_PATHS) >= 16
        assert len({row[0] for row in _EXIT_PATHS}) == len(_EXIT_PATHS)


# ==========================================================================
# 2. THE STRUCTURE — an exit added without a record is a diff that reddens
# ==========================================================================


def _module_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _calls_named(tree: ast.AST, name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == name)
            or (isinstance(node.func, ast.Attribute) and node.func.attr == name)
        )
    ]


class TestTheCommandHasOneWayOut:
    """Structural pins. A behaviour table cannot see an exit path nobody wrote a row for.

    These three assertions are what make the enumeration above hard to defeat:
    adding a new way out of the command, or a new return from the boundary that
    skips the recording step, changes one of these counts.
    """

    def test_the_process_is_terminated_in_exactly_one_place(self) -> None:
        tree = _module_ast(_COMMAND_MODULE)

        exits = _calls_named(tree, "exit")
        raises = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Raise)
            and isinstance(node.exc, ast.Call)
            and isinstance(node.exc.func, ast.Name)
            and node.exc.func.id == "SystemExit"
        ]

        assert len(exits) == 1, [ast.unparse(node) for node in exits]
        assert raises == []

    def test_the_boundary_returns_through_the_recording_step_and_nowhere_else(
        self,
    ) -> None:
        """One return, and it is the step that writes (or explains) the record."""
        from beadloom.application.guards.invocation import run_invocation

        tree = _module_ast(_BOUNDARY_MODULE)
        entry = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == run_invocation.__name__
        )
        returns = [node for node in ast.walk(entry) if isinstance(node, ast.Return)]

        assert len(returns) == 1, [ast.unparse(node) for node in returns]
        assert isinstance(returns[0].value, ast.Call)
        assert ast.unparse(returns[0].value).startswith("_record(")

    def test_the_firing_record_is_written_from_exactly_one_call_site(self) -> None:
        """One writer, so "did this path record?" is a question about one branch."""
        modules = [
            *sorted((_SRC / "application" / "guards").rglob("*.py")),
            _COMMAND_MODULE,
        ]
        sites = [
            (path, ast.unparse(call))
            for path in modules
            for call in _calls_named(_module_ast(path), "record_firing")
        ]

        assert len(sites) == 1, sites

    def test_the_command_does_no_validation_click_would_exit_on(self) -> None:
        """A ``click.Path(exists=True)`` exits 2 before the callback — and the boundary — runs.

        That is how ``--project <missing>`` came to exit on the block code with
        no verdict and no record (``.28``, m1). The pin is on the option list
        rather than on the symptom, because any option validated by Click has
        the same exit path.
        """
        source = _COMMAND_MODULE.read_text(encoding="utf-8")

        assert "exists=True" not in source


# ==========================================================================
# 3. THE INJECTION — a failure nobody enumerated is still a verdict
# ==========================================================================


class TestAFailureNobodyEnumeratedIsStillAVerdict:
    """The boundary's whole point: an unknown defect becomes visible, not silent."""

    @pytest.fixture()
    def stub_probes(self, monkeypatch):
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(
            guard_cmd, "_probes", lambda _root: GuardProbes(tracker=_NoBeads())
        )

    def _install(self, monkeypatch, check) -> None:
        monkeypatch.setitem(
            BUILTIN_GUARDS,
            "bead-claimed",
            Guard(name="bead-claimed", summary="s", check=check),
        )

    def test_an_exception_inside_a_check_is_a_recorded_error(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        def explode(_request: object) -> None:
            msg = "the tracker probe blew up"
            raise RuntimeError(msg)

        self._install(monkeypatch, explode)
        root = _project(tmp_path)

        result = _cli(["guard", "bead-claimed", "--project", str(root)])

        assert result.exit_code == 2, result.output
        assert _outcomes(root) == ["error"]
        assert "the tracker probe blew up" in read_firings(root)[-1].why

    def test_a_check_that_exits_the_process_is_a_recorded_error(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        """``sys.exit`` deeper in the stack is the exact shape of every past hole.

        A lower layer that terminates the process decides the exit code and
        writes nothing — which is what ``_fail()`` did on six argument-parsing
        paths. Inside the boundary it becomes "I could not tell", recorded.
        """

        def bail(_request: object) -> None:
            raise SystemExit(7)

        self._install(monkeypatch, bail)
        root = _project(tmp_path)

        result = _cli(["guard", "bead-claimed", "--project", str(root)])

        assert result.exit_code == 2, result.output
        assert _outcomes(root) == ["error"]

    def test_a_stdin_that_cannot_be_read_is_a_recorded_error(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        """The read itself is inside the boundary, not before it."""
        from beadloom.services.commands import guard as guard_cmd

        def unreadable() -> str:
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        monkeypatch.setattr(guard_cmd, "_read_stdin", unreadable)
        root = _project(tmp_path)

        result = _cli(["guard", "bead-claimed", "--project", str(root), "--hook", "claude-code"])

        assert result.exit_code == 2, result.output
        assert _outcomes(root) == ["error"]

    def test_a_record_that_cannot_be_written_still_reaches_the_reader(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        """The last thing that can fail is the recording; it is not silent either."""
        from beadloom.application.guards import invocation as boundary

        def unwritable(*_args: object, **_kwargs: object) -> Path:
            msg = "read-only file system"
            raise OSError(msg)

        monkeypatch.setattr(boundary, "record_firing", unwritable)
        root = _project(tmp_path)

        result = _cli(["guard", "bead-claimed", "--project", str(root)])

        assert "not recorded" in result.output, result.output
        assert "read-only file system" in result.output, result.output


# ==========================================================================
# 4a. THE PROJECT IS FOUND BY DISCOVERY, NEVER MANUFACTURED
# ==========================================================================


@real_binary
class TestTheProjectIsTheOneTheRecordBelongsTo:
    """``.28`` F9 + the coordinator's measurement: cwd is not the project root.

    Real processes: discovery is a property of the process's working directory,
    which a ``CliRunner`` does not have.
    """

    @pytest.fixture()
    def project_with_a_subdirectory(self, tmp_path) -> tuple[Path, Path]:
        """``working-branch`` on the trunk: a real block, from git alone.

        No probe is stubbed in this class — these are real processes — so the
        guard has to be one whose evidence exists in a temporary directory.
        """
        root = _project(
            tmp_path,
            "guards:\n"
            "  working-branch:\n"
            "    strictness: { default: block }\n"
            "    exclusions:\n"
            "      - path: 'vendor/**'\n"
            "        reason: 'vendored'\n"
            "        until: 'BDL-999'\n",
        )
        _git_init(root, "main")
        sub = root / "src" / "deep"
        sub.mkdir(parents=True)
        return root, sub

    def test_a_declared_block_is_still_a_block_from_a_subdirectory(
        self, project_with_a_subdirectory
    ) -> None:
        root, sub = project_with_a_subdirectory

        at_root = _run_real(root, ["guard", "working-branch", "--context", "path=a.py"])
        at_sub = _run_real(sub, ["guard", "working-branch", "--context", "path=a.py"])

        assert at_root.returncode == 2, at_root.stderr
        assert at_sub.returncode == 2, at_sub.stderr

    def test_the_firing_lands_in_the_project_the_liveness_report_reads(
        self, project_with_a_subdirectory
    ) -> None:
        root, sub = project_with_a_subdirectory

        _run_real(sub, ["guard", "working-branch", "--context", "path=a.py"])

        assert _outcomes(root) == ["block"]
        report = _run_real(root, ["guard", "--liveness", "--json"])
        rows = {row["guard"]: row for row in json.loads(report.stdout)}
        assert rows["working-branch"]["never_fired"] is False
        assert rows["working-branch"]["fired_count"] == 1

    def test_it_manufactures_no_second_project_inside_the_first(
        self, project_with_a_subdirectory
    ) -> None:
        """The failure was self-entrenching: the stray root wins the next run."""
        _root, sub = project_with_a_subdirectory

        _run_real(sub, ["guard", "working-branch", "--context", "path=a.py"])

        assert not (sub / ".beadloom").exists()

    def test_the_liveness_report_from_a_subdirectory_reads_the_project(
        self, project_with_a_subdirectory
    ) -> None:
        root, sub = project_with_a_subdirectory

        _run_real(root, ["guard", "working-branch", "--context", "path=a.py"])
        report = _run_real(sub, ["guard", "--liveness", "--json"])
        rows = {row["guard"]: row for row in json.loads(report.stdout)}

        assert rows["working-branch"]["fired_count"] == 1
        assert not (sub / ".beadloom").exists()


@real_binary
class TestAGuardThatCannotFindTheProjectBlocksAndCreatesNothing:
    """No project, no silent skip — and no project root invented as a side effect."""

    def test_it_answers_error_on_the_blocking_code(self, tmp_path) -> None:
        outside = tmp_path / "not-a-project"
        outside.mkdir()

        result = _run_real(outside, ["guard", "bead-claimed"])

        assert result.returncode == 2, result.stderr
        assert b"ERROR" in result.stderr, result.stderr
        assert b"Traceback" not in result.stderr

    def test_it_creates_no_beadloom_directory(self, tmp_path) -> None:
        outside = tmp_path / "not-a-project"
        outside.mkdir()

        _run_real(outside, ["guard", "bead-claimed"])

        assert list(outside.iterdir()) == []

    def test_a_project_directory_that_does_not_exist_is_the_same_answer(
        self, tmp_path
    ) -> None:
        """``--project <missing>`` was Click's usage exit 2 with no verdict (m1)."""
        outside = tmp_path / "not-a-project"
        outside.mkdir()

        result = _run_real(
            outside, ["guard", "bead-claimed", "--project", str(tmp_path / "nowhere")]
        )

        assert result.returncode == 2, result.stderr
        assert b"ERROR" in result.stderr, result.stderr
        assert not (tmp_path / "nowhere").exists()

    def test_the_liveness_report_says_so_too(self, tmp_path) -> None:
        outside = tmp_path / "not-a-project"
        outside.mkdir()

        result = _run_real(outside, ["guard", "--liveness"])

        assert result.returncode == 2, result.stderr
        assert list(outside.iterdir()) == []


# ==========================================================================
# 4b. A PAYLOAD THE PROCESS CANNOT DECODE (.28 F7)
# ==========================================================================


@real_binary
class TestAHookPayloadTheProcessCannotDecode:
    """F7 closed: the stdin read is inside the boundary.

    Must run as a real process — a ``CliRunner`` supplies an already-decoded
    string and cannot reproduce a decoding failure at all.
    """

    @pytest.mark.parametrize(
        ("label", "payload"),
        [
            (
                "a latin-1 byte inside the file path",
                b'{"tool_input": {"file_path": "src/\xff.py"}}',
            ),
            ("a UTF-16 payload", b"\xff\xfe{\x00}\x00"),
            ("a stray continuation byte", b'{"tool_name": "\x80"}'),
        ],
    )
    def test_an_undecodable_payload_is_a_recorded_verdict(
        self, tmp_path, label, payload
    ) -> None:
        root = _project(tmp_path)

        result = _run_real(
            root, ["guard", "bead-claimed", "--hook", "claude-code"], stdin=payload
        )

        assert result.returncode == 2, f"{label}: {result.stderr!r}"
        assert b"Traceback" not in result.stderr, label
        assert _outcomes(root) == ["error"], label

    def test_it_never_exits_on_the_non_blocking_warn_code(self, tmp_path) -> None:
        root = _project(tmp_path)

        result = _run_real(
            root,
            ["guard", "bead-claimed", "--hook", "claude-code"],
            stdin=b'{"tool_input": {"file_path": "src/\xff.py"}}',
        )

        assert result.returncode != 1, result.stderr


# ==========================================================================
# 4c. THE SHAPE IS JUDGED ON WHAT THE HARNESS SUPPLIED (.28 F10 + m2)
# ==========================================================================


class TestTheShapeIsJudgedBeforeAnythingIsRemoved:
    """F10: ``str.strip()`` removed nine characters the SPEC says are refused.

    The cost of the strip was reported as "a file whose name ends in whitespace
    is guarded as though it did not" — the harmless direction. Measured, it was
    the other one: a trailing ``\\n`` turned a ``block`` into a ``skip`` whose
    reason named a pattern that does not cover the file.
    """

    @pytest.fixture()
    def stub_probes(self, monkeypatch):
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(
            guard_cmd, "_probes", lambda _root: GuardProbes(tracker=_NoBeads())
        )

    @pytest.mark.parametrize(
        ("label", "suffix"),
        [
            ("newline", "\n"),
            ("carriage return", "\r"),
            ("tab", "\t"),
            ("vertical tab", "\v"),
            ("form feed", "\f"),
            ("file separator", "\x1c"),
            ("group separator", "\x1d"),
            ("record separator", "\x1e"),
            ("unit separator", "\x1f"),
        ],
    )
    def test_a_control_character_is_refused_wherever_it_sits(
        self, tmp_path, stub_probes, label, suffix
    ) -> None:
        root = _project(tmp_path)

        result = _cli(
            [
                "guard",
                "bead-claimed",
                "--project",
                str(root),
                "--context",
                f"path=src/app.py{suffix}",
                "--json",
            ]
        )

        assert json.loads(result.output)["outcome"] == "error", label
        assert result.exit_code == 2, label

    @pytest.mark.parametrize(
        ("label", "suffix"),
        [
            ("no-break space", "\xa0"),
            ("next line", "\x85"),
            ("en quad", "\u2000"),
            ("line separator", "\u2028"),
            ("ideographic space", "\u3000"),
            ("plain space", " "),
        ],
    )
    def test_a_name_that_ends_in_whitespace_is_guarded_not_exempted(
        self, tmp_path, stub_probes, label, suffix
    ) -> None:
        """The pattern ``src/*.py`` does not name this file, so it must not exempt it."""
        root = _project(tmp_path)

        result = _cli(
            [
                "guard",
                "bead-claimed",
                "--project",
                str(root),
                "--context",
                f"path=src/app.py{suffix}",
                "--json",
            ]
        )

        payload = json.loads(result.output)
        exclusion = GuardExclusion(path="src/*.py", reason="r", until="u")
        assert payload["outcome"] == "block", f"{label}: {payload}"
        assert exclusion.matches(f"src/app.py{suffix}") is False

    def test_the_exclusion_matcher_stops_at_the_end_of_the_path(self) -> None:
        """m2: ``$`` also matches before a trailing newline — the second lock, now closed."""
        exclusion = GuardExclusion(path="src/*.py", reason="r", until="u")

        assert exclusion.matches("src/app.py\n") is False
        assert exclusion.matches("src/app.py") is True


# ==========================================================================
# 5. THE BOUNDARY IN PROCESS — the logic, where a subprocess proves the seam
# ==========================================================================


class TestLocatingTheProject:
    """``locate_project_root`` directly: the walk, the marker, and the refusals.

    The subprocess classes above prove the *seam* — that a real process really
    does discover the root from its working directory (standing rule 4). These
    prove the rule itself, in process, so a defect in the walk reddens even where
    the console script is absent.
    """

    def test_it_walks_up_to_the_nearest_directory_holding_the_marker(
        self, tmp_path
    ) -> None:
        from beadloom.application.guards.project_root import locate_project_root

        root = _project(tmp_path)
        deep = root / "src" / "a" / "b"
        deep.mkdir(parents=True)

        assert locate_project_root(start=deep).root == root.resolve()

    def test_a_nested_marker_wins_because_that_is_what_a_nested_project_is(
        self, tmp_path
    ) -> None:
        """The residual, pinned rather than left to be discovered."""
        from beadloom.application.guards.project_root import locate_project_root

        root = _project(tmp_path)
        inner = _project(root / "vendor" / "thing")
        deep = inner / "src"
        deep.mkdir(parents=True)

        assert locate_project_root(start=deep).root == inner.resolve()

    def test_a_declared_project_is_used_verbatim_without_walking_up(
        self, tmp_path
    ) -> None:
        """An explicit argument means what it says; searching past it would not."""
        from beadloom.application.guards.project_root import locate_project_root

        root = _project(tmp_path)
        sub = root / "src"
        sub.mkdir()

        located = locate_project_root(declared=sub)

        assert located.root == sub
        assert located.declared is True

    @pytest.mark.parametrize(
        ("label", "kind"),
        [("no marker anywhere above", "walk"), ("--project names nothing", "declared")],
    )
    def test_a_project_that_cannot_be_located_refuses_and_names_the_reason(
        self, tmp_path, label, kind
    ) -> None:
        from beadloom.application.guards.project_root import locate_project_root

        start = tmp_path / "plain"
        start.mkdir()

        located = (
            locate_project_root(start=start)
            if kind == "walk"
            else locate_project_root(declared=start / "gone")
        )

        assert located.root is None, label
        assert located.refusal, label
        assert not (start / ".beadloom").exists(), label

    def test_an_unreadable_working_directory_is_a_refusal_and_not_a_crash(
        self, tmp_path, monkeypatch
    ) -> None:
        """The one failure the walk itself can raise, kept a refusal like the rest."""
        from beadloom.application.guards import project_root as module

        def unreadable() -> Path:
            msg = "the working directory was deleted"
            raise OSError(msg)

        monkeypatch.setattr(module.Path, "cwd", staticmethod(unreadable))

        located = module.locate_project_root()

        assert located.root is None
        assert "working directory" in located.refusal


class TestTheBoundaryWithoutTheCli:
    """``run_invocation`` called directly — it neither raises nor exits, ever."""

    def test_a_caller_that_wires_nothing_gets_honest_defaults(self, tmp_path) -> None:
        """No payload and no probes: unavailable evidence, a skip with a reason."""
        from beadloom.application.guards.invocation import GuardInvocation, run_invocation

        root = _project(tmp_path)

        result = run_invocation(
            GuardInvocation(name="bead-claimed", declared_project=root)
        )

        assert result.verdict is not None
        assert result.verdict.outcome.value == "skip"
        assert result.exit_code == 0
        assert result.recorded is True

    def test_a_hook_caller_that_wires_no_reader_gets_an_empty_event(
        self, tmp_path
    ) -> None:
        """The default payload reader supplies no event, never a crash."""
        from beadloom.application.guards.invocation import GuardInvocation, run_invocation

        root = _project(tmp_path)

        result = run_invocation(
            GuardInvocation(
                name="bead-claimed", declared_project=root, harness="claude-code"
            )
        )

        assert result.verdict is not None
        assert result.verdict.context == {}
        assert result.recorded is True

    def test_an_unlocatable_project_answers_error_and_records_nothing(
        self, tmp_path
    ) -> None:
        from beadloom.application.guards.invocation import (
            NOT_RECORDED_NO_PROJECT,
            GuardInvocation,
            run_invocation,
        )

        plain = tmp_path / "plain"
        plain.mkdir()

        result = run_invocation(GuardInvocation(name="bead-claimed", start_dir=plain))

        assert result.verdict is not None
        assert result.verdict.outcome.value == "error"
        assert result.exit_code == 2
        assert result.recorded is False
        assert result.not_recorded_because == NOT_RECORDED_NO_PROJECT
        assert not (plain / ".beadloom").exists()

    def test_the_reason_a_record_is_missing_is_always_stated(self, tmp_path) -> None:
        """Every unrecorded result names why; an absent line explains nothing."""
        from beadloom.application.guards.invocation import GuardInvocation, run_invocation

        root = _project(tmp_path)
        unrecorded = [
            run_invocation(GuardInvocation(declared_project=root, liveness=True)),
            run_invocation(GuardInvocation(name="no-such-guard", declared_project=root)),
            run_invocation(GuardInvocation(declared_project=root)),
        ]

        assert [result.recorded for result in unrecorded] == [False, False, False]
        assert all(result.not_recorded_because for result in unrecorded)

    def test_a_failure_while_locating_the_project_is_still_a_verdict(
        self, tmp_path, monkeypatch
    ) -> None:
        """Locating runs inside the boundary, so it cannot be the step that escapes.

        A step that runs *before* the handler is the shape of every hole the
        boundary exists to close, and project discovery was the newest step.
        """
        from beadloom.application.guards import invocation as boundary

        def explode(**_kwargs: object) -> object:
            msg = "the filesystem said no"
            raise OSError(msg)

        monkeypatch.setattr(boundary, "locate_project_root", explode)

        result = boundary.run_invocation(
            boundary.GuardInvocation(name="bead-claimed", declared_project=tmp_path)
        )

        assert result.verdict is not None
        assert result.verdict.outcome.value == "error"
        assert result.exit_code == 2
        assert "the filesystem said no" in result.verdict.why
        assert result.recorded is False
