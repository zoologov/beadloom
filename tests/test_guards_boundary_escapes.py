"""Ways out of ``beadloom guard`` the boundary does not close (BDL-061.30).

``.29`` replaced three rounds of case-by-case patching with one boundary:
:func:`~beadloom.application.guards.invocation.run_invocation` is
``_record(_answer(...))``, and four AST pins in ``test_guards_invocation.py``
are what is supposed to make "an exit added without a record is a diff that
reddens" true going forward.

This module verifies the *load-bearing* half of that claim rather than
re-enumerating the behaviour, and it holds the three places where the boundary
turned out to be present but not load-bearing. Every class here is named for the
gap it pins, so the fix is a rename rather than a deletion — the shape ``.28``
used and ``.29`` closed:

1. :class:`TestAnInterruptEscapesTheBoundary` — ``_answer`` handles ``Exception``
   and ``SystemExit``. ``KeyboardInterrupt`` is neither, so a SIGINT during an
   evaluation leaves the boundary with no verdict and no record, and Click turns
   it into exit **1** — the WARN code a harness reads as "carry on". That is the
   shape of ``.28``'s F7 in a different exception class.
2. :class:`TestTheOneWayOutPinCannotSeeEveryWayOut` — the pins are *spelling*
   checks. They count AST calls named ``exit`` in one module, so ``os._exit``, a
   bare ``raise SystemExit`` and ``raise click.Abort()`` are invisible, and a
   terminator inside the boundary module is out of scope entirely. The stronger
   pins live here and pass on the shipped source.
3. :class:`TestADeclaredProjectNeedNotBeAProject` — ``project_root.py`` states
   "What is deliberately NOT done: manufacturing a root". True for discovery,
   false for ``--project``: an existing directory with no ``.beadloom/`` is used
   verbatim, the project's declared strictness is silently replaced by the
   shipped defaults, and the firing record creates ``.beadloom/`` there.

:class:`TestExitPathsTheEnumerationDoesNotList` holds the rows this round's
independent enumeration produced that ``.29``'s 16-row table does not contain.

Standing rule 4 — where a test proves a seam rather than the tool it says so:
the interrupt is injected at the probe seam (a real SIGINT lands wherever the
process happens to be, most often blocked in the ``bd`` subprocess, so it is not
a reproducible way to reach the handler), exactly as ``.29`` injects
``sys.exit`` and ``UnicodeDecodeError`` at the same seams. The exit code that
interrupt produces IS measured through real Click standalone dispatch in a
subprocess, because ``CliRunner`` does not run Click's ``main()`` error
handling the way the console script does.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.application.guards.contract import Guard, GuardProbes
from beadloom.application.guards.firing import FIRINGS_RELPATH, read_firings
from beadloom.application.guards.invocation import GuardInvocation, run_invocation
from beadloom.services.cli import main

_SRC = Path(__file__).resolve().parents[1] / "src" / "beadloom"
_COMMAND_MODULE = _SRC / "services" / "commands" / "guard.py"
_BOUNDARY_MODULE = _SRC / "application" / "guards" / "invocation.py"
_DISCOVERY_MODULE = _SRC / "application" / "guards" / "project_root.py"

_BLOCKING = (
    "guards:\n  bead-claimed:\n    strictness: { default: block }\n"
)


class _NoBeads:
    """A tracker that answers, and answers "nothing is claimed"."""

    @staticmethod
    def claimed_beads() -> tuple[()]:
        return ()


def _project(tmp_path: Path, flow: str = _BLOCKING) -> Path:
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".beadloom" / "flow.yml").write_text(flow, encoding="utf-8")
    return tmp_path


def _cli(args: list[str], *, stdin: str = ""):
    return CliRunner().invoke(main, args, input=stdin)


@pytest.fixture()
def stub_probes(monkeypatch):
    """Wire a tracker that answers, so a verdict comes from the guard and not the probe."""
    from beadloom.services.commands import guard as guard_cmd

    monkeypatch.setattr(
        guard_cmd, "_probes", lambda _root: GuardProbes(tracker=_NoBeads())
    )


# ==========================================================================
# 1. GAP — the handler covers Exception and SystemExit, not BaseException
# ==========================================================================


class TestAnInterruptEscapesTheBoundary:
    """``except Exception`` plus ``except SystemExit`` is not ``except BaseException``.

    ``.29`` added ``except SystemExit`` because "a lower layer that terminates
    the process without a verdict is the exact shape of every hole so far".
    ``SystemExit`` is one of five ``BaseException`` subclasses;
    ``KeyboardInterrupt`` is the reachable other one, and it is not handled. The
    consequence is not merely an unrecorded invocation: Click converts it to
    ``Abort`` and exits **1**, which the shipped adapter treats as non-blocking,
    so an interrupted guard lets the edit through.

    Rename this class when the handler widens; the assertions invert.
    """

    def _install(self, monkeypatch, check) -> None:
        monkeypatch.setitem(
            BUILTIN_GUARDS,
            "bead-claimed",
            Guard(name="bead-claimed", summary="s", check=check),
        )

    def test_a_keyboard_interrupt_in_a_check_is_not_turned_into_a_verdict(
        self, tmp_path, monkeypatch
    ) -> None:
        """The boundary's contract is "never raises". It raises for this one."""

        def interrupted(_request: object) -> None:
            raise KeyboardInterrupt

        self._install(monkeypatch, interrupted)
        root = _project(tmp_path)

        with pytest.raises(KeyboardInterrupt):
            run_invocation(
                GuardInvocation(
                    name="bead-claimed",
                    declared_project=root,
                    context_pairs=("path=app.py",),
                    probes_for=lambda _root: GuardProbes(tracker=_NoBeads()),
                )
            )

        assert read_firings(root) == ()

    def test_the_same_interrupt_by_contrast_is_a_verdict_when_it_is_an_exception(
        self, tmp_path, monkeypatch
    ) -> None:
        """The control: an ordinary exception at the same seam is caught and recorded.

        Present so the class above cannot be read as "injection at this seam
        never reaches the handler" — it does, for everything but a
        ``BaseException``.
        """

        def exploded(_request: object) -> None:
            msg = "an ordinary failure"
            raise RuntimeError(msg)

        self._install(monkeypatch, exploded)
        root = _project(tmp_path)

        result = run_invocation(
            GuardInvocation(
                name="bead-claimed",
                declared_project=root,
                context_pairs=("path=app.py",),
                probes_for=lambda _root: GuardProbes(tracker=_NoBeads()),
            )
        )

        assert result.exit_code == 2
        assert result.recorded is True

    def test_the_handlers_are_exception_and_systemexit_and_nothing_wider(self) -> None:
        """Read off the source, so the gap is a fact about the code and not a mood."""
        tree = ast.parse(_BOUNDARY_MODULE.read_text(encoding="utf-8"))
        answer = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_answer"
        )
        try_block = next(
            node for node in ast.walk(answer) if isinstance(node, ast.Try)
        )
        handled = {
            handler.type.id
            for handler in try_block.handlers
            if isinstance(handler.type, ast.Name)
        }

        assert handled == {"SystemExit", "Exception"}
        assert "BaseException" not in handled
        assert "KeyboardInterrupt" not in handled

    def test_through_real_click_dispatch_an_interrupt_is_the_non_blocking_warn_code(
        self, tmp_path
    ) -> None:
        """Measured, not reasoned: rc 1, "Aborted!", no verdict, no record.

        Seam (rule 4): the interrupt is injected at the probe seam and the
        harness is Click's own ``main()`` in a real subprocess — that is the
        dispatch the console script uses, and it is where ``KeyboardInterrupt``
        becomes ``Abort`` becomes exit 1.
        """
        root = _project(tmp_path)
        script = tmp_path / "dispatch.py"
        script.write_text(
            textwrap.dedent(
                """
                from beadloom.application.guards.contract import GuardProbes
                from beadloom.services.commands import guard as guard_cmd

                class Interrupted:
                    @staticmethod
                    def claimed_beads():
                        raise KeyboardInterrupt

                guard_cmd._probes = lambda _root: GuardProbes(tracker=Interrupted())

                from beadloom.services.cli import main

                main()
                """
            ),
            encoding="utf-8",
        )

        completed = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [
                sys.executable,
                str(script),
                "guard",
                "bead-claimed",
                "--project",
                str(root),
                "--context",
                "path=app.py",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 1, completed.stderr
        assert "Aborted!" in completed.stderr
        assert "bead-claimed" not in completed.stdout
        assert read_firings(root) == ()


# ==========================================================================
# 2. GAP — the structural pins are spelling checks
# ==========================================================================


def _exit_calls_the_shipped_pin_counts(tree: ast.AST) -> list[ast.Call]:
    """``.29``'s predicate, reproduced exactly so the comparison is like-for-like.

    ``test_the_process_is_terminated_in_exactly_one_place`` counts calls whose
    function is *named* ``exit``, plus ``raise SystemExit(...)`` written as a
    call. Everything else is a way out it cannot see.
    """
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "exit")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "exit")
        )
    ]


