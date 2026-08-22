# beadloom:domain=application
# beadloom:feature=flow-guards
"""The guard firing record — evidence that a gate actually ran (BDL-061 S1).

A gate that cannot demonstrate it ran is treated as not having run, so every
evaluation the CLI performs appends one JSON line to
``.beadloom/guard-firings.jsonl``. That file is the only thing guards write, and
it is deliberately **not** the index: a check that writes to the artifact it
inspects cannot be trusted about it.

Append-only JSONL rather than a table: an append is atomic enough for parallel
agents (``O_APPEND`` on one line), needs no schema migration, and a corrupt line
costs exactly that line — :func:`read_firings` skips what it cannot parse rather
than failing the report that depends on it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beadloom.application.guards.models import GuardVerdict

#: Where firings are recorded, relative to the project root.
FIRINGS_RELPATH = Path(".beadloom") / "guard-firings.jsonl"


@dataclass(frozen=True)
class FiringRecord:
    """One recorded guard evaluation."""

    guard: str
    outcome: str
    at: str = ""
    why: str = ""


def record_firing(
    project_root: Path, verdict: GuardVerdict, *, at: datetime | None = None
) -> Path:
    """Append *verdict* to the firing record; return the file written."""
    path = project_root / FIRINGS_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    moment = at or datetime.now(timezone.utc)
    payload = {"at": moment.isoformat(), **verdict.to_dict()}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return path


def read_firings(project_root: Path) -> tuple[FiringRecord, ...]:
    """Every parseable firing, oldest first; an absent file reads as no firings."""
    path = project_root / FIRINGS_RELPATH
    if not path.is_file():
        return ()
    records: list[FiringRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        guard = payload.get("guard")
        outcome = payload.get("outcome")
        if not isinstance(guard, str) or not isinstance(outcome, str):
            continue
        records.append(
            FiringRecord(
                guard=guard,
                outcome=outcome,
                at=str(payload.get("at") or ""),
                why=str(payload.get("why") or ""),
            )
        )
    return tuple(records)
