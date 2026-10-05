"""A flat Python test binds by the module it names, then by its imports (``beadloom-76mk``).

Observed by BDL-076 ``beadloom-ujzb.17`` on the Python adopter fixture: test files
directly under ``tests/`` — the most common Python layout — bound to no node,
because the mirror reads only ``tests/unit/**`` and ``tests/integration/**``.

When the layout declares ``flat_tests`` (``init`` declares it for a Python
project), a ``.py`` test directly under a root binds to the node owning the module
its name names — ``tests/test_invoice.py`` names ``invoice.py`` — when exactly one
node owns a module of that name, else to the one node its imports reach, else to
nothing. A layout that does not declare it binds such a file as before: unplaced.

Stated as data, like the mirror's cases beside this file.
"""

from __future__ import annotations

from beadloom.context_oracle.test_binding import (
    PLACEMENT_IMPORTED,
    PLACEMENT_MIRROR,
    PLACEMENT_NAMED,
    PLACEMENT_OVERRIDE,
    PLACEMENT_UNPLACED,
    bind_test_file,
)
from beadloom.context_oracle.test_layout import TestLayout, layout_from_config

CODE = frozenset(
    {
        "src/shop/__init__.py",
        "src/shop/billing/__init__.py",
        "src/shop/billing/invoice.py",
        "src/shop/billing/models.py",
        "src/shop/storage/__init__.py",
        "src/shop/storage/models.py",
        "src/shop/storage/rates.py",
        "src/shop/cli.py",
    }
)
NODES = (
    ("shop", "src/shop/"),
    ("billing", "src/shop/billing/"),
    ("storage", "src/shop/storage/"),
)


def _layout(tests: dict[str, object] | None = None) -> TestLayout:
    layout, problems = layout_from_config({"tests": {"flat_tests": True, **(tests or {})}})
    assert problems == []
    return layout


def _bind(
    path: str,
    *,
    imported: tuple[str, ...] = (),
    layout: TestLayout | None = None,
    overrides: tuple[tuple[str, str], ...] = (),
) -> tuple[object, ...]:
    bound = bind_test_file(
        path,
        code_files=CODE,
        scan_paths=("src",),
        node_sources=NODES,
        overrides=overrides,
        layout=layout or _layout(),
        imported_refs=imported,
    )
    return bound.kind, bound.ref_id, bound.placement


class TestByTheModuleItNames:
    def test_a_flat_test_binds_to_the_node_owning_the_module_it_names(self) -> None:
        assert _bind("tests/test_invoice.py") == (None, "billing", PLACEMENT_NAMED)

    def test_the_suffix_form_names_the_module_too(self) -> None:
        assert _bind("tests/rates_test.py") == (None, "storage", PLACEMENT_NAMED)

    def test_a_module_no_child_node_owns_binds_to_the_node_that_does(self) -> None:
        assert _bind("tests/test_cli.py") == (None, "shop", PLACEMENT_NAMED)

    def test_a_package_named_by_the_test_binds_to_the_node_owning_it(self) -> None:
        assert _bind("tests/test_billing.py") == (None, "billing", PLACEMENT_NAMED)

    def test_the_name_wins_over_the_imports(self) -> None:
        assert _bind("tests/test_invoice.py", imported=("storage",)) == (
            None,
            "billing",
            PLACEMENT_NAMED,
        )

    def test_a_flat_test_under_a_declared_root_binds_the_same(self) -> None:
        layout = _layout({"roots": ["test"]})
        assert _bind("test/test_invoice.py", layout=layout) == (None, "billing", PLACEMENT_NAMED)


class TestByItsImports:
    def test_a_name_no_module_carries_binds_to_the_one_node_its_imports_reach(self) -> None:
        assert _bind("tests/test_pricing_table.py", imported=("storage", "storage")) == (
            None,
            "storage",
            PLACEMENT_IMPORTED,
        )

    def test_a_name_two_nodes_own_a_module_of_falls_to_the_imports(self) -> None:
        assert _bind("tests/test_models.py", imported=("billing",)) == (
            None,
            "billing",
            PLACEMENT_IMPORTED,
        )


class TestNothingIsGuessed:
    def test_imports_reaching_two_nodes_bind_to_nothing(self) -> None:
        assert _bind("tests/test_end_to_end.py", imported=("billing", "storage")) == (
            None,
            None,
            PLACEMENT_UNPLACED,
        )

    def test_a_name_two_nodes_own_and_no_import_bind_to_nothing(self) -> None:
        assert _bind("tests/test_models.py") == (None, None, PLACEMENT_UNPLACED)

    def test_a_flat_test_that_is_not_python_binds_to_nothing(self) -> None:
        assert _bind("tests/rates_test.go", imported=("storage",)) == (
            None,
            None,
            PLACEMENT_UNPLACED,
        )

    def test_a_test_in_a_folder_that_is_no_kind_is_not_flat(self) -> None:
        assert _bind("tests/misc/test_invoice.py", imported=("billing",)) == (
            None,
            None,
            PLACEMENT_UNPLACED,
        )


class TestWhatItDoesNotChange:
    def test_a_layout_without_flat_tests_leaves_a_flat_test_unplaced(self) -> None:
        layout, _ = layout_from_config({})
        assert _bind("tests/test_invoice.py", imported=("billing",), layout=layout) == (
            None,
            None,
            PLACEMENT_UNPLACED,
        )

    def test_a_declaration_still_wins_over_the_name(self) -> None:
        assert _bind(
            "tests/test_invoice.py", overrides=(("storage", "tests/test_invoice.py"),)
        ) == (None, "storage", PLACEMENT_OVERRIDE)

    def test_the_mirror_under_a_kind_folder_is_unchanged(self) -> None:
        assert _bind("tests/unit/billing/test_invoice.py", imported=("storage",)) == (
            "unit",
            "billing",
            PLACEMENT_MIRROR,
        )
