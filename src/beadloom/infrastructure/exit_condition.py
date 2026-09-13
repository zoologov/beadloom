# beadloom:domain=infrastructure
# beadloom:component=exit-condition
"""What retires a declared exclusion: one definition, below everyone who declares one.

Two surfaces require an exit condition and must promise the same thing by it —
``forbid_import.exempt[].until`` in ``rules.yml``, read by the ``graph`` domain,
and ``guards.<name>.exclusions[].until`` in ``flow.yml``, read by
``onboarding``. A third joined them in BDL-070 B2: the same-layer exemptions on
``architecture-layers``.

The definition was written in ``graph/rules/types.py`` because the first of the
surfaces was built first, so ``onboarding`` imported a peer domain to read it —
two of the sixteen same-layer crossings BDL-070 B2 (``beadloom-xmfs``) triaged
were that one import, in ``config_sync`` and ``flow_suppression``. A vocabulary
that two peers share belongs below both of them rather than in whichever one
wrote it down first, which is the same reason :mod:`.scan_paths` and
:mod:`.doc_roots` are here.

Nothing here reads a file, a clock or a database except the clock a caller may
override, so the question "has this deadline passed" is answerable in a test
without a project.
"""

from __future__ import annotations

import re
from datetime import date

#: The one spelling of a deadline an exit condition may lead with, pinned as a
#: pattern rather than delegated to ``date.fromisoformat``: that parser widened
#: in Python 3.11 (``20260101`` and week dates parse there and raise on 3.10),
#: so leaning on it would make the same ``until:`` enforceable on one supported
#: interpreter and prose on another.
_ISO_DATE_PREFIX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:\b|$)")


def exit_condition_deadline(until: str) -> date | None:
    """The calendar date an exit condition names, or ``None`` when it names an event.

    ``until`` answers one question — *what retires this exclusion* — and there are
    two honest answers: a **date** (``2026-09-01``, optionally followed by the
    prose that explains it) and an **event** (``the repository read seam lands``).
    Only the first is checkable, and this function is the single definition of
    which is which, so no two surfaces that require an exit condition can promise
    different things by it.

    A date must LEAD the string: a deadline is the first thing an exit condition
    says, or it is not one. ``some time after 2026-01-01`` is an event.
    """
    match = _ISO_DATE_PREFIX.match(until.strip())
    if match is None:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:  # a well-formed spelling of a day that does not exist
        return None


def deadline_passed(until: str, *, today: date | None = None) -> bool:
    """True when this exit condition names a deadline and that day is behind us.

    The deadline names the last day the exclusion covers, so ``until`` equal to
    today is still live: an exit condition is an intent, and reading it one day
    early would make every entry expire before its author's own deadline. An
    exit condition that names an event never passes here — nothing in a date
    can observe whether the event happened.
    """
    deadline = exit_condition_deadline(until)
    return deadline is not None and deadline < (today or date.today())
