"""A test file's text is read for the tests pytest collects and the imports it makes.

Split out of ``tests/test_a_test_file_binds_to_the_node_its_path_mirrors.py``
(BDL-074 ``beadloom-2mj3.7``): the reader lives in ``context_oracle/test_file_reader.py``,
beside the binding but not a part of the node the binding is; text in, a count
and a tuple out, so unit.
"""

from __future__ import annotations

from beadloom.context_oracle.test_file_reader import count_test_functions, read_test_file


class TestWhatCountsAsATest:
    def test_the_test_functions_pytest_collects_are_counted(self) -> None:
        text = (
            "def test_a():\n    pass\n\n"
            "async def test_b():\n    pass\n\n"
            "def helper():\n    pass\n\n"
            "class TestThing:\n"
            "    def test_c(self):\n        pass\n"
            "    def not_a_test(self):\n        pass\n\n"
            "class Helper:\n"
            "    def test_d(self):\n        pass\n"
        )
        assert count_test_functions(text) == 3

    def test_a_file_that_does_not_parse_counts_zero(self) -> None:
        assert count_test_functions("def test_a(:\n") == 0

    def test_imports_are_read_in_the_code_index_form(self) -> None:
        text = (
            "import os\n"
            "import beadloom.graph.loader as loader\n"
            "from beadloom.graph import diff\n"
            "from . import sibling\n"
            "from .helpers import build\n"
            "def test_a():\n"
            "    from beadloom.infrastructure.db import open_db\n"
            "class TestB:\n"
            "    def test_b(self):\n"
            "        try:\n"
            "            pass\n"
            "        except ImportError:\n"
            "            import yaml\n"
        )
        assert read_test_file(text).imports == (
            (1, "os"),
            (2, "beadloom.graph.loader"),
            (3, "beadloom.graph"),
            (7, "beadloom.infrastructure.db"),
            (13, "yaml"),
        )
