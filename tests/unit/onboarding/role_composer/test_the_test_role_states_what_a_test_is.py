"""The shipped test role states what a test is, for the adopter who composes it.

The standards live in two layers because they are two kinds of fact. What a
test is — one behaviour, arrange/act/assert, no shared state, named by the
behaviour, placed by the mirror, helpers in one support package, the root found
one way, explicit roots — holds in any stack, so the CORE states it. Where those
things are in a Python project — ``tests/<kind>/<mirrored path>``, ``tests/support``,
``pyproject.toml``, ``tmp_path`` — is the Python overlay's.

Neither layer may carry a fact about this repository: an adopter receives the
shipped fragments verbatim, and a bead id, a Beadloom source path or a file of this
repository's suite in them is a sentence about somebody else's project. Those live
in the project layer, ``.beadloom/flow/roles/test.md``, which never ships.

A core that points to a stack section points to nothing in a stack that ships no
overlay for the role, so every composed role either carries the section or does
not claim one.
"""

from __future__ import annotations

import re

import pytest

from beadloom.onboarding.flow_config import SUPPORTED_ARCHITECTURES, SUPPORTED_STACKS
from beadloom.onboarding.role_composer import ROLE_NAMES, compose_role, roles_templates_root

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

#: Facts about this repository that must not ship: a work-item id, this source
#: tree, or one named file of a test suite (a pattern such as
#: ``tests/unit/<package path>/test_<module>.py`` is a convention and passes).
_THIS_REPOSITORY = re.compile(
    r"beadloom-[a-z0-9]{4}|\bBDL-\d|\bBEAD-\d|src/beadloom/|\btests/(?:[\w.-]+/)*[\w-]+\.\w+"
)

#: A sentence that states a stack section exists. A core may say what an overlay
#: adds when the stack ships one; it may not say the section is there.
_STACK_SECTION_CLAIM = re.compile(r"\*\*STACK\*\*|stack section below|the STACK section")

#: The heading every stack overlay opens with.
_STACK_HEADING = re.compile(r"^## STACK \(", re.MULTILINE)


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


def _shipped_role_fragments() -> list[str]:
    root = roles_templates_root()
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*.md.txt"))


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

    def test_the_core_says_where_a_placed_file_is_read_back(self) -> None:
        """Placing by the mirror is checkable in any stack, by the command that lists it."""
        section = _section(_fragment("core", "test.md.txt"))
        _, _, placed = section.partition("**Placed by the mirror.**")

        assert "`beadloom ctx <ref-id>`" in placed.partition("\n- **")[0]


class TestEveryComposedRoleHasTheSectionItPointsTo:
    @pytest.mark.parametrize("architecture", SUPPORTED_ARCHITECTURES)
    @pytest.mark.parametrize("stack", SUPPORTED_STACKS)
    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_a_role_without_a_stack_section_does_not_claim_one(
        self, role: str, stack: str, architecture: str
    ) -> None:
        text = compose_role(role, architecture=architecture, stack=(stack,))

        claims = _STACK_SECTION_CLAIM.findall(text)

        assert claims == [] or _STACK_HEADING.search(text) is not None, (role, stack, claims)

    def test_the_population_covers_a_stack_that_ships_no_test_overlay(self) -> None:
        """Otherwise the check above holds of the one stack that has the section."""
        root = roles_templates_root()
        without = [
            stack
            for stack in SUPPORTED_STACKS
            if not (root / "stack" / stack / "test.md.txt").is_file()
        ]

        assert without != []


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

    @pytest.mark.parametrize("fragment", _shipped_role_fragments())
    def test_no_shipped_role_fragment_names_a_bead_this_source_tree_or_a_suite_file(
        self, fragment: str
    ) -> None:
        text = _fragment(*fragment.split("/"))

        assert _THIS_REPOSITORY.findall(text) == []

    @pytest.mark.parametrize(
        "sentence",
        [
            "The root comes from one module, `tests/support/repository_root.py`.",
            "See tests/conftest.py for the guard.",
        ],
    )
    def test_a_named_suite_file_is_recognised(self, sentence: str) -> None:
        assert _THIS_REPOSITORY.search(sentence) is not None

    def test_a_mirrored_path_pattern_is_a_convention_and_passes(self) -> None:
        pattern = "tests/unit/<package path>/test_<module>.py  # src/<pkg>/<module>.py"

        assert _THIS_REPOSITORY.search(pattern) is None
