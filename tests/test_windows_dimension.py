"""Every Windows claim this suite makes, and whether anything ever checks it.

BDL-061.39 wrote this file next to a ``tests-windows`` leg; beadloom-mr2l.64
withdrew that leg on a measured cost (~16-28 runner-minutes per PR, and the
pipeline's critical path — the reasoning is in ``.github/workflows/ci.yml``
where the job used to be). Nothing below depended on the leg except the one
prediction that was pinned for it to adjudicate, and that pin is now a
measurement — see :meth:`TestWhatPureWindowsPathSettlesWithoutAWindowsKernel.
test_the_guard_is_told_the_file_the_writer_will_touch`.

THE DEFECT THIS FILE EXISTS FOR. Six guard tests carried
``skipif(sys.platform == "win32", reason="POSIX symlink semantics")`` while CI
had no Windows leg. That is a skip that can never fail: on the platform it names
it does not run, and on every platform that runs it the mark is inert. It is the
same shape as the vacuous symlink-loop test BDL-061.36 repaired and the vacuous
``LC_ALL=C`` leg BDL-061.38 measured — a green that asserts nothing — and adding
a ``windows-latest`` leg WITHOUT touching those marks would have preserved it
exactly while buying a check-run that says "passed".

WHAT WAS ACTUALLY WRONG WITH THOSE SIX. The reason misnamed the obstacle.
Windows HAS symlinks and ``Path.resolve`` follows them; what a Windows process
may lack is the *privilege to create one* (``SeCreateSymbolicLinkPrivilege``,
granted by Developer Mode or an elevated shell). "POSIX symlink semantics" is a
statement about the operating system's model; the true statement is about this
process's capability, it is measurable at run time, and on a runner that has the
privilege the six tests RUN. So all six moved to
:mod:`tests.symlink_capability`, whose skip states a measured refusal instead of
a platform name.

WHAT THIS FILE LOCKS, so the class cannot come back:

1. :func:`test_no_win32_skip_is_unjudged` — a ledger. Any ``skipif`` in
   ``tests/`` that mentions ``sys.platform`` must appear in
   :data:`JUDGED_WINDOWS_SKIPS` naming the POSIX facility Windows does not have.
   There is no "convenience" verdict: a skip that could have been written
   platform-independently has no entry to hide in, so adding one fails the suite.

2. :func:`test_no_platform_xfail_waits_for_a_runner_that_will_not_come` — the
   other way to assert nothing, and the rule that had to move when the leg went.
   With a Windows leg, a platform prediction may be pinned as
   ``xfail(strict=True)`` and the runner adjudicates it. With no such leg the
   mark is inert on every runner, can never flip and is a pin nobody can close,
   so no platform prediction may be pinned on a mark at all: it is measured, or
   it is recorded as a residual.

3. The pure-path half of the Windows story, measured HERE rather than asserted
   in prose — see :class:`TestWhatPureWindowsPathSettlesWithoutAWindowsKernel`.
   ``PureWindowsPath`` implements Windows path *semantics* on every platform, so
   the claims ``paths.py``'s docstrings make about separators, drive letters and
   case can be checked on Linux. What it cannot settle is anything that calls
   the operating system — ``resolve``, ``fsencode``, the filesystem's own
   case-folding. Nothing buys that residue now: it is UNVERIFIED BY DECISION,
   which is a third state next to verified and known-broken, and the SPEC
   (``docs/domains/application/features/flow-guards/SPEC.md``) says so in those
   words rather than letting a green pipeline imply Windows support.
"""

from __future__ import annotations

import ast
import ntpath
import os
import posixpath
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from beadloom.application.guards import paths
from beadloom.application.guards.paths import (
    NATIVE_PATHS,
    POSIX_PATHS,
    RESERVED_DEVICE_NAMES,
    SEPARATOR_SPELLINGS,
    WINDOWS_PATHS,
    PathFlavour,
    PathScope,
    malformed_remediation,
    rejection_reason,
    resolve_edit_path,
)
from tests import symlink_capability
from tests.symlink_capability import (
    SYMLINK_CAPABILITY,
    SYMLINK_SKIP_REASON,
    SYMLINKS_UNAVAILABLE,
)

TESTS_DIR = Path(__file__).resolve().parent

#: The six rows BDL-061.36 item 3 was written about, by node id. Named
#: individually rather than counted: a count stays right while the rows are
#: replaced by different ones, and after beadloom-mr2l.64 withdrew the Windows
#: leg these six plus the ledger above them are the whole surviving deliverable
#: of BDL-061.39 — so what proves they RAN has to be as specific as they are.
#: (Five marks, six rows: one is parametrised over two targets.)
THE_SIX_CAPABILITY_GATED_ROWS = (
    "tests/test_guards_paths.py::TestTraversalCannotBypassAnExclusion::"
    "test_a_symlink_out_of_an_excluded_directory_is_guarded",
    "tests/test_guards_paths.py::TestSymlinksInBothDirections::"
    "test_a_link_into_the_excluded_tree_is_excluded",
    "tests/test_guards_paths.py::TestSymlinksInBothDirections::"
    "test_an_exclusion_stops_applying_when_its_directory_is_a_symlink",
    "tests/test_guards_paths.py::TestASymlinkLoopEndsInAVerdictAndNeverInATraceback::"
    "test_a_real_loop_comes_back_as_a_scope_whatever_this_platform_does[a]",
    "tests/test_guards_paths.py::TestASymlinkLoopEndsInAVerdictAndNeverInATraceback::"
    "test_a_real_loop_comes_back_as_a_scope_whatever_this_platform_does[a/x.py]",
    "tests/test_guards_paths.py::TestASymlinkLoopEndsInAVerdictAndNeverInATraceback::"
    "test_the_guard_reaches_a_verdict_through_a_real_loop",
)


