"""A pattern that names a folder matches the end of a file's path (``beadloom-2mj3.15``).

The retired mapper (main, db5c3f28) read three conventions no file-name pattern can
state: every JS/TS file under a Jest ``__tests__/`` folder, every Java or Kotlin file
under ``src/test/``, and every Swift file under a folder named ``*Tests``. A pattern
with a ``/`` in it is matched against the path's last folders and its name, as a
name pattern is matched against the name alone, so a default can state each of
them and an adopter can declare one of its own (``__tests__/**``).
"""

from __future__ import annotations

import pytest

from beadloom.context_oracle.test_layout import TestLayout, layout_from_config


class TestTheDefaultsStateEachFolderConvention:
    @pytest.mark.parametrize(
        "path",
        [
            "src/orders/__tests__/orders.ts",
            "src/orders/__tests__/orders.tsx",
            "src/orders/__tests__/orders.js",
            "src/orders/__tests__/orders.jsx",
            "src/orders/__tests__/helpers/orders.ts",
            "__tests__/orders.ts",
        ],
    )
    def test_a_script_under_a_jest_tests_folder_is_a_jest_test(self, path: str) -> None:
        assert TestLayout().framework_of(path) == "jest"

    @pytest.mark.parametrize(
        "path",
        [
            "src/orders/__tests__/data.json",
            "src/orders/__tests__/__snapshots__/orders.ts.snap",
            "src/orders/orders.ts",
            "src/__tests__x/orders.ts",
        ],
    )
    def test_a_file_the_jest_folder_convention_does_not_name_is_not_a_test(
        self, path: str
    ) -> None:
        assert TestLayout().framework_of(path) is None

    @pytest.mark.parametrize(
        "path",
        [
            "src/test/java/com/shop/billing/BillingShould.java",
            "src/test/kotlin/com/shop/billing/BillingSpec.kt",
            "billing/src/test/java/com/shop/billing/BillingFixtures.java",
        ],
    )
    def test_every_java_or_kotlin_file_under_src_test_is_a_junit_test(self, path: str) -> None:
        assert TestLayout().framework_of(path) == "junit"

    def test_a_java_file_under_src_main_is_not_a_test(self) -> None:
        assert TestLayout().framework_of("src/main/java/com/shop/Billing.java") is None

    @pytest.mark.parametrize(
        "path", ["Tests/BillingTests/BillingChecks.swift", "Tests/Helpers.swift"]
    )
    def test_every_swift_file_under_a_tests_folder_is_an_xctest(self, path: str) -> None:
        assert TestLayout().framework_of(path) == "xctest"

    def test_a_swift_file_under_sources_is_not_a_test(self) -> None:
        assert TestLayout().framework_of("Sources/Billing/Billing.swift") is None

    def test_a_name_pattern_still_matches_a_bare_name_and_a_name_at_any_depth(self) -> None:
        layout = TestLayout()
        assert layout.framework_of("billing_test.go") == "go_test"
        assert layout.framework_of("internal/billing/billing_test.go") == "go_test"


class TestAnAdopterDeclaresAFolderPattern:
    def _layout(self, *patterns: str) -> TestLayout:
        layout, problems = layout_from_config({"tests": {"patterns": {"jest": list(patterns)}}})
        assert problems == []
        return layout

    def test_a_folder_and_everything_below_it(self) -> None:
        layout = self._layout("__tests__/**")
        assert layout.framework_of("src/a/__tests__/x.ts") == "jest"
        assert layout.framework_of("src/a/__tests__/deep/x.json") == "jest"
        assert layout.framework_of("src/a/x.ts") is None

    def test_a_double_star_between_folders_matches_no_folder_as_well(self) -> None:
        layout = self._layout("e2e/**/*.ts")
        assert layout.framework_of("apps/web/e2e/login.ts") == "jest"
        assert layout.framework_of("apps/web/e2e/flows/login.ts") == "jest"
        assert layout.framework_of("apps/web/src/login.ts") is None

    def test_a_leading_double_star_says_the_same_as_none(self) -> None:
        assert self._layout("**/__tests__/*.ts").framework_of("a/b/__tests__/x.ts") == "jest"


class TestARootThatNamesTheWholeProjectIsRefused:
    @pytest.mark.parametrize("root", [".", "/", "./", "a/../b", ".."])
    def test_the_default_stands_and_the_reason_is_given(self, root: str) -> None:
        layout, problems = layout_from_config({"tests": {"roots": [root]}})
        assert layout.roots == ("tests",)
        assert len(problems) == 1
        assert "`tests.roots`" in problems[0]
