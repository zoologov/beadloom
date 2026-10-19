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

**It names its pairs.** Beside the two counts the ledger carries the ``(doc, file)`` pairs it
counted, one per line, so a run whose surface shrank names the pairs it dropped instead of
printing a smaller number (RFC D11 of BDL-083, BDL-UX #353: a Windows checkout counted 167
pairs where the macOS checkout of the same commit counted 347, and nothing said which).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

_LEDGER_FILENAME = "sync-surface.json"

#: A declared pair as the ledger records it: the document, then the code file.
Pair = tuple[str, str]

#: The two ends of a recorded pair: the document, then the code file.
_PAIR_LENGTH = 2

#: How many dropped pairs a message names before it counts the rest. A Windows checkout
#: dropped 180 at once; a message that lists them all is not read.
_NAMED_DROPS = 10


@dataclass(frozen=True)
class SurfaceLedger:
    """The recorded size of the declared documentation surface."""

    declared_pairs: int
    declared_docs: int
    recorded_at: str = ""
    #: The pairs counted, sorted; empty for a ledger recorded before the list existed.
    pairs: tuple[Pair, ...] = ()


@dataclass(frozen=True)
class SurfaceVerdict:
    """What the current surface looks like next to the recorded one.

    ``recorded`` is False when no ledger exists — reported as *not recorded*
    rather than passed over, because an absent record is not a match.

    ``headline`` is the same fact in a few words, for a one-line step summary;
    ``message`` is the actionable form, for a finding. Both, rather than one
    truncated at the call site, because a summary that has to elide the numbers
    prints exactly the count that means nothing.

    ``dropped`` is the recorded pairs the current run does not declare, sorted; empty when the
    ledger holds no pair list or the caller passed none.
    """

    recorded: bool
    shrank: bool
    message: str
    headline: str = ""
    dropped: tuple[Pair, ...] = ()


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
        pairs=_read_pairs(raw.get("pairs")),
    )


def _read_pairs(raw: object) -> tuple[Pair, ...]:
    """The well-formed ``[doc, file]`` entries of *raw*, sorted; anything else is skipped."""
    if not isinstance(raw, list):
        return ()
    return tuple(
        sorted(
            (entry[0], entry[1])
            for entry in raw
            if isinstance(entry, list)
            and len(entry) == _PAIR_LENGTH
            and all(isinstance(part, str) for part in entry)
        )
    )


def write_ledger(
    project_root: Path,
    *,
    declared_pairs: int,
    declared_docs: int,
    recorded_at: str = "",
    pairs: Iterable[Pair] = (),
) -> Path:
    """Record the current surface. Returns the path written.

    ``recorded_at`` is supplied by the caller (never ``now()`` here) so the file
    is byte-stable for a fixed input and a test does not have to reason about
    the clock. *pairs* are written sorted and distinct, one per line.
    """
    path = ledger_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render(declared_pairs, declared_docs, recorded_at, sorted(set(pairs))),
        encoding="utf-8",
    )
    return path


def _render(declared_pairs: int, declared_docs: int, recorded_at: str, pairs: list[Pair]) -> str:
    """The ledger as JSON with its keys sorted and each pair on a line of its own.

    ``json.dumps(indent=2)`` spreads a two-element list over four lines, so a dropped pair
    would read as four removed lines in a diff, none of which names both of its ends.
    """

    def scalar(value: object) -> str:
        return json.dumps(value, ensure_ascii=False)

    rows = [f"    {scalar(list(pair))}" for pair in pairs]
    pair_block = "[\n" + ",\n".join(rows) + "\n  ]" if rows else "[]"
    return (
        "{\n"
        f'  "declared_docs": {scalar(declared_docs)},\n'
        f'  "declared_pairs": {scalar(declared_pairs)},\n'
        f'  "pairs": {pair_block},\n'
        f'  "recorded_at": {scalar(recorded_at)}\n'
        "}\n"
    )


def compare_surface(
    ledger: SurfaceLedger | None,
    *,
    declared_pairs: int,
    declared_docs: int,
    pairs: Iterable[Pair] | None = None,
) -> SurfaceVerdict:
    """Compare the live surface with the recorded one.

    *pairs* are the pairs the current run declares. With them, and with a ledger that
    records its own, the verdict names the recorded pairs the run dropped (``dropped``),
    and a shrunken surface's message lists them.

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
    dropped = (
        tuple(sorted(set(ledger.pairs) - set(pairs)))
        if pairs is not None and ledger.pairs
        else ()
    )
    if declared_pairs < ledger.declared_pairs or declared_docs < ledger.declared_docs:
        return SurfaceVerdict(
            recorded=True,
            shrank=True,
            message=(
                f"declared surface SHRANK since it was recorded: "
                f"{ledger.declared_pairs} → {declared_pairs} pair(s), "
                f"{ledger.declared_docs} → {declared_docs} declared doc(s)"
                f"{_dropped_clause(ledger, dropped)}"
            ),
            headline=(
                f"declared surface SHRANK {ledger.declared_pairs} → {declared_pairs} pair(s)"
            ),
            dropped=dropped,
        )
    if declared_pairs > ledger.declared_pairs or declared_docs > ledger.declared_docs:
        return SurfaceVerdict(
            recorded=True,
            shrank=False,
            dropped=dropped,
            message=(
                f"declared surface grew: {ledger.declared_pairs} → {declared_pairs} "
                f"pair(s), {ledger.declared_docs} → {declared_docs} declared doc(s); "
                f"re-record with `beadloom sync-check --record-surface`"
            ),
            headline=(
                f"declared surface grew {ledger.declared_pairs} → {declared_pairs} pair(s)"
            ),
        )
    return SurfaceVerdict(recorded=True, shrank=False, message="", dropped=dropped)


def _dropped_clause(ledger: SurfaceLedger, dropped: tuple[Pair, ...]) -> str:
    """The sentence a shrunken surface's message ends with: which pairs went, or why unnamed."""
    if not ledger.pairs:
        return (
            "; the ledger records no pair list, so the dropped pairs cannot be named — "
            "re-record it with `beadloom sync-check --record-surface`"
        )
    if not dropped:
        return ""
    named = ", ".join(f"{doc} ↔ {file}" for doc, file in dropped[:_NAMED_DROPS])
    rest = len(dropped) - _NAMED_DROPS
    more = f" and {rest} more" if rest > 0 else ""
    return f"; dropped {len(dropped)} recorded pair(s): {named}{more}"
