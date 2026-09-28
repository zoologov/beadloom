# beadloom:domain=application
# beadloom:component=mutation-scope
"""The interval a score measured on a random sample supports (BDL-074 D1).

The weekly run mutates a random sample of the declared scope rather than all of
it, because the whole scope did not fit the runner (ten runs killed at about 95
minutes, 2026-09). A score over a sample is an estimate, and an estimate printed
without its interval reads as the whole scope's number.

**Wilson, at 95%, without a finite-population correction.** Wilson because it
stays inside [0, 1] and behaves at the edges, where a kill rate lives: 50 killed
of 50 gives a lower bound under 95% rather than the Wald interval's zero width.
No finite-population correction, because the correction only narrows the
interval, and a sample that is a large share of its population is not what this
run takes; leaving it out makes the stated interval slightly wider than the
sample supports, which is the conservative direction.

The randomness is the runner's claim, not something this module can check. What
it can check is that the sample is no larger than the population it names.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beadloom.application.mutation_scope.score import MutationCounters

#: The two-sided 95% normal quantile.
_Z_95 = 1.959963984540054

#: The confidence the interval is stated at.
CONFIDENCE = 0.95


@dataclass(frozen=True)
class SampleInterval:
    """A score measured on *sample* mutants drawn from *population*, with its interval."""

    population: int
    sample: int
    killed: int
    low: float
    high: float
    confidence: float = CONFIDENCE


def wilson_interval(successes: int, trials: int, z: float = _Z_95) -> tuple[float, float]:
    """The Wilson score interval for *successes* out of *trials*."""
    if trials <= 0:
        msg = "an interval needs at least one trial"
        raise ValueError(msg)
    share = successes / trials
    spread = z * z / trials
    centre = (share + spread / 2) / (1 + spread)
    margin = z * math.sqrt(share * (1 - share) / trials + spread / (4 * trials)) / (1 + spread)
    return max(0.0, centre - margin), min(1.0, centre + margin)


def sample_interval(counters: MutationCounters, *, population: int) -> SampleInterval | None:
    """The interval of the score in *counters*, read as a sample of *population* mutants.

    ``None`` when no mutant was scored: there is no ratio, so there is no
    interval around one. Timeouts count as killed, as they do in the score.
    """
    trials = counters.scored
    if trials == 0:
        return None
    if trials > population:
        msg = (
            f"a sample of {trials} scored mutants cannot be drawn from a population "
            f"of {population}"
        )
        raise ValueError(msg)
    killed = counters.values.get("killed", 0) + counters.values.get("timeout", 0)
    low, high = wilson_interval(killed, trials)
    return SampleInterval(population=population, sample=trials, killed=killed, low=low, high=high)


def describe_sample(interval: SampleInterval) -> str:
    """One sentence naming the sample, its population and the interval."""
    return (
        f"Sample: a random sample of {interval.sample} of {interval.population} "
        f"mutants; {interval.confidence:.0%} interval "
        f"{interval.low * 100:.1f}% to {interval.high * 100:.1f}% (Wilson)"
    )


def sample_payload(interval: SampleInterval) -> dict[str, object]:
    """The interval in the JSON shape the ``mutation`` command prints."""
    return {
        "population": interval.population,
        "sample": interval.sample,
        "killed": interval.killed,
        "confidence": interval.confidence,
        "method": "wilson",
        "low": interval.low,
        "high": interval.high,
    }
