"""A test in a build tool's test tree binds to the node owning the code it mirrors (G2b).

``beadloom-2mj3.13``: Maven and Gradle keep ``src/test/<language>/<package>/
<Class>Test.<ext>`` beside ``src/main/<language>/<package>/<Class>.<ext>``, and
SwiftPM keeps ``Tests/<Target>Tests/<Name>Tests.swift`` beside
``Sources/<Target>/``. The mirror is the one ``tests/unit/`` uses — the path under
the test tree names a code path under the code tree, and the node owning that
path is the node — with each language's test affix taken off the file name, and
a SwiftPM test target ``<Target>Tests`` naming its target ``<Target>``.
"""

from __future__ import annotations

from beadloom.context_oracle.test_binding import (
    PLACEMENT_MIRROR,
    PLACEMENT_UNOWNED,
    bind_test_file,
)

JAVA_CODE = frozenset(
    {
        "src/main/java/com/shop/billing/Billing.java",
        "src/main/java/com/shop/billing/Invoice.java",
        "src/test/java/com/shop/billing/BillingTest.java",
    }
)
JAVA_NODES = (
    ("billing", "src/main/java/com/shop/billing/"),
    ("invoice", "src/main/java/com/shop/billing/Invoice.java"),
)
SWIFT_CODE = frozenset(
    {"Sources/Shop/Billing/Billing.swift", "Sources/Shop/Cart.swift", "Sources/Shop/Shop.swift"}
)
SWIFT_NODES = (
    ("shop", "Sources/Shop/"),
    ("billing", "Sources/Shop/Billing/"),
    ("cart", "Sources/Shop/Cart.swift"),
)


def _bind(
    path: str, code: frozenset[str], nodes: tuple[tuple[str, str], ...]
) -> tuple[object, ...]:
    bound = bind_test_file(
        path, code_files=code, scan_paths=("src",), node_sources=nodes, overrides=()
    )
    return bound.kind, bound.ref_id, bound.placement


class TestTheMavenAndGradleTree:
    def test_a_test_class_binds_to_the_package_its_path_mirrors(self) -> None:
        assert _bind("src/test/java/com/shop/billing/BillingTest.java", JAVA_CODE, JAVA_NODES) == (
            None,
            "billing",
            PLACEMENT_MIRROR,
        )

    def test_the_test_affix_is_taken_off_to_reach_a_file_node(self) -> None:
        for name in ("InvoiceTest", "InvoiceTests", "InvoiceIT", "InvoiceTestCase"):
            assert _bind(f"src/test/java/com/shop/billing/{name}.java", JAVA_CODE, JAVA_NODES) == (
                None,
                "invoice",
                PLACEMENT_MIRROR,
            )

    def test_a_kotlin_test_mirrors_the_kotlin_tree(self) -> None:
        code = frozenset({"src/main/kotlin/com/shop/billing/Billing.kt"})
        nodes = (("billing", "src/main/kotlin/com/shop/billing/"),)
        assert _bind("src/test/kotlin/com/shop/billing/BillingTest.kt", code, nodes) == (
            None,
            "billing",
            PLACEMENT_MIRROR,
        )

    def test_a_package_with_no_code_is_unowned(self) -> None:
        assert _bind("src/test/java/com/shop/vault/VaultTest.java", JAVA_CODE, JAVA_NODES) == (
            None,
            None,
            PLACEMENT_UNOWNED,
        )


class TestTheSwiftPackageTree:
    def test_a_target_test_names_the_folder_of_its_subject(self) -> None:
        assert _bind("Tests/ShopTests/BillingTests.swift", SWIFT_CODE, SWIFT_NODES) == (
            None,
            "billing",
            PLACEMENT_MIRROR,
        )

    def test_a_target_test_names_the_file_of_its_subject(self) -> None:
        assert _bind("Tests/ShopTests/CartTests.swift", SWIFT_CODE, SWIFT_NODES) == (
            None,
            "cart",
            PLACEMENT_MIRROR,
        )

    def test_a_test_naming_no_code_binds_to_its_target(self) -> None:
        assert _bind("Tests/ShopTests/CheckoutFlowTests.swift", SWIFT_CODE, SWIFT_NODES) == (
            None,
            "shop",
            PLACEMENT_MIRROR,
        )
