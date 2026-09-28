"""The landing-lock instructions in a set of texts, judged through the one shared grammar."""

from __future__ import annotations

from beadloom.application.waves import (
    LockSite,
    lock_sites,
)
from beadloom.services.bd_seam.assumptions import lock_invocations
from beadloom.services.bd_seam.invocations import text_invocations


def judged_lock_sites(sources: list[tuple[str, str]]) -> tuple[LockSite, ...]:
    """Judge the lock instructions in *sources*, through the one shared grammar.

    `beadloom-0mdo.51` moved the grammar to the seam and left the judgement here,
    so a test that starts from TEXT composes the two the same way the services
    edge does. Composing them here rather than mocking keeps these tests over the
    real path.
    """
    return lock_sites(lock_invocations(text_invocations(sources)))
