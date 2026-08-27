"""A subprocess that launches Python launches THIS Python (BDL-062.10, m6).

``["python", "-c", ...]`` resolves through ``PATH``. Inside the venv the suite
normally runs in that is the right interpreter by accident, and the accident is
the whole problem: the release process verifies in a **clean room**, and a clean
room whose venv is not on ``PATH`` gets a different interpreter or none at all.
The two sites this sweep was written for failed there with ``FileNotFoundError``
and ``print('hi')`` — a red that says nothing about the code under test, in the
one room whose greenness the release depends on. ``sys.executable`` is the
interpreter running the test, so it is correct in every room by construction.

This is the source-level instrument, deliberately not an environment one: it
fails the day a new call site is written, needs no clean room to run, and cannot
be satisfied by a machine that happens to have ``python`` on ``PATH``.

``SUBPROCESS_CALLS`` and ``called_name`` come from :mod:`tests.decoding_calls`
rather than being restated here. The question that module asks is about codecs
and this one is about ``PATH``, but "which callables spawn a process" is a
single fact, and that module's own docstring records what happens when one fact
is told twice.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from tests.decoding_calls import SUBPROCESS_CALLS, called_name

_REPO_ROOT = Path(__file__).resolve().parent.parent

#: Roots that ship or verify this package. Both are swept: a PATH-sensitive
#: launch in ``tests/`` reddens the clean room, and one in ``src/`` reddens an
#: adopter's machine.
_SWEPT_ROOTS = (_REPO_ROOT / "src" / "beadloom", _REPO_ROOT / "tests")

#: The wrapper this package spawns processes through, alongside ``subprocess``.
#: Omitting it is how the two original sites hid from a ``subprocess``-only grep.
_SPAWNING_CALLS = SUBPROCESS_CALLS | {"run_command"}

#: Names that mean "some Python interpreter, whichever PATH finds first".
_BARE_INTERPRETERS = frozenset({"python", "python3", "py", "python2"})

#: Sites that genuinely want PATH's interpreter rather than this one, each with
#: its reason. Empty on purpose: every launch below is either a helper this
#: suite drives or a tool this package invokes on the user's behalf, and neither
#: wants a different Python from the one already running. An entry is how a
#: future exception becomes visible instead of silent.
_PATH_INTERPRETER_BY_DESIGN: dict[tuple[str, int], str] = {}


def _argv_head(call: ast.Call) -> str | None:
    """The literal first element of the call's argv, or ``None`` when dynamic.

    A dynamic head (``[exe, ...]``, ``[*args]``) is out of this sweep's reach by
    construction, so it is reported as unknown rather than guessed at — see
    :func:`test_the_sweep_reports_a_dynamic_argv_as_unknown`.
    """
    if not call.args:
        return None
    argv = call.args[0]
    if isinstance(argv, (ast.List, ast.Tuple)):
        if not argv.elts:
            return None
        head = argv.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
        return None
    if isinstance(argv, ast.Constant) and isinstance(argv.value, str):
        return argv.value.split()[0] if argv.value.split() else None
    return None


def _interpreter_launch_sites() -> list[tuple[str, int, str]]:
    """Every spawn in the swept roots that names an interpreter PATH resolves."""
    sites: list[tuple[str, int, str]] = []
    for root in _SWEPT_ROOTS:
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            rel = str(path.relative_to(_REPO_ROOT))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or called_name(node) not in _SPAWNING_CALLS:
                    continue
                head = _argv_head(node)
                if head in _BARE_INTERPRETERS:
                    sites.append((rel, node.lineno, str(head)))
    return [s for s in sites if (s[0], s[1]) not in _PATH_INTERPRETER_BY_DESIGN]


class TestEveryInterpreterLaunchNamesThisInterpreter:
    """The source-level sweep, plus the two checks that keep it from lying."""

    def test_no_call_site_launches_an_interpreter_off_the_path(self) -> None:
        sites = _interpreter_launch_sites()
        rendered = "\n".join(f"  {p}:{line} argv[0]={head!r}" for p, line, head in sites)
        assert not sites, (
            "a subprocess launches whatever interpreter PATH resolves, so this "
            "call fails in a clean room whose venv is not on PATH for a reason "
            f"unrelated to what it tests — use sys.executable:\n{rendered}"
        )

    def test_the_sweep_can_actually_see_a_bare_launch(self) -> None:
        """Not vacuous: the walk still recognises the shape it rejects."""
        planted = ast.parse("subprocess.run(['python', '-c', 'pass'])")
        calls = [n for n in ast.walk(planted) if isinstance(n, ast.Call)]
        spawns = [c for c in calls if called_name(c) in _SPAWNING_CALLS]
        assert spawns, "the AST walk no longer recognises a subprocess.run() call"
        assert _argv_head(spawns[0]) in _BARE_INTERPRETERS

    def test_the_sweep_accepts_sys_executable(self) -> None:
        """The corrected shape passes, so the sweep is not rejecting everything."""
        planted = ast.parse("subprocess.run([sys.executable, '-c', 'pass'])")
        spawn = next(n for n in ast.walk(planted) if isinstance(n, ast.Call))
        assert _argv_head(spawn) is None

    def test_the_sweep_reports_a_dynamic_argv_as_unknown(self) -> None:
        """A computed argv is out of reach, and the sweep says so by returning None."""
        planted = ast.parse("subprocess.run([exe, 'ctx'])")
        spawn = next(n for n in ast.walk(planted) if isinstance(n, ast.Call))
        assert _argv_head(spawn) is None

    def test_the_sweep_reaches_both_roots(self) -> None:
        """A denominator, so a sweep that silently scanned nothing cannot read green."""
        scanned = {root: len(list(root.rglob("*.py"))) for root in _SWEPT_ROOTS}
        assert all(count > 0 for count in scanned.values()), scanned


def test_this_interpreter_is_not_necessarily_the_one_on_the_path() -> None:
    """The premise, measured rather than asserted from the docstring.

    If ``sys.executable`` and PATH's ``python`` were always the same file, the
    sweep above would be ceremony. They are the same only when the venv is
    active, which is exactly the condition a clean room removes — so this test
    states the fact it can check on any machine: the interpreter has an absolute
    path of its own, which ``"python"`` does not carry.
    """
    assert Path(sys.executable).is_absolute()
    assert Path(sys.executable).exists()
