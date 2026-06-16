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
import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# TestLintRecalibrationGuard
# ---------------------------------------------------------------------------


class TestLintRecalibrationGuard:
    """Guard the domain-size-limit recalibration (200 -> 280) on the live repo."""

    def _live_findings(self, repo_root: Path) -> list[dict[str, object]]:
        """Return the live repo's lint findings as parsed JSON.

        Uses ``--no-reindex`` against the session ``live_repo_reindexed`` fixture
        so the shared on-disk DB is NOT re-mutated (keeping order-independence
        under pytest-randomly, per the S1 lesson in conftest).
        """
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["lint", "--format", "json", "--project", str(repo_root), "--no-reindex"],
        )
        # 0 = clean, 1 = violations present (e.g. a warn under --fail-on-warn);
        # here we run neither --strict nor --fail-on-warn, so exit is 0.
        assert result.exit_code in (0, 1), result.output
        payload = json.loads(result.output)
        violations = payload["violations"]
        assert isinstance(violations, list)
        return violations

    def test_live_repo_has_zero_lint_violations(
        self, live_repo_reindexed: Path
    ) -> None:
        """The live repo lints clean: zero violations of ANY rule/severity."""
        findings = self._live_findings(live_repo_reindexed)
        assert findings == [], findings

    def test_no_domain_size_limit_warning(
        self, live_repo_reindexed: Path
    ) -> None:
        """No ``domain-size-limit`` finding — the 280 recalibration holds.

        This is the specific recalibration guard: ``lint --strict`` ignores
        warn-severity findings, so we assert directly that the warn-severity
        ``domain-size-limit`` rule produces nothing over the live graph. A
        regression (a domain crossing 280, or a botched recalibration revert)
        fails HERE rather than slipping past the green exit code.
        """
        findings = self._live_findings(live_repo_reindexed)
        size_findings = [
            f for f in findings if f.get("rule_name") == "domain-size-limit"
        ]
        assert size_findings == [], size_findings

    def test_lint_strict_exit_zero_on_live_repo(
        self, live_repo_reindexed: Path
    ) -> None:
        """``lint --strict`` exits 0 — no error-severity boundary violations."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["lint", "--strict", "--project", str(live_repo_reindexed), "--no-reindex"],
        )
        assert result.exit_code == 0, result.output

    def test_recalibrated_rule_threshold_is_280(self) -> None:
        """The repo's ``domain-size-limit`` rule is loaded as a warn at max 280.

        Pins the recalibrated value at the rule-config level (independent of the
        graph state) so a silent revert to 200 is caught even on a small graph.
        """
        from pathlib import Path as _Path

        from beadloom.graph.rules import CardinalityRule, load_rules

        rules_path = _Path.cwd() / ".beadloom" / "_graph" / "rules.yml"
        rules = load_rules(rules_path)
        size_rules = [
            r
            for r in rules
            if isinstance(r, CardinalityRule) and r.name == "domain-size-limit"
        ]
        assert len(size_rules) == 1
        rule = size_rules[0]
        assert rule.max_symbols == 280
        assert rule.severity == "warn"


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
