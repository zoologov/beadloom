"""The reindex package's hub still exports its entry points and re-binds its infra helpers.

The ``application/reindex/`` package replaced one module (BDL-059 S4) and kept its
import path through an ``__init__`` re-export hub; enrichment and change detection
patch three infrastructure helpers through that namespace. The walk over every
decomposed package's ``__all__`` stays in ``tests/test_s4_decomposition.py``.
Split out of it (BDL-074 ``beadloom-2mj3.7``); imports only, so unit.
"""

from __future__ import annotations


class TestReindexHubExports:
    """Spot-check the reindex hub's headline public + infra re-exports."""

    def test_orchestration_entrypoints_importable(self) -> None:
        from beadloom.application.reindex import (
            ReindexResult,
            incremental_reindex,
            reindex,
        )

        assert callable(reindex)
        assert callable(incremental_reindex)
        assert isinstance(ReindexResult, type)

    def test_infra_reexports_bound_on_hub(self) -> None:
        """The infra helpers are re-bound on the hub so ``patch(...)`` here works.

        The ``__init__`` docstring promises ``analyze_git_activity`` /
        ``supported_extensions`` / ``resolve_scan_paths`` are bound at package
        level (so enrichment/change-detection patch them via this namespace).
        """
        import beadloom.application.reindex as rx
        from beadloom.context_oracle.code_indexer import (
            supported_extensions as ce_supported,
        )
        from beadloom.infrastructure.git_activity import (
            analyze_git_activity as ga_analyze,
        )
        from beadloom.infrastructure.scan_paths import (
            resolve_scan_paths as sp_resolve,
        )

        assert rx.analyze_git_activity is ga_analyze
        assert rx.supported_extensions is ce_supported
        assert rx.resolve_scan_paths is sp_resolve
