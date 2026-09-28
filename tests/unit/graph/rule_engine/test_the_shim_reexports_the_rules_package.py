"""The ``graph.rule_engine`` shim answers every name the ``graph.rules`` package exports.

BDL-059 S3 split ``graph/rule_engine.py`` into the ``graph/rules/`` package and left
the old module as a back-compat re-export shim, annotated to the ``graph`` domain.
``from beadloom.graph.rule_engine import X`` keeps working, and the shim hands out
the SAME objects as the package, never a shadow copy that could fork behaviour.

Split out of ``tests/test_s3_decomposition.py`` by node (BDL-074 E1); the federation
half is ``tests/unit/graph/federation/test_the_federation_package_keeps_its_import_path.py``.
"""

from __future__ import annotations

import importlib


class TestPublicSurfaceStability:
    """Every package ``__all__`` symbol resolves via the OLD import path."""

    def test_rule_engine_shim_names_import_via_old_path(self) -> None:
        """Each name in the ``rule_engine`` shim ``__all__`` resolves on the shim.

        ``from beadloom.graph.rule_engine import X`` must keep working after the
        decomposition into ``beadloom.graph.rules``.
        """
        shim = importlib.import_module("beadloom.graph.rule_engine")
        names = list(shim.__all__)
        assert names, "rule_engine shim __all__ must not be empty"
        missing = [name for name in names if not hasattr(shim, name)]
        assert missing == [], f"missing from beadloom.graph.rule_engine: {missing}"

    def test_rule_engine_shim_reexports_private_helper(self) -> None:
        """The shim still exposes ``_remediation_for`` — tests/callers import it by name."""
        shim = importlib.import_module("beadloom.graph.rule_engine")
        assert hasattr(shim, "_remediation_for")
        assert callable(shim._remediation_for)

    def test_shim_symbols_are_identical_objects_to_package(self) -> None:
        """The shim re-exports the SAME objects as the ``rules`` package (no shadow copy).

        Identity (not just name presence) guards against a future shim that
        rebinds a name to a divergent stub, which would silently fork behavior.
        """
        shim = importlib.import_module("beadloom.graph.rule_engine")
        pkg = importlib.import_module("beadloom.graph.rules")
        for name in pkg.__all__:
            assert getattr(shim, name) is getattr(pkg, name), name
