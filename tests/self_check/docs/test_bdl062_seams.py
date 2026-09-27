"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/integration/doc_sync/audit/test_bdl062_seams.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import pytest

from beadloom.doc_sync.audit import (
    IgnoreRule,
    _load_ignore_from_config,
)
from beadloom.doc_sync.scanner import DocScanner
from tests.support.repository_root import REPO_ROOT
from tests.support.retired_facts import (
    RETIRED_FACT,
)

#: This repository's root — the only project whose real config is read here.


@pytest.fixture(scope="module")
def repo_mentions() -> list[object]:
    """Every fact mention in this repository's own documentation surface.

    Module-scoped because the scan reads 59 documents and the three tests below
    ask the same question of the same corpus. Measured at 0.42 s for the scan.
    """
    scanner = DocScanner()
    surface = scanner.resolve_surface(REPO_ROOT, None)
    return list(scanner.scan(list(surface.scanned)))


class TestEverySuppressionStillSuppresses:
    """Each ``docs_audit.ignore`` triple this repository declares still matches.

    There is no production check for this. ``compare_facts`` drops a matching
    mention and counts nothing, ``docs audit`` prints nothing about the rules it
    was given, and no gate step reads them — so an ignore triple outlives the
    prose it was written for in complete silence, and the config comment saying
    it was "measured: 0 matching mentions" is the only record that anybody
    looked. Measured at the time of writing: 10 declared triples, 59 documents,
    41 mentions, every triple matching at least one.
    """

    def test_the_corpus_under_test_is_not_empty(self, repo_mentions: list[object]) -> None:
        """A sweep over zero documents would call every suppression inert."""
        assert len(repo_mentions) > 0

    def test_every_declared_triple_matches_at_least_one_mention(
        self, repo_mentions: list[object]
    ) -> None:
        rules = _load_ignore_from_config(REPO_ROOT)
        assert rules, "this repository declares suppressions; the loader read none"

        inert = [
            f"{rule.path} {rule.fact}={rule.value}"
            for rule in rules
            if not any(rule.matches(m) for m in repo_mentions)  # type: ignore[arg-type]
        ]

        assert inert == [], (
            "these suppressions match no mention in this repository — they "
            "silence nothing and read as coverage they do not have: " + str(inert)
        )

    def test_the_sweep_would_notice_a_triple_that_matches_nothing(self) -> None:
        """The guard's own bite, without editing the config it guards."""
        page = REPO_ROOT / "README.md"
        mentions = DocScanner().scan([page])
        retired = IgnoreRule(path="README.md", fact=RETIRED_FACT, value="12")

        assert [m for m in mentions if retired.matches(m)] == []
