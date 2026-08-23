"""Every Windows claim this suite makes, and whether anything ever checks it (BDL-061.39).

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

2. :func:`test_a_win32_xfail_is_always_strict` — the other way to assert
   nothing. A non-strict ``xfail`` passes whether the prediction holds or not;
   ``strict=True`` turns an unexpected PASS into a failure, which is what makes
   a prediction about Windows adjudicable by the runner rather than by the
   author.

3. The pure-path half of the Windows story, measured HERE rather than asserted
   in prose — see :class:`TestWhatPureWindowsPathSettlesWithoutAWindowsKernel`.
   ``PureWindowsPath`` implements Windows path *semantics* on every platform, so
   the claims ``paths.py``'s docstrings make about separators, drive letters and
   case can be checked on Linux. What it cannot settle is anything that calls
   the operating system — ``resolve``, ``fsencode``, the filesystem's own
   case-folding — and that residue is precisely what the ``tests-windows`` leg
   buys.
"""

from __future__ import annotations

import ast
import ntpath
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from beadloom.application.guards.paths import (
    BACKSLASH_REJECTION,
    PathScope,
    rejection_reason,
    resolve_edit_path,
)
from tests import symlink_capability
from tests.symlink_capability import SYMLINK_CAPABILITY, SYMLINK_SKIP_REASON

TESTS_DIR = Path(__file__).resolve().parent


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


def test_a_win32_xfail_is_always_strict() -> None:
    """A prediction about Windows must be adjudicable by the Windows runner.

    ``xfail(strict=False)`` passes whether the prediction holds or not, so it is
    the skip's failure mode wearing a different word. ``strict=True`` makes an
    unexpected PASS a suite failure — i.e. the runner, not the author, decides
    whether the reasoning was right.
    """
    lax = [
        marker.key
        for marker in _markers_mentioning_platform("xfail")
        if marker.keywords.get("strict") != "True"
    ]
    assert not lax, (
        f"platform xfails that cannot report being wrong: {sorted(lax)}. "
        "Add strict=True so an unexpected pass on that platform fails the suite."
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


class TestWhatPureWindowsPathSettlesWithoutAWindowsKernel:
    """Windows path SEMANTICS are importable; only the system calls need a runner.

    ``PureWindowsPath`` implements the whole of Windows path parsing — separators,
    drive letters, case-folding — on every platform, and on a real Windows build
    ``pathlib.Path`` *is* a ``PureWindowsPath`` subclass. So every claim this
    project makes about how a path STRING is read there can be checked here, and
    the residue that genuinely needs a kernel is small and nameable: ``resolve``
    (which calls the OS), ``os.fsencode`` (whose codec is the machine's), and the
    filesystem's own case-folding (a property of the volume, not of the parser).

    That residue is exactly what the ``tests-windows`` leg buys. Everything in
    this class is bought for free, and every row of it was previously carried
    only in prose.
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

    def test_the_shape_gate_refuses_the_spelling_a_windows_harness_produces(
        self,
    ) -> None:
        """FINDING, pinned rather than fixed — filed as beadloom-mr2l.60.

        ``rejection_reason`` refuses a backslash unconditionally, so on Windows
        it refuses ``src\\app.py`` — the spelling a Windows harness natively
        produces and the one ``pathlib`` there reads correctly. The guard is
        fail-CLOSED (an ``error`` verdict at exit 2, not a bypass), but every
        edit on a Windows machine would be refused, and the stated remediation
        ("supply the target as a POSIX path") is not something the harness can
        do. The refusal's own justification — that the guard and the writer
        "would not be looking at the same file" — is the reverse of true there:
        it is the REFUSAL that stops them looking at the same file.

        Not fixed in BDL-061.39 ON PURPOSE. Relaxing the rule where
        ``os.sep == "\\\\"`` would replace one unverified Windows claim with
        another, which is the defect rather than the remedy; it is a product
        change, and it is beadloom-mr2l.60. What .39 owes is that the leg can
        ADJUDICATE the prediction, which is what the strict xfail below does.
        """
        native_for_windows = ntpath.join("src", "app.py")

        assert native_for_windows == "src\\app.py"
        assert rejection_reason(native_for_windows) == BACKSLASH_REJECTION

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

    @pytest.mark.xfail(
        sys.platform == "win32",
        strict=True,
        reason=(
            "PREDICTION, not a measurement: on Windows os.path.join yields "
            "'src\\\\app.py' and the shape gate refuses every backslash, so the "
            "guard cannot be told about a native edit target at all. Strict, so "
            "the runner adjudicates: if this PASSES on windows-latest the "
            "prediction was wrong and the suite says so. See beadloom-mr2l.60."
        ),
    )
    def test_the_guard_is_told_the_file_the_writer_will_touch(
        self, tmp_path: Path
    ) -> None:
        """The property the shape gate exists to hold, in THIS platform's spelling.

        A harness names the file the way its own platform names files. The guard
        must end up pointing at that same file. Written with ``os.path.join``
        rather than a literal so the row means the same sentence everywhere and
        can be red where the sentence is false — which is the only kind of
        cross-platform assertion worth adding before a runner exists.
        """
        # ``str(Path(...))`` renders with THIS platform's separator — the whole
        # point of the row; a literal would hard-code one platform's answer.
        resolved = resolve_edit_path(str(Path("src", "app.py")), tmp_path)

        assert resolved.scope is PathScope.INSIDE, resolved
        assert resolved.relative == "src/app.py", resolved


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
