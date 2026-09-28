"""Java, Kotlin and Swift test files are recognised by their ecosystem's convention (G2b).

Owner ruling 2026-09-28 on ``beadloom-2mj3.11``'s open decision
(``beadloom-2mj3.13``): the defaults gain each ecosystem's own conventions, and
only those.

- Java: Maven Surefire's default includes ``*Test.java``, ``*Tests.java`` and
  ``*TestCase.java``; Failsafe's ``*IT.java`` and ``*ITCase.java``. Their prefix
  forms (``Test*.java``, ``IT*.java``) are left out: a prefix also names
  production classes such as ``TestDataBuilder``, and a project that uses the
  prefix form declares it.
- Kotlin: ``*Test.kt`` (the Kotlin and Android documentation's form) and
  ``*Tests.kt`` (what Spring Initializr generates).
- Swift: ``*Tests.swift``, the XCTest and Swift Testing templates' form.

The build tools also fix where tests live: Maven and Gradle keep them in
``src/test/<language>/``, mirroring ``src/main/<language>/``, and SwiftPM keeps a
target's tests in ``Tests/<Target>Tests/``, mirroring ``Sources/<Target>/``. Those
are the default mirrors.
"""

from __future__ import annotations

import pytest

from beadloom.context_oracle.test_layout import DEFAULT_MIRRORS, TestLayout, layout_from_config


class TestTheNames:
    @pytest.mark.parametrize(
        ("name", "framework"),
        [
            ("BillingTest.java", "junit"),
            ("BillingTests.java", "junit"),
            ("BillingTestCase.java", "junit"),
            ("BillingIT.java", "junit"),
            ("BillingITCase.java", "junit"),
            ("BillingTest.kt", "junit"),
            ("BillingTests.kt", "junit"),
            ("BillingTests.swift", "xctest"),
        ],
    )
    def test_a_conventional_name_names_its_framework(self, name: str, framework: str) -> None:
        assert TestLayout().framework_of(name) == framework

    @pytest.mark.parametrize(
        "name",
        ["Billing.java", "TestDataBuilder.java", "ITEMS.java", "Billing.kt", "Billing.swift"],
    )
    def test_code_and_the_prefix_forms_are_not_tests(self, name: str) -> None:
        assert TestLayout().framework_of(name) is None


class TestTheMirrors:
    def test_the_build_tools_test_trees_mirror_their_code_trees(self) -> None:
        assert dict(DEFAULT_MIRRORS) == {
            "src/test/java": "src/main/java",
            "src/test/kotlin": "src/main/kotlin",
            "Tests": "Sources",
        }

    def test_a_file_in_a_test_tree_names_its_code_tree_and_the_rest(self) -> None:
        assert TestLayout().mirror_of("src/test/java/com/shop/BillingTest.java") == (
            "src/test/java",
            "src/main/java",
            "com/shop/BillingTest.java",
        )

    def test_a_file_in_no_test_tree_is_not_mirrored(self) -> None:
        assert TestLayout().mirror_of("src/main/java/com/shop/Billing.java") is None
        assert TestLayout().mirror_of("tests/unit/test_billing.py") is None

    def test_declared_mirrors_replace_the_defaults(self) -> None:
        layout, problems = layout_from_config({"tests": {"mirrors": {"test": "lib"}}})
        assert problems == []
        assert layout.mirrors == (("test", "lib"),)

    def test_mirrors_that_are_not_a_mapping_of_folders_are_reported(self) -> None:
        layout, problems = layout_from_config({"tests": {"mirrors": ["src/test/java"]}})
        assert layout.mirrors == DEFAULT_MIRRORS
        assert problems == [
            "`tests.mirrors` in .beadloom/config.yml must map each test folder to the "
            "code folder it mirrors; the default (src/test/java: src/main/java, "
            "src/test/kotlin: src/main/kotlin, Tests: Sources) is used"
        ]