@dataclass(frozen=True)
class WindowsSkip:
    """A skip that survives review: the facility is absent, not merely awkward."""

    #: The POSIX facility Windows does not provide, named specifically enough
    #: that a reader can check the claim.
    facility: str
    #: Why the behaviour under test cannot arise on Windows at all.
    why: str


#: Every ``skipif(... sys.platform ...)`` in ``tests/``, judged. The key is
#: ``<file>::<qualified name>``, where ``<module>`` means a module-level
#: ``pytestmark``. A skip with no entry here fails :func:`test_no_win32_skip_is_unjudged`.
JUDGED_WINDOWS_SKIPS: dict[str, WindowsSkip] = {
    "test_decoding_symmetry.py::<module>": WindowsSkip(
        facility="raw undecodable bytes in file names and git object headers",
        why=(
            "the fixtures write a 0xFF byte into names and commit metadata and "
            "replace PATH with a shebang stub; NTFS stores names as UTF-16 and "
            "cannot hold a lone byte, and Windows has no shebang mechanism, so "
            "the fixture cannot be built rather than the assertion being wrong"
        ),
    ),
    "test_guard_probes_encoding.py::<module>": WindowsSkip(
        facility="raw bytes in a git ref name and an executable shebang stub on PATH",
        why=(
            "same class: the probe seam is fed a branch name that is not valid "
            "UTF-8 and a `bd` replaced by a shebang script, neither of which a "
            "Windows process can be handed"
        ),
    ),
    "test_ci_locale_dimension.py::test_shipped_env_is_genuinely_non_utf8_on_linux": (
        WindowsSkip(
            facility="a filesystem encoding the interpreter is allowed to choose",
            why=(
                "not a Windows row — a darwin one, kept in the same ledger because "
                "it is the same question. CPython FORCES a UTF-8 filesystem "
                "encoding on macOS and Windows, so the assertion 'the shipped "
                "env is genuinely non-UTF-8' is false there BY DESIGN. It runs "
                "on every ubuntu leg of every PR (BDL-061.38), which is the "
                "opposite of a skip that can never fail"
            ),
        )
    ),
    "test_atomic_io_call_sites.py::TestEdgeCases::"
    "test_nonwritable_dir_raises_and_leaves_no_partial": WindowsSkip(
        facility="POSIX directory mode bits (`chmod 0o500` denying creation)",
        why=(
            "Windows derives directory writability from ACLs, not from the mode "
            "bits `Path.chmod` sets, so the unwritable directory the row needs "
            "cannot be created this way — the row would pass by not reproducing "
            "its own precondition. (The same row already fails as root in a "
            "container for the same reason; BDL-061.38 measured it.)"
        ),
    ),
}


@dataclass(frozen=True)
class _Marker:
    """One ``pytest.mark.<kind>`` call found in a test module."""

    key: str
    kind: str
    condition: str
    keywords: dict[str, str]


