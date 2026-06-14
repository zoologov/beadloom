# beadloom:domain=ai_agents
# beadloom:feature=ai-techwriter
"""Per-session 429/5xx exponential back-off for the parallel CI agent (S5).

The CI tech-writer drives several Goose sessions concurrently against one
rate-limited model endpoint (the \\$30 plan). A transient ``429 Too Many
Requests`` / ``5xx`` from the provider is NOT a doc problem — it is a
"slow down and retry" signal. :func:`retry_with_backoff` wraps a single
session's work in a bounded exponential back-off so a burst of concurrent
sessions degrades gracefully (each waits a little longer) instead of failing.

The model boundary signals a retryable provider error by raising
:class:`RateLimitError`; anything else propagates unchanged. The ``sleep`` seam
is injected so the policy is deterministic + instant under test (no real wait,
no network) — the harness stays fully seam-mocked.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Default attempt budget for one session (1 initial try + back-off retries).
DEFAULT_BACKOFF_ATTEMPTS = 4
#: Default base delay (seconds) for the exponential schedule (``base * 2**n``).
DEFAULT_BACKOFF_BASE = 1.0
#: Cap any single back-off wait so a long schedule cannot stall the CI job.
DEFAULT_BACKOFF_MAX_DELAY = 30.0


class RateLimitError(RuntimeError):
    """A transient, retryable provider error (HTTP 429 or 5xx).

    The agent seam raises this (instead of a bare :class:`RuntimeError`) when
    the model endpoint reports rate-limiting / a transient server error, so the
    back-off policy can tell "retry after waiting" apart from a genuine failure.
    """


def backoff_delay(attempt: int, *, base: float, max_delay: float) -> float:
    """Exponential delay for a 0-indexed *attempt* (``base * 2**attempt``), capped.

    Deterministic (no jitter) so tests assert the exact schedule; the cap keeps
    a long retry chain from stalling the job past :data:`DEFAULT_BACKOFF_MAX_DELAY`.
    """
    return min(base * (2.0**attempt), max_delay)


def retry_with_backoff(
    call: Callable[[], T],
    *,
    attempts: int = DEFAULT_BACKOFF_ATTEMPTS,
    base: float = DEFAULT_BACKOFF_BASE,
    max_delay: float = DEFAULT_BACKOFF_MAX_DELAY,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run *call*, retrying ONLY on :class:`RateLimitError` with exponential back-off.

    Up to *attempts* total tries (>= 1). On a :class:`RateLimitError` it waits
    :func:`backoff_delay` then retries; the final attempt re-raises so the
    caller (the session worker) handles the give-up. Any non-rate-limit
    exception propagates immediately — back-off is for transient 429/5xx only.

    *sleep* is injected (defaults to :func:`time.sleep`) so the policy is
    instant + deterministic under test.
    """
    budget = max(attempts, 1)
    for attempt in range(budget):
        try:
            return call()
        except RateLimitError as exc:
            if attempt + 1 >= budget:
                raise
            delay = backoff_delay(attempt, base=base, max_delay=max_delay)
            logger.warning(
                "rate-limited (attempt %d/%d), backing off %.1fs: %s",
                attempt + 1,
                budget,
                delay,
                exc,
            )
            sleep(delay)
    # Unreachable: the loop either returns or re-raises on the final attempt.
    msg = "retry_with_backoff: empty attempt budget"
    raise RuntimeError(msg)
