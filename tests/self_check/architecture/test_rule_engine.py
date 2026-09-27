"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_rule_engine.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rule_engine import (
    NodeMatcher,
)
from beadloom.infrastructure.db import open_db

if TYPE_CHECKING:
    from pathlib import Path


class TestUnregisteredFeatureCandidateRealRepo:
    """Run the (retired) sprawl-lint against the real Beadloom index (BDL-051 dogfood).

    Slice 1 saw the onboarding modules as domain-only sprawl candidates; Slice 3b
    (BEAD-14) re-modeled them into features (config-check, branch-protection,
    agentic-flow-setup, ai-techwriter-setup). So they must now carry a
    ``# beadloom:feature=`` annotation and NO LONGER be flagged as candidates.
    """

    def test_remodeled_onboarding_modules_no_longer_candidates(
        self, self_check_snapshot: Path
    ) -> None:
        # The self-check snapshot's index, never the live one (BDL-074 A1, A2): read
        # as it happened to be on disk, the answer depended on the last reindex.
        from beadloom.graph.rule_engine import (
            UnregisteredFeatureCandidateRule,
            evaluate_unregistered_feature_candidate_rules,
        )

        conn = open_db(self_check_snapshot / ".beadloom" / "beadloom.db")
        try:
            rules = [
                UnregisteredFeatureCandidateRule(
                    name="unregistered-feature-candidate",
                    description="domain-only modules",
                    for_matcher=NodeMatcher(kind="domain"),
                    min_symbols=5,
                )
            ]
            violations = evaluate_unregistered_feature_candidate_rules(conn, rules)
        finally:
            conn.close()

        flagged = {v.file_path for v in violations}
        remodeled = {
            "src/beadloom/onboarding/config_sync.py",
            "src/beadloom/onboarding/branch_protection.py",
            "src/beadloom/onboarding/agentic_flow_setup.py",
            "src/beadloom/onboarding/ai_techwriter_setup.py",
        }
        # Post-S3b: each re-modeled module is a feature now, so it is NOT a candidate.
        assert flagged.isdisjoint(remodeled), f"still flagged: {flagged & remodeled}"
        # Whatever (if anything) remains is still advisory warn (never fails the build).
        assert all(v.severity == "warn" for v in violations)
