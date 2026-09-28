"""The ``graph.federation`` package still answers every name its old module path did.

BDL-059 S3 split ``graph/federation.py`` into a same-domain package. Every symbol in
the package's ``__all__`` still imports from ``beadloom.graph.federation``, and the
hub re-exports the SAME objects its submodules define, so the split stayed
source-compatible for every existing caller.

Split out of ``tests/test_s3_decomposition.py`` by node (BDL-074 E1); the rule-engine
shim's half is ``tests/unit/graph/rule_engine/test_the_shim_reexports_the_rules_package.py``.
"""

from __future__ import annotations

import importlib


class TestPublicSurfaceStability:
    """Every package ``__all__`` symbol resolves via the OLD import path."""

    def test_federation_all_symbols_import_via_old_path(self) -> None:
        """Each name in ``graph.federation.__init__.__all__`` imports from the package.

        Callers wrote ``from beadloom.graph.federation import X`` before the
        split; the re-export hub must keep every such name resolvable.
        """
        pkg = importlib.import_module("beadloom.graph.federation")
        names = list(pkg.__all__)
        assert names, "federation __all__ must not be empty"
        missing = [name for name in names if not hasattr(pkg, name)]
        assert missing == [], f"missing from beadloom.graph.federation: {missing}"

    def test_federation_subpackage_symbols_match_hub(self) -> None:
        """Hub-exported federation symbols are the SAME objects as in their submodules."""
        pkg = importlib.import_module("beadloom.graph.federation")
        refs = importlib.import_module("beadloom.graph.federation.refs")
        # A representative symbol from each responsibility submodule.
        assert pkg.parse_ref is refs.parse_ref
        assert pkg.FederatedRef is refs.FederatedRef
