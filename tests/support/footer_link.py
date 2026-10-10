"""The one mention of this repository a portal may carry: the footer's link to it.

BDL-080 S4d (``beadloom-af99.7``). The "Powered by Beadloom" footer links to
Beadloom's own repository on every portal, by the owner's ruling of 2026-10-09,
from its second line since S4e (``beadloom-af99.9``).
A check that no text of this repository reaches an adopter's portal removes that
one address first, and only as this exact address: a path under it, or any other
text of this repository's identity, is still a leak.

Kept apart from :mod:`tests.support.adopter_portals`, which locates the
repository root when it is imported: an acceptance step copied out of the
checkout can import this module where it could not import that one.
"""

from __future__ import annotations

import re

#: Beadloom's own repository, where the footer's second line links.
BEADLOOM_REPOSITORY = "https://github.com/zoologov/beadloom"
_FOOTER_LINK = re.compile(re.escape(BEADLOOM_REPOSITORY) + r"(?![\w./-])")


def without_the_footer_link(text: str) -> str:
    """*text* without the footer's link to Beadloom's repository, the one mention allowed."""
    return _FOOTER_LINK.sub("", text)
