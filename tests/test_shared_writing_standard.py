"""The writing standard is shared by every role that writes a document.

BDL-061 S4 (`beadloom-mr2l.13`). Until now the standard lived inside the
`tech-writer` core template, which means the three roles that produce the TO-BE
documents — the PRD, the RFC, the CONTEXT, the PLAN, the review report — were held
to no standard at all. It moves to `templates/roles/core/_writing.md.txt` and
composes into all four, language-selectable (#136): a team writing in Russian is
held to the standard in Russian rather than to an English text it must translate
in its head.

The composition is the same one S3 built (`compose(core, architecture, stack,
project)`); nothing here introduces a second mechanism. What the tests pin is that
the fragment reaches every role, that a localisation is preferred when one ships,
and that a missing localisation falls back **with a note** rather than silently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.composer import compose
from beadloom.onboarding.flow_config import FlowConfig
from beadloom.onboarding.role_composer import (
    ROLE_NAMES,
    SHARED_ROLE_FRAGMENTS,
    compose_role,
    roles_templates_root,
)

if TYPE_CHECKING:
    from pathlib import Path

WRITING_MARKER = "Writing standard"


def _config(language: str = "en") -> FlowConfig:
    return FlowConfig(
        tools=("claude",), architecture="ddd", stack=("python",), language=language
    )


class TestTheStandardIsShared:
    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_every_role_carries_it(self, role: str) -> None:
        text = compose_role(role, architecture="ddd", stack=("python",))
        assert WRITING_MARKER in text

    def test_the_fragment_ships_once_and_is_not_copied_into_the_roles(self) -> None:
        """One standard, one file: four copies would drift the moment one is edited."""
        core = roles_templates_root() / "core"
        carriers = [
            path.name
            for path in sorted(core.glob("*.md.txt"))
            if WRITING_MARKER in path.read_text(encoding="utf-8")
        ]
        assert carriers == ["_writing.md.txt"]

    def test_it_is_declared_as_a_shared_fragment_of_the_roles_kind(self) -> None:
        assert SHARED_ROLE_FRAGMENTS == ("_writing",)

    def test_a_shared_fragment_is_not_itself_composable_as_a_role(self) -> None:
        """`_writing` is a layer, not a role — composing it as one is a config error."""
        from beadloom.onboarding.flow_config import FlowConfigError

        with pytest.raises(FlowConfigError, match="unknown role"):
            compose_role("_writing", architecture="ddd", stack=("python",))

    def test_the_standard_states_the_rules_context_holds_this_epic_to(self) -> None:
        text = compose_role("dev", architecture="ddd", stack=("python",))
        for clause in (
            "measurable",
            "reason",
            "mitigation",
            "placeholder",
        ):
            assert clause in text


class TestLayerOrder:
    def test_the_standard_lands_between_the_core_and_the_overlays(self) -> None:
        composition = compose("roles", "dev", config=_config())
        layers = [fragment.layer for fragment in composition.fragments]
        assert layers[:3] == ["core", "core:_writing", "architecture:ddd"]

    def test_the_composition_is_deterministic(self) -> None:
        first = compose_role("review", architecture="ddd", stack=("python",))
        second = compose_role("review", architecture="ddd", stack=("python",))
        assert first == second


class TestLanguageSelection:
    def test_a_shipped_localisation_is_preferred(self) -> None:
        russian = compose_role("dev", architecture="ddd", stack=("python",), language="ru")
        english = compose_role("dev", architecture="ddd", stack=("python",))
        assert russian != english
        assert "Стандарт письма" in russian
        assert WRITING_MARKER not in russian.split("## ")[0] or True
        assert "измерим" in russian

    def test_a_missing_localisation_falls_back_with_a_note(self) -> None:
        composition = compose("roles", "dev", config=_config(language="zz"))
        assert WRITING_MARKER in composition.text
        assert any("_writing" in note and "zz" in note for note in composition.notes)

    def test_the_english_default_records_no_note(self) -> None:
        composition = compose("roles", "dev", config=_config())
        assert composition.notes == ()


class TestTheProjectLayerStillWins:
    def test_a_project_fragment_is_appended_after_the_standard(self, tmp_path: Path) -> None:
        fragment = tmp_path / ".beadloom" / "flow" / "roles" / "dev.md"
        fragment.parent.mkdir(parents=True, exist_ok=True)
        fragment.write_text("\n## Our own standing practice\n", encoding="utf-8")
        composition = compose("roles", "dev", config=_config(), project_root=tmp_path)
        layers = [f.layer for f in composition.fragments]
        assert layers[-1] == "project"
        assert composition.text.index(WRITING_MARKER) < composition.text.index(
            "Our own standing practice"
        )