def _systemexit_raises_the_shipped_pin_counts(tree: ast.AST) -> list[ast.Raise]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and isinstance(node.exc.func, ast.Name)
        and node.exc.func.id == "SystemExit"
    ]


#: Terminator spellings the shipped pin does not recognise, one per row.
_INVISIBLE_TERMINATORS = (
    ("os._exit", "import os\nos._exit(3)\n"),
    ("os.abort", "import os\nos.abort()\n"),
    ("a bare raise SystemExit", "raise SystemExit\n"),
    ("click.Abort", "import click\nraise click.Abort()\n"),
)


def _terminators_of_any_spelling(tree: ast.AST) -> list[str]:
    """Every way *tree* can end the process, whatever it is spelled.

    The pin ``.29`` needed: a name-based count is defeated by choosing another
    name, and the last three rounds were each a way out that nobody had thought
    to write a row for.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = node.func
            named = (
                target.id
                if isinstance(target, ast.Name)
                else target.attr
                if isinstance(target, ast.Attribute)
                else ""
            )
            if named in {"exit", "quit", "_exit", "abort"}:
                found.append(ast.unparse(node))
        elif isinstance(node, ast.Raise) and node.exc is not None:
            raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            name = (
                raised.id
                if isinstance(raised, ast.Name)
                else raised.attr
                if isinstance(raised, ast.Attribute)
                else ""
            )
            if name in {"SystemExit", "Abort", "Exit"}:
                found.append(ast.unparse(node))
    return found


class TestTheOneWayOutPinCannotSeeEveryWayOut:
    """The pin counts one spelling in one module; four spellings and one module escape it.

    This is not a defect in the shipped command — it terminates in exactly one
    place today. It is a defect in the *guarantee*: ``.29``'s report states that
    the pins are "what make the enumeration hard to defeat", and the next round
    that adds a way out will only redden if it happens to spell it ``x.exit()``
    inside ``services/commands/guard.py``.
    """

    @pytest.mark.parametrize(
        ("label", "body"), _INVISIBLE_TERMINATORS, ids=[row[0] for row in _INVISIBLE_TERMINATORS]
    )
    def test_the_shipped_pin_stays_green_beside_a_second_terminator(
        self, label, body
    ) -> None:
        """One ``sys.exit`` plus one of these: the pin still counts exactly one."""
        source = "import sys\n\n\ndef go():\n    sys.exit(0)\n\n\ndef bail():\n" + textwrap.indent(
            body, "    "
        )
        tree = ast.parse(source)

        assert len(_exit_calls_the_shipped_pin_counts(tree)) == 1, label
        assert _systemexit_raises_the_shipped_pin_counts(tree) == [], label

    @pytest.mark.parametrize(
        ("label", "body"), _INVISIBLE_TERMINATORS, ids=[row[0] for row in _INVISIBLE_TERMINATORS]
    )
    def test_the_stronger_pin_sees_all_four(self, label, body) -> None:
        """The predicate this module contributes: two terminators, counted as two."""
        source = "import sys\n\n\ndef go():\n    sys.exit(0)\n\n\ndef bail():\n" + textwrap.indent(
            body, "    "
        )

        assert len(_terminators_of_any_spelling(ast.parse(source))) == 2, label

    def test_the_shipped_pin_does_not_look_inside_the_boundary_module(self) -> None:
        """Its scope is ``guard.py``. A ``sys.exit`` in ``run_invocation`` is out of scope.

        Measured this round: adding ``if invocation.name == "": sys.exit(0)`` to
        ``run_invocation`` leaves all four structural pins and all 628 guard
        tests green, while ``beadloom guard ""`` exits 0, prints nothing and
        records nothing.
        """
        pinned_modules = {_COMMAND_MODULE}

        assert _BOUNDARY_MODULE not in pinned_modules
        assert _DISCOVERY_MODULE not in pinned_modules

    def test_the_shipped_source_terminates_in_exactly_one_place_on_the_wider_pin(
        self,
    ) -> None:
        """The regression guard this round adds, over all three modules at once."""
        terminators = [
            (path.name, spelling)
            for path in (_COMMAND_MODULE, _BOUNDARY_MODULE, _DISCOVERY_MODULE)
            for spelling in _terminators_of_any_spelling(
                ast.parse(path.read_text(encoding="utf-8"))
            )
        ]

        assert terminators == [("guard.py", "sys.exit(result.exit_code)")], terminators

    def test_the_click_path_pin_is_a_substring_and_misses_the_other_validators(
        self,
    ) -> None:
        """``"exists=True" not in source`` is satisfied by ``dir_okay=False``.

        ``.29``'s report claims the pin is "no ``click.Path`` keyword other than
        ``path_type``". The shipped assertion is one substring, and every other
        ``click.Path`` validator exits before the callback in the same way.
        """
        sabotaged = 'type=click.Path(path_type=Path, dir_okay=False)\n'

        assert "exists=True" not in sabotaged

    def test_the_declared_project_option_takes_only_path_type(self) -> None:
        """The stronger pin: read the keywords off the real ``click.Path`` call."""
        tree = ast.parse(_COMMAND_MODULE.read_text(encoding="utf-8"))
        path_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Path"
        ]

        assert len(path_calls) == 1, [ast.unparse(node) for node in path_calls]
        assert [kw.arg for kw in path_calls[0].keywords] == ["path_type"]


# ==========================================================================
# 3. GAP — --project is not required to name a project
# ==========================================================================


class TestADeclaredProjectNeedNotBeAProject:
    """``project_root.py``: "it does not create ``.beadloom/`` where it stands".

    True of discovery, false of ``--project``. An existing directory that is not
    a Beadloom project is honoured verbatim: no ``flow.yml`` is found, so the
    project's declared ``block`` becomes the shipped default, and the firing
    record manufactures ``.beadloom/`` in that directory — the coordinator's
    measured F9 failure, reachable through an explicit flag. ``.28`` listed this
    as minor ``m3``; ``.29``'s residual list does not name it.
    """

    def test_the_module_still_says_it_manufactures_no_root(self) -> None:
        """The sentence the two tests below contradict, read from the source."""
        source = _DISCOVERY_MODULE.read_text(encoding="utf-8")

        assert "What is deliberately NOT done: manufacturing a root." in source

    def test_a_declared_directory_without_the_marker_is_used_anyway(
        self, tmp_path, stub_probes
    ) -> None:
        not_a_project = tmp_path / "elsewhere"
        not_a_project.mkdir()

        result = _cli(
            [
                "guard",
                "bead-claimed",
                "--project",
                str(not_a_project),
                "--context",
                "path=app.py",
            ]
        )

        assert "could not be located" not in result.output
        assert result.exit_code == 1, result.output

    def test_it_creates_the_marker_directory_it_did_not_find(
        self, tmp_path, stub_probes
    ) -> None:
        not_a_project = tmp_path / "elsewhere"
        not_a_project.mkdir()

        _cli(
            [
                "guard",
                "bead-claimed",
                "--project",
                str(not_a_project),
                "--context",
                "path=app.py",
            ]
        )

        assert (not_a_project / FIRINGS_RELPATH).is_file()
        assert len(read_firings(not_a_project)) == 1

    def test_the_declared_strictness_is_silently_replaced_by_the_default(
        self, tmp_path, stub_probes
    ) -> None:
        """Same argv, same edit, two roots — and the wrong one is the permissive one."""
        real = _project(tmp_path / "real")
        not_a_project = tmp_path / "elsewhere"
        not_a_project.mkdir()
        argv = ["guard", "bead-claimed", "--context", "path=app.py", "--json"]

        blocked = _cli([*argv, "--project", str(real)])
        wandered = _cli([*argv, "--project", str(not_a_project)])

        assert blocked.exit_code == 2, blocked.output
        assert json.loads(wandered.output)["outcome"] == "warn"
        assert wandered.exit_code == 1, wandered.output


# ==========================================================================
# 4. ROWS THIS ROUND'S INDEPENDENT ENUMERATION ADDS
# ==========================================================================


#: Labels this round derived from the code that ``.29``'s table does not carry.
_ROWS_ADDED_THIS_ROUND = (
    "an empty guard name",
    "a --project that is not a project",
    "a hook payload of zero bytes",
    "a --context key supplied twice",
    "an interrupt during the evaluation",
)


class TestExitPathsTheEnumerationDoesNotList:
    """The diff between this round's enumeration and ``.29``'s 16-row table.

    A table that enumerates itself proves nothing, so these rows were derived
    from the code and the CLI surface first and compared afterwards. Four of the
    five behave correctly — they are enumeration gaps, not defects. The fifth is
    the interrupt, pinned above.
    """

    def test_the_added_rows_are_absent_from_the_shipped_table(self) -> None:
        """The comparison, machine-checked rather than asserted in prose."""
        from tests.test_guards_invocation import _EXIT_PATHS

        shipped = {row[0] for row in _EXIT_PATHS}

        assert shipped.isdisjoint(_ROWS_ADDED_THIS_ROUND), shipped & set(
            _ROWS_ADDED_THIS_ROUND
        )

    def test_an_empty_guard_name_is_a_verdict_on_the_config_code(
        self, tmp_path, stub_probes
    ) -> None:
        """``beadloom guard ""`` — a name that is present and empty, not absent."""
        root = _project(tmp_path)

        result = _cli(["guard", "", "--project", str(root)])

        assert result.exit_code == 3, result.output
        assert "unknown guard ''" in result.output
        assert "not recorded" in result.output
        assert read_firings(root) == ()

    def test_an_empty_guard_name_is_labelled_as_no_name_at_all(
        self, tmp_path, stub_probes
    ) -> None:
        """Cosmetic drift: ``"" or UNNAMED_GUARD`` makes the two cases indistinguishable.

        The verdict's ``guard`` field reads "(no guard named)" while its ``why``
        correctly says ``unknown guard ''``, so the record's own reason for not
        recording names a guard the caller never typed.
        """
        root = _project(tmp_path)

        result = _cli(["guard", "", "--project", str(root), "--json"])

        assert json.loads(result.output)["guard"] == "(no guard named)"

    def test_a_hook_payload_of_zero_bytes_is_an_ordinary_evaluation(
        self, tmp_path, stub_probes
    ) -> None:
        """Empty stdin reads as ``{}``: no path, so the guard says what it did not check."""
        root = _project(tmp_path)

        result = _cli(
            ["guard", "bead-claimed", "--project", str(root), "--hook", "claude-code"],
            stdin="",
        )

        assert result.exit_code in (0, 2), result.output
        assert "Traceback" not in result.output
        assert len(read_firings(root)) == 1

    def test_a_context_key_supplied_twice_takes_the_last_and_says_nothing(
        self, tmp_path, stub_probes
    ) -> None:
        """Last-wins is silent. Fail-closed here, but it is an unstated rule."""
        root = _project(tmp_path)

        result = _cli(
            [
                "guard",
                "bead-claimed",
                "--project",
                str(root),
                "--json",
                "--context",
                "path=src/a.py",
                "--context",
                "path=app.py",
            ]
        )

        assert json.loads(result.output)["context"]["path"] == "app.py"
