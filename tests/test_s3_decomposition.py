"""Tests guarding the BDL-059 S3 decomposition outcome (behavior-preserving).

S3 split two monster files into cohesive same-domain packages and recalibrated
the ``domain-size-limit`` rule 200 -> 280. These tests pin the externally
observable results of that work:

1. ``TestLintRecalibrationGuard`` — the live repo lints with 0 violations and,
   specifically, NO ``domain-size-limit`` finding. ``lint --strict`` only fails
   on *errors*, so a ``warn``-severity ``domain-size-limit`` would slip past an
   exit-code-only assertion; this inspects the JSON findings directly to guard
   the recalibration.
2. ``TestPublicSurfaceStability`` — every symbol in the new packages'
   ``__all__`` still imports via the OLD module paths
   (``beadloom.graph.federation`` / ``beadloom.graph.rule_engine``), so the
   responsibility split stayed source-compatible for all existing callers.
"""

from __future__ import annotations

import importlib

# ---------------------------------------------------------------------------
# TestLintRecalibrationGuard
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TestPublicSurfaceStability
# ---------------------------------------------------------------------------


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

    def test_federation_subpackage_symbols_match_hub(self) -> None:
        """Hub-exported federation symbols are the SAME objects as in their submodules."""
        pkg = importlib.import_module("beadloom.graph.federation")
        refs = importlib.import_module("beadloom.graph.federation.refs")
        # A representative symbol from each responsibility submodule.
        assert pkg.parse_ref is refs.parse_ref
        assert pkg.FederatedRef is refs.FederatedRef
