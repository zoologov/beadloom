"""The shipped test role states what a test is, for the adopter who composes it.

The standards live in two layers because they are two kinds of fact. What a
test is — one behaviour, arrange/act/assert, no shared state, named by the
behaviour, placed by the mirror, helpers in one support package, the root found
one way, explicit roots — holds in any stack, so the CORE states it. Where those
things are in a Python project — ``tests/<kind>/<mirrored path>``, ``tests/support``,
``pyproject.toml``, ``tmp_path`` — is the Python overlay's.

Neither layer may carry a fact about this repository: an adopter receives the
shipped fragments verbatim, and a bead id or a Beadloom source path in them is a
sentence about somebody else's project.
"""

from __future__ import annotations

import re

import pytest

from beadloom.onboarding.role_composer import compose_role, roles_templates_root

#: The heading the standards live under, in the core fragment.
_SECTION_HEADING = "### What a test is"

#: One lead phrase per standard, in the order the core states them.
STANDARDS = (
    "One behaviour per test",
    "Arrange, act, assert",
    "No shared mutable state",
    "Named by the behaviour",
    "Placed by the mirror",
    "Shared helpers in one support package",
    "The repository root is found one way",
    "Explicit roots, never the working directory",
)

#: What the Python overlay must make concrete.
PYTHON_FACTS = (
    "tests/unit/",
    "tests/integration/",
    "tests/support/",
    "tests:",
    "pyproject.toml",
    "tmp_path",
)

#: Words that belong to one stack, and so not to the core's standards.
_STACK_WORDS = re.compile(r"\.py\b|pytest|pyproject|conftest|tmp_path|__file__")

#: Facts about this repository that must not ship.
_THIS_REPOSITORY = re.compile(r"beadloom-[a-z0-9]{4}|\bBDL-\d|\bBEAD-\d|src/beadloom/")


def _section(text: str) -> str:
    _, _, after = text.partition(_SECTION_HEADING)
    assert after, f"no {_SECTION_HEADING!r} section"
    section, _, _ = after.partition("\n### ")
    return section


def _fragment(*parts: str) -> str:
    return roles_templates_root().joinpath(*parts).read_text(encoding="utf-8")


def _shipped_test_fragments() -> list[str]:
    root = roles_templates_root()
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("test.md.txt"))


class TestTheCoreStatesEachStandard:
    @pytest.mark.parametrize("architecture", ["ddd", "fsd"])
    @pytest.mark.parametrize("stack", [("python",), ("typescript",)])
    def test_every_composed_test_role_states_every_standard(
        self, architecture: str, stack: tuple[str, ...]
    ) -> None:
        section = _section(compose_role("test", architecture=architecture, stack=stack))

        missing = [standard for standard in STANDARDS if f"**{standard}" not in section]

        assert missing == []

    def test_the_standards_are_stated_in_the_order_a_test_is_written(self) -> None:
        section = _section(_fragment("core", "test.md.txt"))

        positions = [section.index(f"**{standard}") for standard in STANDARDS]

        assert positions == sorted(positions)

    def test_the_core_states_them_without_naming_a_stack(self) -> None:
        section = _section(_fragment("core", "test.md.txt"))

        assert _STACK_WORDS.findall(section) == []


class TestThePythonOverlayMakesThemConcrete:
    def test_the_overlay_names_where_each_standard_lives(self) -> None:
        overlay = _fragment("stack", "python", "test.md.txt")

        missing = [fact for fact in PYTHON_FACTS if fact not in overlay]

        assert missing == []

    def test_the_overlay_no_longer_prescribes_a_flat_folder(self) -> None:
        overlay = _fragment("stack", "python", "test.md.txt")

        assert "flat, no subdirs" not in overlay


class TestNothingShippedDescribesThisRepository:
    def test_the_population_is_every_shipped_test_fragment(self) -> None:
        fragments = _shipped_test_fragments()

        assert "core/test.md.txt" in fragments
        assert "stack/python/test.md.txt" in fragments

    @pytest.mark.parametrize("fragment", _shipped_test_fragments())
    def test_no_shipped_test_fragment_names_a_bead_an_epic_or_this_source_tree(
        self, fragment: str
    ) -> None:
        text = _fragment(*fragment.split("/"))

        assert _THIS_REPOSITORY.findall(text) == []
