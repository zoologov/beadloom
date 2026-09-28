"""Where a project's tests are, and which files are tests, is read from its config (BDL-074 G2).

Review ``beadloom-b9ll`` M3: the binding read only ``tests/**/test_*.py``, so a Go
module, a TypeScript project or a Python project keeping its tests in ``test/`` had
no test file at all. The owner ruled (2026-09-28) that the test roots and the
file-name patterns are configuration, with defaults for Python, Go and JS/TS, and
that the framework is named from the patterns a file matched. Review m4: the kind
folders are configuration too, so a kind has a stated source.

Pure: a config mapping in, a layout out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.context_oracle.test_layout import (
    DEFAULT_PATTERNS,
    KIND_ACCEPTANCE,
    KIND_INTEGRATION,
    KIND_SELF_CHECK,
    KIND_UNIT,
    TestLayout,
    layout_from_config,
    load_test_layout,
)

if TYPE_CHECKING:
    from pathlib import Path


def _layout(tests: object) -> tuple[TestLayout, list[str]]:
    return layout_from_config({"tests": tests})


class TestTheDefaults:
    """A project that declares nothing gets the layout Beadloom ships."""

    def test_the_root_is_tests_and_tests_beside_the_code_are_read(self) -> None:
        layout, problems = layout_from_config({})
        assert layout.roots == ("tests",)
        assert layout.beside_code is True
        assert problems == []

    def test_python_go_and_js_ts_patterns_name_their_framework(self) -> None:
        layout, _ = layout_from_config({})
        assert layout.framework_of("test_ledger.py") == "pytest"
        assert layout.framework_of("ledger_test.py") == "pytest"
        assert layout.framework_of("billing_test.go") == "go_test"
        assert layout.framework_of("cart.test.ts") == "jest"
        assert layout.framework_of("cart.spec.tsx") == "jest"

    def test_a_file_no_pattern_matches_is_not_a_test(self) -> None:
        layout, _ = layout_from_config({})
        assert layout.framework_of("billing.go") is None
        assert layout.framework_of("conftest.py") is None
        assert not layout.is_test_file("cart.ts")

    def test_the_default_patterns_are_the_five_the_owner_named(self) -> None:
        assert dict(DEFAULT_PATTERNS) == {
            "pytest": ("test_*.py", "*_test.py"),
            "go_test": ("*_test.go",),
            "jest": ("*.test.*", "*.spec.*", "__tests__/**/*.[jt]s", "__tests__/**/*.[jt]sx"),
            "junit": (
                "*Test.java",
                "*Tests.java",
                "*TestCase.java",
                "*IT.java",
                "*ITCase.java",
                "*Test.kt",
                "*Tests.kt",
                "src/test/**/*.java",
                "src/test/**/*.kt",
            ),
            "xctest": ("*Tests.swift", "*Tests/**/*.swift"),
        }

    def test_each_kind_is_the_folder_of_its_own_name_and_none_is_declared(self) -> None:
        layout, _ = layout_from_config({})
        assert layout.folder_of(KIND_UNIT) == "unit"
        assert layout.folder_of(KIND_SELF_CHECK) == "self_check"
        assert layout.declared_kinds == frozenset()


class TestADeclaredLayout:
    """What `tests:` in `.beadloom/config.yml` declares replaces the default it names."""

    def test_declared_roots_replace_the_default(self) -> None:
        layout, problems = _layout({"roots": ["test", "spec/"]})
        assert layout.roots == ("test", "spec")
        assert problems == []

    def test_declared_patterns_replace_every_default_group(self) -> None:
        layout, _ = _layout({"patterns": {"junit": ["*Test.java"]}})
        assert layout.framework_of("LedgerTest.java") == "junit"
        assert layout.framework_of("test_ledger.py") is None

    def test_a_declared_kind_folder_replaces_only_that_kind(self) -> None:
        layout, _ = _layout({"kinds": {"acceptance": "e2e"}})
        assert layout.folder_of(KIND_ACCEPTANCE) == "e2e"
        assert layout.folder_of(KIND_INTEGRATION) == "integration"
        assert layout.declared_kinds == frozenset({KIND_ACCEPTANCE})

    def test_tests_beside_the_code_can_be_switched_off(self) -> None:
        layout, _ = _layout({"beside_code": False})
        assert layout.beside_code is False


class TestWhereAFileIs:
    """A path is under a root, in a kind folder of it, or neither."""

    def test_a_file_in_a_kind_folder_of_a_root_names_its_kind_and_the_rest(self) -> None:
        layout, _ = _layout({"roots": ["test"], "kinds": {"acceptance": "e2e"}})
        assert layout.locate("test/unit/ledger/test_posting.py") == (
            KIND_UNIT,
            "ledger/test_posting.py",
        )
        assert layout.locate("test/e2e/steps/test_story.py") == (
            KIND_ACCEPTANCE,
            "steps/test_story.py",
        )

    def test_a_file_under_a_root_in_no_kind_folder_has_no_kind(self) -> None:
        layout, _ = layout_from_config({})
        assert layout.locate("tests/test_flat.py") == (None, "")
        assert layout.locate("tests/misc/test_story.py") == (None, "")

    def test_a_file_under_no_root_is_not_located(self) -> None:
        layout, _ = layout_from_config({})
        assert layout.locate("internal/billing/billing_test.go") is None
        assert layout.locate("testsuite/test_x.py") is None

    def test_the_kind_folders_are_stated_under_every_root(self) -> None:
        layout, _ = _layout({"roots": ["test", "spec"]})
        assert layout.kind_prefixes(KIND_UNIT) == ("test/unit/", "spec/unit/")


class TestAMalformedDeclaration:
    """A declaration that cannot be used is reported, and the default stands for it."""

    def test_roots_that_are_not_a_list_of_paths_are_reported(self) -> None:
        layout, problems = _layout({"roots": "test"})
        assert layout.roots == ("tests",)
        assert problems == [
            "`tests.roots` in .beadloom/config.yml must be a list of folders inside the "
            "project, none of them the project itself or outside it; the default (tests) "
            "is used"
        ]

    def test_patterns_that_are_not_lists_of_names_by_framework_are_reported(self) -> None:
        layout, problems = _layout({"patterns": ["*_test.go"]})
        assert layout.framework_of("test_ledger.py") == "pytest"
        assert len(problems) == 1
        assert "`tests.patterns`" in problems[0]

    def test_an_unknown_kind_is_reported_and_ignored(self) -> None:
        layout, problems = _layout({"kinds": {"e2e": "e2e"}})
        assert layout.declared_kinds == frozenset()
        assert problems == [
            "`tests.kinds.e2e` in .beadloom/config.yml names no kind Beadloom knows "
            "(acceptance, integration, self_check, unit); it is ignored"
        ]

    def test_a_tests_key_that_is_not_a_mapping_is_reported(self) -> None:
        layout, problems = layout_from_config({"tests": ["tests"]})
        assert layout.roots == ("tests",)
        assert len(problems) == 1


class TestAConfigThatCannotBeRead:
    def test_a_config_that_is_not_utf8_is_reported_and_the_default_stands(
        self, tmp_path: Path
    ) -> None:
        config = tmp_path / ".beadloom" / "config.yml"
        config.parent.mkdir(parents=True)
        config.write_bytes(b"tests:\n  roots: [t\xe9st]\n")
        layout, problems = load_test_layout(tmp_path)
        assert layout == TestLayout()
        assert problems == [
            ".beadloom/config.yml could not be read; the default test layout is used"
        ]

    def test_no_config_file_is_the_default_and_no_problem(self, tmp_path: Path) -> None:
        assert load_test_layout(tmp_path) == (TestLayout(), [])
