"""The three ways past the boundary BDL-061.30 measured, and the pins that close them.

``.29`` replaced three rounds of case-by-case patching with one boundary:
:func:`~beadloom.application.guards.invocation.run_invocation` is
``_record(_answer(...))``. ``.30`` attacked it and could not break the render
step, the exit-code rule, the three recording exceptions, walk-up discovery or
append atomicity — but it did find three ways past its *edges*, and one of them
was the deliverable's own guarantee:

1. :class:`TestAnInterruptIsARecordedVerdictLikeAnyOtherFailure` — ``_answer``
   handled ``Exception`` and ``SystemExit``. ``KeyboardInterrupt`` is neither,
   so an interrupt during an evaluation left the boundary with no verdict and no
   record and Click turned it into exit **1**, the WARN code a harness reads as
   "carry on". Closed by widening the last-resort handler to ``BaseException``,
   with the consequence argued in ``flow-guards/SPEC.md``: an interrupt is now a
   recorded "I could not tell" at exit 2, which BLOCKS the edit.
2. :class:`TestControlLeavesTheBoundaryPathInExactlyOnePlace` — the structural
   pins checked a *spelling*. Measured by ``.30``: ``sys.exit(0)`` inside
   ``run_invocation`` shipped 628/628 green while ``beadloom guard ""`` exited 0
   recording nothing. Closed by making the pin as wide as its invariant — see
   the section-2 preamble of ``test_guards_invocation.py``, which holds the pin;
   this module holds the evidence that the pin *bites*, including the measured
   terminator table it is built on.
3. :class:`TestADeclaredProjectMustBeAProject` — ``--project`` honoured any
   ``is_dir()``, so an existing directory that was not a project silently traded
   the declared ``block`` for the shipped default ``warn`` and gained a
   self-entrenching ``.beadloom/``. Closed by requiring the marker, and the
   docstring that denied it now says what the code does.

:class:`TestTheRowsThisRoundAddedAreNowEnumerated` closes the enumeration gap:
the four argv-reachable rows ``.30`` derived are now in the shipped table, and
the fifth — the interrupt — is a row of ``_INJECTED_FAILURES``.

Standing rule 4 — where a test proves a seam rather than the tool it says so:
the interrupt is injected at the probe seam (a real SIGINT lands wherever the
process happens to be, most often blocked in the ``bd`` subprocess, so it is not
a reproducible way to reach the handler), exactly as ``.29`` injects
``sys.exit`` and ``UnicodeDecodeError`` at the same seams. The exit code an
interrupt produces IS measured through real Click standalone dispatch in a
subprocess, because ``CliRunner`` does not run Click's ``main()`` error handling
the way the console script does.
"""

from __future__ import annotations

import ast
import json
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.application.guards.contract import Guard, GuardProbes
from beadloom.application.guards.firing import FIRINGS_RELPATH, read_firings
from beadloom.application.guards.invocation import GuardInvocation, run_invocation
from beadloom.services.cli import main
from tests.test_guards_invocation import (
    THE_ONE_WAY_OUT,
    boundary_path_modules,
    click_refuses,
    declared_conversion,
    declared_conversions,
    process_terminators,
    record_firing_sites,
    terminators_on_the_boundary_path,
)

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src" / "beadloom"
_COMMAND_MODULE = _SRC / "services" / "commands" / "guard.py"
_BOUNDARY_MODULE = _SRC / "application" / "guards" / "invocation.py"
_DISCOVERY_MODULE = _SRC / "application" / "guards" / "project_root.py"
_SPEC = _ROOT / "docs" / "domains" / "application" / "features" / "flow-guards" / "SPEC.md"

_BLOCKING = "guards:\n  bead-claimed:\n    strictness: { default: block }\n"


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


