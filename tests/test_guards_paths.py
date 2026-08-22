"""The edit path a guard is asked about: normalisation and the project boundary.

The path arrives from the harness as ``tool_input.file_path`` — i.e. from the
model — and it decides whether an exclusion matches, which decides whether the
guard runs at all. So every case here is a way to switch a gate off from the
outside, and each one is asserted end-to-end through ``evaluate_guard`` rather
than on the resolver alone: the bypass that shipped was invisible at the unit
level because the resolver looked reasonable in isolation.

Reproduced from review .3 (C1), with a ``scripts/**`` exclusion declared:

    scripts/deploy.sh              -> skip   (correct)
    scripts/../src/app.py          -> skip   (BYPASS: src/app.py is edited)
"""

from __future__ import annotations

import errno
import json
import sys
from pathlib import Path

import pytest

from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.models import GuardOutcome
from beadloom.application.guards.paths import PathScope, resolve_edit_path

_EXCLUDED_SCRIPTS = (
    "guards:\n"
    "  bead-claimed:\n"
    "    exclusions:\n"
    "      - path: 'scripts/**'\n"
    "        reason: 'operational scripts are not bead-scoped'\n"
    "        until: 'BDL-999'\n"
)

_EXCLUDE_EVERYTHING = (
    "guards:\n"
    "  bead-claimed:\n"
    "    exclusions:\n"
    "      - path: '**'\n"
    "        reason: 'migrating'\n"
    "        until: 'BDL-999'\n"
)


def _verdict(tmp_path, probes, path: str):
    return evaluate_guard(
        "bead-claimed",
        project_root=tmp_path,
        context={"path": path},
        probes=probes(beads=()),
    )


def _fail_resolution_of(monkeypatch, segment: str, error: BaseException) -> None:
    """Make ``Path.resolve`` raise *error* for paths through *segment*, and only those.

    Injection rather than a whole-class stub, because the resolution of the
    project root itself must keep working: a stub that raises for every path
    would prove that the handler catches its own fixture. The real
    ``Path.resolve`` is kept and called for everything else.
    """
    real = Path.resolve

    def resolve(self, strict=False):  # mirrors Path.resolve's own signature
        if segment in self.parts:
            raise error
        return real(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve)


class TestTraversalCannotBypassAnExclusion:
    """A path that resolves OUT of an excluded directory is not excluded."""

    @pytest.mark.parametrize(
        ("label", "path"),
        [
            ("bare traversal", "scripts/../src/app.py"),
            ("dot-prefixed traversal", "./scripts/../src/app.py"),
            ("doubled traversal", "scripts/sub/../../src/app.py"),
            ("redundant separators", "scripts/.././src/app.py"),
        ],
    )
    def test_a_traversing_path_is_guarded_not_skipped(
        self, tmp_path, write_flow_yml, make_guard_probes, label, path
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, path)

        assert verdict.outcome is GuardOutcome.WARN, f"{label}: {verdict.why}"
        assert "src/app.py" in verdict.why

    def test_an_absolute_traversing_path_is_guarded_not_skipped(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)
        absolute = str(tmp_path / "scripts" / ".." / "src" / "app.py")

        verdict = _verdict(tmp_path, make_guard_probes, absolute)

        assert verdict.outcome is GuardOutcome.WARN, verdict.why
        assert "src/app.py" in verdict.why

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
    def test_a_symlink_out_of_an_excluded_directory_is_guarded(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """A lexical fix would still let a symlink carry the exemption out."""
        write_flow_yml(_EXCLUDED_SCRIPTS)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "link.py").symlink_to(tmp_path / "src" / "app.py")

        verdict = _verdict(tmp_path, make_guard_probes, "scripts/link.py")

        assert verdict.outcome is GuardOutcome.WARN, verdict.why
        assert "src/app.py" in verdict.why


