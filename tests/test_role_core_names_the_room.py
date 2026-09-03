"""The completion checklist names ROOMS, not only commands.

`uv run mypy src/` is not a claim until it says which interpreter. BDL-067
reported "green on the tree" nine times from one platform against CI legs on
another; a type check ran against one interpreter locally and four in CI, and an
unnecessary `type: ignore` became a red pull request in eighteen seconds.

Two things are pinned here, and the second is the one a rewrite loses first:
the statement reaches every role from ONE file, and it points at the command
that DERIVES the rooms instead of spelling them. A checklist that spells its
interpreters is a checklist that goes stale the first time a leg changes.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.composer import compose, templates_dir
from beadloom.onboarding.flow_config import FlowConfig
from beadloom.onboarding.role_composer import (
    ROLE_NAMES,
    SHARED_ROLE_FRAGMENTS,
    compose_role,
    roles_templates_root,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The statement's own words, so a rewrite that drops it is caught.
ROOM_MARKER = "the room it was taken in"

#: What a clean room cannot see. Two spellings, because the sentence may be
#: written either way and this is a shape check, not a spelling check.
CLEAN_ROOM_LIMITS = ("blind", "interaction")

#: A literal interpreter version, which is what a derived checklist must not
#: spell beside its type checker.
_VERSION_RE = re.compile(r"\b\d+\.\d+\b")


def _shipped_templates() -> list[Path]:
    return sorted(p for p in templates_dir().rglob("*.txt") if p.is_file())


class TestEveryRoleIsToldWhichRoomItMeasuredIn:
    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_every_composed_role_carries_the_statement(self, role: str) -> None:
        text = compose_role(role, architecture="ddd", stack=("python",))
        assert ROOM_MARKER in text

    def test_it_ships_once_rather_than_being_copied_into_each_role(self) -> None:
        """Five copies drift the moment one is edited — the writing standard's rule."""
        core = roles_templates_root() / "core"
        carriers = [
            path.name
            for path in sorted(core.glob("*.md.txt"))
            if ROOM_MARKER in path.read_text(encoding="utf-8")
        ]
        assert carriers == ["_rooms.md.txt"]

    def test_it_is_declared_as_a_shared_fragment_of_the_roles_kind(self) -> None:
        assert "_rooms" in SHARED_ROLE_FRAGMENTS

    def test_it_points_at_the_command_that_derives_the_rooms(self) -> None:
        text = compose_role("dev", architecture="ddd", stack=("python",))
        assert "beadloom rooms" in text

    def test_it_does_not_claim_a_room_naming_verdict_is_stronger(self) -> None:
        """The verdict is the same verdict. Writing otherwise is the defect."""
        fragment = (roles_templates_root() / "core" / "_rooms.md.txt").read_text(
            encoding="utf-8"
        )
        assert "answerable" in fragment
        for word in ("stronger verdict", "safer", "more reliable"):
            assert word not in fragment.lower()


class TestTheCleanRoomLimitIsStatedWhereTheClaimIsMade:
    def test_every_template_instructing_a_clean_room_states_what_it_cannot_see(
        self,
    ) -> None:
        """The population is derived: any file that adds the instruction is judged.

        A clean-room verification is correct and structurally cannot see an
        interaction with a bead running beside it. Stating the instruction
        without the limit is what left four agents each honestly reporting green
        on a tree that was red.
        """
        offenders = [
            path.relative_to(templates_dir()).as_posix()
            for path in _shipped_templates()
            if "clean room" in (text := path.read_text(encoding="utf-8")).lower()
            and not any(limit in text.lower() for limit in CLEAN_ROOM_LIMITS)
        ]
        assert offenders == []

    def test_the_roles_that_make_the_claim_carry_the_limit(self) -> None:
        for role in ("dev", "test", "review"):
            text = compose_role(role, architecture="ddd", stack=("python",)).lower()
            assert "clean room" in text
            assert any(limit in text for limit in CLEAN_ROOM_LIMITS)


class TestThePythonChecklistNamesItsInterpretersWithoutSpellingThem:
    @pytest.fixture()
    def overlay(self) -> str:
        return (
            templates_dir() / "roles" / "stack" / "python" / "dev.md.txt"
        ).read_text(encoding="utf-8")

    def test_the_type_check_no_longer_stands_as_an_unattributed_command(
        self, overlay: str
    ) -> None:
        assert "beadloom rooms --dimension python" in overlay

    def test_no_line_beside_the_type_checker_spells_a_version(
        self, overlay: str
    ) -> None:
        """A spelled list satisfies every test beside it and then goes stale."""
        spelled = [
            line
            for line in overlay.splitlines()
            if "mypy" in line and _VERSION_RE.search(line)
        ]
        assert spelled == []


class TestTheCompositionStaysDeterministic:
    def test_the_shared_layers_land_between_the_core_and_the_overlays(self) -> None:
        config = FlowConfig(
            tools=("claude",), architecture="ddd", stack=("python",), language="en"
        )
        layers = [f.layer for f in compose("roles", "dev", config=config).fragments]
        assert layers[: len(SHARED_ROLE_FRAGMENTS) + 2] == [
            "core",
            *[f"core:{name}" for name in SHARED_ROLE_FRAGMENTS],
            "architecture:ddd",
        ]

    def test_the_english_default_records_no_note(self) -> None:
        config = FlowConfig(
            tools=("claude",), architecture="ddd", stack=("python",), language="en"
        )
        assert compose("roles", "dev", config=config).notes == ()

    def test_a_shipped_localisation_is_preferred_for_the_room_statement(self) -> None:
        config = FlowConfig(
            tools=("claude",), architecture="ddd", stack=("python",), language="ru"
        )
        composition = compose("roles", "dev", config=config)
        assert not any("_rooms" in note for note in composition.notes)