def _must_not_escape(call):
    """Run *call*, turning an escape from the boundary into a FAILED, not an abort.

    An uncaught ``KeyboardInterrupt`` interrupts the whole pytest session, and
    "the run stopped" is not "the test failed" — standing rule 5 asks for FAILED
    and for countable numbers. This makes an escape a countable failure of the
    test that asserts it cannot happen.
    """
    try:
        return call()
    except BaseException as exc:
        pytest.fail(f"control escaped the boundary as {type(exc).__name__}")


@pytest.fixture()
def stub_probes(monkeypatch):
    """Wire a tracker that answers, so a verdict comes from the guard and not the probe."""
    from beadloom.services.commands import guard as guard_cmd

    monkeypatch.setattr(
        guard_cmd, "_probes", lambda _root: GuardProbes(tracker=_NoBeads())
    )


# ==========================================================================
# 1. CLOSED — the handler of last resort is BaseException
# ==========================================================================


class TestAnInterruptIsARecordedVerdictLikeAnyOtherFailure:
    """``except Exception`` plus ``except SystemExit`` was not ``except BaseException``.

    ``.29`` added ``except SystemExit`` because "a lower layer that terminates
    the process without a verdict is the exact shape of every hole so far".
    ``SystemExit`` is one of the ``BaseException`` subclasses;
    ``KeyboardInterrupt`` is the reachable other one, and it was not handled —
    so an interrupted guard let the edit through at exit 1 AND left no trace,
    the one combination this slice exists to prevent.

    THE COST OF THE FIX, because it is not free: an interrupt is now a recorded
    ``error`` at exit 2, so pressing Ctrl-C during a guarded edit BLOCKS that
    edit instead of waving it through. That is argued in ``flow-guards/SPEC.md``
    rather than assumed here, and the short form is: SIGINT reaches the whole
    foreground process group, so the harness's own tool call is interrupted with
    the guard, and a guard that did not answer must not be read as one that
    passed.
    """

    def _install(self, monkeypatch, check) -> None:
        monkeypatch.setitem(
            BUILTIN_GUARDS,
            "bead-claimed",
            Guard(name="bead-claimed", summary="s", check=check),
        )

    def _invocation(self, root: Path) -> GuardInvocation:
        return GuardInvocation(
            name="bead-claimed",
            declared_project=root,
            context_pairs=("path=app.py",),
            probes_for=lambda _root: GuardProbes(tracker=_NoBeads()),
        )

    def test_a_keyboard_interrupt_in_a_check_is_turned_into_a_recorded_verdict(
        self, tmp_path, monkeypatch
    ) -> None:
        """The boundary's contract is "never raises". It now holds for this one too."""

        def interrupted(_request: object) -> None:
            raise KeyboardInterrupt

        self._install(monkeypatch, interrupted)
        root = _project(tmp_path)

        result = _must_not_escape(lambda: run_invocation(self._invocation(root)))

        assert result.exit_code == 2
        assert result.recorded is True
        assert "interrupted" in result.verdict.why
        assert [record.outcome for record in read_firings(root)] == ["error"]

    def test_the_same_seam_by_contrast_is_a_verdict_when_it_is_an_exception(
        self, tmp_path, monkeypatch
    ) -> None:
        """The control: an ordinary exception at the same seam is caught and recorded.

        Present so the class cannot be read as "injection at this seam always
        works" — it did work, for everything except a ``BaseException``.
        """

        def exploded(_request: object) -> None:
            msg = "an ordinary failure"
            raise RuntimeError(msg)

        self._install(monkeypatch, exploded)
        root = _project(tmp_path)

        result = run_invocation(self._invocation(root))

        assert result.exit_code == 2
        assert result.recorded is True

    class _AnExitNobodyNamed(BaseException):
        """A ``BaseException`` that is none of the classes anybody wrote a clause for."""

    @pytest.mark.parametrize(
        ("label", "failure"),
        [
            ("SystemExit", lambda: SystemExit(7)),
            ("KeyboardInterrupt", KeyboardInterrupt),
            ("GeneratorExit", GeneratorExit),
            ("a BaseException nobody named", _AnExitNobodyNamed),
        ],
    )
    def test_every_baseexception_a_check_can_raise_becomes_a_verdict(
        self, tmp_path, monkeypatch, label, failure
    ) -> None:
        """Behaviour, not spelling: the last clause has to catch what nobody listed.

        Two named clauses give ``SystemExit`` and ``KeyboardInterrupt`` a reason
        a reader can act on; the last one exists so that the class nobody
        thought of is a verdict rather than an escape.
        """

        def fail(_request: object) -> None:
            raise failure()

        self._install(monkeypatch, fail)
        root = _project(tmp_path)

        result = _must_not_escape(lambda: run_invocation(self._invocation(root)))

        assert result.exit_code == 2, label
        assert result.recorded is True, label
        assert result.verdict.why, label

    def test_the_last_handler_is_baseexception_so_nothing_can_be_left_out(self) -> None:
        """Read off the source: the clause order, and that the last one is the widest."""
        tree = ast.parse(_BOUNDARY_MODULE.read_text(encoding="utf-8"))
        answer = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_answer"
        )
        try_block = next(node for node in ast.walk(answer) if isinstance(node, ast.Try))
        handled = [
            handler.type.id
            for handler in try_block.handlers
            if isinstance(handler.type, ast.Name)
        ]

        assert handled[-1] == "BaseException", handled
        assert set(handled) == {"SystemExit", "KeyboardInterrupt", "BaseException"}

    def test_an_interrupt_while_the_record_is_written_still_reaches_the_reader(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        """``_record``'s handler is as wide as ``_answer``'s — the asymmetry ``.30`` named."""
        from beadloom.application.guards import invocation as boundary

        def interrupted(*_args: object, **_kwargs: object) -> Path:
            raise KeyboardInterrupt

        monkeypatch.setattr(boundary, "record_firing", interrupted)
        root = _project(tmp_path)

        result = _must_not_escape(
            lambda: _cli(["guard", "bead-claimed", "--project", str(root)])
        )

        assert result.exit_code == 2, result.output
        assert "not recorded" in result.output, result.output

    def test_through_real_click_dispatch_an_interrupt_blocks_and_leaves_a_record(
        self, tmp_path
    ) -> None:
        """Measured, not reasoned: rc 2, a verdict, a record — and no "Aborted!".

        Seam (rule 4): the interrupt is injected at the probe seam and the
        harness is Click's own ``main()`` in a real subprocess — that is the
        dispatch the console script uses, and it is where ``KeyboardInterrupt``
        used to become ``Abort`` and then exit 1.
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

        assert completed.returncode == 2, completed.stderr
        assert "Aborted!" not in completed.stderr
        assert "bead-claimed: ERROR" in completed.stderr, completed.stderr
        assert [record.outcome for record in read_firings(root)] == ["error"]


# ==========================================================================
# 2. CLOSED — the pin is now as wide as the invariant it is about
# ==========================================================================


#: ``(label, body, catchable)`` — constructs that end a process, each MEASURED
#: below rather than asserted. ``catchable`` says whether an ``except
#: BaseException`` around the construct sees it, which is the difference between
#: a terminator the boundary's own handler converts into a verdict and one that
#: nothing above it can convert into anything.
#:
#: Left out of the measured rows, and recognised on the same footing: ``os.abort``
#: (documented as "generate a SIGABRT signal to the current process" — the
#: measured ``os.kill`` row's mechanism) and the ``os.exec*`` family (which
#: replace the process image). They are omitted only because SIGABRT writes a
#: crash report on every run of the suite, which is a cost the measurement does
#: not repay.
_TERMINATORS = (
    ("sys.exit", "import sys\n\nsys.exit(0)\n", True),
    ("a bare raise SystemExit", "raise SystemExit\n", True),
    ("raise SystemExit(1)", "raise SystemExit(1)\n", True),
    ("the exit builtin", "exit(0)\n", True),
    ("the quit builtin", "quit(0)\n", True),
    ("click.Abort", "import click\n\nraise click.Abort()\n", True),
    ("os._exit", "import os\n\nos._exit(0)\n", False),
    (
        "os.kill on this process",
        "import os\nimport signal\n\nos.kill(os.getpid(), signal.SIGTERM)\n",
        False,
    ),
    (
        "signal.raise_signal",
        "import signal\n\nsignal.raise_signal(signal.SIGTERM)\n",
        False,
    ),
)

#: ``.30``'s finding B2, verbatim: the exact edit that shipped 628/628 green.
_B2_SABOTAGE = (
    "    return _record(_answer(invocation))",
    '    if invocation.name == "":\n        sys.exit(0)\n'
    "    return _record(_answer(invocation))",
)


def _run(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        check=False,
    )


def _retired_click_path_pin(source: str) -> list[list[str]]:
    """The pin ``.3`` retired: the keywords of every call spelling ``click.Path``.

    Kept only as the thing the sabotage below is measured against — a retired
    pin that nobody can run is a claim about a pin, not a measurement of one.
    """
    return [
        [keyword.arg or "**" for keyword in node.keywords]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "click.Path"
    ]


def _sabotaged(module: Path, anchor: str, replacement: str) -> ast.Module:
    """*module*'s real source with one edit applied, parsed — never written to disk."""
    source = module.read_text(encoding="utf-8")
    assert source.count(anchor) == 1, anchor
    return ast.parse(source.replace(anchor, replacement))


class TestControlLeavesTheBoundaryPathInExactlyOnePlace:
    """Evidence that the pin bites, and the measurements the pin is built on.

    The pin itself lives in ``test_guards_invocation.py`` (section 2). What is
    here is the part a pin cannot assert about itself: that every construct it
    flags really does end a process, and that the two sabotages ``.30`` walked
    past are now seen.
    """

    @pytest.mark.parametrize(
        ("label", "body", "catchable"), _TERMINATORS, ids=[row[0] for row in _TERMINATORS]
    )
    def test_a_process_does_not_continue_past_any_of_them(
        self, label, body, catchable
    ) -> None:
        """The table is measured, so it is a fact about behaviour and not a name list."""
        completed = _run(body + 'print("SURVIVED")\n')

        assert "SURVIVED" not in completed.stdout, f"{label}: {completed.stdout}"

    @pytest.mark.parametrize(
        ("label", "body", "catchable"), _TERMINATORS, ids=[row[0] for row in _TERMINATORS]
    )
    def test_the_uncatchable_ones_end_it_from_inside_a_handler_too(
        self, label, body, catchable
    ) -> None:
        """The distinction the boundary turns on, measured rather than assumed.

        A catchable terminator inside ``_answer``'s ``try`` becomes a verdict;
        an uncatchable one ends the process wherever it stands, which is why the
        structural pin has to see both.
        """
        guarded = (
            "try:\n"
            + textwrap.indent(body, "    ")
            + 'except BaseException:\n    print("CAUGHT")\nprint("SURVIVED")\n'
        )

        completed = _run(guarded)

        assert ("CAUGHT" in completed.stdout) is catchable, f"{label}: {completed.stdout}"
        if not catchable:
            assert "SURVIVED" not in completed.stdout, label

    @pytest.mark.parametrize(
        ("label", "body", "catchable"), _TERMINATORS, ids=[row[0] for row in _TERMINATORS]
    )
    def test_the_pin_sees_every_terminator_the_table_measures(
        self, label, body, catchable
    ) -> None:
        """One ordinary exit plus one of these: the pin counts two, not one.

        ``.29``'s predicate counted calls *named* ``exit`` written as a call, so
        it counted one here for every row but the first — four of these are the
        spellings ``.30`` measured it blind to.
        """
        source = (
            "import sys\n\n\ndef go():\n    sys.exit(0)\n\n\ndef bail():\n"
            + textwrap.indent(body, "    ")
        )

        assert len(process_terminators(ast.parse(source))) == 2, label

    def test_a_terminator_inside_the_boundary_module_is_seen(self) -> None:
        """``.30``'s B2 edit, applied to the real source in memory and scanned.

        Measured there: one return, one ``record_firing`` call site and one
        ``x.exit`` in ``guard.py`` all preserved, 628/628 green, and
        ``beadloom guard ""`` exiting 0 recording nothing.
        """
        sabotaged = _sabotaged(_BOUNDARY_MODULE, *_B2_SABOTAGE)

        assert process_terminators(ast.parse(_BOUNDARY_MODULE.read_text())) == []
        assert process_terminators(sabotaged) == ["sys.exit(0)"]

    def test_a_terminator_in_any_other_module_on_the_path_is_seen(self) -> None:
        """Not only the boundary: discovery is on the path, and so is every sibling."""
        sabotaged = _sabotaged(
            _DISCOVERY_MODULE,
            "    if declared is not None:",
            "    if declared is not None:\n        os._exit(3)",
        )

        assert process_terminators(sabotaged) == ["os._exit(3)"]

    def test_every_module_of_the_package_is_scanned_not_only_the_three_named(
        self,
    ) -> None:
        """A listed scope is what ``.30`` walked past; this one is derived."""
        scope = boundary_path_modules()

        assert _BOUNDARY_MODULE in scope
        assert _DISCOVERY_MODULE in scope
        assert _SRC / "application" / "guards" / "firing.py" in scope
        assert terminators_on_the_boundary_path() == [THE_ONE_WAY_OUT]

    def test_the_retired_pin_is_blind_to_the_validator_a_later_option_would_use(
        self,
    ) -> None:
        """``.3``'s N2, made a test rather than a memory (BDL-061.32).

        Two pins have now been retired here. ``"exists=True" not in source``
        fell to ``dir_okay=False`` (``.30``, B5); the allowlist over
        ``click.Path`` keywords that replaced it falls to anything that is not a
        ``click.Path`` — and ``--work-kind`` as a ``click.Choice`` is the option
        S2/S3 will plausibly write, strictness being per work kind already. The
        sabotage below is that option, added to the real command source: the
        retired pin reads the file and finds it unchanged, because a
        ``click.Choice`` is not a ``click.Path`` call and carries no keyword for
        an allowlist to see. What replaced it does not ask what the constructor
        is called; it asks whether the conversion can refuse an argv string.

        A keyword allowlist has a second blindness, and it is the one that cost
        something: it can only see keywords somebody TYPED. ``click.Path``
        defaults ``readable=True``, so the shipped ``--project`` refused an
        unreadable directory in Click, before the callback — under a pin that
        read ``[["path_type"]]`` and was satisfied (BDL-061.32).
        """
        sabotaged = _sabotaged(
            _COMMAND_MODULE,
            '@click.option("--json", "output_json", is_flag=True',
            '@click.option("--work-kind", type=click.Choice(["feature", "bugfix"]))\n'
            '@click.option("--json", "output_json", is_flag=True',
        )
        work_kind = click.Option(["--work-kind"], type=click.Choice(["feature", "bugfix"]))
        command = click.Command(
            "guard", params=[work_kind], callback=lambda **_: None
        )

        assert _retired_click_path_pin(ast.unparse(sabotaged)) == _retired_click_path_pin(
            _COMMAND_MODULE.read_text(encoding="utf-8")
        )
        assert declared_conversion(work_kind) == "Choice(['feature', 'bugfix'])"
        assert declared_conversion(work_kind) not in declared_conversions().values()
        assert click_refuses(command, work_kind, "epci") is not None

    def test_the_one_writer_pin_reads_the_whole_source_tree(self) -> None:
        """``.30``, B4: a ``record_firing`` elsewhere in ``services/`` was not counted."""
        sites = record_firing_sites()

        assert sites == [
            (
                "application/guards/invocation.py",
                "record_firing(result.project_root, result.verdict)",
            )
        ], sites


# ==========================================================================
# 3. CLOSED — --project must name a project
# ==========================================================================


#: Every way the root a guard writes into can be chosen. The honesty note that
#: failed three times in this slice — "the guard manufactures no root" — is
#: quantified over this table instead of being asserted about the walk alone,
#: because it was true of the walk and false through the flag every time.
_WAYS_A_ROOT_IS_NAMED = (
    ("discovery from a directory inside the project", "inside", 2),
    ("discovery from a directory that is not in a project", "outside", 2),
    ("--project naming the project", "declared-project", 2),
    ("--project naming a directory that is not a project", "declared-plain", 2),
    ("--project naming a subdirectory of the project", "declared-subdir", 2),
    ("--project naming a directory that does not exist", "declared-missing", 2),
    ("--project naming a file", "declared-file", 2),
)


class TestADeclaredProjectMustBeAProject:
    """``project_root.py``: "it does not create ``.beadloom/`` where it stands".

    That was true of discovery and false through ``--project``: an existing
    directory that was not a Beadloom project was honoured verbatim, no
    ``flow.yml`` was found, the project's declared ``block`` became the shipped
    default ``warn``, and the firing record manufactured ``.beadloom/`` there —
    the coordinator's measured F9 failure, reachable through an explicit flag.
    ``.28`` filed it as minor ``m3``; ``.29``'s residual list did not name it.
    """

    def _roots(self, tmp_path: Path, kind: str) -> tuple[Path, list[str]]:
        """``(cwd-ish start, argv tail)`` for one row of the table above."""
        project = _project(tmp_path / "project")
        plain = tmp_path / "plain"
        plain.mkdir()
        (tmp_path / "a-file").write_text("x", encoding="utf-8")
        subdir = project / "src"
        subdir.mkdir()
        choices = {
            "inside": (subdir, []),
            "outside": (plain, []),
            "declared-project": (plain, ["--project", str(project)]),
            "declared-plain": (plain, ["--project", str(plain)]),
            "declared-subdir": (plain, ["--project", str(subdir)]),
            "declared-missing": (plain, ["--project", str(tmp_path / "nowhere")]),
            "declared-file": (plain, ["--project", str(tmp_path / "a-file")]),
        }
        return choices[kind]

    @pytest.mark.parametrize(
        ("label", "kind", "exit_code"),
        _WAYS_A_ROOT_IS_NAMED,
        ids=[row[0] for row in _WAYS_A_ROOT_IS_NAMED],
    )
    def test_no_way_of_naming_a_root_manufactures_one(
        self, tmp_path, monkeypatch, stub_probes, label, kind, exit_code
    ) -> None:
        """The claim, quantified over every way the root is chosen — not over one.

        Every row blocks at exit 2 (the guard is declared blocking, and where no
        project can be located "I could not tell" blocks too), and no directory
        that did not already carry the marker acquires one.
        """
        start, tail = self._roots(tmp_path, kind)
        monkeypatch.chdir(start)

        result = _cli(["guard", "bead-claimed", "--context", "path=app.py", *tail])

        assert result.exit_code == exit_code, f"{label}: {result.output}"
        marked = {
            path.parent
            for path in tmp_path.rglob(".beadloom")
            if path.is_dir()
        }
        assert marked == {tmp_path / "project"}, f"{label}: {marked}"

    def test_a_declared_directory_without_the_marker_is_refused_by_name(
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

        assert result.exit_code == 2, result.output
        assert "not a Beadloom project" in result.output, result.output
        assert not (not_a_project / FIRINGS_RELPATH).exists()

    def test_the_declared_strictness_cannot_be_traded_for_the_default(
        self, tmp_path, stub_probes
    ) -> None:
        """Same argv, same edit, two roots — and the wrong one no longer answers."""
        real = _project(tmp_path / "real")
        not_a_project = tmp_path / "elsewhere"
        not_a_project.mkdir()
        argv = ["guard", "bead-claimed", "--context", "path=app.py", "--json"]

        blocked = _cli([*argv, "--project", str(real)])
        wandered = _cli([*argv, "--project", str(not_a_project)])

        assert blocked.exit_code == 2, blocked.output
        assert json.loads(blocked.output)["outcome"] == "block"
        assert wandered.exit_code == 2, wandered.output
        assert json.loads(wandered.output)["outcome"] == "error"

    def test_the_module_says_what_the_code_does_about_manufacturing_a_root(
        self,
    ) -> None:
        """The honesty note, pinned to the behaviour it describes.

        An understating honesty note has been the finding three times in this
        slice. The sentence is read out of the source here so that a future
        round that re-widens ``--project`` has to edit a paragraph that a test
        is holding.
        """
        prose = " ".join(_DISCOVERY_MODULE.read_text(encoding="utf-8").split())

        assert "What is deliberately NOT done: manufacturing a root" in prose
        assert "by ANY route, **including through ``--project``**" in prose
        assert "it does not create one where it was pointed" in prose

    def test_the_spec_names_the_marker_requirement_in_its_residual_list(self) -> None:
        """The list ``.29`` left this out of, now carrying it."""
        spec = _SPEC.read_text(encoding="utf-8")

        assert "--project" in spec
        assert "must carry" in spec


# ==========================================================================
# 4. CLOSED — the rows this round added are enumerated
# ==========================================================================


#: Labels BDL-061.30 derived from the code that ``.29``'s 16-row table lacked.
_ROWS_ADDED_THIS_ROUND = (
    "an empty guard name",
    "a --project that is not a project",
    "a hook payload of zero bytes",
    "a --context key supplied twice",
    "an interrupt during the evaluation",
)


class TestTheRowsThisRoundAddedAreNowEnumerated:
    """The diff between ``.30``'s independent enumeration and the shipped table.

    A table that enumerates itself proves nothing, so these rows were derived
    from the code and the CLI surface first and compared afterwards. Four are
    argv-reachable and are now rows of ``_EXIT_PATHS``; the fifth is injected
    and is a row of ``_INJECTED_FAILURES``.
    """

    def test_every_added_row_is_present_in_a_shipped_enumeration(self) -> None:
        """The comparison, machine-checked rather than asserted in prose."""
        from tests.test_guards_invocation import _EXIT_PATHS, _INJECTED_FAILURES

        shipped = {row[0] for row in _EXIT_PATHS} | {row[0] for row in _INJECTED_FAILURES}

        assert set(_ROWS_ADDED_THIS_ROUND) <= shipped, (
            set(_ROWS_ADDED_THIS_ROUND) - shipped
        )

    def test_an_empty_guard_name_is_reported_as_the_name_the_caller_typed(
        self, tmp_path, stub_probes
    ) -> None:
        """``name or UNNAMED_GUARD`` swallowed ``""`` and quoted a guard nobody typed."""
        root = _project(tmp_path)

        result = _cli(["guard", "", "--project", str(root), "--json"])

        assert result.exit_code == 3, result.output
        assert json.loads(result.output)["guard"] == ""
        assert "''" in json.loads(result.output)["not_recorded_because"]
        assert read_firings(root) == ()

    def test_a_hook_payload_of_zero_bytes_is_an_ordinary_evaluation(
        self, tmp_path, stub_probes
    ) -> None:
        """Empty stdin reads as ``{}``: no path, so the guard says what it did not check."""
        root = _project(tmp_path)

        result = _cli(
            ["guard", "bead-claimed", "--project", str(root), "--hook", "claude-code"],
            stdin="",
        )

        assert "Traceback" not in result.output
        assert len(read_firings(root)) == 1

    def test_a_context_key_supplied_twice_takes_the_last_and_the_spec_says_so(
        self, tmp_path, stub_probes
    ) -> None:
        """Last-wins was an unstated rule. It is stated now, and read back here."""
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
        assert "the last occurrence wins" in _SPEC.read_text(encoding="utf-8")

    def test_a_closed_standard_input_states_a_cause_instead_of_an_internal_repr(
        self, tmp_path
    ) -> None:
        """``0<&-`` makes ``sys.stdin`` ``None``; the reason read as an ``AttributeError``.

        Fail-closed either way, but ``'NoneType' object has no attribute 'read'``
        is an internal repr where a stated cause belongs.

        Seam (rule 4): a real process with file descriptor 0 actually closed —
        ``CliRunner`` installs a stream of its own, and monkeypatching
        ``sys.stdin`` is undone by that installation, so neither can reproduce
        the condition CPython creates at interpreter start-up.
        """
        root = _project(tmp_path)
        argv = shlex.join(
            [
                sys.executable,
                "-c",
                "from beadloom.services.cli import main; main()",
                "guard",
                "bead-claimed",
                "--project",
                str(root),
                "--hook",
                "claude-code",
            ]
        )

        completed = subprocess.run(  # noqa: S603 — fixed argv, quoted, no shell expansion
            ["/bin/sh", "-c", f"exec {argv} 0<&-"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 2, completed.stderr
        assert "no standard input" in completed.stderr, completed.stderr
        assert "NoneType" not in completed.stderr
        assert "Traceback" not in completed.stderr


# ==========================================================================
# 5. CLOSED — the render step cannot choose the exit code
# ==========================================================================


class TestTheRenderStepCannotChangeTheVerdict:
    """``_emit`` runs after the boundary returns, so it is wrapped rather than trusted.

    ``.30`` attacked it and reported honestly that it could not reach a raising
    case: ``PYTHONIOENCODING=ascii`` does not break the hard-coded em-dash, a
    lone surrogate survives ``repr()`` and ``ensure_ascii``, a closed fd 1 does
    not raise, and the output is far under the pipe buffer. "Nobody could break
    it this round" is not a guarantee, so the claim is now a mechanism: the
    render is inside a ``try`` and the exit is outside it.
    """

    def _explode(self, monkeypatch, failure=RuntimeError) -> None:
        from beadloom.services.commands import guard as guard_cmd

        def raising(*_args: object, **_kwargs: object) -> None:
            raise failure("the verdict could not be printed")

        monkeypatch.setattr(guard_cmd, "_emit", raising)

    def test_a_failure_while_rendering_does_not_change_the_exit_code(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        root = _project(tmp_path)
        self._explode(monkeypatch)

        result = _cli(["guard", "bead-claimed", "--project", str(root), "--context", "path=a.py"])

        assert result.exit_code == 2, result.output

    def test_an_interrupt_while_rendering_does_not_change_it_either(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        root = _project(tmp_path)
        self._explode(monkeypatch, failure=lambda _message: KeyboardInterrupt())

        result = _must_not_escape(
            lambda: _cli(
                ["guard", "bead-claimed", "--project", str(root), "--context", "path=a.py"]
            )
        )

        assert result.exit_code == 2, result.output

    def test_a_failure_while_rendering_is_stated_rather_than_swallowed(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        root = _project(tmp_path)
        self._explode(monkeypatch)

        result = _cli(["guard", "bead-claimed", "--project", str(root), "--context", "path=a.py"])

        assert "could not be printed" in result.output, result.output

    def test_the_record_is_already_written_when_the_render_fails(
        self, tmp_path, monkeypatch, stub_probes
    ) -> None:
        """The recording step runs inside the boundary, so it precedes any of this."""
        root = _project(tmp_path)
        self._explode(monkeypatch)

        _cli(["guard", "bead-claimed", "--project", str(root), "--context", "path=a.py"])

        assert [record.outcome for record in read_firings(root)] == ["block"]
