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
