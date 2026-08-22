# beadloom:domain=application
# beadloom:feature=flow-guards
"""Liveness — which guards are actually doing anything (BDL-061 S1).

Two ways a guard stops protecting anything without anyone noticing: it is
configured off (or excluded everywhere), and it simply never fires. Both are
reported per guard, alongside the firing evidence, by ``beadloom guard
--liveness``.

This module reads; it decides nothing. Whether an idle guard should fail a build
is the Gate's question (S2+), and folding that policy in here would make the
report unusable on a fresh clone, where every guard is legitimately idle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.guards.checks import GUARD_NAMES
from beadloom.application.guards.config import load_guards_config
from beadloom.application.guards.firing import read_firings

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.guards.config import GuardsConfig
    from beadloom.application.guards.firing import FiringRecord


@dataclass(frozen=True)
class GuardLiveness:
    """One guard's liveness row."""

    guard: str
    declared: bool
    strictness: str
    fired_count: int
    never_fired: bool
    excluded_everywhere: bool
    last_fired_at: str = ""
    last_outcome: str = ""

    @property
    def idle(self) -> bool:
        """True when this guard protects nothing right now."""
        return self.never_fired or self.excluded_everywhere

    def to_dict(self) -> dict[str, object]:
        """JSON-ready mapping for ``--liveness --json``."""
        return {
            "guard": self.guard,
            "declared": self.declared,
            "strictness": self.strictness,
            "fired_count": self.fired_count,
            "never_fired": self.never_fired,
            "excluded_everywhere": self.excluded_everywhere,
            "last_fired_at": self.last_fired_at,
            "last_outcome": self.last_outcome,
            "idle": self.idle,
        }


def _row(name: str, config: GuardsConfig, firings: tuple[FiringRecord, ...]) -> GuardLiveness:
    """Build one liveness row from the config and the recorded firings."""
    spec = config.spec_for(name)
    own = [record for record in firings if record.guard == name]
    last = own[-1] if own else None
    return GuardLiveness(
        guard=name,
        declared=spec.declared,
        strictness=spec.strictness_for(None),
        fired_count=len(own),
        never_fired=not own,
        excluded_everywhere=spec.excluded_everywhere(),
        last_fired_at=last.at if last else "",
        last_outcome=last.outcome if last else "",
    )


def build_liveness(project_root: Path) -> tuple[GuardLiveness, ...]:
    """Liveness rows for every registered guard, in deterministic name order."""
    config = load_guards_config(project_root)
    firings = read_firings(project_root)
    return tuple(_row(name, config, firings) for name in GUARD_NAMES)