class TestAnHonestExclusionStillApplies:
    """Closing the bypass must not break the exclusion it protects."""

    @pytest.mark.parametrize(
        "path", ["scripts/deploy.sh", "./scripts/deploy.sh", "scripts/nested/deploy.sh"]
    )
    def test_a_path_genuinely_inside_the_excluded_tree_skips(
        self, tmp_path, write_flow_yml, make_guard_probes, path
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, path)

        assert verdict.outcome is GuardOutcome.SKIP, verdict.why
        assert "scripts/**" in verdict.why

    def test_an_absolute_path_inside_the_project_skips(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, str(tmp_path / "scripts" / "deploy.sh"))

        assert verdict.outcome is GuardOutcome.SKIP, verdict.why


class TestAPathOutsideTheProject:
    """Decision: an outside path inherits no exclusion, and the verdict says so."""

    @pytest.mark.parametrize(
        ("label", "relative"),
        [("traversal above the root", "../elsewhere/app.py"), ("sibling", "../app.py")],
    )
    def test_it_is_not_matched_against_any_exclusion(
        self, tmp_path, write_flow_yml, make_guard_probes, label, relative
    ) -> None:
        write_flow_yml(_EXCLUDE_EVERYTHING)

        verdict = _verdict(tmp_path, make_guard_probes, relative)

        assert verdict.outcome is GuardOutcome.WARN, f"{label}: {verdict.why}"

    def test_an_absolute_outside_path_is_not_matched_against_any_exclusion(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDE_EVERYTHING)
        outside = tmp_path.parent / "outside-project" / "app.py"

        verdict = _verdict(tmp_path, make_guard_probes, str(outside))

        assert verdict.outcome is GuardOutcome.WARN, verdict.why

    def test_the_verdict_states_that_the_target_is_outside_the_project(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDE_EVERYTHING)

        verdict = _verdict(tmp_path, make_guard_probes, "../elsewhere/app.py")

        assert any("outside the project" in item for item in verdict.not_covered), (
            verdict.not_covered
        )

    def test_it_is_not_reported_as_a_path_the_harness_failed_to_supply(
        self, tmp_path, make_guard_probes
    ) -> None:
        """The two are different facts; conflating them makes the note false."""
        verdict = _verdict(tmp_path, make_guard_probes, "../elsewhere/app.py")

        assert not any("supplied no path" in item for item in verdict.not_covered), (
            verdict.not_covered
        )


class TestResolveEditPath:
    def test_no_path_is_absent(self, tmp_path) -> None:
        resolved = resolve_edit_path(None, tmp_path)

        assert resolved.scope is PathScope.ABSENT
        assert resolved.relative is None

    def test_an_empty_path_is_absent(self, tmp_path) -> None:
        assert resolve_edit_path("", tmp_path).scope is PathScope.ABSENT

    def test_a_whitespace_only_path_is_judged_as_the_name_it_is(self, tmp_path) -> None:
        """Nothing is stripped before the shape is judged (BDL-061.29, F10).

        ``'   '`` names a file called three spaces, which is legal on this
        platform; ``'\n'`` carries a control character and is refused. Treating
        either as "the harness supplied no path" was a guess, and the guess ran
        BEFORE the shape gate — which is how nine C0 characters the SPEC refuses
        were silently accepted.
        """
        assert resolve_edit_path("   ", tmp_path).scope is PathScope.INSIDE
        assert resolve_edit_path("\n", tmp_path).scope is PathScope.MALFORMED

    def test_an_inside_path_is_relative_posix(self, tmp_path) -> None:
        resolved = resolve_edit_path("src/./a/../a/b.py", tmp_path)

        assert resolved.scope is PathScope.INSIDE
        assert resolved.relative == "src/a/b.py"

    def test_an_outside_path_keeps_no_relative_form(self, tmp_path) -> None:
        resolved = resolve_edit_path("../a.py", tmp_path)

        assert resolved.scope is PathScope.OUTSIDE
        assert resolved.relative is None
        assert resolved.label.endswith("a.py")

    def test_the_project_root_itself_resolves_inside(self, tmp_path) -> None:
        resolved = resolve_edit_path(str(tmp_path), tmp_path)

        assert resolved.scope is PathScope.INSIDE

    def test_a_root_reached_through_a_symlink_is_still_inside(self, tmp_path) -> None:
        """``/tmp`` is a symlink on macOS; an unresolved root would say OUTSIDE."""
        real = tmp_path / "real"
        real.mkdir()
        link = tmp_path / "link"
        link.symlink_to(real, target_is_directory=True)

        assert resolve_edit_path(str(link / "a.py"), real).scope is PathScope.INSIDE


