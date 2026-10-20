"""The files that carry the composed core, compared and refreshed as one (BDL-083 S2R Major 1).

Unit tests of :mod:`beadloom.onboarding.composed_core` over hand-built texts: the
comparison blanks the rendered regions on every side, the digest it records is
blind to them, and the refresh reaches every carrier on disk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.composed_core import (
    CLAUDE_MD_RELPATH,
    core_carriers,
    core_digest,
    core_state,
    refresh_core_regions,
)
from beadloom.onboarding.flow_manifest import ArtifactState
from beadloom.onboarding.tool_reach import cursor_core_rule_relpath

if TYPE_CHECKING:
    from pathlib import Path

_CURSOR_CORE = str(cursor_core_rule_relpath())


def _core(version: str, *, tail: str = "") -> str:
    return (
        "# CLAUDE.md\n\n## 0.1 Project: acme\n\n"
        "<!-- beadloom:auto-start project-info -->\n"
        f"- **Current version:** {version}\n"
        "<!-- beadloom:auto-end -->\n\n## 1. Rules\n\nRun the Gate.\n"
        f"{tail}"
    )


def _project(tmp_path: Path, version: str) -> Path:
    root = tmp_path / "acme"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "acme"\nversion = "{version}"\n', encoding="utf-8"
    )
    return root


def _carry(root: Path, relpath: str, text: str) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestTheCarriers:
    def test_are_claude_md_and_the_cursor_core_rule(self) -> None:
        assert core_carriers() == (CLAUDE_MD_RELPATH, _CURSOR_CORE)


class TestTheComparison:
    def test_a_moved_region_is_not_a_moved_body(self) -> None:
        state = core_state(
            on_disk=_core("1.0.0"),
            expected=_core("2.0.0"),
            recorded=core_digest(_core("1.0.0")),
        )
        assert state is ArtifactState.CLEAN

    def test_a_body_changed_outside_the_regions_is_a_hand_edit(self) -> None:
        state = core_state(
            on_disk=_core("1.0.0", tail="\n## OUR RULE\n"),
            expected=_core("1.0.0"),
            recorded=core_digest(_core("0.1.0")),
        )
        assert state is ArtifactState.HAND_EDITED

    def test_a_body_we_wrote_under_an_old_composition_is_stale(self) -> None:
        old = _core("1.0.0", tail="\nOld core text.\n")
        state = core_state(
            on_disk=old.replace("1.0.0", "1.5.0"),
            expected=_core("2.0.0"),
            recorded=core_digest(old),
        )
        assert state is ArtifactState.STALE

    def test_an_alternate_is_compared_with_its_regions_blanked(self) -> None:
        state = core_state(
            on_disk=_core("1.0.0", tail="\nShipped only.\n"),
            expected=_core("1.0.0", tail="\nWith a project layer.\n"),
            recorded=None,
            alternates=(_core("9.9.9", tail="\nShipped only.\n"),),
        )
        assert state is ArtifactState.STALE

    def test_the_digest_does_not_see_a_region(self) -> None:
        assert core_digest(_core("1.0.0")) == core_digest(_core("2.0.0"))
        assert core_digest(_core("1.0.0")) != core_digest(_core("1.0.0", tail="x\n"))


class TestTheRefresh:
    def test_re_renders_the_region_in_every_carrier(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "2.0.0")
        _carry(root, CLAUDE_MD_RELPATH, _core("1.0.0"))
        _carry(root, _CURSOR_CORE, "---\nalwaysApply: true\n---\n" + _core("1.0.0"))
        changed = refresh_core_regions(root)
        assert changed == {CLAUDE_MD_RELPATH: ["project-info"], _CURSOR_CORE: ["project-info"]}
        for relpath in core_carriers():
            assert "- **Current version:** 2.0.0" in (root / relpath).read_text(encoding="utf-8")

    def test_a_dry_run_names_the_regions_and_writes_nothing(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "2.0.0")
        _carry(root, _CURSOR_CORE, _core("1.0.0"))
        assert refresh_core_regions(root, dry_run=True) == {_CURSOR_CORE: ["project-info"]}
        assert (root / _CURSOR_CORE).read_text(encoding="utf-8") == _core("1.0.0")

    def test_an_absent_or_current_carrier_is_not_in_the_result(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "2.0.0")
        refresh_core_regions(root)
        _carry(root, CLAUDE_MD_RELPATH, _core("1.0.0"))
        refresh_core_regions(root)
        assert refresh_core_regions(root) == {}
