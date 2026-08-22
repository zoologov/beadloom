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

import sys

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

    def test_a_blank_path_is_absent(self, tmp_path) -> None:
        assert resolve_edit_path("   ", tmp_path).scope is PathScope.ABSENT

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


class TestAWindowsStyleSeparator:
    """RECORDED GAP: a backslash path is read as one filename on POSIX.

    Measured, not reasoned about. ``src\\app.py`` supplied to a POSIX Beadloom
    resolves to a single top-level component, because a backslash is a legal
    character in a POSIX file name and the resolver cannot know the harness meant
    a directory separator.

    Against ``scripts/**`` that is the safe direction (the guard runs anyway).
    Against a single-component pattern such as ``*.py`` it is the C1 shape again:
    the guard SKIPS, the printed reason names an exclusion that is false about the
    file the harness will write, and ``not_covered`` says nothing about the
    ambiguity. Reachable from Claude Code on Windows, from WSL, and from any model
    that writes a Windows path.

    Pinned rather than fixed here (this is the verification bead): the fix is a
    ``not_covered`` note when the target contains a backslash, or normalising
    separators before resolution. Either reddens the second test below.
    """

    def test_a_backslash_path_does_not_bypass_a_directory_pattern(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        verdict = _verdict(tmp_path, make_guard_probes, "scripts\\..\\src\\app.py")

        assert verdict.outcome is GuardOutcome.WARN, verdict.why

    def test_a_backslash_path_does_bypass_a_single_component_pattern(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_TOP_LEVEL_PY)

        posix = _verdict(tmp_path, make_guard_probes, "src/app.py")
        windows = _verdict(tmp_path, make_guard_probes, "src\\app.py")

        assert posix.outcome is GuardOutcome.WARN, posix.why
        # The gap: the same file, spelled for a different OS, is exempted.
        assert windows.outcome is GuardOutcome.SKIP, windows.why
        assert "*.py" in windows.why
        # And nothing in the verdict warns the reader that the separator was
        # read as part of the file name. That silence is the defect.
        assert not any("\\" in item for item in windows.not_covered), windows.not_covered


class TestANullByteInTheSuppliedPath:
    """RECORDED GAP: resolution raises, so the guard produces no verdict at all.

    Introduced BY the traversal fix: ``Path.resolve`` calls ``lstat``, which
    rejects an embedded NUL with ``ValueError``; the lexical matching it replaced
    never touched the filesystem. :func:`_resolved` catches ``OSError`` only, so
    the exception escapes ``evaluate_guard``.

    Cost, measured end-to-end through the CLI: the process exits **1** — the code
    reserved for ``warn``, which a harness treats as non-blocking — so a path with
    a NUL downgrades a ``block`` to a message, and ``record_firing`` never runs, so
    the firing log has no evidence the edit happened. Reachable: the path comes
    from ``tool_input.file_path`` in a JSON payload, and JSON can carry ``\\u0000``.

    The fix is one exception type (``except (OSError, ValueError)``), which would
    make both assertions below fail. That is the point of pinning them.
    """

    _NUL_PATH = "src/app.py\x00"

    def test_resolution_raises_instead_of_classifying_the_target(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="null"):
            resolve_edit_path(self._NUL_PATH, tmp_path)

    def test_the_guard_produces_no_verdict_for_it(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)

        with pytest.raises(ValueError, match="null"):
            _verdict(tmp_path, make_guard_probes, self._NUL_PATH)

    def test_the_cli_exits_on_the_warn_code_with_no_firing_recorded(
        self, tmp_path, write_flow_yml, monkeypatch
    ) -> None:
        """The reachable route: a hook payload, through the real command."""
        import json as _json

        from click.testing import CliRunner

        from beadloom.application.guards.contract import GuardProbes
        from beadloom.services.cli import main
        from beadloom.services.commands import guard as guard_cmd

        write_flow_yml(_EXCLUDED_SCRIPTS)
        monkeypatch.setattr(guard_cmd, "_probes", lambda _root: GuardProbes())
        payload = _json.dumps(
            {"hook_event_name": "PreToolUse", "tool_input": {"file_path": self._NUL_PATH}}
        )

        result = CliRunner().invoke(
            main,
            ["guard", "bead-claimed", "--project", str(tmp_path), "--hook", "claude-code"],
            input=payload,
        )

        assert isinstance(result.exception, ValueError), result.output
        assert result.exit_code == 1, result.output
        assert not (tmp_path / ".beadloom" / "guard-firings.jsonl").exists()


class TestASymlinkLoopDoesNotRaise:
    """The case :func:`_resolved`'s ``except OSError`` names cannot actually occur.

    ``Path.resolve()`` defaults to ``strict=False``, and since 3.6 that returns
    the longest resolvable prefix instead of raising ``ELOOP``. Measured on
    3.13.7: ``a -> b -> a`` resolves to ``<root>/a`` and no exception is raised,
    for the link itself and for a path through it.

    So the handler is dead for its documented reason — while the exception
    resolution *does* raise (``ValueError`` on an embedded NUL, pinned above) is
    the one it does not catch. Recorded as a finding rather than fixed here.
    """

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
    def test_a_path_through_a_loop_still_classifies_as_inside(self, tmp_path) -> None:
        (tmp_path / "a").symlink_to(tmp_path / "b")
        (tmp_path / "b").symlink_to(tmp_path / "a")

        resolved = resolve_edit_path("a/x.py", tmp_path)

        assert resolved.scope is PathScope.INSIDE
        assert resolved.relative == "a/x.py"

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
    def test_the_guard_still_reaches_a_verdict_through_a_loop(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(_EXCLUDED_SCRIPTS)
        (tmp_path / "a").symlink_to(tmp_path / "b")
        (tmp_path / "b").symlink_to(tmp_path / "a")

        verdict = _verdict(tmp_path, make_guard_probes, "a/x.py")

        assert verdict.outcome is GuardOutcome.WARN, verdict.why
