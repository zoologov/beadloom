"""A flat Python test binds on every reindex of a layout declaring it (BDL-078 ``beadloom-76mk``).

The reindex hands each test file's resolved imports to the binding, so a flat test
named after no module binds to the one node its imports reach; it records the
layout's ``flat_tests``, so switching it off re-binds on the next incremental
reindex rather than keeping the bindings it no longer declares; and the ``Tests:``
line counts the flat files among the bound ones.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import yaml

from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.application.reindex.test_index import describe_placements
from beadloom.context_oracle.test_binding import (
    PLACEMENT_IMPORTED,
    PLACEMENT_NAMED,
    PLACEMENT_UNPLACED,
)
from beadloom.infrastructure.repository import TEST_LAYOUT_KEY, read_test_layout
from tests.support.adopter_test_layouts import write

if TYPE_CHECKING:
    from pathlib import Path

_CODE = {
    "src/shop/__init__.py": "",
    "src/shop/billing/__init__.py": "",
    "src/shop/billing/invoice.py": "def total() -> int:\n    return 0\n",
    "src/shop/storage/__init__.py": "",
    "src/shop/storage/rates.py": "def rate() -> int:\n    return 2\n",
}
_TESTS = {
    "tests/test_invoice.py": "def test_total() -> None:\n    pass\n",
    "tests/test_pricing_table.py": (
        "from shop.storage.rates import rate\n\n\ndef test_rate() -> None:\n    pass\n"
    ),
    "tests/test_end_to_end.py": (
        "from shop.storage.rates import rate\nfrom shop.billing.invoice import total\n\n\n"
        "def test_both() -> None:\n    pass\n"
    ),
}


def _config(root: Path, *, flat_tests: bool) -> None:
    config = {"languages": [".py"], "scan_paths": ["src"], "tests": {"flat_tests": flat_tests}}
    write(root, ".beadloom/config.yml", yaml.safe_dump(config, sort_keys=False))


def _project(root: Path) -> Path:
    for relative, text in {**_CODE, **_TESTS}.items():
        write(root, relative, text)
    nodes = [
        {"ref_id": "shop", "kind": "service", "summary": "Shop", "source": "src/shop/"},
        {
            "ref_id": "billing",
            "kind": "domain",
            "summary": "Billing",
            "source": "src/shop/billing/",
        },
        {
            "ref_id": "storage",
            "kind": "domain",
            "summary": "Storage",
            "source": "src/shop/storage/",
        },
    ]
    edges = [{"src": ref, "dst": "shop", "kind": "part_of"} for ref in ("billing", "storage")]
    graph = {"nodes": nodes, "edges": edges}
    write(root, ".beadloom/_graph/services.yml", yaml.safe_dump(graph, sort_keys=False))
    _config(root, flat_tests=True)
    return root


def _rows(root: Path) -> list[tuple[str, str | None, str]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [
            (str(path), ref_id, str(placement))
            for path, ref_id, placement in conn.execute(
                "SELECT path, ref_id, placement FROM test_files ORDER BY path"
            ).fetchall()
        ]


_BOUND = [
    ("tests/test_end_to_end.py", None, PLACEMENT_UNPLACED),
    ("tests/test_invoice.py", "billing", PLACEMENT_NAMED),
    ("tests/test_pricing_table.py", "storage", PLACEMENT_IMPORTED),
]


class TestAFullReindex:
    def test_each_flat_test_binds_by_its_name_then_its_imports(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        reindex(root)
        assert _rows(root) == _BOUND

    def test_the_flat_files_are_counted_among_the_bound(self) -> None:
        counts = {PLACEMENT_NAMED: 1, PLACEMENT_IMPORTED: 1, PLACEMENT_UNPLACED: 1}
        assert describe_placements(counts, {}) == (
            "3 files (2 bound to a node (2 flat, by the module named or imported), 1 unplaced)"
        )


class TestAnIncrementalReindex:
    def test_an_unchanged_project_keeps_its_flat_bindings(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        reindex(root)
        incremental_reindex(root)
        assert _rows(root) == _BOUND

    def test_switching_flat_tests_off_unbinds_them_on_the_next_reindex(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        reindex(root)
        _config(root, flat_tests=False)
        incremental_reindex(root)
        assert _rows(root) == [(path, None, PLACEMENT_UNPLACED) for path, _, _ in _BOUND]


class TestARecordWrittenBeforeTheKey:
    def test_it_reads_as_flat_tests_off(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        reindex(root)
        with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
            (encoded,) = conn.execute(
                "SELECT value FROM meta WHERE key = ?", (TEST_LAYOUT_KEY,)
            ).fetchone()
            older = {k: v for k, v in json.loads(encoded).items() if k != "flat_tests"}
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = ?", (json.dumps(older), TEST_LAYOUT_KEY)
            )
            recorded = read_test_layout(conn)
        assert recorded is not None
        assert recorded.flat_tests is False
