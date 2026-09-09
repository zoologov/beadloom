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
from beadloom.onboarding.role_duties import CARRIES_MARKER

# The whole CLI, because the check below asks whether a command a role is
# offered is one the root group holds: importing one command module would make
# every other command read as unregistered.
from beadloom.services.cli import main
from beadloom.services.commands.clean_room import clean_room

if TYPE_CHECKING:
    from pathlib import Path

    import click

#: The statement's own words, so a rewrite that drops it is caught.
ROOM_MARKER = "the room it was taken in"

#: What a clean room cannot see. Two spellings, because the sentence may be
#: written either way and this is a shape check, not a spelling check.
CLEAN_ROOM_LIMITS = ("blind", "interaction")

#: A literal interpreter version, which is what a derived checklist must not
#: spell beside its type checker.
_VERSION_RE = re.compile(r"\b\d+\.\d+\b")

#: The duty the rooms fragment carries, and therefore the section boundary the
#: flag check below reads. The marker is machine-readable already — the duty
#: check finds the fragment by it — so the section is derived, not counted in
#: lines.
CLEAN_ROOM_DUTY = "clean-room"

#: An inline code span, which is how every one of these documents writes a
#: command. Anything outside one is prose and is not read as an invocation.
_CODE_SPAN = re.compile(r"`([^`\n]+)`")

#: Where one invocation ends and the next begins inside a single span, so
#: `beadloom reindex && beadloom lint --strict` is two invocations and not one
#: command holding another's flag.
_SEGMENT = re.compile(r"&&|\|\||;|→|->|\|")


def _option_spellings(command: click.Command) -> set[str]:
    """Every spelling of every option *command* accepts, from click itself."""
    return {spelling for param in command.params for spelling in param.opts}


def _flags(segment: str) -> list[str]:
    """The option tokens of one invocation, punctuation stripped."""
    return [
        word.rstrip(".,;:)")
        for word in segment.split()[2:]
        if word.startswith("--")
    ]


def _invocations(text: str) -> list[tuple[str, list[str]]]:
    """Every `beadloom <command> …` a reader of *text* is offered, as (name, flags)."""
    found: list[tuple[str, list[str]]] = []
    for body in _CODE_SPAN.findall(text):
        for segment in _SEGMENT.split(body):
            words = segment.split()
            if len(words) >= 2 and words[0] == "beadloom":
                found.append((words[1], _flags(segment)))
    return found


def _duty_section(fragment_name: str) -> str:
    """The clean-room duty text of a shipped fragment, from its own marker on."""
    fragment = (roles_templates_root() / "core" / fragment_name).read_text(
        encoding="utf-8"
    )
    marker = f"{CARRIES_MARKER}={CLEAN_ROOM_DUTY}"
    _, found, tail = fragment.partition(marker)
    assert found, f"{fragment_name} no longer carries {marker!r}"
    return tail


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


class TestTheDutyOffersTheCommandThatBuildsTheRoom:
    """The prose offers a command; the command's own name decides the words.

    The room's PATH was bound to `room_for` by beadloom-67t1, and the text then
    said nothing about the command that builds it — so the five cores still
    described a by-hand convention while `beadloom clean-room` derived the path,
    refused a directory it had not created and built the room's own interpreter.
    That is the same drift one layer up, and it is bound here the same way: the
    literals below come from click, so renaming the command or one of its
    options reddens the text that offers it.

    THE LIMIT, stated rather than discovered: this binds the SPELLINGS the prose
    offers and never their completeness. Nothing derivable says which of a
    command's options change what a verdict MEANS, so an option added later is
    not reported here — a reader adding one decides whether the duty text has to
    say so.
    """

    def test_the_cli_registers_the_command_the_duty_text_offers(self) -> None:
        """A command the root group no longer holds is a command nobody can run."""
        assert main.commands.get(clean_room.name) is clean_room

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_every_composed_role_is_offered_it_by_name(self, role: str) -> None:
        text = compose_role(role, architecture="ddd", stack=("python",))
        assert f"beadloom {clean_room.name}" in text

    @pytest.mark.parametrize("fragment", ["_rooms.md.txt", "_rooms.ru.md.txt"])
    def test_every_flag_the_duty_offers_is_an_option_of_that_command(
        self, fragment: str
    ) -> None:
        section = _duty_section(fragment)
        offered = {
            flag
            for name, flags in _invocations(section)
            if name == clean_room.name
            for flag in flags
        }
        assert offered, (
            f"{fragment} offers {clean_room.name} with no option at all, so this "
            "check would pass over a duty text that names none"
        )
        assert offered <= _option_spellings(clean_room)

    def test_both_shipped_spellings_offer_the_same_invocation(self) -> None:
        """One duty, two languages. A rename must reach both or this goes red."""
        spellings = {
            fragment: sorted(
                (name, tuple(flags))
                for name, flags in _invocations(_duty_section(fragment))
            )
            for fragment in ("_rooms.md.txt", "_rooms.ru.md.txt")
        }
        assert spellings["_rooms.md.txt"], "the duty text offers no command at all"
        assert spellings["_rooms.md.txt"] == spellings["_rooms.ru.md.txt"]


class TestEveryCommandARoleIsOfferedIsOneItCanRun:
    """The population is derived from the composition, not from a list here.

    A regression guard rather than a red-first assertion, and it is declared as
    one: it was GREEN over the 25 invocations the five composed roles carried
    before this bead, and it was verified to bite by renaming an option of
    `clean-room` in the source, which reddens it. It exists because the duty
    text now offers flags, and a flag in prose is the one kind of instruction
    that fails only in the agent's hands.
    """

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_every_invocation_names_a_registered_command_and_its_own_flags(
        self, role: str
    ) -> None:
        text = compose_role(role, architecture="ddd", stack=("python",))
        wrong: list[str] = []
        for name, flags in _invocations(text):
            command = main.commands.get(name)
            if command is None:
                wrong.append(f"`beadloom {name}` is not a command")
                continue
            spellings = _option_spellings(command)
            wrong.extend(
                f"`beadloom {name}` has no option {flag}"
                for flag in flags
                if flag not in spellings
            )
        assert wrong == [], f"{role}: " + "; ".join(wrong)
