"""A test file inside a node's source binds to the node that covers it (BDL-074 G2).

Review ``beadloom-b9ll`` M3, owner ruling 2026-09-28: ``foo_test.go`` beside
``foo.go``, ``test_x.py`` beside ``x.py`` and ``x.test.ts`` beside ``x.ts`` bind to
the node whose source covers them — by the ownership rule the mirror already uses,
never by a name. A test is bound by the mirror, by its place beside the code, or
by a ``tests:`` declaration, and by nothing else.

Stated as data, like the mirror's cases beside this file.
"""

from __future__ import annotations

from beadloom.context_oracle.test_binding import (
    PLACEMENT_BESIDE_CODE,
    PLACEMENT_MIRROR,
    PLACEMENT_OTHER_KIND,
    PLACEMENT_OVERRIDE,
    PLACEMENT_UNPLACED,
    bind_test_file,
)
from beadloom.context_oracle.test_layout import TestLayout, layout_from_config

GO_CODE = frozenset(
    {
        "internal/billing/billing.go",
        "internal/billing/billing_test.go",
        "internal/orders/orders.go",
        "internal/orders/orders_test.go",
        "internal/shared/money_test.go",
    }
)
GO_NODES = (("shop", ""), ("billing", "internal/billing/"), ("orders", "internal/orders/"))

PY_CODE = frozenset(
    {
        "src/shop/__init__.py",
        "src/shop/billing/__init__.py",
        "src/shop/billing/invoice.py",
        "src/shop/billing/test_invoice.py",
        "src/shop/cart.ts",
        "src/shop/cart.test.ts",
    }
)
PY_NODES = (("shop", "src/shop/"), ("billing", "src/shop/billing/"))


def _layout(tests: dict[str, object] | None = None) -> TestLayout:
    layout, problems = layout_from_config({} if tests is None else {"tests": tests})
    assert problems == []
    return layout


def _bind(
    path: str,
    *,
    code: frozenset[str],
    nodes: tuple[tuple[str, str], ...],
    layout: TestLayout | None = None,
    scan_paths: tuple[str, ...] = ("src",),
    overrides: tuple[tuple[str, str], ...] = (),
) -> tuple[object, ...]:
    bound = bind_test_file(
        path,
        code_files=code,
        scan_paths=scan_paths,
        node_sources=nodes,
        overrides=overrides,
        layout=layout or _layout(),
    )
    return bound.kind, bound.ref_id, bound.placement


class TestBesideTheCode:
    def test_a_go_test_beside_its_package_binds_to_the_node_covering_it(self) -> None:
        assert _bind(
            "internal/billing/billing_test.go",
            code=GO_CODE,
            nodes=GO_NODES,
            scan_paths=("internal",),
        ) == (None, "billing", PLACEMENT_BESIDE_CODE)

    def test_a_python_test_beside_its_module_binds_to_the_most_specific_node(self) -> None:
        assert _bind("src/shop/billing/test_invoice.py", code=PY_CODE, nodes=PY_NODES) == (
            None,
            "billing",
            PLACEMENT_BESIDE_CODE,
        )

    def test_a_ts_test_beside_its_module_binds_to_the_node_covering_it(self) -> None:
        assert _bind("src/shop/cart.test.ts", code=PY_CODE, nodes=PY_NODES) == (
            None,
            "shop",
            PLACEMENT_BESIDE_CODE,
        )

    def test_a_test_inside_no_node_source_binds_to_nothing_and_is_unplaced(self) -> None:
        assert _bind(
            "internal/shared/money_test.go",
            code=GO_CODE,
            nodes=GO_NODES,
            scan_paths=("internal",),
        ) == (None, None, PLACEMENT_UNPLACED)

    def test_the_name_of_a_test_beside_the_code_decides_nothing(self) -> None:
        """`orders_test.go` placed in billing's folder is billing's: the place binds."""
        code = GO_CODE | {"internal/billing/orders_test.go"}
        assert _bind(
            "internal/billing/orders_test.go", code=code, nodes=GO_NODES, scan_paths=("internal",)
        ) == (None, "billing", PLACEMENT_BESIDE_CODE)

    def test_a_declaration_still_wins_over_the_place(self) -> None:
        assert _bind(
            "internal/billing/billing_test.go",
            code=GO_CODE,
            nodes=GO_NODES,
            scan_paths=("internal",),
            overrides=(("orders", "internal/billing/billing_test.go"),),
        ) == (None, "orders", PLACEMENT_OVERRIDE)

    def test_switched_off_a_test_beside_the_code_is_unplaced(self) -> None:
        assert _bind(
            "src/shop/billing/test_invoice.py",
            code=PY_CODE,
            nodes=PY_NODES,
            layout=_layout({"beside_code": False}),
        ) == (None, None, PLACEMENT_UNPLACED)


class TestAConfiguredRoot:
    def test_the_mirror_runs_under_a_declared_root(self) -> None:
        assert _bind(
            "test/unit/billing/test_invoice.py",
            code=PY_CODE,
            nodes=PY_NODES,
            layout=_layout({"roots": ["test"]}),
        ) == ("unit", "billing", PLACEMENT_MIRROR)

    def test_a_declared_kind_folder_places_its_files_as_that_kind(self) -> None:
        assert _bind(
            "test/e2e/test_checkout.py",
            code=PY_CODE,
            nodes=PY_NODES,
            layout=_layout({"roots": ["test"], "kinds": {"acceptance": "e2e"}}),
        ) == ("acceptance", None, PLACEMENT_OTHER_KIND)

    def test_a_file_flat_under_a_declared_root_is_unplaced_not_beside_the_code(self) -> None:
        """A root is not code, even when a node's source happens to cover it."""
        assert _bind(
            "src/shop/tests/test_flat.py",
            code=PY_CODE,
            nodes=PY_NODES,
            layout=_layout({"roots": ["src/shop/tests"]}),
        ) == (None, None, PLACEMENT_UNPLACED)