# ---------------------------------------------------------------------------
# Independent re-verification of the .25 fix (BDL-061.26).
#
# The matrix below is the whole set of spellings a model can supply, each with
# the outcome MEASURED through ``evaluate_guard`` rather than reasoned about.
# Two of them are recorded gaps that survive the fix and are named nowhere in
# its honesty note; they are pinned here so a later fix must redden them.
# ---------------------------------------------------------------------------

_EXCLUDED_TOP_LEVEL_PY = (
    "guards:\n"
    "  bead-claimed:\n"
    "    exclusions:\n"
    "      - path: '*.py'\n"
    "        reason: 'top-level helper scripts are not bead-scoped'\n"
    "        until: 'BDL-999'\n"
)


class TestTheTraversalMatrix:
    """Every spelling of "somewhere else", against a declared ``scripts/**``.

    ``WARN`` means the guard ran (the exclusion did not apply); ``SKIP`` means
    it was exempted. The reason column of each row says what a wrong answer
    would cost, because the failure mode is silent either way: a wrong ``SKIP``
    is an unguarded write carrying a reassuring reason, a wrong ``WARN`` is an
    exclusion the author declared and does not get.
    """

    @pytest.mark.parametrize(
        ("label", "path", "expected", "resolves_to"),
        [
            ("bare traversal", "scripts/../src/app.py", GuardOutcome.WARN, "src/app.py"),
            ("dot-prefixed", "./scripts/../src/app.py", GuardOutcome.WARN, "src/app.py"),
            ("dot inside", "scripts/./../src/app.py", GuardOutcome.WARN, "src/app.py"),
            ("doubled separator", "scripts//../src/app.py", GuardOutcome.WARN, "src/app.py"),
            ("traversal then back in", "scripts/../scripts/x.sh", GuardOutcome.SKIP, ""),
            ("honest member", "scripts/deploy.sh", GuardOutcome.SKIP, ""),
            ("directory form", "scripts/../src/", GuardOutcome.WARN, "src"),
        ],
    )
    def test_the_verdict_follows_the_file_not_the_spelling(
        self, tmp_path, write_flow_yml, make_guard_probes, label, path, expected, resolves_to
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, path)

        assert verdict.outcome is expected, f"{label}: {verdict.why}"
        if resolves_to:
            assert resolves_to in verdict.why, f"{label}: {verdict.why}"