class _MarkerFinder(ast.NodeVisitor):
    """Collect ``pytest.mark.skipif`` / ``pytest.mark.xfail`` calls and where they sit."""

    def __init__(self, relative: str) -> None:
        self._relative = relative
        self._scope: list[str] = []
        self.markers: list[_Marker] = []

    def _visit_scope(self, node: ast.AST, name: str) -> None:
        self._scope.append(name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scope(node, node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_scope(node, node.name)

    def visit_Call(self, node: ast.Call) -> None:
        kind = _mark_kind(node.func)
        if kind in {"skipif", "xfail"}:
            condition = " ".join(ast.unparse(arg) for arg in node.args)
            keywords = {
                kw.arg: ast.unparse(kw.value) for kw in node.keywords if kw.arg
            }
            condition = " ".join([condition, keywords.get("condition", "")]).strip()
            self.markers.append(
                _Marker(
                    key=f"{self._relative}::{'::'.join(self._scope) or '<module>'}",
                    kind=kind,
                    condition=condition,
                    keywords=keywords,
                )
            )
        self.generic_visit(node)


def _mark_kind(func: ast.expr) -> str:
    """``pytest.mark.skipif`` -> ``"skipif"``; anything else -> ``""``."""
    if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Attribute):
        return ""
    if func.value.attr != "mark":
        return ""
    return func.attr


def _markers_mentioning_platform(kind: str) -> list[_Marker]:
    """Every *kind* marker in ``tests/`` whose condition reads ``sys.platform``.

    Parsed from the source rather than collected from pytest on purpose: a mark
    that is inert on this platform is invisible to collection, which is the very
    property that let six of them sit unexamined.
    """
    found: list[_Marker] = []
    for path in sorted(TESTS_DIR.rglob("*.py")):
        finder = _MarkerFinder(path.relative_to(TESTS_DIR).as_posix())
        finder.visit(ast.parse(path.read_text(encoding="utf-8")))
        found.extend(
            marker
            for marker in finder.markers
            if marker.kind == kind and "sys.platform" in marker.condition
        )
    return found


def _module_attributes_read(module: Path) -> set[str]:
    """Every ``<name>.<attr>`` the module's CODE reads, prose excluded.

    Read through :mod:`ast` rather than by searching the text, because the
    property is about what the module DOES and the module now explains what it
    deliberately does not do — a text search cannot tell an access from the
    sentence describing one, and would make the explanation itself a violation.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"))
    return {
        f"{node.value.id}.{node.attr}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    }


def test_no_win32_skip_is_unjudged() -> None:
    """Every platform skip names the facility Windows lacks, or it is not allowed.

    The ledger has no verdict meaning "this could run on Windows but nobody
    wanted to make it" — that state is what this bead removed, so re-entering it
    requires deleting an assertion rather than adding a line.
    """
    discovered = {marker.key for marker in _markers_mentioning_platform("skipif")}
    judged = set(JUDGED_WINDOWS_SKIPS)

    unjudged = discovered - judged
    stale = judged - discovered
    assert discovered == judged, (
        "a platform skip is not accounted for in JUDGED_WINDOWS_SKIPS.\n"
        f"  skipped on a platform with no judgement: {sorted(unjudged)}\n"
        f"  judged but no longer present:            {sorted(stale)}\n"
        "A skip that can never fail proves nothing; either state the POSIX "
        "facility Windows does not have, or make the test platform-independent."
    )


def test_no_platform_xfail_waits_for_a_runner_that_will_not_come() -> None:
    """A prediction is pinned on a mark only when something can adjudicate it.

    THE RULE MOVED, and it moved because the ground under it did. BDL-061.39
    wrote it as "a platform xfail must be ``strict=True``", which was right while
    a ``tests-windows`` leg was landing: strict turns an unexpected PASS into a
    suite failure, so the RUNNER decides whether the author's reasoning held. The
    owner withdrew that leg in ``beadloom-mr2l.64``, and a strict xfail with no
    runner behind it is worse than a lax one — it is inert on every leg, it can
    never flip, and it is therefore a pin nobody can close while looking exactly
    like an open question being tracked.

    So while this project runs on no Windows leg, a platform prediction is
    written as a MEASUREMENT or recorded as a residual, never as a mark. The two
    ways out are both real and both used in this file:
    ``PureWindowsPath``/``ntpath`` settle anything about how a path STRING is
    read (see :class:`TestWhatPureWindowsPathSettlesWithoutAWindowsKernel`), and
    what genuinely needs a kernel is stated as *unverified by decision* in
    ``docs/domains/application/features/flow-guards/SPEC.md``.
    """
    pinned = [marker.key for marker in _markers_mentioning_platform("xfail")]

    assert not pinned, (
        f"platform xfails nothing can adjudicate: {sorted(pinned)}.\n"
        "No leg of this pipeline runs a platform other than the one you are on "
        "(beadloom-mr2l.64 withdrew tests-windows on cost), so this mark is "
        "inert everywhere and cannot report being wrong. Measure the prediction "
        "with PureWindowsPath/ntpath where it is a question about path "
        "semantics, or write it down as a residual in the SPEC. If a platform "
        "leg is ever bought back, restore the earlier rule with it: the mark is "
        "then allowed and MUST carry strict=True."
    )


class TestTheScannerItselfBites:
    """The ledger is only a lock if the scan actually finds things."""

    def test_it_finds_a_module_level_pytestmark(self, tmp_path: Path) -> None:
        module = tmp_path / "test_sample.py"
        module.write_text(
            "import pytest, sys\n"
            'pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="x")\n',
            encoding="utf-8",
        )
        finder = _MarkerFinder("test_sample.py")
        finder.visit(ast.parse(module.read_text(encoding="utf-8")))

        assert [(m.key, m.kind) for m in finder.markers] == [
            ("test_sample.py::<module>", "skipif")
        ]

    def test_it_finds_a_mark_on_a_method_and_names_its_class(
        self, tmp_path: Path
    ) -> None:
        module = tmp_path / "test_sample.py"
        module.write_text(
            "import pytest, sys\n"
            "class TestThing:\n"
            '    @pytest.mark.skipif(sys.platform == "win32", reason="x")\n'
            "    def test_it(self):\n"
            "        pass\n",
            encoding="utf-8",
        )
        finder = _MarkerFinder("test_sample.py")
        finder.visit(ast.parse(module.read_text(encoding="utf-8")))

        assert [m.key for m in finder.markers] == ["test_sample.py::TestThing::test_it"]

    def test_a_condition_keyword_is_read_too(self, tmp_path: Path) -> None:
        """``skipif(condition=..., reason=...)`` is the same skip, spelled long."""
        module = tmp_path / "test_sample.py"
        module.write_text(
            "import pytest, sys\n"
            'pytestmark = pytest.mark.skipif(condition=sys.platform == "win32", reason="x")\n',
            encoding="utf-8",
        )
        finder = _MarkerFinder("test_sample.py")
        finder.visit(ast.parse(module.read_text(encoding="utf-8")))

        assert "sys.platform" in finder.markers[0].condition

    def test_an_unrelated_mark_is_not_collected(self, tmp_path: Path) -> None:
        module = tmp_path / "test_sample.py"
        module.write_text(
            "import pytest, sys\n"
            'pytestmark = pytest.mark.parametrize("x", [sys.platform])\n',
            encoding="utf-8",
        )
        finder = _MarkerFinder("test_sample.py")
        finder.visit(ast.parse(module.read_text(encoding="utf-8")))

        assert finder.markers == []

    def test_the_real_tests_directory_is_scanned_and_not_empty(self) -> None:
        """Guards the glob: a scan that finds nothing would pass the ledger vacuously."""
        assert _markers_mentioning_platform("skipif"), (
            "the scanner found no platform skips at all in tests/ — the ledger "
            "would then be satisfied by an empty set rather than by a judgement"
        )

    @pytest.mark.parametrize("strict", ["True", "False"])
    def test_a_platform_xfail_is_found_whether_or_not_it_is_strict(
        self, tmp_path: Path, strict: str
    ) -> None:
        """The one rule in this file whose real-tree population is EMPTY.

        ``test_no_platform_xfail_waits_for_a_runner_that_will_not_come`` asserts
        that nothing in ``tests/`` pins a platform prediction on a mark. That is
        true, and an assertion about an empty set is exactly the shape this whole
        family of beads exists to distrust: it passes identically when the scan
        is broken. So the scan is exercised here on a module that DOES carry the
        mark — both spellings, because ``strict=True`` is the one the withdrawn
        leg made legitimate and the one most likely to be re-added by hand.
        """
        module = tmp_path / "test_sample.py"
        module.write_text(
            "import pytest, sys\n"
            f'@pytest.mark.xfail(sys.platform == "win32", strict={strict}, reason="x")\n'
            "def test_it():\n"
            "    pass\n",
            encoding="utf-8",
        )
        finder = _MarkerFinder("test_sample.py")
        finder.visit(ast.parse(module.read_text(encoding="utf-8")))

        assert [(m.key, m.kind) for m in finder.markers] == [
            ("test_sample.py::test_it", "xfail")
        ]
        assert "sys.platform" in finder.markers[0].condition


class TestWhatPureWindowsPathSettlesWithoutAWindowsKernel:
    """Windows path SEMANTICS are importable; only the system calls need a runner.

    ``PureWindowsPath`` implements the whole of Windows path parsing — separators,
    drive letters, case-folding — on every platform, and on a real Windows build
    ``pathlib.Path`` *is* a ``PureWindowsPath`` subclass. So every claim this
    project makes about how a path STRING is read there can be checked here, and
    the residue that genuinely needs a kernel is small and nameable: ``resolve``
    (which calls the OS), ``os.fsencode`` (whose codec is the machine's), and the
    filesystem's own case-folding (a property of the volume, not of the parser).

    Everything in this class is bought for free, and every row of it was
    previously carried only in prose. The residue is bought by nobody: the
    ``tests-windows`` leg that would have measured it was withdrawn on cost
    (beadloom-mr2l.64), so it is stated as unverified by decision in the SPEC
    instead of being pinned on a mark that no runner can ever flip.
    """

    def test_a_backslash_is_a_separator_there_and_a_name_character_here(self) -> None:
        """The two halves of BACKSLASH_REJECTION's own sentence, measured.

        The refusal says a backslash "separates directories on the harness's
        platform and is an ordinary file-name character on this one". Both
        clauses are true — but they describe two DIFFERENT platforms, and the
        guard runs in the same process tree as the harness.
        """
        assert PureWindowsPath("src\\app.py").parts == ("src", "app.py")
        assert PurePosixPath("src\\app.py").parts == ("src\\app.py",)

    def test_the_shape_gate_accepts_the_spelling_a_windows_harness_produces(
        self, tmp_path: Path
    ) -> None:
        """CLOSED by beadloom-0mdo.33; this row is the finding turned round.

        It used to assert the defect: ``rejection_reason`` refused a backslash
        unconditionally, so on Windows it refused ``src\\app.py`` — the spelling
        a Windows harness natively produces and the one ``pathlib`` there reads
        correctly — which made every guarded edit there an ``error`` at exit 2
        with a remediation ("supply the target as a POSIX path") the harness
        cannot carry out.

        The rule is now over the separator rather than over the character, so
        the same string is refused where a backslash is an ordinary file-name
        character and accepted where it is a separator. Both halves are asserted
        here, on one machine, because the flavour is an argument: what the
        withdrawn ``tests-windows`` leg would have adjudicated (beadloom-mr2l.64)
        is decided by passing the platform in.
        """
        native_for_windows = ntpath.join("src", "app.py")

        assert native_for_windows == "src\\app.py"
        assert rejection_reason(native_for_windows, flavour=WINDOWS_PATHS) == ""
        assert rejection_reason(native_for_windows, flavour=POSIX_PATHS) != ""

        accepted = resolve_edit_path(
            native_for_windows, tmp_path, flavour=WINDOWS_PATHS
        )

        assert accepted.scope is not PathScope.MALFORMED, accepted
        # What the shape gate accepted names two components there, which is the
        # property the refusal was destroying. The RESOLUTION of it is this
        # machine's and is not a claim about Windows — see the SPEC's residual.
        assert PureWindowsPath(native_for_windows).parts == ("src", "app.py")

    def test_a_drive_letter_is_a_root_there_and_a_directory_name_here(self) -> None:
        """The SPEC's drive-letter paragraph is platform-conditional and says it is not.

        ``flow-guards/SPEC.md`` states that ``C:/Users/...`` "is read as a
        relative directory called ``C:``, because this build of Beadloom
        resolves paths with POSIX semantics". There is no such build property —
        it is the platform, and on Windows the same string is an ABSOLUTE path
        with a root. Filed with the backslash finding (beadloom-mr2l.60).
        """
        assert PurePosixPath("C:/Users/x/app.py").is_absolute() is False
        assert PureWindowsPath("C:/Users/x/app.py").is_absolute() is True

    def test_the_drive_letter_lands_inside_the_project_on_a_posix_build(
        self, tmp_path: Path
    ) -> None:
        """The consequence of the row above, asserted end to end on THIS platform.

        Because the string is relative here, it is joined onto the project root
        and reported as a project-relative directory literally named ``C:``.
        That is the documented answer and it had no test; on Windows the branch
        taken is the other one (absolute, hence ``OUTSIDE`` unless the project
        lives on that drive), which no assertion here can reach.
        """
        resolved = resolve_edit_path("C:/Users/x/app.py", tmp_path)

        assert resolved.scope is PathScope.INSIDE, resolved
        assert resolved.relative == "C:/Users/x/app.py", resolved

    def test_two_spellings_that_are_one_file_there_and_two_files_here(self) -> None:
        """BDL-061.36 item 4, on the axis it was never checked on.

        Exclusion patterns are matched against ``ResolvedEditPath.relative``, a
        string. The path PARSER folds case on Windows, so ``SRC/App.py`` and
        ``src/app.py`` are the same path object there and two different strings
        here — i.e. the same declared exclusion covers a different set of edits
        depending on the platform. (The FILESYSTEM's case-folding is a further,
        volume-dependent question this row deliberately does not touch: macOS is
        usually case-insensitive too, and no assertion here can settle it.)
        """
        assert PureWindowsPath("SRC/App.py") == PureWindowsPath("src/app.py")
        assert PurePosixPath("SRC/App.py") != PurePosixPath("src/app.py")

    def test_the_guard_is_told_the_file_the_writer_will_touch(
        self, tmp_path: Path
    ) -> None:
        """The property the shape gate exists to hold, in THIS platform's spelling.

        A harness names the file the way its own platform names files. The guard
        must end up pointing at that same file. Written with ``os.path.join``
        rather than a literal so the row means the same sentence everywhere and
        is red wherever the sentence is false.

        IT CARRIED A STRICT ``xfail(sys.platform == "win32")`` UNTIL
        beadloom-mr2l.64, and losing the mark is not the finding being dropped —
        it is the finding being upgraded. The mark existed so that a
        ``windows-latest`` runner would ADJUDICATE the prediction: an unexpected
        PASS there would have failed the suite and said the reasoning was wrong.
        The owner withdrew that leg on cost, and a strict xfail with no runner
        behind it can never flip in either direction — a pin nobody can close,
        which reads like a tracked question and is not one. The prediction is
        settled by measurement instead, in the two rows below and in the refusal
        row above: they are enough to compose the Windows verdict without a
        Windows kernel, and ``test_no_platform_xfail_waits_for_a_runner_that_
        will_not_come`` keeps the mark from coming back while no leg can judge it.
        """
        # ``str(Path(...))`` renders with THIS platform's separator — the whole
        # point of the row; a literal would hard-code one platform's answer.
        resolved = resolve_edit_path(str(Path("src", "app.py")), tmp_path)

        assert resolved.scope is PathScope.INSIDE, resolved
        assert resolved.relative == "src/app.py", resolved

    def test_the_module_that_refuses_names_no_platform(self) -> None:
        """The licence for measuring the other platform here, after the fix.

        Before beadloom-0mdo.33 this row said the module had NO platform
        dependence at all, and that was the whole trouble: one code path
        everywhere meant the backslash refusal fired on the platform where a
        backslash is the separator. The module is platform-dependent now, and
        the property that replaces "no dependence" is a narrower one — the
        dependence goes through what :mod:`os` DECLARES about this machine
        (``os.sep``, ``os.altsep``) and never through what the platform is
        CALLED. ``sys.platform`` and ``os.name`` are still absent, which is what
        keeps the flavour a value the suite can substitute rather than a branch
        only a Windows runner could enter.

        If a ``sys.platform`` branch is ever added here, every Windows row in
        this class stops being a measurement and becomes a prediction again,
        and this is the row that says so.
        """
        read = _module_attributes_read(Path(paths.__file__))

        assert "sys.platform" not in read
        assert "os.name" not in read
        assert "os.sep" in read

    def test_the_native_flavour_is_the_one_pathlib_itself_uses(self) -> None:
        """Two independent derivations of the same fact must agree.

        ``NATIVE_PATHS`` is chosen by ``os.sep``; ``pathlib`` chooses its own
        class by ``os.name``. If those ever disagreed, the guard would judge a
        name under one platform's rules and resolve it under another's — so the
        agreement is asserted rather than assumed, and it is the assertion that
        would bite on a runner this project does not have.
        """
        assert (NATIVE_PATHS is WINDOWS_PATHS) is isinstance(Path(), PureWindowsPath)
        assert NATIVE_PATHS.separators == {sep for sep in (os.sep, os.altsep) if sep}
        assert isinstance(Path(), NATIVE_PATHS.parser)

    @pytest.mark.parametrize(
        ("label", "raw", "flavour"),
        [
            ("a foreign separator", "src\\app.py", POSIX_PATHS),
            ("a trailing dot", "src/app.py.", WINDOWS_PATHS),
            ("a trailing space", "src/app.py ", WINDOWS_PATHS),
            ("a reserved device name", "docs/CON.md", WINDOWS_PATHS),
        ],
    )
    def test_every_platform_rule_is_decided_before_the_call_the_platform_owns(
        self,
        monkeypatch: pytest.MonkeyPatch,
        label: str,
        raw: str,
        flavour: PathFlavour,
    ) -> None:
        """The second half of the licence: every platform rule is lexical.

        ``rejection_reason`` ends with ``os.fsencode``, whose codec IS the
        machine's — the one line in the function whose behaviour a Windows
        kernel could change. Each rule that differs between the two flavours is
        decided before it, so the answer this class measures for a platform is
        the answer that platform would give. Asserted by making the call fail
        loudly if it is ever reached, rather than by reading the source and
        believing the order.

        Parametrised over all four rules rather than over the backslash alone:
        the row that only covered the backslash was true and stopped being
        enough the moment the name-layer rules were added, which is the shape of
        every finding in this slice.
        """

        def unreachable(_: str) -> bytes:
            raise AssertionError(
                f"os.fsencode was reached for {label}, so the rule is not "
                "purely lexical and the Windows verdicts measured in this class "
                "no longer follow from a run on this machine"
            )

        monkeypatch.setattr(paths.os, "fsencode", unreachable)

        assert rejection_reason(raw, flavour=flavour) != ""


class TestWhatTheNameLayerOwesOnWindows:
    """The rules the shape gate never asked for, and this bead's item 3.

    The Win32 name layer does not merely PARSE a name, it REWRITES one: it
    strips a trailing dot or space, and it resolves a reserved device name to a
    character device in whatever directory it appears. Each is exactly the
    condition ``paths.py`` exists for — the guard records one file and the
    writer touches another — and each is a stronger argument for a refusal than
    the backslash the module used to refuse instead.

    Every row runs on whatever machine collects it, by passing the platform in.
    What that cannot reach — whether the Win32 layer strips in the way this
    assumes, and what ``Path.resolve`` then does with the accepted name — is a
    residual in the SPEC, not a prediction here.
    """

    @pytest.mark.parametrize(
        ("label", "raw"),
        [
            ("a trailing dot on the file", "src/app.py."),
            ("a trailing space on the file", "src/app.py "),
            ("a trailing dot on a directory", "src./app.py"),
            ("a trailing space on a directory", "src /app.py"),
        ],
    )
    def test_a_name_the_layer_would_rewrite_is_refused_there_and_kept_here(
        self, tmp_path: Path, label: str, raw: str
    ) -> None:
        """Refused where the layer rewrites, accepted where nothing does.

        Both directions, because a rule applied on the wrong platform is the
        defect this bead is repairing: these are ordinary, legal names on a
        POSIX filesystem and refusing them there would be the same class of
        over-refusal one platform further on.
        """
        refused = resolve_edit_path(raw, tmp_path, flavour=WINDOWS_PATHS)

        assert refused.scope is PathScope.MALFORMED, f"{label}: {refused}"
        assert refused.relative is None, label
        assert "strips" in refused.rejection, refused.rejection

        kept = resolve_edit_path(raw, tmp_path, flavour=POSIX_PATHS)

        assert kept.scope is PathScope.INSIDE, f"{label}: {kept}"

    @pytest.mark.parametrize("device", sorted(RESERVED_DEVICE_NAMES))
    def test_every_reserved_device_name_is_refused_where_it_names_a_device(
        self, tmp_path: Path, device: str
    ) -> None:
        """Quantified over the declared set, not over three examples of it.

        A write to ``CON`` on Windows reaches the console and creates no file at
        all, so a guard that resolved it to a path under the project root would
        be reporting about a file nobody wrote. The extension does not save it —
        ``CON.md`` is the console too — and neither does the directory, which is
        why the rule looks at every component.
        """
        raw = f"docs/{device}.md"

        refused = resolve_edit_path(raw, tmp_path, flavour=WINDOWS_PATHS)

        assert refused.scope is PathScope.MALFORMED, refused
        assert "device" in refused.rejection, refused.rejection

        kept = resolve_edit_path(raw, tmp_path, flavour=POSIX_PATHS)

        assert kept.scope is PathScope.INSIDE, kept

    def test_the_device_name_is_matched_however_it_is_cased(
        self, tmp_path: Path
    ) -> None:
        """Win32 matches the device name case-insensitively, so the rule must.

        A rule that only caught ``CON`` would be a spelling again: ``con`` and
        ``Con`` reach the same device.
        """
        for spelling in ("con", "Con", "cOn"):
            refused = resolve_edit_path(
                f"docs/{spelling}", tmp_path, flavour=WINDOWS_PATHS
            )

            assert refused.scope is PathScope.MALFORMED, refused

    def test_a_name_that_merely_starts_with_a_device_name_is_not_refused(
        self, tmp_path: Path
    ) -> None:
        """The over-refusal direction, which is the one this bead is about.

        ``console.py`` and ``nullable.md`` are not devices. A rule written as a
        prefix test would refuse them, and a guard that refuses ordinary project
        files is exactly the failure the backslash rule produced on Windows.
        """
        for raw in ("src/console.py", "docs/nullable.md", "src/comms/app.py"):
            resolved = resolve_edit_path(raw, tmp_path, flavour=WINDOWS_PATHS)

            assert resolved.scope is PathScope.INSIDE, resolved

    def test_the_characters_win32_forbids_outright_are_deliberately_not_refused(
        self, tmp_path: Path
    ) -> None:
        """The stated boundary of the rule, asserted so it cannot drift into one.

        ``<>"|?*`` are illegal in a Win32 file name, and a write to such a name
        FAILS — loudly, with nothing created. The shape gate exists to stop the
        guard and the writer looking at different files, and a write that never
        happens produces no such disagreement, so refusing here would be the
        guard inventing a naming policy nobody declared. Stated in the module
        docstring and in the SPEC; pinned here so a later "while we are at it"
        has to change a test that says why.
        """
        for raw in ("src/a<b.py", "src/a?b.py", "src/a*b.py", 'src/a"b.py'):
            resolved = resolve_edit_path(raw, tmp_path, flavour=WINDOWS_PATHS)

            assert resolved.scope is PathScope.INSIDE, resolved


class TestTheRuleTheBackslashWasASpellingOf:
    """Item 2: the refusal is over the separator, not over one character.

    The old rule refused ``\\`` unconditionally and justified it with a sentence
    about "the harness's platform" and "this one" — two platforms, where the
    guard runs in the harness's own process tree and there is one. The rule is
    now: a separator spelling THIS platform does not read as a separator is
    refused, because the guard cannot tell whether such a target names one file
    or several. On a POSIX machine that is the same single character as before,
    which is why nothing about this project's own behaviour moves.
    """

    def test_the_refused_set_is_derived_from_the_platforms_own_declarations(
        self,
    ) -> None:
        """No spelling is authored: both flavours come from the stdlib's modules.

        A hand-written set is a spelling of the rule and would be wrong the same
        way the backslash was — right until the platform it describes is not the
        one running.
        """
        assert POSIX_PATHS.separators == {posixpath.sep}
        assert WINDOWS_PATHS.separators == {ntpath.sep, ntpath.altsep}
        assert sorted(SEPARATOR_SPELLINGS) == ["/", "\\"]
        assert SEPARATOR_SPELLINGS - WINDOWS_PATHS.separators == set()

    def test_a_mixed_spelling_is_legal_where_both_are_separators(
        self, tmp_path: Path
    ) -> None:
        """``src\\sub/app.py`` is one unambiguous path on Windows and was refused.

        The row beadloom-mr2l.60 named when it said to consider ``os.altsep``:
        the mixed form is what a Windows harness produces when a POSIX-spelled
        relative path is joined onto a native one, and there is nothing
        ambiguous about it there.
        """
        assert PureWindowsPath("src\\sub/app.py").parts == ("src", "sub", "app.py")

        accepted = resolve_edit_path("src\\sub/app.py", tmp_path, flavour=WINDOWS_PATHS)

        assert accepted.scope is not PathScope.MALFORMED, accepted

    def test_the_forward_slash_is_never_foreign_on_either_platform(
        self, tmp_path: Path
    ) -> None:
        """The rule cannot refuse the spelling every platform reads.

        Stated as its own row because it is the one way a rule quantified over a
        SET could be worse than the character it replaced: if a flavour ever
        declared ``/`` foreign, every ordinary target in this repository would be
        refused, on both platforms at once.
        """
        for flavour in (POSIX_PATHS, WINDOWS_PATHS, NATIVE_PATHS):
            resolved = resolve_edit_path("src/app.py", tmp_path, flavour=flavour)

            assert resolved.scope is PathScope.INSIDE, resolved

    def test_the_reason_no_longer_describes_two_platforms_at_once(self) -> None:
        """The half of the finding that is about the SENTENCE, not the verdict.

        beadloom-mr2l.60's real complaint: both clauses of the old reason were
        true and they were about different machines. The reason now names the
        platform the SPELLING comes from — which is a fact about the string —
        and this one, which is a fact about the process; those can differ
        without the sentence being false.
        """
        reason = rejection_reason("src\\app.py", flavour=POSIX_PATHS)

        assert "a backslash" in reason
        assert "the platform that spelling comes from" in reason
        assert "harness" not in reason

    def test_the_way_out_is_spelled_in_the_platforms_own_separators(self) -> None:
        """A remediation that names a platform is a way out only on that one.

        It read "supply the target as a POSIX path", which on Windows names
        something the harness there cannot produce — the finding one layer down
        from the refusal itself.
        """
        assert malformed_remediation(POSIX_PATHS).startswith(
            "supply the target as a path this platform spells literally ('/'"
        )
        assert "'/' or " + repr("\\") in malformed_remediation(WINDOWS_PATHS)
        assert "reserved device name" in malformed_remediation(WINDOWS_PATHS)
        assert "reserved device name" not in malformed_remediation(POSIX_PATHS)
        for flavour in (POSIX_PATHS, WINDOWS_PATHS):
            assert "POSIX" not in malformed_remediation(flavour)


class TestTheSymlinkCapabilityProbe:
    """The replacement for the six platform marks must itself be non-vacuous."""

    def test_a_refusal_is_recorded_exactly_when_something_refused(self) -> None:
        """The reason and the verdict cannot disagree.

        A probe that reported a refusal while claiming the capability (or the
        reverse) would produce a skip whose text contradicts its own condition,
        which is how an unread reason becomes an unexamined skip.
        """
        assert SYMLINK_CAPABILITY.both == (not SYMLINK_CAPABILITY.refusal)

    def test_this_machine_can_link_so_the_six_guard_rows_actually_run(self) -> None:
        """Stated as an assertion, not a comment: the rows are live where we test.

        If a future image cannot create symlinks this fails LOUDLY here instead
        of quietly skipping six guard tests elsewhere — the whole failure mode
        this bead is about.
        """
        assert SYMLINK_CAPABILITY.both, SYMLINK_CAPABILITY.refusal

    def test_a_refusal_is_reported_with_the_operating_system_s_own_words(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The Windows branch, on a machine that is not Windows.

        WinError 1314 ("A required privilege is not held by the client") is what
        a Windows process without ``SeCreateSymbolicLinkPrivilege`` gets. It is
        injected because this machine will never raise it, and the assertion is
        that the reason a reader sees carries the OS's text rather than a
        platform name.
        """

        def refuse(*args: object, **kwargs: object) -> None:
            raise OSError(1314, "A required privilege is not held by the client")

        monkeypatch.setattr(symlink_capability.os, "symlink", refuse)

        measured = symlink_capability._probe()

        assert measured.files is False
        assert measured.directories is False
        assert "required privilege is not held" in measured.refusal

    def test_a_link_that_lands_somewhere_else_is_not_a_capability(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A filesystem that "supports" links by copying is not what the rows need.

        The probe reads the link back instead of trusting that ``os.symlink``
        returned; without that, a container filesystem that silently degrades a
        link into a copy would report the capability and the six rows would run
        and assert the wrong thing.
        """
        real_symlink = symlink_capability.os.symlink

        def degrade(target: object, link: object, **kwargs: object) -> None:
            del target
            Path(str(link)).write_text("not a link\n", encoding="utf-8")

        monkeypatch.setattr(symlink_capability.os, "symlink", degrade)
        try:
            measured = symlink_capability._probe()
        finally:
            monkeypatch.setattr(symlink_capability.os, "symlink", real_symlink)

        assert measured.files is False
        assert "resolved to" in measured.refusal

    def test_the_skip_reason_names_a_measurement_and_not_a_platform(self) -> None:
        """Regression lock on the defect: "POSIX symlink semantics" is not a reason."""
        assert "could not create a symbolic link" in SYMLINK_SKIP_REASON
        assert "SeCreateSymbolicLinkPrivilege" in SYMLINK_SKIP_REASON

    def test_the_six_guard_rows_no_longer_carry_a_platform_mark(self) -> None:
        """The six, by name — so deleting the fix cannot pass silently.

        Named individually rather than counted: a count stays right while the
        rows are replaced by different ones, and these six are the specific
        tests BDL-061.36 item 3 was written about.
        """
        source = (TESTS_DIR / "test_guards_paths.py").read_text(encoding="utf-8")

        assert "sys.platform" not in source, (
            "test_guards_paths.py skips on a platform name again; the six "
            "symlink rows are capability-gated on purpose (BDL-061.39)"
        )
        assert source.count("skipif(SYMLINKS_UNAVAILABLE") == 5, (
            "the five capability marks (six collected rows — one is "
            "parametrised over two targets) are the six tests this bead un-skipped"
        )

    def test_the_skip_condition_is_the_measurement_and_not_a_value(self) -> None:
        """FOUND BY REVIEW `.15` (M7) AND MEASURED HERE BEFORE IT WAS FIXED.

        One line — ``SYMLINKS_UNAVAILABLE = True`` in place of
        ``not SYMLINK_CAPABILITY.both`` — put all six rows back into the state
        this family of beads exists to remove, and the suite did not notice:
        133 passed / 6 skipped / 0 failed, rc 0, with the reader told only
        "could not create a symbolic link ... no reason recorded". Every
        assertion in this class was about the CAPABILITY object; none was about
        the link between the capability and the condition the marks read, so the
        chain could be cut at exactly that joint.

        It matters more since beadloom-mr2l.64. With the Windows leg withdrawn,
        these six rows and the ledger are what is left of BDL-061.39, and a
        withdrawal that quietly took the value along with the cost is not the
        decision the owner made.
        """
        assert (not SYMLINK_CAPABILITY.both) == SYMLINKS_UNAVAILABLE, (
            "the six guard rows are skipped on something other than the "
            "measurement: SYMLINKS_UNAVAILABLE must BE `not "
            "SYMLINK_CAPABILITY.both` and nothing else, or the probe can answer "
            "'unavailable' everywhere while the suite stays green"
        )

    def test_the_six_rows_are_observed_to_run_rather_than_inferred_to(self) -> None:
        """The same guard again, and this time about the OUTCOME, not the wiring.

        The row above closes the one joint the review cut. This one does not
        care where the cut is: it runs the six by node id in a child pytest and
        reads what happened to them, so a constant condition, an edited mark, a
        module-level ``pytestmark``, a ``conftest`` that deselects them or a
        renamed row all redden it. That is the standard this epic converged on —
        a check that cannot fail is not a check — applied to the probe itself,
        which had until now been the one thing checking everything else.

        A machine that genuinely cannot create a symbolic link fails here rather
        than skipping six guard tests quietly elsewhere. That is deliberate and
        it is the same stance as
        ``test_this_machine_can_link_so_the_six_guard_rows_actually_run``: this
        project's own runners can link, so the honest report of an image that
        cannot is a red row that names the reason, not a green suite.
        """
        completed = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "pytest",
                *THE_SIX_CAPABILITY_GATED_ROWS,
                "-p",
                "no:randomly",
                "-q",
                "--no-header",
                "-rs",
                "--tb=line",
            ],
            capture_output=True,
            text=True,
            cwd=TESTS_DIR.parent,
            check=False,
        )
        report = completed.stdout + completed.stderr

        assert completed.returncode == 0, (
            "the six capability-gated guard rows did not all pass. A non-zero "
            "exit with no failure below usually means a node id no longer "
            f"exists — they are named, not counted, on purpose.\n{report}"
        )
        assert "skipped" not in report.lower(), (
            "at least one of the six was SKIPPED on a machine that can create "
            f"symbolic links, which is the defect BDL-061.39 removed.\n{report}"
        )
        assert f"{len(THE_SIX_CAPABILITY_GATED_ROWS)} passed" in report, report
