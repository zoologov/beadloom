"""Adversarial re-verification of the narrowed guard path input (BDL-061.28).

Independent of the fix author's own suite (standing rule 6). ``.27`` stopped
normalising the model-supplied edit target and started REFUSING anything outside
a stated shape, so the question is no longer "is there another traversal" but
four narrower ones, one class each below:

1. Does the code accept exactly what ``flow-guards/SPEC.md`` says it accepts?
   Both directions matter — a refusal wider than documented breaks legitimate
   work, one that is narrower is a bypass.
2. Does every invocation that names a registered guard leave a firing record?
   That is a stated invariant with, per the SPEC, exactly one exception.
3. Does the exit-code contract hold through the real binary for every outcome,
   including the new ``error``?
4. Are the residuals ``.27`` names as deliberately open as narrow as claimed?

Where a test proves a seam rather than the tool (standing rule 4) it says so in
its docstring; the exit-code, stdin-decoding and project-root classes run the
installed ``beadloom`` executable in a subprocess, because a ``CliRunner`` proves
Click's dispatch and not the process's exit status or its stdin decoding.

Several tests here pin a GAP: they assert today's measured behaviour and their
docstring names the invariant it breaks, so that CLOSING the gap reddens the pin
and the fix cannot land silently. Each such class is named ``...IsNot...`` or
carries "GAP" in the docstring's first line.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.application.guards.config import GuardExclusion
from beadloom.application.guards.contract import GuardProbes
from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.firing import read_firings
from beadloom.application.guards.models import GuardOutcome
from beadloom.application.guards.paths import PathScope, rejection_reason, resolve_edit_path
from beadloom.services.cli import main
from tests.filesystem_names import (
    UNENCODABLE_FRAGMENT,
    filesystem_can_name,
    unnameable_reason,
)

_SPEC = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "domains"
    / "application"
    / "features"
    / "flow-guards"
    / "SPEC.md"
)

#: A guard declared blocking, with one ordinary exclusion over ``src/``.
_BLOCKING_WITH_EXCLUSION = (
    "guards:\n"
    "  bead-claimed:\n"
    "    strictness: { default: block }\n"
    "    exclusions:\n"
    "      - path: 'src/**'\n"
    "        reason: 'generated sources'\n"
    "        until: 'BDL-999'\n"
)

#: The same, with a single-component pattern — the shape F1 bypassed.
_BLOCKING_EXCLUDING_TOP_LEVEL_PY = (
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


def _verdict(root: Path, path: str | None, **context: str):
    """Evaluate ``bead-claimed`` in *root* for *path*, tracker answering "none"."""
    ctx = dict(context)
    if path is not None:
        ctx["path"] = path
    return evaluate_guard(
        "bead-claimed",
        project_root=root,
        context=ctx,
        probes=GuardProbes(tracker=_NoBeads()),
    )


def _cli(args: list[str], *, stdin: str = ""):
    return CliRunner().invoke(main, args, input=stdin)


# --------------------------------------------------------------------------
# The real installed executable. A CliRunner cannot answer "what exit status
# did the process return" or "what happens to undecodable bytes on stdin".
# --------------------------------------------------------------------------

_BEADLOOM = shutil.which("beadloom") or str(Path(sys.executable).parent / "beadloom")

real_binary = pytest.mark.skipif(
    not Path(_BEADLOOM).exists(),
    reason="beadloom console script not installed in this environment",
)


def _run_real(
    root: Path, args: list[str], *, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    """Run the installed ``beadloom`` in *root* with raw bytes on stdin."""
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [_BEADLOOM, *args],
        cwd=str(root),
        input=stdin,
        capture_output=True,
        check=False,
    )


def _git_init(root: Path, branch: str) -> None:
    subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "init", "-q", "-b", branch, str(root)],  # noqa: S607
        check=True,
        capture_output=True,
    )


def _project(tmp_path: Path, flow: str, *, branch: str | None = None) -> Path:
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".beadloom" / "flow.yml").write_text(flow, encoding="utf-8")
    if branch is not None:
        _git_init(tmp_path, branch)
    return tmp_path


def _outcomes(root: Path) -> list[str]:
    return [record.outcome for record in read_firings(root)]


# ==========================================================================
# 1. THE ACCEPTED SHAPE, FROM BOTH SIDES
# ==========================================================================


class TestTheAcceptedShapeAgreesWithTheSpec:
    """What the SPEC says is accepted must not be refused, and vice versa.

    The SPEC sentence under test (``flow-guards/SPEC.md``, "The accepted shape"):
    a well-formed edit target is a non-empty string with no C0 control character
    and no ``DEL``, no backslash, no leading ``~``, and encodable for this
    filesystem.
    """

    @pytest.mark.parametrize(
        ("label", "raw"),
        [
            ("an ordinary relative path", "src/app.py"),
            ("a dot-prefixed path", "./src/app.py"),
            ("a path with a traversal that stays inside", "src/../src/app.py"),
            ("a dotfile", ".gitignore"),
            ("a path under a dot-directory", ".beadloom/flow.yml"),
            ("spaces in a component", "src/a b/c d.py"),
            ("non-ASCII letters", "src/\u0444\u0430\u0439\u043b.py"),
            ("a percent sequence, never decoded", "src/percent%20encoded.py"),
            ("a percent-encoded traversal, never decoded", "%2e%2e/etc/passwd"),
            ("a tilde that is not the first character", "src/~backup.py"),
            ("a round-trippable non-UTF-8 byte", "src/\udcff.py"),
            ("a name that is only dots", "..."),
            ("a very long single component", "a" * 4096 + ".py"),
            ("a very long path with many components", "/".join(["d" * 200] * 40)),
            ("an emoji", "src/\U0001f600.py"),
            ("a Unicode look-alike separator", "src\u2044app.py"),
            ("a homoglyph directory", "\u0455rc/app.py"),
        ],
    )
    def test_a_target_the_spec_accepts_is_not_refused(self, tmp_path, label, raw) -> None:
        """A refusal wider than the document breaks work nobody agreed to break.

        The SPEC's last clause — "encodable for this filesystem" — makes the
        accepted SET a property of the image, so four of these rows (the
        Cyrillic name, the emoji, the look-alike separator, the homoglyph
        directory) are accepted where the filesystem can spell them and refused
        where it cannot. Both answers are the document; the row asserts the one
        that is true here rather than the one a UTF-8 machine gives
        (BDL-061.42 measured the difference on the ``tests-locale`` legs).
        """
        resolved = resolve_edit_path(raw, tmp_path)

        if not filesystem_can_name(raw):
            assert resolved.scope is PathScope.MALFORMED, unnameable_reason(raw)
            assert UNENCODABLE_FRAGMENT in rejection_reason(raw), rejection_reason(raw)
            return
        assert resolved.scope is not PathScope.MALFORMED, f"{label}: {resolved.rejection}"
        assert rejection_reason(raw) == "", label

    @pytest.mark.parametrize(
        ("label", "raw", "offence"),
        [
            ("one backslash", "src\\app.py", "backslash"),
            ("mixed separators", "src\\sub/app.py", "backslash"),
            ("a trailing backslash", "src/app.py\\", "backslash"),
            ("a UNC path", "\\\\server\\share\\app.py", "backslash"),
            ("a Windows drive with backslashes", "C:\\Users\\a\\app.py", "backslash"),
            ("a NUL at the end", "src/app.py\x00", "control character"),
            ("a NUL in the middle", "src/a\x00b.py", "control character"),
            ("a NUL at the start", "\x00src/app.py", "control character"),
            ("a bell", "src/a\x07b.py", "control character"),
            ("an ANSI escape", "src/\x1b[31mapp.py", "control character"),
            ("a DEL byte", "src/app\x7f.py", "control character"),
            ("a newline in the middle", "src/app\n.py", "control character"),
            ("a carriage return in the middle", "src/app\r.py", "control character"),
            ("a home-relative path", "~/secrets.env", "'~'"),
            ("another user's home", "~root/.ssh/authorized_keys", "'~'"),
            ("a bare tilde", "~", "'~'"),
            ("a lone surrogate", "src/\ud800.py", "cannot be encoded"),
        ],
    )
    def test_a_target_the_spec_refuses_does_not_slip_through(
        self, tmp_path, label, raw, offence
    ) -> None:
        """A refusal narrower than the document is a bypass."""
        resolved = resolve_edit_path(raw, tmp_path)

        assert resolved.scope is PathScope.MALFORMED, f"{label}: {resolved}"
        assert resolved.relative is None, label
        assert offence in resolved.rejection, f"{label}: {resolved.rejection!r}"

    @pytest.mark.parametrize(
        ("label", "raw"),
        [
            ("a backslash", "src\\app.py"),
            ("a NUL", "src/app.py\x00"),
            ("a leading tilde", "~/secrets.env"),
            ("a lone surrogate", "src/\ud800.py"),
        ],
    )
    def test_a_refused_target_is_never_matched_against_an_exclusion(
        self, tmp_path, label, raw
    ) -> None:
        """The ordering invariant, asserted against a catch-all that would swallow it.

        With ``**`` declared, every well-formed path skips; a refused one must
        still reach ``error``, because matching a pattern against a string the
        guard declined to interpret is the bypass the order removes.
        """
        root = _project(
            tmp_path,
            "guards:\n"
            "  bead-claimed:\n"
            "    strictness: { default: block }\n"
            "    exclusions:\n"
            "      - path: '**'\n"
            "        reason: 'everything, briefly'\n"
            "        until: 'BDL-999'\n",
        )

        verdict = _verdict(root, raw)

        assert verdict.outcome is GuardOutcome.ERROR, f"{label}: {verdict.why}"
        assert verdict.exit_code == 2, label

    def test_the_refusal_holds_because_a_refused_path_carries_no_relative_form(
        self, tmp_path
    ) -> None:
        """Which lock is actually holding, measured rather than assumed.

        The evaluator and the SPEC both explain the refusal by ORDER — the
        malformed check runs "before exclusions, because matching a pattern
        against a string the guard has refused to interpret is the bypass this
        order removes". Measured, the order is not what holds: moving the
        exclusion lookup ahead of the malformed check reddens nothing (148
        passed), because ``exclusion_for(None)`` returns ``None``. Removing
        ``relative=None`` from the refusal reddens 17. The stated reason names
        the weaker of the two guarantees; this pins the load-bearing one.
        """
        from beadloom.application.guards.config import build_guards_config

        spec = build_guards_config(
            {
                "guards": {
                    "bead-claimed": {
                        "exclusions": [
                            {"path": "**", "reason": "everything", "until": "BDL-999"}
                        ]
                    }
                }
            }
        ).spec_for("bead-claimed")
        resolved = resolve_edit_path("src\\app.py", tmp_path)

        assert resolved.relative is None
        assert spec.exclusion_for(resolved.relative) is None

    def test_a_refused_target_is_echoed_escaped_and_bounded(self, tmp_path) -> None:
        """A model-supplied string reaches a human's stderr and a JSONL record.

        Both are places an unbounded, unescaped string does damage, so the
        refusal echoes ``repr`` truncated at 120 characters.
        """
        resolved = resolve_edit_path("src/\x01" + "a" * 400 + ".py", tmp_path)

        assert "\x01" not in resolved.label
        assert len(resolved.label) <= 121
        assert resolved.label.endswith("\u2026")

    def test_an_accepted_target_is_not_escaped_on_its_way_to_the_reader(
        self, tmp_path
    ) -> None:
        """The bounded other half, stated rather than left to be discovered.

        A target inside the shape is echoed verbatim into ``why``, so a
        bidirectional override or a zero-width character reorders what a human
        reads in the hook's stderr. Display-only — the verdict itself is about
        the file the writer will touch — and every character that could inject a
        terminal control sequence is already outside the shape.
        """
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)
        target = "docs/\u202egpj.txt"

        verdict = _verdict(root, target)

        if not filesystem_can_name(target):
            # Where the filesystem cannot spell the name it never reaches the
            # display path at all: the shape gate refuses it first and the echo
            # is the bounded ``repr``, so the override character cannot reorder
            # anything a human reads. The safer half of the same property, and
            # the answer this image genuinely gives (BDL-061.42).
            assert UNENCODABLE_FRAGMENT in verdict.why, verdict.why
            assert "\u202e" not in verdict.why, unnameable_reason(target)
            return
        assert "\u202e" in verdict.why

    def test_every_clause_of_the_spec_sentence_is_enforced_by_the_code(self) -> None:
        """The SPEC's shape sentence and ``rejection_reason`` must not drift apart.

        F6 was the SPEC quoting a matcher the code does not emit. This is the
        same pairing for the sentence that now decides what a guard will look at:
        each clause the document states is exercised against a string that
        breaks only that clause.
        """
        sentence = " ".join(_SPEC.read_text(encoding="utf-8").split())
        clauses = {
            "no C0 control character and no `DEL`": "a\x01b",
            "contains no backslash": "a\\b",
            "does not begin with `~`": "~a",
            "can be encoded for this filesystem": "a\ud800b",
        }

        for clause, breaker in clauses.items():
            assert clause in sentence, f"the SPEC no longer states: {clause}"
            assert rejection_reason(breaker) != "", f"unenforced clause: {clause}"


class TestTheStripHappensBeforeTheShapeIsJudged:
    """CLOSED by BDL-061.29: nothing is removed before the shape is judged.

    The gap this class pinned: ``resolve_edit_path`` stripped and *then* judged,
    and :meth:`str.strip` removes every character Python calls whitespace —
    including ``\\t \\n \\v \\f \\r`` and ``U+001C``-``U+001F``, nine code points
    inside the ``U+0000``-``U+001F`` range the same SPEC paragraph says is
    refused. Two sentences of the SPEC disagreed and the code resolved the
    disagreement in the ACCEPTING direction, which turned a ``block`` into a
    ``skip`` whose printed reason named a pattern that does not cover the file
    the writer would create.

    The tests are kept, inverted: each one now asserts the closed behaviour, so
    re-introducing any strip reddens the same rows that were red before the fix.
    """

    @pytest.mark.parametrize(
        ("label", "char"),
        [
            ("tab", "\t"),
            ("newline", "\n"),
            ("vertical tab", "\x0b"),
            ("form feed", "\x0c"),
            ("carriage return", "\r"),
            ("file separator", "\x1c"),
            ("group separator", "\x1d"),
            ("record separator", "\x1e"),
            ("unit separator", "\x1f"),
        ],
    )
    def test_a_control_character_at_either_end_is_refused_like_any_other(
        self, tmp_path, label, char
    ) -> None:
        trailing = resolve_edit_path(f"src/app.py{char}", tmp_path)
        leading = resolve_edit_path(f"{char}src/app.py", tmp_path)

        assert trailing.scope is PathScope.MALFORMED, f"trailing {label}: {trailing}"
        assert trailing.relative is None, label
        assert leading.scope is PathScope.MALFORMED, f"leading {label}: {leading}"

    @pytest.mark.parametrize(
        ("label", "char"),
        [
            ("no-break space", "\xa0"),
            ("next line", "\x85"),
            ("en quad", "\u2000"),
            ("line separator", "\u2028"),
            ("ideographic space", "\u3000"),
        ],
    )
    def test_unicode_whitespace_names_the_file_it_actually_names(
        self, tmp_path, label, char
    ) -> None:
        """These name real, creatable files that differ from the stripped one.

        "Creatable" is the load-bearing word and it is ambient: on an image whose
        filesystem encoding cannot spell the character, no such file can exist, so
        the shape gate refuses the target instead. What the row is actually about
        — that the character is never silently REMOVED — holds in both worlds, and
        is asserted in both (BDL-061.42).
        """
        target = f"src/app.py{char}"
        resolved = resolve_edit_path(target, tmp_path)

        if not filesystem_can_name(target):
            assert resolved.scope is PathScope.MALFORMED, unnameable_reason(target)
            assert UNENCODABLE_FRAGMENT in resolved.rejection, resolved.rejection
            return
        assert resolved.scope is PathScope.INSIDE, label
        assert resolved.relative == f"src/app.py{char}", f"{label}: {resolved.relative!r}"

    @pytest.mark.parametrize(
        ("label", "suffix", "outcome", "exit_code"),
        [
            ("a trailing newline", "\n", GuardOutcome.ERROR, 2),
            ("a trailing tab", "\t", GuardOutcome.ERROR, 2),
            ("a trailing no-break space", "\xa0", GuardOutcome.BLOCK, 2),
            ("a trailing space", " ", GuardOutcome.BLOCK, 2),
        ],
    )
    def test_the_exclusion_no_longer_covers_a_file_its_pattern_does_not_name(
        self, tmp_path, label, suffix, outcome, exit_code
    ) -> None:
        """The consequence, measured: no row reaches ``skip`` any more.

        A control character is refused (the shape gate), and a whitespace
        character names a different file that ``src/*.py`` does not cover, so it
        is guarded. Both are the over-guarding direction, with a stated reason.
        """
        root = _project(tmp_path, _BLOCKING_EXCLUDING_TOP_LEVEL_PY)
        target = f"src/app.py{suffix}"

        verdict = _verdict(root, target)

        if not filesystem_can_name(target):
            # The whitespace rows name a DIFFERENT file only where the filesystem
            # can spell it; where it cannot, the shape gate refuses the target
            # first. `error` rather than `block`, same exit code, and the row's
            # own claim — no row reaches `skip`, and the pattern is not quoted at
            # a file it does not name — is asserted either way (BDL-061.42).
            outcome = GuardOutcome.ERROR
        assert verdict.outcome is outcome, f"{label}: {verdict.why}"
        assert verdict.exit_code == exit_code, label
        assert "src/*.py" not in verdict.why, label

    def test_the_file_the_guard_exempted_is_the_file_the_pattern_names(
        self, tmp_path
    ) -> None:
        """Stated as the property, not as the spelling: the two now agree."""
        exclusion = GuardExclusion(path="src/*.py", reason="r", until="u")
        root = _project(tmp_path, _BLOCKING_EXCLUDING_TOP_LEVEL_PY)

        assert exclusion.matches("src/app.py") is True
        assert exclusion.matches("src/app.py\xa0") is False
        assert _verdict(root, "src/app.py").outcome is GuardOutcome.SKIP


class TestAnEmptyTargetIsAbsentAndTheSpecNowSaysSo:
    """CLOSED by BDL-061.29, in the document — which is where the defect was.

    The SPEC's shape sentence opened with "a non-empty string", so by the
    document an empty target was an ``error``; the code classified it
    :attr:`PathScope.ABSENT` and the guard ran normally, naming the missing path
    in ``not_covered``. The code had the better behaviour ("no path supplied" is
    not "a malformed path"), so the SPEC was corrected to it — F6's class.

    A whitespace-only target is no longer absent, because nothing is stripped
    before the judgement: ``'   '`` names a file called three spaces and
    ``'\\t'`` carries a control character.
    """

    @pytest.mark.parametrize("raw", ["", None])
    def test_an_empty_target_is_absent_as_the_spec_now_states(
        self, tmp_path, raw
    ) -> None:
        resolved = resolve_edit_path(raw, tmp_path)

        assert resolved.scope is PathScope.ABSENT, resolved
        assert resolved.rejection == ""

    def test_the_spec_no_longer_calls_an_empty_target_malformed(self) -> None:
        """The two artifacts are read together, so they cannot drift apart again."""
        spec = _SPEC.read_text(encoding="utf-8")

        assert "absent or empty target is not a refusal" in spec

    @pytest.mark.parametrize(
        ("raw", "scope"),
        [("   ", PathScope.INSIDE), ("\t", PathScope.MALFORMED), ("\n", PathScope.MALFORMED)],
    )
    def test_a_whitespace_only_target_is_judged_as_the_name_it_is(
        self, tmp_path, raw, scope
    ) -> None:
        assert resolve_edit_path(raw, tmp_path).scope is scope

    def test_the_guard_still_answers_and_says_no_path_was_supplied(self, tmp_path) -> None:
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        verdict = _verdict(root, "")

        assert verdict.outcome is GuardOutcome.BLOCK
        assert any("supplied no path" in note for note in verdict.not_covered), (
            verdict.not_covered
        )


class TestTheExclusionMatcherIsAnchoredAtBothEnds:
    """CLOSED by BDL-061.29: ``\\Z`` where ``$`` was.

    ``_glob_to_regex`` ended its pattern with ``$`` and called ``.match``, and
    Python's ``$`` also matches *before* a trailing newline — so ``src/*.py``
    covered ``'src/app.py\\n'``, a different file. It was latent only because the
    resolver stripped the newline first: two locks with the same hole, and the
    outer one was what held. Both are closed, and this pin is what proves the
    inner one was not left open behind the fix to the outer one.
    """

    def test_a_pattern_does_not_cover_a_path_that_differs_by_a_trailing_newline(
        self,
    ) -> None:
        exclusion = GuardExclusion(path="src/*.py", reason="r", until="u")

        assert exclusion.matches("src/app.py\n") is False
        assert exclusion.matches("src/app.py") is True

    def test_it_still_matches_nothing_with_further_text_after_the_newline(self) -> None:
        exclusion = GuardExclusion(path="src/*.py", reason="r", until="u")

        assert exclusion.matches("src/app.py\nevil.sh") is False
        assert exclusion.matches("src/app.py\n\n") is False


# ==========================================================================
# 2. NO INVOCATION WITHOUT A FIRING RECORD
# ==========================================================================


class TestEveryWayTheCommandCanTerminate:
    """Enumerated, not sampled: each way ``guard`` can end, and whether it records.

    The SPEC states the invariant with exactly one exception: "No invocation
    that names a registered guard ends without a firing record. The single
    exception is a name that is not a registered guard."

    Six rows breached it when this class was written (BDL-061.28, F8) — every
    argument-parsing and hook-payload failure exited through ``_fail()``, which
    called :func:`sys.exit` before the record was reached. BDL-061.29 put one
    boundary around the whole invocation, and the ``records`` column below now
    reads ``True`` for every row that names a registered guard. The enumeration
    that keeps it that way lives in ``tests/test_guards_invocation.py``; this
    table stays as the independent measurement it was.
    """

    @pytest.mark.parametrize(
        ("label", "args", "stdin", "flow", "exit_code", "records"),
        [
            (
                "a guard that passes",
                ["guard", "working-branch"],
                "",
                "guards:\n  working-branch:\n    strictness: { default: warn }\n",
                0,
                True,
            ),
            (
                "a refused path",
                ["guard", "bead-claimed", "--context", "path=src\\app.py"],
                "",
                _BLOCKING_WITH_EXCLUSION,
                2,
                True,
            ),
            (
                "an excluded path",
                ["guard", "bead-claimed", "--context", "path=src/a.py"],
                "",
                _BLOCKING_WITH_EXCLUSION,
                0,
                True,
            ),
            (
                "an unreadable flow.yml",
                ["guard", "bead-claimed"],
                "",
                "guards: [1, 2\n",
                3,
                True,
            ),
            (
                "an exclusion with no reason",
                ["guard", "bead-claimed"],
                "",
                "guards:\n  bead-claimed:\n    exclusions:\n      - path: 'x/**'\n",
                3,
                True,
            ),
            (
                "a guard name nobody registered",
                ["guard", "no-such-guard"],
                "",
                _BLOCKING_WITH_EXCLUSION,
                3,
                False,
            ),
            (
                "a malformed --context pair",
                ["guard", "bead-claimed", "--context", "nonsense"],
                "",
                _BLOCKING_WITH_EXCLUSION,
                3,
                True,
            ),
            (
                "a --context pair with an empty key",
                ["guard", "bead-claimed", "--context", "=value"],
                "",
                _BLOCKING_WITH_EXCLUSION,
                3,
                True,
            ),
            (
                # 2, not 3, since BDL-061.33: the row is only reachable through a
                # hook, and 3 does not block there.
                "a harness nobody supports",
                ["guard", "bead-claimed", "--hook", "no-such-harness"],
                "",
                _BLOCKING_WITH_EXCLUSION,
                2,
                True,
            ),
            (
                "a hook payload that is not JSON",
                ["guard", "bead-claimed", "--hook", "claude-code"],
                "{not json",
                _BLOCKING_WITH_EXCLUSION,
                2,
                True,
            ),
            (
                "a hook payload that is not an object",
                ["guard", "bead-claimed", "--hook", "claude-code"],
                "[1, 2]",
                _BLOCKING_WITH_EXCLUSION,
                2,
                True,
            ),
        ],
    )
    def test_the_invocation_ends_with_a_record_or_is_named_as_an_exception(
        self, tmp_path, monkeypatch, label, args, stdin, flow, exit_code, records
    ) -> None:
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        root = _project(tmp_path, flow)

        result = _cli([*args, "--project", str(root)], stdin=stdin)

        assert result.exit_code == exit_code, f"{label}: {result.output}"
        assert bool(_outcomes(root)) is records, f"{label}: {_outcomes(root)}"

    @pytest.mark.parametrize(
        ("label", "args", "stdin", "exit_code"),
        [
            ("a malformed --context pair", ["--context", "nonsense"], "", 3),
            # 2, not 3, since BDL-061.33 — see the row above.
            ("a harness nobody supports", ["--hook", "no-such-harness"], "", 2),
            ("a hook payload that is not JSON", ["--hook", "claude-code"], "{not json", 2),
        ],
    )
    def test_a_registered_guard_no_longer_ends_without_a_record(
        self, tmp_path, monkeypatch, label, args, stdin, exit_code
    ) -> None:
        """CLOSED by BDL-061.29 — the gap this test was written to pin.

        Each of these names ``bead-claimed`` — a registered guard — and used to
        leave ``guard-firings.jsonl`` untouched, so ``--liveness`` went on
        reporting whatever the previous run said. The hook-payload row was the
        one that mattered: that string comes from the harness, so it was the F2
        shape (model-controlled input, no verdict, no record) with a different
        spelling. It now also blocks rather than exiting on the configuration
        code, because the input describes the edit in flight.
        """
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        result = _cli(
            ["guard", "bead-claimed", "--project", str(root), *args], stdin=stdin
        )

        assert result.exit_code == exit_code, f"{label}: {result.output}"
        assert _outcomes(root) == ["error"], label

    def test_liveness_shows_the_invocation_that_could_not_answer(
        self, tmp_path, monkeypatch
    ) -> None:
        """The consequence, inverted: the report can no longer read healthy through it.

        It used to be byte-identical before and after an unrecorded invocation,
        so yesterday's verdict was still on the screen while today's edit went
        unguarded.
        """
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        _cli(["guard", "bead-claimed", "--project", str(root), "--context", "path=a.py"])
        before = _cli(["guard", "--liveness", "--project", str(root), "--json"]).output
        _cli(
            ["guard", "bead-claimed", "--project", str(root), "--hook", "claude-code"],
            stdin="{not json",
        )
        after = _cli(["guard", "--liveness", "--project", str(root), "--json"]).output

        rows_before = {row["guard"]: row for row in json.loads(before)}
        rows_after = {row["guard"]: row for row in json.loads(after)}
        assert rows_after["bead-claimed"]["fired_count"] == (
            rows_before["bead-claimed"]["fired_count"] + 1
        )
        assert rows_after["bead-claimed"]["last_outcome"] == "error"

    def test_an_exception_inside_a_check_becomes_a_recorded_verdict(
        self, tmp_path, monkeypatch
    ) -> None:
        """The route the fix added, exercised at the CHECK rather than the evaluator.

        ``.27`` pinned this by exploding ``evaluate_guard`` itself; a check is
        where a future defect actually lives, and it is behind two more layers.
        """
        from beadloom.application.guards.checks import BUILTIN_GUARDS
        from beadloom.application.guards.contract import Guard
        from beadloom.services.commands import guard as guard_cmd

        def explode(_request: object) -> None:
            msg = "the tracker probe blew up"
            raise RuntimeError(msg)

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        monkeypatch.setitem(
            BUILTIN_GUARDS,
            "bead-claimed",
            Guard(name="bead-claimed", summary="s", check=explode),
        )
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        result = _cli(["guard", "bead-claimed", "--project", str(root)])

        assert result.exit_code == 2, result.output
        assert _outcomes(root) == ["error"]
        assert "the tracker probe blew up" in read_firings(root)[-1].why

    def test_a_missing_tracker_is_a_recorded_skip_not_a_silent_pass(
        self, tmp_path, monkeypatch
    ) -> None:
        """A probe that cannot answer must skip with a reason, and be recorded."""
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        result = _cli(
            ["guard", "bead-claimed", "--project", str(root), "--context", "path=a.py"]
        )

        assert result.exit_code == 0, result.output
        assert _outcomes(root) == ["skip"]
        assert "tracker is unavailable" in read_firings(root)[-1].why


class TestEveryRefusalNamesWhatItDidNotCheck:
    """``not_covered`` on every route that produces ``error``, not just the two shown.

    ``.27`` set the precedent that a refused evaluation reports "everything this
    guard checks" as unchecked. There are exactly three routes to ``error``: a
    refused path (the evaluator), a configuration error and an unexpected
    exception (both the CLI). All three are asserted here, and the note is
    checked for being TRUE — naming the guard's whole scope and the stage that
    was never reached — rather than merely non-empty.
    """

    def test_a_refused_path_reports_everything_as_unchecked(self, tmp_path) -> None:
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        verdict = _verdict(root, "src\\app.py")

        assert verdict.not_covered == (
            "everything this guard checks: the edit target 'src\\\\app.py' was "
            "refused as malformed before any exclusion or check was applied to it",
        )

    def test_the_refusal_note_is_true_no_exclusion_and_no_check_ran(
        self, tmp_path, monkeypatch
    ) -> None:
        """The note claims nothing ran; assert nothing ran, rather than trusting it."""
        from beadloom.application.guards.checks import BUILTIN_GUARDS
        from beadloom.application.guards.contract import Guard

        calls: list[str] = []

        def record_call(_request: object) -> None:
            calls.append("check")
            raise AssertionError("the check must not run for a refused path")

        monkeypatch.setitem(
            BUILTIN_GUARDS,
            "bead-claimed",
            Guard(name="bead-claimed", summary="s", check=record_call),
        )
        monkeypatch.setattr(
            GuardExclusion,
            "matches",
            lambda self, path: calls.append("exclusion") or False,
        )
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        verdict = _verdict(root, "src/app.py\x00")

        assert verdict.outcome is GuardOutcome.ERROR
        assert calls == []

    @pytest.mark.parametrize(
        ("label", "flow"),
        [
            ("invalid YAML", "guards: [1, 2\n"),
            (
                "an exclusion with no reason",
                "guards:\n  bead-claimed:\n    exclusions:\n      - path: 'x/**'\n",
            ),
            ("a guard nobody registered", "guards:\n  nope-guard:\n    strictness: warn\n"),
        ],
    )
    def test_a_configuration_error_reports_everything_as_unchecked(
        self, tmp_path, monkeypatch, label, flow
    ) -> None:
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        root = _project(tmp_path, flow)

        result = _cli(["guard", "bead-claimed", "--project", str(root), "--json"])
        payload = json.loads(result.output)

        assert result.exit_code == 3, label
        assert payload["outcome"] == "error", label
        assert payload["not_covered"] == [
            "everything guard 'bead-claimed' checks: the evaluation did not complete"
        ], label
        assert payload["remediation"], label

    def test_an_unexpected_exception_reports_everything_as_unchecked(
        self, tmp_path, monkeypatch
    ) -> None:
        from beadloom.services.commands import guard as guard_cmd

        def explode(*_args: object, **_kwargs: object) -> None:
            msg = "nobody has written this defect yet"
            raise RuntimeError(msg)

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        monkeypatch.setattr(
            "beadloom.application.guards.invocation.evaluate_guard", explode
        )
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        result = _cli(["guard", "bead-claimed", "--project", str(root), "--json"])
        payload = json.loads(result.output)

        assert result.exit_code == 2
        assert payload["not_covered"] == [
            "everything guard 'bead-claimed' checks: the evaluation did not complete"
        ]

    def test_an_error_verdict_cannot_be_built_without_the_note(self) -> None:
        """The invariant that makes the three cases above structural, not habitual."""
        from beadloom.application.guards.models import GuardVerdict

        with pytest.raises(ValueError, match="did not check"):
            GuardVerdict(guard="bead-claimed", outcome=GuardOutcome.ERROR, why="x")


# ==========================================================================
# 3. THE EXIT-CODE CONTRACT, THROUGH THE REAL PROCESS
# ==========================================================================


@real_binary
class TestTheExitCodeContractThroughTheRealBinary:
    """Every outcome's exit status, measured on the installed executable.

    Standing rule 4: a ``CliRunner`` result proves Click's dispatch and the
    ``SystemExit`` it raises; the harness reads a PROCESS exit status, and that
    is what is measured here. ``working-branch`` is used because it needs only
    git, so every row is real end to end — no probe is stubbed.
    """

    @pytest.mark.parametrize(
        ("label", "flow", "branch", "extra", "expected"),
        [
            (
                "pass off the trunk",
                "guards:\n  working-branch:\n    strictness: { default: warn }\n",
                "features/BDL-061",
                [],
                0,
            ),
            (
                "skip when strictness is off",
                "guards:\n  working-branch:\n    strictness: { default: off }\n",
                "main",
                [],
                0,
            ),
            (
                "warn on the trunk",
                "guards:\n  working-branch:\n    strictness: { default: warn }\n",
                "main",
                [],
                1,
            ),
            (
                "block on the trunk",
                "guards:\n  working-branch:\n    strictness: { default: block }\n",
                "main",
                [],
                2,
            ),
            (
                "error on a refused path",
                "guards:\n  working-branch:\n    strictness: { default: block }\n",
                "features/BDL-061",
                ["--context", "path=src\\app.py"],
                2,
            ),
            (
                "config error on unreadable YAML",
                "guards: [1, 2\n",
                "main",
                [],
                3,
            ),
        ],
    )
    def test_the_process_exit_status_carries_the_outcome(
        self, tmp_path, label, flow, branch, extra, expected
    ) -> None:
        root = _project(tmp_path, flow, branch=branch)

        result = _run_real(root, ["guard", "working-branch", *extra])

        assert result.returncode == expected, (
            f"{label}: {result.stdout!r} {result.stderr!r}"
        )
        assert b"Traceback" not in result.stderr, label

    @pytest.mark.parametrize(
        ("label", "flow", "branch", "stream"),
        [
            (
                "a pass is quiet on stdout",
                "guards:\n  working-branch:\n    strictness: { default: warn }\n",
                "features/BDL-061",
                "stdout",
            ),
            (
                "a warn reaches stderr",
                "guards:\n  working-branch:\n    strictness: { default: warn }\n",
                "main",
                "stderr",
            ),
            (
                "a block reaches stderr",
                "guards:\n  working-branch:\n    strictness: { default: block }\n",
                "main",
                "stderr",
            ),
        ],
    )
    def test_the_outcome_reaches_the_stream_the_harness_reads(
        self, tmp_path, label, flow, branch, stream
    ) -> None:
        root = _project(tmp_path, flow, branch=branch)

        result = _run_real(root, ["guard", "working-branch"])
        chosen = result.stdout if stream == "stdout" else result.stderr
        other = result.stderr if stream == "stdout" else result.stdout

        assert b"working-branch:" in chosen, label
        assert b"working-branch:" not in other, label

    def test_every_real_invocation_is_recorded(self, tmp_path) -> None:
        root = _project(
            tmp_path,
            "guards:\n  working-branch:\n    strictness: { default: block }\n",
            branch="main",
        )

        _run_real(root, ["guard", "working-branch"])
        _run_real(root, ["guard", "working-branch", "--context", "path=a\\b.py"])

        assert _outcomes(root) == ["block", "error"]

    def test_a_missing_project_directory_is_a_verdict_and_not_clicks_usage_exit(
        self, tmp_path
    ) -> None:
        """CLOSED by BDL-061.29 (m1): the option is no longer validated by Click.

        ``--project`` used to carry ``exists=True``, so a directory that does not
        exist produced Click's own exit 2 — the code the SPEC reserves for a
        block — with no verdict and no firing record: a usage error wearing a
        block's clothes. Validation now happens inside the boundary, so the same
        argv produces an ``error`` verdict that says the project could not be
        located. It still exits 2, and that is the point: the guard genuinely
        cannot answer, so the edit must stop. Nothing is recorded, because
        recording would require inventing the project this invocation could not
        find — the one exception the SPEC names for exactly this reason.
        """
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION, branch="main")

        result = _run_real(root, ["guard", "working-branch", "--project", str(root / "gone")])

        assert result.returncode == 2, result.stderr
        assert b"Invalid value" not in result.stderr
        assert b"working-branch: ERROR" in result.stderr
        assert not (root / "gone").exists()
        assert read_firings(root) == ()


@real_binary
class TestAHookPayloadTheProcessCannotDecode:
    """CLOSED by BDL-061.29: the stdin read moved inside the boundary.

    The gap: ``--hook`` read ``sys.stdin.read()``, which decodes with the
    process's encoding and ``errors='strict'``. A payload carrying a byte that
    is not valid UTF-8 raised ``UnicodeDecodeError`` OUTSIDE both the
    ``HookPayloadError`` handler (it is not one) and the ``except Exception``
    around ``evaluate_guard`` (it happened before it), so the invocation ended
    in a raw traceback, exit 1 — the WARN code, which the shipped adapter's own
    comment calls "shown, never blocking" — no verdict, and no firing record.
    Four properties, identical to F2's, from the same input class.

    The accepted shape explicitly admits non-UTF-8 file names, so the transport
    was refusing, with a crash, a name the shape gate one layer down accepts.
    Both halves are asserted side by side below.

    Must run as a real process: a ``CliRunner`` supplies an already-decoded
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
    def test_an_undecodable_payload_is_a_recorded_verdict_on_the_blocking_code(
        self, tmp_path, label, payload
    ) -> None:
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        result = _run_real(
            root, ["guard", "bead-claimed", "--hook", "claude-code"], stdin=payload
        )

        assert result.returncode == 2, f"{label}: {result.stderr!r}"
        assert b"Traceback" not in result.stderr, label
        assert b"UnicodeDecodeError" not in result.stderr, label
        assert _outcomes(root) == ["error"], label

    def test_the_same_file_name_is_accepted_when_it_reaches_the_shape_gate(
        self, tmp_path
    ) -> None:
        """The other half: the shape admits what the transport used to crash on."""
        resolved = resolve_edit_path("src/\udcff.py", tmp_path)

        assert resolved.scope is PathScope.INSIDE, resolved


@real_binary
class TestTheProjectIsDiscoveredNotTakenFromTheShell:
    """CLOSED by BDL-061.29: the root is the nearest ancestor holding ``.beadloom/``.

    The gap: the shipped adapter passes no ``--project``, so the decision root
    was ``Path.cwd()`` and ``load_guards_config`` did not walk upwards.
    ``hook_command`` anchored the SCRIPT with ``$CLAUDE_PROJECT_DIR`` and its
    docstring gave the reason — cwd "is not the project root for every tool
    invocation" — then left the decision on cwd anyway. Measured from a
    subdirectory of a project whose ``flow.yml`` declares ``block``: the
    declared strictness was gone (block, exit 2 → warn, exit 1, non-blocking),
    the declared exclusions were gone with it, and the firing was written to a
    NEW ``<subdir>/.beadloom/`` that ``--liveness`` at the root never reads —
    which also manufactured a second project root inside the first, so the next
    invocation from there would find the stray marker and entrench the reading.
    """

    @pytest.fixture()
    def project_with_a_subdirectory(self, tmp_path) -> tuple[Path, Path]:
        root = _project(
            tmp_path,
            "guards:\n"
            "  working-branch:\n"
            "    strictness: { default: block }\n"
            "    exclusions:\n"
            "      - path: 'vendor/**'\n"
            "        reason: 'vendored'\n"
            "        until: 'BDL-999'\n",
            branch="main",
        )
        sub = root / "src" / "deep"
        sub.mkdir(parents=True)
        return root, sub

    def test_a_declared_block_stays_a_block_from_a_subdirectory(
        self, project_with_a_subdirectory
    ) -> None:
        root, sub = project_with_a_subdirectory

        at_root = _run_real(root, ["guard", "working-branch"])
        at_sub = _run_real(sub, ["guard", "working-branch"])

        assert at_root.returncode == 2, at_root.stderr
        assert at_sub.returncode == 2, at_sub.stderr

    def test_the_firing_lands_where_the_liveness_report_reads_it(
        self, project_with_a_subdirectory
    ) -> None:
        root, sub = project_with_a_subdirectory

        _run_real(sub, ["guard", "working-branch"])

        assert _outcomes(root) == ["block"]
        assert read_firings(sub) == ()

    def test_the_liveness_report_at_the_root_shows_the_subdirectory_firing(
        self, project_with_a_subdirectory
    ) -> None:
        root, sub = project_with_a_subdirectory

        _run_real(sub, ["guard", "working-branch"])
        report = _run_real(root, ["guard", "--liveness", "--json"])
        rows = {row["guard"]: row for row in json.loads(report.stdout)}

        assert rows["working-branch"]["never_fired"] is False
        assert rows["working-branch"]["fired_count"] == 1

    def test_it_creates_no_beadloom_directory_outside_the_project_root(
        self, project_with_a_subdirectory
    ) -> None:
        """A guard's only write is the PROJECT's firing record — never a new root."""
        _root, sub = project_with_a_subdirectory

        _run_real(sub, ["guard", "working-branch"])

        assert not (sub / ".beadloom").exists()


# ==========================================================================
# 4. THE RESIDUALS THE FIX NAMED, AND THE ADVERSARIAL TABLE
# ==========================================================================


class TestTheResidualsTheFixNamed:
    """Each residual ``.27`` left open, checked against the width it claims.

    Three are as narrow as stated and are pinned as such. The whitespace one is
    not, and its counter-evidence lives in
    :class:`TestTheStripHappensBeforeTheShapeIsJudged`.
    """

    @pytest.mark.parametrize(
        ("label", "raw", "expected_relative"),
        [
            ("a drive letter with POSIX separators", "C:/Users/a/app.py", "C:/Users/a/app.py"),
            ("a lowercase drive letter", "c:/temp/x.py", "c:/temp/x.py"),
        ],
    )
    def test_a_bare_drive_letter_reads_as_a_relative_directory(
        self, tmp_path, label, raw, expected_relative
    ) -> None:
        """Residual 2, confirmed narrow: it over-guards, it does not exempt.

        The target is treated as a directory named ``C:`` inside the project, so
        the guard runs on a file that does not exist rather than skipping — the
        safe direction, and the same direction the SPEC claims.
        """
        resolved = resolve_edit_path(raw, tmp_path)

        assert resolved.scope is PathScope.INSIDE, label
        assert resolved.relative == expected_relative, label

    def test_a_drive_letter_is_not_exempted_by_an_exclusion_written_for_the_tree(
        self, tmp_path
    ) -> None:
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        verdict = _verdict(root, "C:/src/app.py")

        assert verdict.outcome is GuardOutcome.BLOCK, verdict.why

    @pytest.mark.parametrize(
        ("label", "raw"),
        [
            ("a Cyrillic 's'", "\u0455rc/app.py"),
            ("a division slash", "src\u2044app.py"),
            ("a fullwidth solidus", "src\uff0fapp.py"),
            ("a look-alike of the excluded directory", "s\u0433c/app.py"),
        ],
    )
    def test_a_homoglyph_names_a_different_file_and_is_guarded_not_exempted(
        self, tmp_path, label, raw
    ) -> None:
        """Residual 3, confirmed narrow: the exclusion stops applying, it does not widen.

        ``src/**`` is declared; none of these are under ``src/`` as the
        filesystem reads them, so the guard runs. Over-guarding, as claimed.
        """
        root = _project(tmp_path, _BLOCKING_WITH_EXCLUSION)

        verdict = _verdict(root, raw)

        if not filesystem_can_name(raw):
            # A homoglyph the filesystem cannot spell is refused before any
            # exclusion is consulted. The claim under test — the exclusion stops
            # applying, it does not widen — holds in the over-guarding direction
            # here too, which is what this asserts (BDL-061.42).
            assert verdict.outcome is GuardOutcome.ERROR, f"{label}: {verdict.why}"
            assert UNENCODABLE_FRAGMENT in verdict.why, verdict.why
            return
        assert verdict.outcome is GuardOutcome.BLOCK, f"{label}: {verdict.why}"

    @pytest.mark.parametrize(
        ("label", "raw"),
        [
            ("4096 characters in one component", "a" * 4096 + ".py"),
            ("40 components of 200 characters", "/".join(["d" * 200] * 40)),
            ("a thousand traversals that stay inside", "src/" + "x/../" * 1000 + "app.py"),
        ],
    )
    def test_the_absence_of_a_length_limit_costs_nothing(self, tmp_path, label, raw) -> None:
        """Residual: no length limit, "the OS enforces its own maximum".

        Confirmed narrow — resolution answers without raising, and the answer is
        inside the project, so the guard runs.
        """
        resolved = resolve_edit_path(raw, tmp_path)

        assert resolved.scope is PathScope.INSIDE, f"{label}: {resolved}"

    @pytest.mark.parametrize(
        ("label", "raw"),
        [
            ("a percent-encoded traversal", "%2e%2e/%2e%2e/etc/passwd"),
            ("a percent-encoded separator", "src%2fapp.py"),
            ("a percent-encoded NUL", "src/app.py%00"),
        ],
    )
    def test_percent_encoding_is_never_decoded(self, tmp_path, label, raw) -> None:
        """Residual: nothing decodes it, so it names a literally-spelled file.

        Confirmed narrow: the traversal does not escape the project and the
        encoded NUL is an ordinary name, so the guard sees what the writer will
        write.
        """
        resolved = resolve_edit_path(raw, tmp_path)

        assert resolved.scope is PathScope.INSIDE, label
        assert resolved.relative == raw, label

    def test_the_whitespace_residual_is_gone_rather_than_narrowed(
        self, tmp_path
    ) -> None:
        """Residual 1 was NOT narrow, and BDL-061.29 removed it instead of rewording it.

        The SPEC stated the cost as "a file whose name genuinely ends in
        whitespace is guarded as though it did not". Measured, the same strip
        also swallowed nine C0 control characters the paragraph above said were
        refused. There is no strip now: each of those nine is refused, and a
        name that really ends in whitespace is guarded as the name it is.
        """
        control_characters_accepted = [
            char
            for char in "\t\n\v\f\r\x1c\x1d\x1e\x1f"
            if resolve_edit_path(f"src/app.py{char}", tmp_path).scope is not PathScope.MALFORMED
        ]

        assert control_characters_accepted == []
        assert resolve_edit_path("src/app.py ", tmp_path).relative == "src/app.py "


class TestTheAdversarialTable:
    """The table the bead asks for: one row per spelling, verdict and record.

    Every row is measured through the CLI so the exit code and the firing record
    are the real ones, not the evaluator's opinion of them. The configuration is
    constant: ``bead-claimed`` at ``strictness: block`` with ``src/**`` excluded,
    tracker answering "nothing claimed". So ``block`` = the guard ran and found a
    violation, ``skip`` = it was exempted or could not apply, ``error`` = it
    refused to interpret the target.
    """

    @pytest.mark.parametrize(
        ("label", "path", "outcome", "exit_code"),
        [
            # -- the spellings the bead names ---------------------------------
            ("a backslash separator", "src\\app.py", "error", 2),
            ("mixed separators", "src\\sub/app.py", "error", 2),
            ("a NUL byte", "src/app.py\x00", "error", 2),
            ("an ANSI escape", "src/\x1b[31mapp.py", "error", 2),
            ("a DEL byte", "src/app\x7f.py", "error", 2),
            ("a percent-encoded traversal", "%2e%2e/%2e%2e/etc/passwd", "block", 2),
            ("a Unicode separator look-alike", "src\u2044app.py", "block", 2),
            ("a homoglyph directory", "\u0455rc/app.py", "block", 2),
            ("an over-long path", "a" * 4096 + ".py", "block", 2),
            ("a path that is only dots", "...", "block", 2),
            ("a path that is only two dots", "..", "block", 2),
            ("an empty target", "", "block", 2),
            ("the project root itself", ".", "block", 2),
            ("a leading tilde", "~/secrets.env", "error", 2),
            # -- the three the exclusion is meant to cover ---------------------
            ("an honestly excluded path", "src/app.py", "skip", 0),
            ("an excluded path reached by traversal", "docs/../src/app.py", "skip", 0),
            ("the excluded directory itself", "src/", "block", 2),
            # -- rows nobody has named before ---------------------------------
            ("a trailing newline on an excluded path", "src/app.py\n", "error", 2),
            ("a trailing no-break space", "src/app.py\xa0", "skip", 0),
            ("a zero-width space inside an excluded path", "src/ap\u200bp.py", "skip", 0),
            ("a right-to-left override", "src/\u202egpj.txt", "skip", 0),
            ("the guard's own configuration file", ".beadloom/flow.yml", "block", 2),
            ("a traversal that leaves and returns", "../{name}/src/app.py", "skip", 0),
        ],
    )
    def test_the_row_reaches_the_stated_verdict_and_is_recorded(
        self, tmp_path, monkeypatch, label, path, outcome, exit_code
    ) -> None:
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(
            guard_cmd, "_probes", lambda _root: GuardProbes(tracker=_NoBeads())
        )
        root = _project(tmp_path / "project", _BLOCKING_WITH_EXCLUSION)
        (root / "src").mkdir()
        supplied = path.format(name=root.name) if "{name}" in path else path
        if not filesystem_can_name(supplied):
            # The table's verdicts are written for a filesystem that can spell
            # every row. Where this image cannot, the shape gate refuses the
            # target before any exclusion or check applies, so the row's verdict
            # is `error`/2 — the same table read on a different machine, stated
            # here rather than pinned to the author's (BDL-061.42).
            outcome, exit_code = "error", 2

        result = _cli(
            ["guard", "bead-claimed", "--project", str(root), "--context", f"path={supplied}"]
        )

        assert result.exit_code == exit_code, f"{label}: {result.output}"
        assert _outcomes(root) == [outcome], f"{label}: {result.output}"

    @pytest.mark.parametrize(
        ("label", "relative_target"),
        [
            ("an absolute path outside the project", "outside/secret.txt"),
            ("a symlink pointing outside the project", "src/link.txt"),
        ],
    )
    def test_a_target_outside_the_project_is_guarded_and_says_so(
        self, tmp_path, monkeypatch, label, relative_target
    ) -> None:
        """Both spellings of "elsewhere on the machine": absolute, and via a link."""
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(
            guard_cmd, "_probes", lambda _root: GuardProbes(tracker=_NoBeads())
        )
        root = _project(tmp_path / "project", _BLOCKING_WITH_EXCLUSION)
        (root / "src").mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("x", encoding="utf-8")
        (root / "src" / "link.txt").symlink_to(outside / "secret.txt")
        supplied = (
            str(tmp_path / relative_target)
            if relative_target.startswith("outside")
            else relative_target
        )

        result = _cli(
            [
                "guard",
                "bead-claimed",
                "--project",
                str(root),
                "--context",
                f"path={supplied}",
                "--json",
            ]
        )
        payload = json.loads(result.output)

        assert payload["outcome"] == "block", label
        assert any("outside the project root" in note for note in payload["not_covered"]), (
            f"{label}: {payload['not_covered']}"
        )
        assert _outcomes(root) == ["block"], label