class TestThePathOutsideTheProjectIsNamed:
    """An outside target inherits nothing and the verdict says which file it was."""

    def test_a_sibling_directory_sharing_the_roots_name_is_outside(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """``<root>-evil/app.py`` starts with the root as a STRING but is not in it.

        Pins the containment test against a future rewrite to ``startswith``:
        that refactor looks equivalent, passes every other case in this file,
        and would hand an exclusion to a directory next door.
        """
        root = tmp_path / "proj"
        root.mkdir()
        write_flow_yml(_EXCLUDE_EVERYTHING, root=root)
        evil = tmp_path / "proj-evil" / "app.py"

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=root,
            context={"path": str(evil)},
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.WARN, verdict.why
        assert any("outside the project" in item for item in verdict.not_covered), (
            verdict.not_covered
        )

    def test_a_deep_traversal_above_the_root_names_the_resolved_target(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDE_EVERYTHING)

        verdict = _verdict(tmp_path, make_guard_probes, "../" * 8 + "etc/passwd")

        assert verdict.outcome is GuardOutcome.WARN, verdict.why
        assert any("etc/passwd" in item for item in verdict.not_covered), verdict.not_covered


class TestSymlinksInBothDirections:
    """Resolution follows the link, so the exclusion follows the file it lands on."""

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
    def test_a_link_into_the_excluded_tree_is_excluded(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """The direction the traversal fix must not have broken.

        ``src/link.sh`` -> ``scripts/deploy.sh``: the write lands inside the
        excluded tree, so the declared exemption genuinely applies.
        """
        write_flow_yml(_EXCLUDED_SCRIPTS)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "link.sh").symlink_to(tmp_path / "scripts" / "deploy.sh")

        verdict = _verdict(tmp_path, make_guard_probes, "src/link.sh")

        assert verdict.outcome is GuardOutcome.SKIP, verdict.why

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
    def test_an_exclusion_stops_applying_when_its_directory_is_a_symlink(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """``scripts`` -> ``tools`` makes ``scripts/**`` exempt nothing.

        Consequence of resolving, and the safe direction (the guard runs), but
        it is a declared exclusion that silently stops applying — pinned so the
        behaviour is a decision rather than a surprise. ``--liveness`` does not
        report it either: the pattern matches no *file* only because
        :func:`project_files` does not follow links, and the row it would appear
        in is ``dead_exclusions``.
        """
        write_flow_yml(_EXCLUDED_SCRIPTS)
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (tmp_path / "scripts").symlink_to(tmp_path / "tools", target_is_directory=True)

        verdict = _verdict(tmp_path, make_guard_probes, "scripts/deploy.sh")

        assert verdict.outcome is GuardOutcome.WARN, verdict.why
        assert "tools/deploy.sh" in verdict.why


class TestThePathThatIsTheProjectRoot:
    """A target normalising to the root itself is inside it, and named ``.``."""

    @pytest.mark.parametrize("spelling", [".", "./", "src/.."])
    def test_the_root_is_inside_and_relative_to_itself(
        self, tmp_path, write_flow_yml, make_guard_probes, spelling
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, spelling)

        assert verdict.outcome is GuardOutcome.WARN, verdict.why
        assert not any("outside the project" in item for item in verdict.not_covered), (
            verdict.not_covered
        )

    def test_the_absolute_root_is_not_reported_as_an_absent_path(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """It is a supplied path, so the "no path" note would be false about it."""
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, str(tmp_path))

        assert not any("supplied no path" in item for item in verdict.not_covered), (
            verdict.not_covered
        )

    def test_a_catch_all_exclusion_still_covers_the_root(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDE_EVERYTHING)

        assert _verdict(tmp_path, make_guard_probes, ".").outcome is GuardOutcome.SKIP


class TestTheAcceptedPathShape:
    """What this guard accepts as an edit target, and what it refuses outright.

    Two bypasses in a row — the C1 traversal, then a backslash and a NUL — came
    from one place: an arbitrary, model-supplied string was NORMALISED, and every
    normalisation is a guess about what the harness will actually write. So the
    input is narrowed rather than the guessing extended.

    Accepted: a non-empty string with no C0 control character or DEL, no
    backslash, no leading ``~``, and encodable for this filesystem. Anything else
    is REFUSED — never repaired, never resolved, never matched against an
    exclusion.
    """

    @pytest.mark.parametrize(
        ("label", "raw", "offence"),
        [
            ("a Windows separator", "src\\app.py", "backslash"),
            ("a Windows absolute path", "C:\\Users\\a\\app.py", "backslash"),
            ("a NUL byte", "src/app.py\x00", "control character"),
            ("a newline", "src/app\n.py", "control character"),
            ("a DEL byte", "src/app\x7f.py", "control character"),
            ("an escape byte", "src/\x1b[31mapp.py", "control character"),
            ("a lone surrogate", "src/\ud800.py", "cannot be encoded"),
            ("a home-relative path", "~/secrets.env", "'~'"),
            ("another user's home", "~root/.ssh/authorized_keys", "'~'"),
        ],
    )
    def test_a_path_outside_the_shape_is_refused_and_the_reason_names_the_offence(
        self, tmp_path, label, raw, offence
    ) -> None:
        resolved = resolve_edit_path(raw, tmp_path)

        assert resolved.scope is PathScope.MALFORMED, f"{label}: {resolved}"
        assert resolved.relative is None, label
        assert offence in resolved.rejection, f"{label}: {resolved.rejection!r}"

    @pytest.mark.parametrize(
        "raw",
        [
            "src/app.py",
            "./src/app.py",
            "src/../src/app.py",
            "src/a b/c d.py",
            "src/файл.py",
            "src/app.py ",
            "src/percent%20encoded.py",
            "src/~backup.py",
            "src/\udcff.py",
        ],
    )
    def test_an_ordinary_path_is_still_accepted(self, tmp_path, raw) -> None:
        """The shape must be narrow, not hostile.

        ``%20`` is never decoded, so the pattern sees the name the writer will
        use; ``~`` matters only as the first character; ``\\udcff`` is a real
        non-UTF-8 byte that ``os.fsencode`` round-trips, so it names a file that
        can actually exist.
        """
        resolved = resolve_edit_path(raw, tmp_path)

        assert resolved.scope is PathScope.INSIDE, f"{raw!r}: {resolved}"

    def test_a_resolution_the_os_refuses_becomes_a_refusal_not_a_traceback(
        self, tmp_path, monkeypatch
    ) -> None:
        """The last resort behind the shape gate, exercised deliberately.

        No known input reaches it once the shape is enforced — which is exactly
        why it is here and why it is tested with an injected failure: the
        property being held is "an unknown input becomes a refusal", and an
        unknown input cannot, by definition, be written down.
        """
        from pathlib import Path as _Path

        def explode(self: _Path, *args: object, **kwargs: object) -> _Path:
            msg = "some future libc refusal"
            raise OSError(msg)

        monkeypatch.setattr(_Path, "resolve", explode)

        resolved = resolve_edit_path("src/app.py", tmp_path)

        assert resolved.scope is PathScope.MALFORMED, resolved
        assert "some future libc refusal" in resolved.rejection


class TestARefusedPathIsAVerdictNotATraceback:
    """A path the guard will not interpret still ends in an answer.

    The answer is ``error`` and it carries the BLOCKING exit code. The reasoning,
    written out because the choice is the whole point: ``skip`` reads as "not
    applicable" and lets the edit through; ``warn`` exits 1, which the shipped
    adapter's harness treats as non-blocking — that is precisely how the NUL got
    past everything; and exit 3 is reserved for a usage or configuration error,
    which is a defect in the project's own files rather than a statement about
    this edit. "I cannot tell what you are about to write" must stop what is
    about to be written, and in the harness this ships an adapter for, only 2
    stops it.
    """

    def test_the_guard_answers_instead_of_raising(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_TOP_LEVEL_PY)

        verdict = _verdict(tmp_path, make_guard_probes, "src\\app.py")

        assert verdict.outcome is GuardOutcome.ERROR, verdict.why
        assert "backslash" in verdict.why

    def test_a_nul_reaches_a_verdict_where_it_used_to_raise(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, "src/app.py\x00")

        assert verdict.outcome is GuardOutcome.ERROR, verdict.why

    def test_the_same_file_spelled_for_another_os_is_no_longer_exempted(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """F1: ``src\\app.py`` skipped on ``*.py`` while the write landed on src/app.py."""
        write_flow_yml(_EXCLUDED_TOP_LEVEL_PY)

        posix = _verdict(tmp_path, make_guard_probes, "src/app.py")
        windows = _verdict(tmp_path, make_guard_probes, "src\\app.py")

        assert posix.outcome is GuardOutcome.WARN, posix.why
        assert windows.outcome is GuardOutcome.ERROR, windows.why
        assert "*.py" not in windows.why

    def test_a_catch_all_exclusion_does_not_swallow_a_refused_path(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """The refusal is decided before any exclusion is matched, on purpose."""
        write_flow_yml(_EXCLUDE_EVERYTHING)

        verdict = _verdict(tmp_path, make_guard_probes, "src/app.py\x00")

        assert verdict.outcome is GuardOutcome.ERROR, verdict.why

    def test_the_refusal_names_what_it_did_not_check_and_how_to_proceed(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, "src\\app.py")

        assert verdict.not_covered, "an error that names nothing cannot be acted on"
        assert any("refused" in item for item in verdict.not_covered), verdict.not_covered
        assert verdict.remediation

    def test_the_refusal_carries_the_blocking_code_not_the_warn_code(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """Exit 1 is the warn code, which a harness reads as "carry on"."""
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, "src\\app.py")

        assert verdict.exit_code == 2

    def test_a_guard_configured_off_stays_off(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """Refusing the input does not override a declared, deliberate opt-out.

        ``off`` is a human decision recorded in flow.yml; the guard never looks
        at the path at all, so there is nothing to be misled about.
        """
        write_flow_yml(
            "guards:\n  bead-claimed:\n    strictness: {default: 'off'}\n"
        )

        verdict = _verdict(tmp_path, make_guard_probes, "src\\app.py")

        assert verdict.outcome is GuardOutcome.SKIP, verdict.why
        assert "off" in verdict.why


class TestNoInvocationEndsWithoutARecord:
    """Every invocation that named a guard leaves a firing record.

    F2 cost two things, and the second was the worse one: the NUL produced no
    record, so ``guard --liveness`` went on showing an older ``skip`` and the
    event did not exist in the one report whose entire product is honesty about
    dead gates. A crash is a verdict of "I could not tell" and is recorded as
    one.
    """

    @staticmethod
    def _run(tmp_path, monkeypatch, payload: str):
        from click.testing import CliRunner

        from beadloom.application.guards.contract import GuardProbes
        from beadloom.services.cli import main
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        return CliRunner().invoke(
            main,
            ["guard", "bead-claimed", "--project", str(tmp_path), "--hook", "claude-code"],
            input=payload,
        )

    @staticmethod
    def _records(tmp_path):
        from beadloom.application.guards.firing import read_firings

        return read_firings(tmp_path)

    def test_a_nul_from_a_json_payload_blocks_and_is_recorded(
        self, tmp_path, write_flow_yml, monkeypatch
    ) -> None:
        """The reachable route, verbatim: JSON carries a NUL as ``\\u0000``."""
        write_flow_yml(_EXCLUDED_SCRIPTS)
        payload = (
            '{"hook_event_name": "PreToolUse", "tool_name": "Write", '
            '"tool_input": {"file_path": "src/app.py\\u0000"}}'
        )

        result = self._run(tmp_path, monkeypatch, payload)
        records = self._records(tmp_path)

        assert result.exception is None or isinstance(result.exception, SystemExit), (
            result.output
        )
        assert result.exit_code == 2, result.output
        assert [record.outcome for record in records] == ["error"], records

    def test_a_backslash_path_blocks_instead_of_skipping(
        self, tmp_path, write_flow_yml, monkeypatch
    ) -> None:
        write_flow_yml(_EXCLUDED_TOP_LEVEL_PY)
        payload = json.dumps(
            {"hook_event_name": "PreToolUse", "tool_input": {"file_path": "src\\app.py"}}
        )

        result = self._run(tmp_path, monkeypatch, payload)

        assert result.exit_code == 2, result.output
        assert [record.outcome for record in self._records(tmp_path)] == ["error"]

    def test_an_unexpected_failure_becomes_a_recorded_verdict(
        self, tmp_path, write_flow_yml, monkeypatch
    ) -> None:
        """Whatever breaks inside evaluation, the invocation still ends in a record.

        The shape gate closes the two failures we know about; this closes the
        third one nobody has typed yet.
        """
        def explode(*_args: object, **_kwargs: object) -> None:
            msg = "a future defect nobody has written yet"
            raise RuntimeError(msg)

        write_flow_yml(_EXCLUDED_SCRIPTS)
        monkeypatch.setattr(
            "beadloom.application.guards.invocation.evaluate_guard", explode
        )
        payload = json.dumps(
            {"hook_event_name": "PreToolUse", "tool_input": {"file_path": "src/app.py"}}
        )

        result = self._run(tmp_path, monkeypatch, payload)
        records = self._records(tmp_path)

        assert result.exception is None or isinstance(result.exception, SystemExit), (
            result.output
        )
        assert result.exit_code == 2, result.output
        assert [record.outcome for record in records] == ["error"], records
        assert "a future defect nobody has written yet" in records[-1].why

    def test_a_config_error_reaching_a_hook_is_recorded_and_blocks(
        self, tmp_path, write_flow_yml, monkeypatch
    ) -> None:
        """A broken flow.yml is recorded, and through a hook it exits 2.

        It exited 3 until BDL-061.33, and 3 blocks nothing in the harness this
        adapter binds to — so the single file of this feature an adopter edits by
        hand could switch every bound guard off by a mistyped line. Exit 3 still
        exists for a shell caller (BDL-061.2), where a configuration defect must
        stay distinguishable from a guard that fired and no edit is waiting on
        the answer; see ``tests/test_guards_fail_closed.py`` for both halves.
        """
        write_flow_yml(
            "guards:\n  bead-claimed:\n    exclusions:\n      - path: 'x/**'\n"
        )
        payload = json.dumps(
            {"hook_event_name": "PreToolUse", "tool_input": {"file_path": "src/app.py"}}
        )

        result = self._run(tmp_path, monkeypatch, payload)

        assert result.exit_code == 2, result.output
        assert [record.outcome for record in self._records(tmp_path)] == ["error"]

    def test_an_unregistered_guard_name_records_nothing(
        self, tmp_path, monkeypatch, guard_project
    ) -> None:
        """The one invocation with nothing to record: there is no such guard.

        Recording it would invent a row in a report that is organised by guard,
        and the caller's own shell already carries the error.
        """
        from click.testing import CliRunner

        from beadloom.application.guards.contract import GuardProbes
        from beadloom.services.cli import main
        from beadloom.services.commands import guard as guard_cmd

        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        result = CliRunner().invoke(
            main, ["guard", "no-such-guard", "--project", str(tmp_path)]
        )

        assert result.exit_code == 3, result.output
        assert self._records(tmp_path) == ()


class TestASymlinkLoopEndsInAVerdictAndNeverInATraceback:
    """A loop reaches a verdict on every interpreter — including those that raise.

    MEASURED with real interpreters (``uv run --python X``), for the link itself
    and for a path through it, on ``a -> b -> a``::

        3.10.1   RuntimeError("Symlink loop from '<root>/a'")
        3.11.13  RuntimeError("Symlink loop from '<root>/a'")
        3.12.12  RuntimeError("Symlink loop from '<root>/a'")
        3.13.7   returns the path unresolved, raises nothing

    That divergence is the whole reason this class was rewritten (BDL-061.36).
    Its predecessor asserted ``scope is INSIDE`` and ``relative == 'a/x.py'`` —
    the 3.13 answer — under a docstring stating as a fact that ``resolve()``
    does not raise on a loop. On 3.10-3.12 the resolution raised ``RuntimeError``,
    which is neither ``OSError`` nor ``ValueError`` and so escaped the handler
    sitting directly beneath a comment calling the case unreachable. Two CI jobs
    failed on tests that were green here, because "green on this machine" and
    "the property holds" were the same sentence in a single-interpreter suite.

    So nothing below asserts what THIS interpreter does with a loop. The
    property is asserted instead — *a supplied path comes back as a scope, and
    a resolution that refuses comes back as a stated refusal* — twice over:
    once against the real filesystem, where the platform decides which branch
    runs, and once with the exception INJECTED, so the raising branch is covered
    on an interpreter that will not produce it. A test that can only run where
    the bug cannot appear is not coverage of the bug.
    """

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
    @pytest.mark.parametrize("target", ["a", "a/x.py"])
    def test_a_real_loop_comes_back_as_a_scope_whatever_this_platform_does(
        self, tmp_path, target
    ) -> None:
        """Both branches are correct; ending in an exception is not one of them."""
        (tmp_path / "a").symlink_to(tmp_path / "b")
        (tmp_path / "b").symlink_to(tmp_path / "a")

        resolved = resolve_edit_path(target, tmp_path)

        if resolved.scope is PathScope.MALFORMED:
            assert resolved.rejection, resolved
        else:
            assert resolved.scope is PathScope.INSIDE, resolved
            assert resolved.relative == target, resolved

    @pytest.mark.parametrize(
        ("label", "error"),
        [
            (
                "3.10-3.12's RuntimeError, which no handler caught",
                RuntimeError("Symlink loop from '/p/a'"),
            ),
            (
                "the ELOOP the CI log also showed",
                OSError(errno.ELOOP, "Too many levels of symbolic links"),
            ),
            ("a ValueError, as an embedded NUL once produced", ValueError("nul")),
            (
                "an exception class nobody has enumerated yet",
                LookupError("something the OS layer may do next"),
            ),
        ],
    )
    def test_an_injected_refusal_becomes_a_refusal_with_a_reason(
        self, tmp_path, monkeypatch, label, error
    ) -> None:
        """The raising branch, on an interpreter that does not raise.

        The last row is the point of the parametrisation rather than a filler:
        the handler is meant to be as wide as the sentence "no supplied path
        ends in a traceback", and a handler enumerating three exception classes
        would satisfy the first three rows and fail the fourth — which is
        exactly how ``RuntimeError`` got out.
        """
        _fail_resolution_of(monkeypatch, "a", error)

        resolved = resolve_edit_path("a/x.py", tmp_path)

        assert resolved.scope is PathScope.MALFORMED, label
        assert type(error).__name__ in resolved.rejection, resolved.rejection

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
    def test_the_guard_reaches_a_verdict_through_a_real_loop(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)
        (tmp_path / "a").symlink_to(tmp_path / "b")
        (tmp_path / "b").symlink_to(tmp_path / "a")

        verdict = _verdict(tmp_path, make_guard_probes, "a/x.py")

        assert verdict.outcome in {GuardOutcome.WARN, GuardOutcome.ERROR}, verdict
        assert verdict.why, verdict

    def test_the_guard_reaches_a_verdict_when_resolution_raises(
        self, tmp_path, monkeypatch, write_flow_yml, make_guard_probes
    ) -> None:
        """What an adopter on 3.10 gets: a blocking verdict that says why.

        Stated because it is a real behaviour difference and not a detail: on an
        interpreter that raises, a loop is an ``error`` at exit 2 — the edit is
        refused with a reason — while on 3.13 the same edit is evaluated. The
        divergence belongs to ``Path.resolve``; what this slice owes is that
        neither side is a traceback and both sides say what they did.
        """
        write_flow_yml(_EXCLUDED_SCRIPTS)
        _fail_resolution_of(monkeypatch, "a", RuntimeError("Symlink loop from '/p/a'"))

        verdict = _verdict(tmp_path, make_guard_probes, "a/x.py")

        assert verdict.outcome is GuardOutcome.ERROR, verdict
        assert "RuntimeError" in verdict.why, verdict.why
        assert verdict.remediation, verdict
