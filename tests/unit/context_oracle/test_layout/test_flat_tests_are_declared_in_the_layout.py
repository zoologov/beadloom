"""Whether flat tests bind is declared in the test layout (BDL-078 ``beadloom-76mk``).

``flat_tests`` in the ``tests:`` block of ``.beadloom/config.yml`` says that a
Python test directly under a root binds by the module its name names, then by its
imports. It is off unless declared — a name is the guess the mirror replaced, so
a project states it — and ``init`` declares it for a Python project. A file is
flat when it sits directly in a root, with no folder between.

Pure: a config mapping in, a layout out.
"""

from __future__ import annotations

from beadloom.context_oracle.test_layout import TestLayout, layout_from_config


class TestTheDeclaration:
    def test_flat_tests_are_off_unless_declared(self) -> None:
        layout, problems = layout_from_config({})
        assert layout.flat_tests is False
        assert problems == []

    def test_flat_tests_can_be_declared(self) -> None:
        layout, problems = layout_from_config({"tests": {"flat_tests": True}})
        assert layout.flat_tests is True
        assert problems == []

    def test_a_value_that_is_not_a_boolean_is_reported_and_the_default_stands(self) -> None:
        layout, problems = layout_from_config({"tests": {"flat_tests": "yes"}})
        assert layout.flat_tests is False
        assert problems == [
            "`tests.flat_tests` in .beadloom/config.yml must be true or false; "
            "the default (false) is used"
        ]


class TestAFlatFile:
    def test_a_file_directly_in_a_root_is_flat(self) -> None:
        layout, _ = layout_from_config({"tests": {"roots": ["tests", "qa/checks"]}})
        assert layout.is_flat("tests/test_invoice.py") is True
        assert layout.is_flat("qa/checks/test_invoice.py") is True

    def test_a_file_in_a_folder_of_a_root_or_under_no_root_is_not_flat(self) -> None:
        layout, _ = layout_from_config({})
        assert layout.is_flat("tests/unit/test_invoice.py") is False
        assert layout.is_flat("tests/misc/test_invoice.py") is False
        assert layout.is_flat("src/test_invoice.py") is False


class TestTheRecord:
    def test_the_index_records_whether_flat_tests_bind(self) -> None:
        layout, _ = layout_from_config({"tests": {"flat_tests": True}})
        recorded = layout.recorded()
        assert recorded.flat_tests is True
        assert '"flat_tests": true' in recorded.encode()

    def test_a_layout_that_declares_nothing_records_flat_tests_off(self) -> None:
        recorded = TestLayout().recorded()
        assert recorded.flat_tests is False
        assert '"flat_tests": false' in recorded.encode()
