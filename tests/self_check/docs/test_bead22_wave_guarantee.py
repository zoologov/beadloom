"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_bead22_wave_guarantee.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

from beadloom.application.waves import (
    SHARED_MEDIA,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


#: The log every shared medium cites its evidence from.
_UX_LOG = REPO_ROOT / ".claude" / "development" / "BDL-UX-Issues.md"


class TestTheSecondClauseCannotBeSilencedWhileAWaveHoldsTwo:
    """Where a medium cannot be made independent, the wave has to say so."""

    def test_every_medium_cites_an_issue_that_exists_in_the_log(self) -> None:
        """TRUE HERE IS NOT TRUE — the evidence has to resolve to a real entry."""
        log = _UX_LOG.read_text(encoding="utf-8")
        # `~~` marks a CLOSED entry, which is still an entry: the citation
        # resolves to a real observation whether or not the defect is fixed.
        # Reading only the open form made closing a cited issue delete the
        # evidence for a medium that is still shared (`beadloom-mr2l.78`).
        numbered = set(re.findall(r"^(\d+)\. (?:~~)?\[", log, flags=re.MULTILINE))
        historical = set(re.findall(r"Opened #(\d+)", log))
        known = numbered | historical
        assert known, "the UX log yielded no entries — the fixture, not the code, is wrong"
        for medium in SHARED_MEDIA:
            cited = re.findall(r"#(\d+)", medium.evidence)
            assert cited, f"{medium.name} cites no issue"
            for number in cited:
                assert number in known, f"{medium.name} cites #{number}, absent from the log"
