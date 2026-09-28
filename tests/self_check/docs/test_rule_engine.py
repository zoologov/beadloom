"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/integration/graph/rules/test_rule_engine.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import re
from typing import ClassVar

from tests.support.repository_root import REPO_ROOT


class TestTheSpecTableIsCheckedAgainstTheLoader:
    """`rule-engine/SPEC.md` claims its rule-type table is checked against the
    loader's own dispatch. Until BDL-062 `.4` nothing checked it, so the table
    stated a check that did not exist — the defect class BDL-062 is about, in
    the document that describes the rule engine.

    The table went stale twice while claiming otherwise: `.2` added
    `doc_area_coherence` and `.1` added `summary_facts`, and the count in
    `.beadloom/AGENTS.md` read `(unknown)` for three rules at the same time.
    """

    #: Named from this file rather than from the working directory (BDL-074 A1).
    SPEC = (
        REPO_ROOT / "docs/domains/graph/features/rule-engine/SPEC.md"
    )

    #: How the SPEC spells each cardinal it may use for the count. Written out
    #: because a number spelled as a word is invisible to `docs audit`, which is
    #: why this claim needed a test of its own (BDL-UX #196).
    _CARDINALS: ClassVar[dict[int, str]] = {
        9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve",
        13: "Thirteen", 14: "Fourteen", 15: "Fifteen",
    }

    def _keywords_in_table(self) -> set[str]:
        """The `Keyword` column of the rule-type table, read off the document."""
        rows = re.findall(
            r"^\|\s*\*\*[^|]+\*\*\s*\|\s*`([a-z_]+)`\s*\|",
            self.SPEC.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        return set(rows)

    def test_the_table_lists_every_authoring_key_and_no_other(self) -> None:
        from beadloom.graph.rules.loader import AUTHORING_KEYS

        listed = self._keywords_in_table()
        assert listed == set(AUTHORING_KEYS), (
            f"missing from the SPEC table: {sorted(set(AUTHORING_KEYS) - listed)}; "
            f"listed but not accepted by the loader: {sorted(listed - set(AUTHORING_KEYS))}"
        )

    def test_the_stated_count_is_the_number_of_authoring_keys(self) -> None:
        from beadloom.graph.rules.loader import AUTHORING_KEYS

        expected = self._CARDINALS[len(AUTHORING_KEYS)]
        text = self.SPEC.read_text(encoding="utf-8")
        assert f"**{expected}** rule types exist" in text, (
            f"the SPEC does not state {expected} rule types; the loader accepts "
            f"{len(AUTHORING_KEYS)}"
        )
