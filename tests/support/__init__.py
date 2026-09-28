"""Helpers the test modules share (BDL-074 B1).

A test module never imports another test module: what two of them need lives
here, under a name that says what it is for. That is what lets a test file move
to any folder without taking a neighbour's definitions with it.
"""

import pytest

# The bodies in `ci_pipeline_properties` are test bodies that a product test and
# a self-check share (BDL-074 F3). pytest rewrites the asserts of test modules
# only, so without this a failing property would report a bare AssertionError.
pytest.register_assert_rewrite("tests.support.ci_pipeline_properties")
