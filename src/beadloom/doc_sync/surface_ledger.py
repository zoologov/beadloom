# beadloom:domain=doc-sync
# beadloom:feature=sync-check
"""The declared-surface ledger: how much there was to check, last time.

**Why this module exists.** *Nothing may pass by having less to check.* When a
declared SPEC was deleted, the gate printed ``269 pair(s) fresh`` where the
previous run had printed ``275`` and nothing anywhere mentioned the six that
vanished (BDL-UX #174). The count was the available signal and it was discarded,
because there was nowhere to remember the previous one.

**Where it lives, and why.** Beside the docs, in a COMMITTED file
(``.beadloom/sync-surface.json``) — never in ``.beadloom/beadloom.db``. The
database is a derived cache: git-ignored, per-machine, dropped by every rebuild
and absent on every fresh CI checkout, so a baseline kept there is destroyed by
the very act (a rebuild) that most needs it (BDL-UX #175). A committed ledger
survives a rebuild, travels with the clone, and its changes are reviewable in a
diff like any other claim about the project.

**Recorded only by an explicit act.** ``sync-check --record-surface`` writes it;
no ordinary run does. A check that silently re-records the number it is checking
against re-attests without evidence (BDL-UX #163) and would make the ratchet
decorative — the point of a ratchet is that lowering it is a decision somebody
made on purpose and left in the history.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_LEDGER_FILENAME = "sync-surface.json"


@dataclass(frozen=True)
class SurfaceLedger:
    """The recorded size of the declared documentation surface."""

    declared_pairs: int
    declared_docs: int
    recorded_at: str = ""


@dataclass(frozen=True)
class SurfaceVerdict:
    """What the current surface looks like next to the recorded one.

    ``recorded`` is False when no ledger exists — reported as *not recorded*
    rather than passed over, because an absent record is not a match.

    ``headline`` is the same fact in a few words, for a one-line step summary;
    ``message`` is the actionable form, for a finding. Both, rather than one
    truncated at the call site, because a summary that has to elide the numbers
    prints exactly the count that means nothing.
    """

    recorded: bool
    shrank: bool
    message: str
    headline: str = ""


def ledger_path(project_root: Path) -> Path:
    """Location of the committed ledger."""
    return project_root / ".beadloom" / _LEDGER_FILENAME


def read_ledger(project_root: Path) -> SurfaceLedger | None:
    """Read the ledger, or ``None`` when it is absent or unreadable.

    A malformed ledger reads as absent on purpose: the caller reports "not
    recorded", which is true and actionable, rather than crashing the gate on a
    file whose only job is to hold two integers.
    """
    path = ledger_path(project_root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    pairs = raw.get("declared_pairs")
    docs = raw.get("declared_docs")
    if not isinstance(pairs, int) or not isinstance(docs, int):
        return None
    recorded_at = raw.get("recorded_at")
    return SurfaceLedger(
        declared_pairs=pairs,
        declared_docs=docs,
        recorded_at=recorded_at if isinstance(recorded_at, str) else "",
    )


def write_ledger(
    project_root: Path,
    *,
    declared_pairs: int,
    declared_docs: int,
    recorded_at: str = "",
) -> Path:
    """Record the current surface. Returns the path written.

    ``recorded_at`` is supplied by the caller (never ``now()`` here) so the file
    is byte-stable for a fixed input and a test does not have to reason about
    the clock.
    """
    path = ledger_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "declared_docs": declared_docs,
        "declared_pairs": declared_pairs,
        "recorded_at": recorded_at,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def compare_surface(
    ledger: SurfaceLedger | None,
    *,
    declared_pairs: int,
    declared_docs: int,
) -> SurfaceVerdict:
    """Compare the live surface with the recorded one.

    Three outcomes, and only one of them is silence:

    - **not recorded** — no ledger; say so, because "nothing to compare" is not
      "nothing changed".
    - **shrank** — fewer pairs or fewer declared docs than recorded. Reported
      with BOTH numbers, since the delta is the whole signal.
    - **grew or unchanged** — a growing surface needs no defence; ``message`` is
      empty when it is exactly unchanged, and names the growth otherwise so the
      ledger can be re-recorded deliberately.
    """
    if ledger is None:
        return SurfaceVerdict(
            recorded=False,
            shrank=False,
            message=(
                "declared surface not recorded — run `beadloom sync-check "
                "--record-surface` to record it, so a future run can tell when "
                "the surface shrinks"
            ),
            headline="declared surface not recorded",
        )
    if declared_pairs < ledger.declared_pairs or declared_docs < ledger.declared_docs:
        return SurfaceVerdict(
            recorded=True,
            shrank=True,
            message=(
                f"declared surface SHRANK since it was recorded: "
                f"{ledger.declared_pairs} → {declared_pairs} pair(s), "
                f"{ledger.declared_docs} → {declared_docs} declared doc(s)"
            ),
            headline=(
                f"declared surface SHRANK {ledger.declared_pairs} → {declared_pairs} pair(s)"
            ),
        )
    if declared_pairs > ledger.declared_pairs or declared_docs > ledger.declared_docs:
        return SurfaceVerdict(
            recorded=True,
            shrank=False,
            message=(
                f"declared surface grew: {ledger.declared_pairs} → {declared_pairs} "
                f"pair(s), {ledger.declared_docs} → {declared_docs} declared doc(s); "
                f"re-record with `beadloom sync-check --record-surface`"
            ),
            headline=(
                f"declared surface grew {ledger.declared_pairs} → {declared_pairs} pair(s)"
            ),
        )
    return SurfaceVerdict(recorded=True, shrank=False, message="")
