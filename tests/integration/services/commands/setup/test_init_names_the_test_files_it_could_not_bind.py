"""``init`` states how it bound the test files and names each it could not (``beadloom-76mk``).

Observed by BDL-076 ``beadloom-ujzb.17``: after ``init`` a node card said "no
bound tests" and impact marked every node at risk, and nothing ``init`` printed
said why. Every branch of ``init`` that re-indexes now prints the ``Tests:`` line
``reindex`` prints, and below it each test file bound to no node, by path and by
placement, so the adopter can lay it out or declare it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


_CODE = {
    "src/shop/__init__.py": "",
    "src/shop/billing/__init__.py": "",
    "src/shop/billing/invoice.py": "def total() -> int:\n    return 0\n",
    "src/shop/storage/__init__.py": "",
    "src/shop/storage/rates.py": "def rate() -> int:\n    return 2\n",
}
_BOUND_TEST = "tests/test_invoice.py"
_UNBOUND_TEST = "tests/test_end_to_end.py"
_TESTS = {
    _BOUND_TEST: "def test_total() -> None:\n    pass\n",
    _UNBOUND_TEST: (
        "from shop.storage.rates import rate\nfrom shop.billing.invoice import total\n\n\n"
        "def test_both() -> None:\n    pass\n"
    ),
}


def _project(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _init(root: Path, *args: str) -> str:
    result = CliRunner().invoke(main, ["init", *args, "--project", str(root)])
    assert result.exit_code == 0, result.output
    return result.output


def _unbound_lines(output: str) -> list[str]:
    lines = output.splitlines()
    (heading,) = [i for i, line in enumerate(lines) if "bound to no node" in line]
    return [line.strip() for line in lines[heading + 1 :] if line.startswith("    ")]


class TestTheYesBranch:
    def test_the_tests_line_counts_the_flat_file_among_the_bound(self, tmp_path: Path) -> None:
        output = _init(_project(tmp_path, {**_CODE, **_TESTS}), "--yes")
        assert (
            "Tests: 2 files (1 bound to a node (1 flat, by the module named or imported), "
            "1 unplaced)"
        ) in output

    def test_each_unbound_file_is_named_with_its_placement(self, tmp_path: Path) -> None:
        output = _init(_project(tmp_path, {**_CODE, **_TESTS}), "--yes")
        assert _unbound_lines(output) == [f"{_UNBOUND_TEST} (unplaced)"]

    def test_a_project_whose_every_test_binds_names_none(self, tmp_path: Path) -> None:
        output = _init(_project(tmp_path, {**_CODE, _BOUND_TEST: _TESTS[_BOUND_TEST]}), "--yes")
        assert "Tests: 1 files (1 bound to a node" in output
        assert "bound to no node" not in output

    def test_a_project_with_no_test_file_states_no_tests_line(self, tmp_path: Path) -> None:
        output = _init(_project(tmp_path, _CODE), "--yes")
        assert "Tests:" not in output


class TestTheBootstrapBranch:
    def test_each_unbound_file_is_named_with_its_placement(self, tmp_path: Path) -> None:
        output = _init(_project(tmp_path, {**_CODE, **_TESTS}), "--bootstrap")
        assert _unbound_lines(output) == [f"{_UNBOUND_TEST} (unplaced)"]


class TestTheWizard:
    def test_each_unbound_file_is_named_after_the_wizard_reindexes(self, tmp_path: Path) -> None:
        root = _project(tmp_path, {**_CODE, **_TESTS})
        with (
            patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "yes"]),
            patch("rich.prompt.Confirm.ask", return_value=False),
        ):
            output = _init(root)
        assert _unbound_lines(output) == [f"{_UNBOUND_TEST} (unplaced)"]


class TestTheIndexIsReadThroughTheReadOnlyFactory:
    """BDL-078 ``beadloom-btkd.18`` (review m4): no connection opened by hand.

    ``open_db_readonly`` is the one place that opens an index for reading: the
    ``mode=ro`` URI, ``query_only`` on, and an absent file refused rather than
    created. The echo of the test binding opened its own connection beside it,
    with the URI and without ``query_only``.
    """

    def test_the_test_binding_is_read_on_a_query_only_connection(self, tmp_path: Path) -> None:
        import sqlite3

        from beadloom.application.reindex import test_index

        query_only: list[int] = []
        counts = test_index.placement_counts

        def recording(conn: sqlite3.Connection) -> dict[str, int]:
            query_only.append(conn.execute("PRAGMA query_only").fetchone()[0])
            return counts(conn)

        root = _project(tmp_path, {**_CODE, **_TESTS})
        with patch.object(test_index, "placement_counts", recording):
            output = _init(root, "--yes")

        assert _unbound_lines(output) == [f"{_UNBOUND_TEST} (unplaced)"]
        assert query_only == [1]
