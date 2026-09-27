"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_readme_pair_gate.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import pytest


def test_this_repository_holds_its_own_readme_pair() -> None:
    """The dogfood leg: the pair this project declares is compared on every run."""
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parents[3]
    if not (root / ".beadloom" / "config.yml").is_file():
        pytest.skip("not running from a checkout of this repository")
    from beadloom.application.gate_document_pairs import step_readme_pair

    step = step_readme_pair(root)
    assert step.skipped is False, "this repository declares its README pair"
    assert step.passed is True
    assert "pair(s) held" in step.summary
