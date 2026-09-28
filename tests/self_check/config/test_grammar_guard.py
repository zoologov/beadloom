"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_grammar_guard.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from tests.support.repository_root import REPO_ROOT


def _declared_tree_sitter_specifier() -> str:
    """Return the version specifier pyproject declares for the tree-sitter core.

    Read with a regex rather than a TOML parser: ``tomllib`` only exists on
    3.11+, and this guard has to run on every supported interpreter.
    """
    import re

    pyproject = REPO_ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    # Matches "tree-sitter<spec>" but not "tree-sitter-python..." — anything
    # after the name must be a specifier character or the closing quote.
    matches = re.findall(r'"tree-sitter((?:[<>=!~,][^"]*)?)"', text)
    assert len(matches) == 1, (
        f"expected exactly one tree-sitter core requirement, found {matches}"
    )
    return matches[0]


def test_tree_sitter_core_requirement_is_bounded_above() -> None:
    """The ABI host must carry an upper bound (BDL-UX #150).

    Grammar wheels declare their core requirement only under a ``core`` extra,
    which a normal install never activates — so nothing but this pin stops a
    fresh install from pairing a newer core with the current grammars. That
    pairing does not fail loudly: small parses succeed and a real reindex
    segfaults partway through, which is how it reached users.
    """
    specifier = _declared_tree_sitter_specifier()

    assert any(op in specifier for op in ("<", "==", "~=")), (
        f"tree-sitter is pinned as 'tree-sitter{specifier}' with no upper "
        "bound — a fresh install can resolve an untested core ABI and "
        "segfault mid-reindex."
    )


def test_installed_tree_sitter_satisfies_the_declared_bound() -> None:
    """The environment running the suite is inside the range users install.

    Without this, a locally-upgraded core could pass the whole suite and hide
    that the declared bound no longer matches what was actually exercised.
    """
    from importlib.metadata import version

    from packaging.specifiers import SpecifierSet

    specifier = SpecifierSet(_declared_tree_sitter_specifier())
    installed = version("tree-sitter")

    assert specifier.contains(installed), (
        f"installed tree-sitter {installed} is outside the declared "
        f"'{specifier}' — the suite is not exercising the range users install."
    )
